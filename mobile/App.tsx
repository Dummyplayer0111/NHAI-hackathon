import React, { useEffect, useMemo, useRef, useState } from "react";
import { ActivityIndicator, Alert, Pressable, SafeAreaView, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import NetInfo from "@react-native-community/netinfo";
import { StatusBar } from "expo-status-bar";

import { APP_VERSION, MODEL_VERSION } from "./src/config";
import { downloadOfflineProfile, syncAttendanceBatch } from "./src/services/api";
import { createFaceCaptureAdapter } from "./src/services/faceCapture";
import { createSignedAttendanceRecord, runOfflineVerification } from "./src/services/offlineAuth";
import { deletePurgedRecords, getPendingRecords, loadDeviceSession, saveDeviceSession, savePendingRecord } from "./src/services/storage";
import { AttendanceRecord, DeviceSession, LivenessChallenge, SyncResult } from "./src/types";

declare const __DEV__: boolean;

const demoSession: DeviceSession = {
  employeeId: "EMP102",
  employeeName: "Ramesh",
  projectId: "NH44-PKG07",
  deviceId: "DEVICE123",
  deviceSecret: "demo-device-secret",
  faceTemplate: { embedding: [0.16, 0.22, 0.44, 0.31] },
  faceMatchThreshold: 0.75,
  livenessChallenges: ["blink", "smile", "turn_left", "turn_right"],
};

const challengeLabels: Record<LivenessChallenge, string> = {
  blink: "Blink twice",
  smile: "Smile",
  turn_left: "Turn head left",
  turn_right: "Turn head right",
};

export default function App() {
  const cameraRef = useRef<CameraView | null>(null);
  const [permission, requestPermission] = useCameraPermissions();
  const [online, setOnline] = useState<boolean | null>(null);
  const [session, setSession] = useState<DeviceSession | null>(null);
  const [pending, setPending] = useState<AttendanceRecord[]>([]);
  const [busy, setBusy] = useState(false);
  const [challenge, setChallenge] = useState<LivenessChallenge>("blink");
  const [lastResult, setLastResult] = useState<string>("Ready for offline verification");
  const [setupEmployeeId, setSetupEmployeeId] = useState("");
  const [setupDeviceId, setSetupDeviceId] = useState("");
  const [setupDeviceSecret, setSetupDeviceSecret] = useState("");

  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener((state) => {
      setOnline(Boolean(state.isConnected && state.isInternetReachable !== false));
    });
    return unsubscribe;
  }, []);

  useEffect(() => {
    void hydrate();
  }, []);

  useEffect(() => {
    if (online) {
      void syncPending();
    }
  }, [online]);

  const authStatus = useMemo(() => {
    if (online === null) return "Checking network";
    return online ? "Online sync available" : "Offline field mode";
  }, [online]);

  async function hydrate() {
    const storedSession = await loadDeviceSession();
    if (storedSession) {
      setSession(storedSession);
      setSetupEmployeeId(storedSession.employeeId);
      setSetupDeviceId(storedSession.deviceId);
      setSetupDeviceSecret(storedSession.deviceSecret);
    }
    setPending(await getPendingRecords());
  }

  async function loadDemoProfile() {
    await saveDeviceSession(demoSession);
    setSession(demoSession);
    setLastResult("Demo offline profile stored securely");
  }

  async function refreshProfileFromBackend() {
    const employeeId = session?.employeeId ?? setupEmployeeId.trim();
    const deviceId = session?.deviceId ?? setupDeviceId.trim();
    const deviceSecret = session?.deviceSecret ?? setupDeviceSecret.trim();
    if (!employeeId || !deviceId || !deviceSecret) {
      Alert.alert("Device setup required", "Enter employee ID, device ID, and device secret before downloading from backend.");
      return;
    }
    setBusy(true);
    try {
      const profile = await downloadOfflineProfile(employeeId, deviceId, deviceSecret);
      const updatedSession = {
        employeeId,
        deviceId,
        deviceSecret,
        employeeName: profile.name,
        projectId: profile.projectId,
        faceTemplate: profile.faceTemplate,
        faceMatchThreshold: profile.faceMatchThreshold,
        livenessChallenges: profile.livenessChallenges,
      };
      await saveDeviceSession(updatedSession);
      setSession(updatedSession);
      setLastResult("Offline profile refreshed from backend");
    } catch (error) {
      setLastResult(`Profile download failed: ${(error as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  async function markAttendance() {
    if (!session) {
      Alert.alert("No offline profile", "Load the demo profile or download a registered employee profile first.");
      return;
    }
    setBusy(true);
    try {
      const captureSample = await createFaceCaptureAdapter().capture(challenge, {
        camera: cameraRef.current,
      });
      const verification = await runOfflineVerification({
        challenge,
        faceTemplate: session.faceTemplate,
        threshold: session.faceMatchThreshold,
        captureSample,
      });

      if (!verification.livenessPassed || verification.faceMatchScore < session.faceMatchThreshold) {
        setLastResult(`Rejected offline: score ${verification.faceMatchScore.toFixed(2)}, liveness ${verification.livenessScore.toFixed(2)}, quality ${verification.faceQualityScore.toFixed(2)}`);
        return;
      }

      const record = await createSignedAttendanceRecord({
        session,
        verification,
        challenge,
        appVersion: APP_VERSION,
        modelVersion: MODEL_VERSION,
      });
      await savePendingRecord(record);
      const nextPending = await getPendingRecords();
      setPending(nextPending);
      setLastResult(`Saved offline in ${verification.processingTimeMs}ms via ${verification.engine}: ${record.eventId}`);
    } catch (error) {
      setLastResult(`Verification failed: ${(error as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  async function syncPending() {
    const currentSession = await loadDeviceSession();
    const records = await getPendingRecords();
    if (!currentSession || records.length === 0 || !online) return;

    setBusy(true);
    try {
      const results = await syncAttendanceBatch(records, currentSession.deviceSecret);
      const purgedIds = results.filter((result: SyncResult) => result.purgeAllowed).map((result) => result.eventId);
      await deletePurgedRecords(purgedIds);
      setPending(await getPendingRecords());
      setLastResult(purgedIds.length > 0 ? `Synced and purged ${purgedIds.length} record(s)` : "Sync completed with no purge approvals");
    } catch (error) {
      setLastResult(`Sync waiting: ${(error as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  const challenges = session?.livenessChallenges ?? demoSession.livenessChallenges;

  return (
    <SafeAreaView style={styles.screen}>
      <StatusBar style="light" />
      <View style={styles.header}>
        <View style={styles.brandMark}>
          <MaterialCommunityIcons name="road-variant" size={24} color="#ffffff" />
        </View>
        <View style={styles.headerText}>
          <Text style={styles.appName}>NHAI Datalake 3.0</Text>
          <Text style={styles.subName}>Secure Offline Field Attendance</Text>
        </View>
        <View style={[styles.statusPill, online ? styles.statusOnline : styles.statusOffline]}>
          <Text style={styles.statusText}>{online ? "ONLINE" : "OFFLINE"}</Text>
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.projectBand}>
          <View>
            <Text style={styles.label}>Project</Text>
            <Text style={styles.projectTitle}>{session?.projectId ?? "No project profile"}</Text>
          </View>
          <Text style={styles.modeText}>{authStatus}</Text>
        </View>

        <View style={styles.profilePanel}>
          <View style={styles.profileRow}>
            <InfoBlock label="Employee" value={session ? `${session.employeeName} / ${session.employeeId}` : "Not loaded"} />
            <InfoBlock label="Device" value={session?.deviceId ?? "Not registered"} />
          </View>
          <View style={styles.profileRow}>
            <InfoBlock label="Model" value={`${MODEL_VERSION}`} />
            <InfoBlock label="Target" value="<1s / <20MB" />
          </View>
        </View>

        <View style={styles.setupPanel}>
          <Text style={styles.sectionTitle}>Device Provisioning</Text>
          <View style={styles.inputRow}>
            <TextInput
              value={setupEmployeeId}
              onChangeText={setSetupEmployeeId}
              placeholder="Employee ID"
              autoCapitalize="characters"
              style={styles.input}
              placeholderTextColor="#7890a0"
            />
            <TextInput
              value={setupDeviceId}
              onChangeText={setSetupDeviceId}
              placeholder="Device ID"
              autoCapitalize="characters"
              style={styles.input}
              placeholderTextColor="#7890a0"
            />
          </View>
          <TextInput
            value={setupDeviceSecret}
            onChangeText={setSetupDeviceSecret}
            placeholder="Device secret"
            secureTextEntry
            style={styles.input}
            placeholderTextColor="#7890a0"
          />
        </View>

        <View style={styles.cameraPanel}>
          {permission?.granted ? (
            <CameraView ref={cameraRef} style={styles.camera} facing="front" />
          ) : (
            <View style={styles.cameraFallback}>
              <MaterialCommunityIcons name="camera-off" size={42} color="#31516f" />
              <Text style={styles.cameraFallbackText}>Camera permission is required</Text>
              <PrimaryButton label="Allow Camera" icon="camera" onPress={requestPermission} />
            </View>
          )}
          <View style={styles.faceGuide} pointerEvents="none" />
        </View>

        <View style={styles.challengePanel}>
          <Text style={styles.sectionTitle}>Liveness Challenge</Text>
          <View style={styles.challengeGrid}>
            {challenges.map((item) => (
              <Pressable
                key={item}
                style={[styles.challengeButton, challenge === item && styles.challengeButtonActive]}
                onPress={() => setChallenge(item)}
              >
                <Text style={[styles.challengeText, challenge === item && styles.challengeTextActive]}>
                  {challengeLabels[item]}
                </Text>
              </Pressable>
            ))}
          </View>
          <Text style={styles.promptText}>{challengeLabels[challenge]}</Text>
        </View>

        <View style={styles.actions}>
          <PrimaryButton label="Verify & Mark Attendance" icon="face-recognition" onPress={markAttendance} disabled={busy} />
          <SecondaryButton label="Sync Pending" icon="cloud-upload-outline" onPress={syncPending} disabled={busy || !online} />
        </View>

        <View style={styles.secondaryActions}>
          {__DEV__ ? <SecondaryButton label="Load Demo Profile" icon="account-check-outline" onPress={loadDemoProfile} disabled={busy} /> : null}
          <SecondaryButton label="Refresh Profile" icon="download-outline" onPress={refreshProfileFromBackend} disabled={busy || !online} />
        </View>

        <View style={styles.syncPanel}>
          <View style={styles.syncHeader}>
            <Text style={styles.sectionTitle}>Pending Sync</Text>
            <Text style={styles.pendingCount}>{pending.length}</Text>
          </View>
          {busy ? <ActivityIndicator color="#0f6b4f" /> : null}
          <Text style={styles.resultText}>{lastResult}</Text>
          {pending.slice(0, 4).map((record) => (
            <View key={record.eventId} style={styles.pendingRow}>
              <Text style={styles.pendingId}>{record.eventId}</Text>
              <Text style={styles.pendingMeta}>{record.faceMatchScore.toFixed(2)} / {record.challenge.join(", ")}</Text>
            </View>
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

function InfoBlock({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.infoBlock}>
      <Text style={styles.label}>{label}</Text>
      <Text style={styles.infoValue}>{value}</Text>
    </View>
  );
}

function PrimaryButton({ label, icon, onPress, disabled }: { label: string; icon: keyof typeof MaterialCommunityIcons.glyphMap; onPress: () => void; disabled?: boolean }) {
  return (
    <Pressable style={[styles.primaryButton, disabled && styles.disabled]} onPress={onPress} disabled={disabled}>
      <MaterialCommunityIcons name={icon} size={20} color="#ffffff" />
      <Text style={styles.primaryButtonText}>{label}</Text>
    </Pressable>
  );
}

function SecondaryButton({ label, icon, onPress, disabled }: { label: string; icon: keyof typeof MaterialCommunityIcons.glyphMap; onPress: () => void; disabled?: boolean }) {
  return (
    <Pressable style={[styles.secondaryButton, disabled && styles.disabled]} onPress={onPress} disabled={disabled}>
      <MaterialCommunityIcons name={icon} size={18} color="#17486a" />
      <Text style={styles.secondaryButtonText}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#eef3f1" },
  header: { backgroundColor: "#17486a", paddingHorizontal: 16, paddingVertical: 14, flexDirection: "row", alignItems: "center", gap: 12 },
  brandMark: { width: 40, height: 40, borderRadius: 6, backgroundColor: "#f58220", alignItems: "center", justifyContent: "center" },
  headerText: { flex: 1 },
  appName: { color: "#ffffff", fontSize: 18, fontWeight: "700" },
  subName: { color: "#d9e6ed", fontSize: 12, marginTop: 2 },
  statusPill: { paddingHorizontal: 10, paddingVertical: 6, borderRadius: 4 },
  statusOnline: { backgroundColor: "#0f6b4f" },
  statusOffline: { backgroundColor: "#b54708" },
  statusText: { color: "#ffffff", fontSize: 11, fontWeight: "800" },
  content: { padding: 14, gap: 12, paddingBottom: 30 },
  projectBand: { backgroundColor: "#ffffff", borderLeftColor: "#f58220", borderLeftWidth: 5, padding: 14, borderRadius: 6, flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10 },
  label: { color: "#587082", fontSize: 11, fontWeight: "700", textTransform: "uppercase" },
  projectTitle: { color: "#17364d", fontSize: 17, fontWeight: "800", marginTop: 4 },
  modeText: { color: "#0f6b4f", fontSize: 12, fontWeight: "700", textAlign: "right" },
  profilePanel: { backgroundColor: "#ffffff", borderRadius: 6, padding: 14, gap: 12 },
  profileRow: { flexDirection: "row", gap: 10 },
  infoBlock: { flex: 1 },
  infoValue: { color: "#17364d", fontSize: 14, fontWeight: "700", marginTop: 4 },
  setupPanel: { backgroundColor: "#ffffff", borderRadius: 6, padding: 14, gap: 10 },
  inputRow: { flexDirection: "row", gap: 10 },
  input: { flex: 1, minHeight: 44, borderWidth: 1, borderColor: "#b9c8d3", borderRadius: 6, paddingHorizontal: 12, color: "#17364d", fontSize: 14, fontWeight: "700", backgroundColor: "#f7faf9" },
  cameraPanel: { height: 310, borderRadius: 6, overflow: "hidden", backgroundColor: "#d8e1e6", position: "relative" },
  camera: { flex: 1 },
  cameraFallback: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, padding: 18 },
  cameraFallbackText: { color: "#31516f", fontSize: 14, fontWeight: "700" },
  faceGuide: { position: "absolute", alignSelf: "center", top: 52, width: 190, height: 220, borderRadius: 95, borderWidth: 3, borderColor: "#f58220" },
  challengePanel: { backgroundColor: "#ffffff", borderRadius: 6, padding: 14, gap: 12 },
  sectionTitle: { color: "#17364d", fontSize: 16, fontWeight: "800" },
  challengeGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  challengeButton: { paddingHorizontal: 12, paddingVertical: 10, borderRadius: 4, borderWidth: 1, borderColor: "#b9c8d3", backgroundColor: "#f7faf9" },
  challengeButtonActive: { backgroundColor: "#17486a", borderColor: "#17486a" },
  challengeText: { color: "#17486a", fontSize: 13, fontWeight: "700" },
  challengeTextActive: { color: "#ffffff" },
  promptText: { color: "#b54708", fontSize: 18, fontWeight: "800" },
  actions: { gap: 10 },
  secondaryActions: { flexDirection: "row", gap: 10 },
  primaryButton: { minHeight: 48, borderRadius: 6, backgroundColor: "#0f6b4f", alignItems: "center", justifyContent: "center", flexDirection: "row", gap: 8, paddingHorizontal: 14 },
  primaryButtonText: { color: "#ffffff", fontSize: 15, fontWeight: "800" },
  secondaryButton: { flex: 1, minHeight: 44, borderRadius: 6, backgroundColor: "#ffffff", borderWidth: 1, borderColor: "#b9c8d3", alignItems: "center", justifyContent: "center", flexDirection: "row", gap: 7, paddingHorizontal: 10 },
  secondaryButtonText: { color: "#17486a", fontSize: 13, fontWeight: "800" },
  disabled: { opacity: 0.45 },
  syncPanel: { backgroundColor: "#ffffff", borderRadius: 6, padding: 14, gap: 10 },
  syncHeader: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  pendingCount: { color: "#ffffff", backgroundColor: "#17486a", minWidth: 30, textAlign: "center", paddingVertical: 4, borderRadius: 4, fontWeight: "800" },
  resultText: { color: "#31516f", fontSize: 13, fontWeight: "600" },
  pendingRow: { borderTopWidth: 1, borderTopColor: "#e5ecef", paddingTop: 8, flexDirection: "row", justifyContent: "space-between", gap: 10 },
  pendingId: { color: "#17364d", fontSize: 12, fontWeight: "800" },
  pendingMeta: { color: "#587082", fontSize: 12, fontWeight: "700" },
});
