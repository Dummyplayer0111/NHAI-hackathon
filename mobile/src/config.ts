import Constants from "expo-constants";
export {
  MODEL_EMBEDDING_SIZE,
  MODEL_INPUT_HEIGHT,
  MODEL_INPUT_WIDTH,
  MODEL_SHA256,
  MODEL_VERSION,
} from "./constants";

const extra = Constants.expoConfig?.extra ?? {};

export const API_BASE_URL = String(extra.apiBaseUrl ?? "http://127.0.0.1:8000");
export const APP_VERSION = String(extra.appVersion ?? "1.0.0");
export const ENABLE_PROTOTYPE_BIOMETRIC_ADAPTER = Boolean(extra.enablePrototypeBiometricAdapter);
