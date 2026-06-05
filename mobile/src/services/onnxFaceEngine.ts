import { Asset } from "expo-asset";
import { Directory, File, Paths } from "expo-file-system";
import * as ort from "onnxruntime-react-native";

import { MODEL_EMBEDDING_SIZE, MODEL_INPUT_HEIGHT, MODEL_INPUT_WIDTH } from "../constants";
import { FaceFrame, FaceTemplate } from "../types";

const modelAsset = require("../../assets/models/MobileFaceNet.onnx");

export type OnnxFaceEngineInput = {
  faceFrame: FaceFrame;
  faceTemplate: FaceTemplate;
};

let sessionPromise: Promise<ort.InferenceSession> | null = null;

export async function runOnnxFaceMatch(input: OnnxFaceEngineInput): Promise<number> {
  const reference = input.faceTemplate.embedding;
  if (!reference || reference.length === 0) {
    throw new Error("missing_face_template_embedding");
  }

  const session = await getSession();
  const tensor = preprocessFaceFrame(input.faceFrame);
  const feeds: Record<string, ort.Tensor> = {
    [session.inputNames[0]]: tensor,
  };
  const output = await session.run(feeds);
  const firstOutput = output[session.outputNames[0]];
  const embedding = Array.from(firstOutput.data as Float32Array);
  return cosineSimilarity(normalize(embedding), normalize(reference));
}

async function getSession(): Promise<ort.InferenceSession> {
  if (!sessionPromise) {
    sessionPromise = loadModelUri().then((uri) => ort.InferenceSession.create(uri));
  }
  return sessionPromise;
}

async function loadModelUri(): Promise<string> {
  const asset = Asset.fromModule(modelAsset);
  await asset.downloadAsync();
  const localUri = asset.localUri ?? asset.uri;
  if (!localUri) {
    throw new Error("model_asset_unavailable");
  }
  if (localUri.startsWith("file://")) {
    return localUri;
  }
  const file = await File.downloadFileAsync(
    localUri,
    new Directory(Paths.cache),
    { idempotent: true },
  );
  return file.uri;
}

function preprocessFaceFrame(frame: FaceFrame): ort.Tensor {
  if (frame.width !== MODEL_INPUT_WIDTH || frame.height !== MODEL_INPUT_HEIGHT) {
    throw new Error("face_frame_must_be_112x112_rgb");
  }
  const expectedBytes = MODEL_INPUT_WIDTH * MODEL_INPUT_HEIGHT * 3;
  if (frame.rgb.length !== expectedBytes) {
    throw new Error("invalid_face_frame_rgb_length");
  }

  const chw = new Float32Array(expectedBytes);
  const plane = MODEL_INPUT_WIDTH * MODEL_INPUT_HEIGHT;
  for (let index = 0; index < plane; index += 1) {
    const rgbIndex = index * 3;
    chw[index] = (frame.rgb[rgbIndex] - 127.5) / 128.0;
    chw[plane + index] = (frame.rgb[rgbIndex + 1] - 127.5) / 128.0;
    chw[2 * plane + index] = (frame.rgb[rgbIndex + 2] - 127.5) / 128.0;
  }
  return new ort.Tensor("float32", chw, [1, 3, MODEL_INPUT_HEIGHT, MODEL_INPUT_WIDTH]);
}

function normalize(values: number[]): number[] {
  const magnitude = Math.sqrt(values.reduce((sum, value) => sum + value * value, 0));
  if (magnitude === 0) return values.slice(0, MODEL_EMBEDDING_SIZE);
  return values.slice(0, MODEL_EMBEDDING_SIZE).map((value) => value / magnitude);
}

function cosineSimilarity(left: number[], right: number[]): number {
  const length = Math.min(left.length, right.length);
  let dot = 0;
  let leftNorm = 0;
  let rightNorm = 0;
  for (let index = 0; index < length; index += 1) {
    dot += left[index] * right[index];
    leftNorm += left[index] * left[index];
    rightNorm += right[index] * right[index];
  }
  if (leftNorm === 0 || rightNorm === 0) return 0;
  return dot / (Math.sqrt(leftNorm) * Math.sqrt(rightNorm));
}
