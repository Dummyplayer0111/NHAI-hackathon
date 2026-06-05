import { MODEL_VERSION } from "../config";
import { createBiometricEngine } from "./biometricEngine";
import { signPayload } from "./crypto";
import { FaceCaptureSample } from "./faceCapture";
import { AttendanceRecord, DeviceSession, FaceTemplate, LivenessChallenge, VerificationResult } from "../types";

type VerificationInput = {
  challenge: LivenessChallenge;
  faceTemplate: FaceTemplate;
  threshold: number;
  captureSample?: FaceCaptureSample;
};

type SignedRecordInput = {
  session: DeviceSession;
  verification: VerificationResult;
  challenge: LivenessChallenge;
  appVersion: string;
  modelVersion: string;
};

export async function runOfflineVerification(input: VerificationInput): Promise<VerificationResult> {
  return createBiometricEngine().verify({
    challenge: input.challenge,
    faceTemplate: input.faceTemplate,
    threshold: input.threshold,
    faceFrame: input.captureSample?.faceFrame,
    livenessFrames: input.captureSample?.livenessFrames,
    quality: input.captureSample?.quality,
  });
}

export async function createSignedAttendanceRecord(input: SignedRecordInput): Promise<AttendanceRecord> {
  const event = {
    eventId: `evt_${Date.now()}`,
    employeeId: input.session.employeeId,
    deviceId: input.session.deviceId,
    projectId: input.session.projectId,
    timestamp: new Date().toISOString(),
    latitude: 12.9716,
    longitude: 77.5946,
    locationAccuracyMeters: 12,
    faceMatchScore: roundScore(input.verification.faceMatchScore),
    livenessPassed: input.verification.livenessPassed,
    livenessScore: roundScore(input.verification.livenessScore),
    faceQualityPassed: input.verification.faceQualityPassed,
    faceQualityScore: roundScore(input.verification.faceQualityScore),
    faceQualityReasons: input.verification.faceQualityReasons,
    challenge: [input.challenge],
    modelVersion: input.modelVersion || MODEL_VERSION,
    appVersion: input.appVersion,
    biometricEngine: input.verification.engine,
    deviceSequence: Date.now(),
    syncStatus: "pending" as const,
  };

  const signaturePayload = { ...event };
  delete (signaturePayload as Partial<typeof event>).syncStatus;

  return {
    ...event,
    signature: signPayload(signaturePayload, input.session.deviceSecret),
  };
}

function roundScore(value: number): number {
  return Math.round(value * 1000) / 1000;
}
