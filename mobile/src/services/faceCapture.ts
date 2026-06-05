import { MODEL_INPUT_HEIGHT, MODEL_INPUT_WIDTH } from "../constants";
import { ENABLE_PROTOTYPE_BIOMETRIC_ADAPTER } from "../config";
import { NativeModules } from "react-native";
import { LivenessChallenge } from "../types";
import {
  FaceCaptureSample,
  NativeFaceCapturePayload,
  normalizeNativeFaceCapturePayload,
} from "./faceCapturePayload";
import { CameraCaptureSource, captureImageUris } from "./faceCaptureCamera";
import { createReferenceFrames } from "./liveness";

export { FaceCaptureSample, NativeFaceCapturePayload, normalizeNativeFaceCapturePayload };
export { CameraCaptureSource };

export type FaceCaptureOptions = {
  camera?: CameraCaptureSource | null;
};

export interface FaceCaptureAdapter {
  capture(challenge: LivenessChallenge, options?: FaceCaptureOptions): Promise<FaceCaptureSample>;
}

type NativeFaceCaptureModule = {
  captureFaceSample(options: {
    challenge: LivenessChallenge;
    width: number;
    height: number;
    frames: number;
    imageUris: string[];
  }): Promise<NativeFaceCapturePayload>;
};

const nativeFaceCapture = NativeModules.NHAIFaceCapture as NativeFaceCaptureModule | undefined;

class PrototypeFaceCaptureAdapter implements FaceCaptureAdapter {
  async capture(challenge: LivenessChallenge): Promise<FaceCaptureSample> {
    return {
      faceFrame: createNeutralFaceFrame(),
      livenessFrames: createReferenceFrames(challenge),
      quality: {
        facesDetected: 1,
        brightness: 0.58,
        blurScore: 0.82,
        faceBoxRatio: 0.38,
      },
    };
  }
}

class NativeFaceCaptureAdapter implements FaceCaptureAdapter {
  async capture(challenge: LivenessChallenge, options?: FaceCaptureOptions): Promise<FaceCaptureSample> {
    if (!nativeFaceCapture?.captureFaceSample) {
      throw new Error("native_face_capture_not_linked");
    }
    if (!options?.camera) {
      throw new Error("camera_capture_source_required");
    }
    const frames = expectedFrameCount(challenge);
    const imageUris = await captureImageUris(options.camera, frames);
    const payload = await nativeFaceCapture.captureFaceSample({
      challenge,
      width: MODEL_INPUT_WIDTH,
      height: MODEL_INPUT_HEIGHT,
      frames,
      imageUris,
    });
    return normalizeNativeFaceCapturePayload(payload);
  }
}

export function createFaceCaptureAdapter(): FaceCaptureAdapter {
  return ENABLE_PROTOTYPE_BIOMETRIC_ADAPTER
    ? new PrototypeFaceCaptureAdapter()
    : new NativeFaceCaptureAdapter();
}

function createNeutralFaceFrame(): FaceCaptureSample["faceFrame"] {
  const bytes = MODEL_INPUT_WIDTH * MODEL_INPUT_HEIGHT * 3;
  const rgb = new Uint8Array(bytes);
  for (let index = 0; index < bytes; index += 3) {
    rgb[index] = 144;
    rgb[index + 1] = 132;
    rgb[index + 2] = 118;
  }
  return {
    width: MODEL_INPUT_WIDTH,
    height: MODEL_INPUT_HEIGHT,
    rgb,
  };
}

function expectedFrameCount(challenge: LivenessChallenge): number {
  return challenge === "blink" ? 4 : 3;
}
