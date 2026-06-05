import { APP_VERSION, MODEL_SHA256, MODEL_VERSION } from "../config";
import { BenchmarkReport, DeviceSession, VerificationResult } from "../types";

export function createBenchmarkReport(input: {
  session: DeviceSession;
  deviceInfo: BenchmarkReport["deviceInfo"];
  samples: VerificationResult[];
}): BenchmarkReport {
  if (input.samples.length === 0) {
    throw new Error("benchmark_requires_samples");
  }
  const timings = input.samples
    .map((sample) => sample.processingTimeMs)
    .sort((left, right) => left - right);
  const maxMs = timings[timings.length - 1];
  return {
    employeeId: input.session.employeeId,
    deviceId: input.session.deviceId,
    projectId: input.session.projectId,
    appVersion: APP_VERSION,
    modelVersion: MODEL_VERSION,
    modelSha256: MODEL_SHA256,
    biometricEngine: input.samples.some((sample) => sample.engine === "onnx") ? "onnx" : "prototype",
    deviceInfo: input.deviceInfo,
    iterations: input.samples.length,
    averageMs: round(timings.reduce((sum, value) => sum + value, 0) / timings.length),
    p95Ms: round(timings[Math.floor((timings.length - 1) * 0.95)]),
    maxMs: round(maxMs),
    targetMs: 1000,
    withinTarget: maxMs < 1000,
    capturedAt: new Date().toISOString(),
  };
}

function round(value: number): number {
  return Math.round(value * 1000) / 1000;
}
