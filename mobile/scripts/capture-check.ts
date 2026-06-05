import { MODEL_INPUT_HEIGHT, MODEL_INPUT_WIDTH } from "../src/constants";
import { captureImageUris } from "../src/services/faceCaptureCamera";
import { normalizeNativeFaceCapturePayload } from "../src/services/faceCapturePayload";
import { createReferenceFrames } from "../src/services/liveness";

function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(message);
  }
}

async function main(): Promise<void> {
  const nativePayload = {
    width: MODEL_INPUT_WIDTH,
    height: MODEL_INPUT_HEIGHT,
    rgb: new Uint8Array(MODEL_INPUT_WIDTH * MODEL_INPUT_HEIGHT * 3),
    landmarks: createReferenceFrames("blink"),
    quality: {
      facesDetected: 1,
      brightness: 0.58,
      blurScore: 0.82,
      faceBoxRatio: 0.38,
    },
  };
  const sample = normalizeNativeFaceCapturePayload(nativePayload);
  assert(sample.faceFrame.width === MODEL_INPUT_WIDTH, "invalid frame width");
  assert(sample.faceFrame.height === MODEL_INPUT_HEIGHT, "invalid frame height");
  assert(sample.faceFrame.rgb.length === MODEL_INPUT_WIDTH * MODEL_INPUT_HEIGHT * 3, "invalid RGB frame length");
  assert(sample.livenessFrames.length > 0, "missing liveness frames");
  assert(sample.quality.facesDetected === 1, "expected one face in prototype sample");

  try {
    normalizeNativeFaceCapturePayload({ ...nativePayload, width: MODEL_INPUT_WIDTH - 1 });
    throw new Error("expected invalid native frame width to fail");
  } catch (error) {
    assert((error as Error).message === "native_face_frame_must_be_112x112_rgb", "unexpected native frame validation error");
  }

  let captures = 0;
  const imageUris = await captureImageUris({
    async takePictureAsync() {
      captures += 1;
      return { uri: `file:///capture-${captures}.jpg` };
    },
  }, 4);
  assert(captures === 4, "expected four capture frames for blink");
  assert(imageUris[3] === "file:///capture-4.jpg", "invalid capture URI order");

  try {
    await captureImageUris({
      async takePictureAsync() {
        return {};
      },
    }, 1);
    throw new Error("expected missing camera URI to fail");
  } catch (error) {
    assert((error as Error).message === "camera_capture_uri_missing", "unexpected camera URI validation error");
  }
  console.log("capture checks passed");
}

void main();
