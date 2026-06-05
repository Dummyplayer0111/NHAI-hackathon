import { MODEL_INPUT_HEIGHT, MODEL_INPUT_WIDTH } from "../constants";
import { FaceFrame, FaceQualityInput } from "../types";
import { FaceLandmarks } from "./liveness";

export type FaceCaptureSample = {
  faceFrame: FaceFrame;
  livenessFrames: FaceLandmarks[];
  quality: FaceQualityInput;
};

export type NativeFaceCapturePayload = {
  width: number;
  height: number;
  rgb: number[] | Uint8Array | string;
  landmarks: FaceLandmarks[];
  quality: FaceQualityInput;
};

export function normalizeNativeFaceCapturePayload(payload: NativeFaceCapturePayload): FaceCaptureSample {
  if (payload.width !== MODEL_INPUT_WIDTH || payload.height !== MODEL_INPUT_HEIGHT) {
    throw new Error("native_face_frame_must_be_112x112_rgb");
  }

  const rgb = decodeRgb(payload.rgb);
  const expectedBytes = MODEL_INPUT_WIDTH * MODEL_INPUT_HEIGHT * 3;
  if (rgb.length !== expectedBytes) {
    throw new Error("native_face_frame_invalid_rgb_length");
  }
  if (!payload.landmarks.length) {
    throw new Error("native_face_landmarks_required");
  }
  validateQuality(payload.quality);

  return {
    faceFrame: {
      width: payload.width,
      height: payload.height,
      rgb,
    },
    livenessFrames: payload.landmarks,
    quality: payload.quality,
  };
}

function decodeRgb(rgb: NativeFaceCapturePayload["rgb"]): Uint8Array {
  if (rgb instanceof Uint8Array) {
    return rgb;
  }
  if (Array.isArray(rgb)) {
    return Uint8Array.from(rgb);
  }
  const base64Decoder = globalThis.atob;
  if (typeof base64Decoder === "function") {
    return Uint8Array.from(base64Decoder(rgb), (char) => char.charCodeAt(0));
  }
  const nodeBuffer = (globalThis as { Buffer?: { from(value: string, encoding: "base64"): Uint8Array } }).Buffer;
  if (nodeBuffer) {
    return Uint8Array.from(nodeBuffer.from(rgb, "base64"));
  }
  throw new Error("native_face_frame_base64_decoder_unavailable");
}

function validateQuality(quality: FaceQualityInput): void {
  const values = [
    quality.facesDetected,
    quality.brightness,
    quality.blurScore,
    quality.faceBoxRatio,
  ];
  if (values.some((value) => !Number.isFinite(value))) {
    throw new Error("native_face_quality_invalid");
  }
}
