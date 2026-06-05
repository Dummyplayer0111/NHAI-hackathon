import * as SecureStore from "expo-secure-store";

import { AttendanceRecord, DeviceSession } from "../types";

const SESSION_KEY = "nhai.device.session";
const PENDING_KEY = "nhai.pending.attendance";

export async function saveDeviceSession(session: DeviceSession): Promise<void> {
  await SecureStore.setItemAsync(SESSION_KEY, JSON.stringify(session), {
    keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
  });
}

export async function loadDeviceSession(): Promise<DeviceSession | null> {
  const value = await SecureStore.getItemAsync(SESSION_KEY);
  return value ? (JSON.parse(value) as DeviceSession) : null;
}

export async function getPendingRecords(): Promise<AttendanceRecord[]> {
  const value = await SecureStore.getItemAsync(PENDING_KEY);
  return value ? (JSON.parse(value) as AttendanceRecord[]) : [];
}

export async function savePendingRecord(record: AttendanceRecord): Promise<void> {
  const records = await getPendingRecords();
  await SecureStore.setItemAsync(PENDING_KEY, JSON.stringify([...records, record]), {
    keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
  });
}

export async function deletePurgedRecords(eventIds: string[]): Promise<void> {
  if (eventIds.length === 0) return;
  const records = await getPendingRecords();
  const keep = records.filter((record) => !eventIds.includes(record.eventId));
  await SecureStore.setItemAsync(PENDING_KEY, JSON.stringify(keep), {
    keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
  });
}
