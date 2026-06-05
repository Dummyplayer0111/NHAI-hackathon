import { API_BASE_URL, MODEL_SHA256, MODEL_VERSION } from "../config";
import { AttendanceRecord, BenchmarkReport, BenchmarkSyncResponse, OfflineProfileResponse, SyncResult } from "../types";

async function parseJson(response: Response) {
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail ?? `HTTP ${response.status}`);
  }
  return body;
}

export async function downloadOfflineProfile(employeeId: string, deviceId: string, deviceSecret: string): Promise<OfflineProfileResponse> {
  const response = await fetch(`${API_BASE_URL}/offline-profile/${encodeURIComponent(employeeId)}?deviceId=${encodeURIComponent(deviceId)}`, {
    headers: { "X-Device-Secret": deviceSecret },
  });
  const profile = await parseJson(response) as OfflineProfileResponse;
  if (profile.model.version !== MODEL_VERSION) {
    throw new Error("backend_model_version_mismatch");
  }
  if (profile.model.sha256 !== MODEL_SHA256) {
    throw new Error("backend_model_checksum_mismatch");
  }
  if (profile.model.withinTargetSize !== true) {
    throw new Error("backend_model_size_exceeds_target");
  }
  return profile;
}

export async function syncAttendanceBatch(records: AttendanceRecord[], deviceSecret: string): Promise<SyncResult[]> {
  const response = await fetch(`${API_BASE_URL}/sync/attendance/batch`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Device-Secret": deviceSecret,
    },
    body: JSON.stringify({ events: records }),
  });
  const body = await parseJson(response);
  return body.results as SyncResult[];
}

export async function syncBenchmarkReport(report: BenchmarkReport, deviceSecret: string): Promise<BenchmarkSyncResponse> {
  const response = await fetch(`${API_BASE_URL}/sync/benchmark`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Device-Secret": deviceSecret,
    },
    body: JSON.stringify(report),
  });
  return parseJson(response) as Promise<BenchmarkSyncResponse>;
}
