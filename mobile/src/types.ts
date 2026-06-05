export type LivenessChallenge = "blink" | "smile" | "turn_left" | "turn_right";

export type FaceTemplate = {
  embedding?: number[];
  encryptedEmbedding?: string;
  [key: string]: unknown;
};

export type FaceFrame = {
  width: number;
  height: number;
  rgb: Uint8Array;
};

export type FaceQualityInput = {
  facesDetected: number;
  brightness: number;
  blurScore: number;
  faceBoxRatio: number;
};

export type DeviceSession = {
  employeeId: string;
  employeeName: string;
  projectId: string;
  deviceId: string;
  deviceSecret: string;
  faceTemplate: FaceTemplate;
  faceMatchThreshold: number;
  livenessChallenges: LivenessChallenge[];
};

export type OfflineProfileResponse = {
  employeeId: string;
  name: string;
  projectId: string;
  deviceId: string;
  faceTemplate: FaceTemplate;
  faceMatchThreshold: number;
  model: {
    name?: string;
    version?: string;
    sha256?: string;
    sizeMb?: number;
    withinTargetSize?: boolean;
    [key: string]: unknown;
  };
  livenessChallenges: LivenessChallenge[];
};

export type VerificationResult = {
  faceMatchScore: number;
  livenessPassed: boolean;
  livenessScore: number;
  faceQualityPassed: boolean;
  faceQualityScore: number;
  faceQualityReasons: string[];
  processingTimeMs: number;
  engine: "prototype" | "onnx";
};

export type AttendanceRecord = {
  eventId: string;
  employeeId: string;
  deviceId: string;
  projectId: string;
  timestamp: string;
  latitude: number;
  longitude: number;
  locationAccuracyMeters: number;
  faceMatchScore: number;
  livenessPassed: boolean;
  livenessScore: number;
  faceQualityPassed: boolean;
  faceQualityScore: number;
  faceQualityReasons: string[];
  challenge: LivenessChallenge[];
  modelVersion: string;
  appVersion: string;
  biometricEngine: "prototype" | "onnx";
  deviceSequence: number;
  syncStatus: "pending";
  signature: string;
};

export type SyncResult = {
  eventId: string;
  status: "success" | "rejected";
  serverAckId?: string;
  purgeAllowed: boolean;
  reason?: string;
};

export type DeviceInfo = {
  platform: string;
  osVersion: string;
  model: string;
  ramGb?: number;
};

export type BenchmarkReport = {
  employeeId: string;
  deviceId: string;
  projectId: string;
  appVersion: string;
  modelVersion: string;
  modelSha256: string;
  biometricEngine: "prototype" | "onnx";
  deviceInfo: DeviceInfo;
  iterations: number;
  averageMs: number;
  p95Ms: number;
  maxMs: number;
  targetMs: number;
  withinTarget: boolean;
  capturedAt: string;
};

export type BenchmarkSyncResponse = {
  status: "success" | "rejected";
  benchmarkId?: string;
  accepted: boolean;
  reason?: string;
};
