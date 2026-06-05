import { ENABLE_PROTOTYPE_BIOMETRIC_ADAPTER } from "../config";
import { createReferenceFrames, evaluateFaceQuality, scoreLivenessChallenge } from "./liveness";
import { runOnnxFaceMatch } from "./onnxFaceEngine";
import { FaceFrame, FaceQualityInput, FaceTemplate, LivenessChallenge, VerificationResult } from "../types";
import { FaceLandmarks } from "./liveness";

export type BiometricEngineInput = {
  challenge: LivenessChallenge;
  faceTemplate: FaceTemplate;
  threshold: number;
  faceFrame?: FaceFrame;
  livenessFrames?: FaceLandmarks[];
  quality?: FaceQualityInput;
};

export interface BiometricEngine {
  verify(input: BiometricEngineInput): Promise<VerificationResult>;
}

class PrototypeBiometricEngine implements BiometricEngine {
  async verify(input: BiometricEngineInput): Promise<VerificationResult> {
    const started = Date.now();
    const embeddingSize = Array.isArray(input.faceTemplate.embedding) ? input.faceTemplate.embedding.length : 128;
    const faceMatchScore = embeddingSize > 0 ? Math.max(input.threshold, 0.82) : 0;
    const quality = evaluateFaceQuality(input.quality ?? {
      facesDetected: 1,
      brightness: 0.58,
      blurScore: 0.82,
      faceBoxRatio: 0.38,
    });
    const livenessScore = scoreLivenessChallenge(
      input.challenge,
      input.livenessFrames ?? createReferenceFrames(input.challenge),
    );
    await wait(220);
    return {
      faceMatchScore,
      livenessPassed: livenessScore >= 0.7 && quality.passed,
      livenessScore,
      faceQualityPassed: quality.passed,
      faceQualityScore: quality.score,
      faceQualityReasons: quality.reasons,
      processingTimeMs: Date.now() - started,
      engine: "prototype",
    };
  }
}

class NativeModelBiometricEngine implements BiometricEngine {
  async verify(input: BiometricEngineInput): Promise<VerificationResult> {
    const started = Date.now();
    if (!input.faceFrame) {
      throw new Error("face_frame_required_for_onnx_engine");
    }
    if (!input.livenessFrames || !input.quality) {
      throw new Error("liveness_frames_and_quality_required_for_onnx_engine");
    }
    const quality = evaluateFaceQuality(input.quality);
    const [faceMatchScore, livenessScore] = await Promise.all([
      runOnnxFaceMatch({
        faceFrame: input.faceFrame,
        faceTemplate: input.faceTemplate,
      }),
      Promise.resolve(scoreLivenessChallenge(input.challenge, input.livenessFrames)),
    ]);
    return {
      faceMatchScore,
      livenessPassed: livenessScore >= 0.7 && quality.passed,
      livenessScore,
      faceQualityPassed: quality.passed,
      faceQualityScore: quality.score,
      faceQualityReasons: quality.reasons,
      processingTimeMs: Date.now() - started,
      engine: "onnx",
    };
  }
}

export function createBiometricEngine(): BiometricEngine {
  return ENABLE_PROTOTYPE_BIOMETRIC_ADAPTER
    ? new PrototypeBiometricEngine()
    : new NativeModelBiometricEngine();
}

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
