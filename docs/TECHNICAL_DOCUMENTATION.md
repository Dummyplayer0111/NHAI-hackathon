# Technical Documentation

## Architecture

Online setup:

1. Employee is enrolled on server with employee details, project ID, and face template.
2. Device is registered against employee and project.
3. Backend returns a device secret once. The app stores it securely.
4. App downloads offline profile and stores the encrypted face template locally.

Offline authentication:

1. App detects no network and stays fully offline.
2. Camera captures face frames.
3. Face quality is checked locally.
4. Random liveness challenge is shown locally.
5. App computes face embedding locally.
6. App compares embedding with stored face template.
7. App creates pending attendance event.
8. App signs event payload with HMAC-SHA256.
9. App includes monotonic `deviceSequence`, face-quality evidence, GPS accuracy, and biometric engine evidence.
10. App stores event in encrypted local storage.

Online sync:

1. App detects network restoration.
2. App posts pending event(s) to FastAPI.
3. Backend verifies trust rules and HMAC.
4. Backend stores accepted logs in MongoDB.
5. Backend returns `purgeAllowed: true`.
6. App deletes only acknowledged local records.
7. App can post signed/authenticated benchmark evidence to `/sync/benchmark`.

## Model

- Name: MobileFaceNet
- File: `MobileFaceNet.onnx`
- Current size: about 3.8 MB
- SHA-256: `6a2722edc8168a7ac3dcb2c21f5649654f8089ab6ee43c59a0a5ddcffca1f726`
- Target size: under 20 MB
- Input: `112x112` RGB face crop
- Output: face embedding
- Matching: cosine similarity

## Backend Stack

- FastAPI
- Pydantic
- PyMongo
- MongoDB
- HMAC-SHA256 for signed offline logs

## Mobile Integration Notes

Implemented mobile prototype:

- App root: `mobile/App.tsx`
- Secure storage: `mobile/src/services/storage.ts`
- HMAC signing: `mobile/src/services/crypto.ts`
- Backend sync: `mobile/src/services/api.ts`
- Benchmark report assembly: `mobile/src/services/benchmark.ts`
- Biometric adapter boundary: `mobile/src/services/biometricEngine.ts`
- ONNX Runtime MobileFaceNet adapter: `mobile/src/services/onnxFaceEngine.ts`
- Face crop and landmark capture boundary: `mobile/src/services/faceCapture.ts`
- Front-camera still burst capture: `mobile/src/services/faceCaptureCamera.ts`
- Native face-capture payload validation: `mobile/src/services/faceCapturePayload.ts`
- Android/iOS native module contract: `mobile/native/NHAIFaceCaptureModule.md`
- Expo native integration plugin: `mobile/plugins/withNHAIFaceCapture.js`
- Android native detector reference: `mobile/native/android/NHAIFaceCaptureModule.kt`
- iOS native detector reference: `mobile/native/ios/NHAIFaceCaptureModule.swift`
- Liveness and face-quality scoring: `mobile/src/services/liveness.ts`
- Offline record assembly: `mobile/src/services/offlineAuth.ts`

Recommended open-source production path:

- Camera: `expo-camera` for prototype or `react-native-vision-camera` for lower-level frame processors
- Model runtime: `onnxruntime-react-native` is wired through `mobile/src/services/onnxFaceEngine.ts`
- Production camera integration: implement the `NHAIFaceCapture` Android/iOS native module behind `mobile/src/services/faceCapture.ts`
- Secure storage: platform keystore/keychain backed encrypted storage
- Local pending queue: platform secure storage for prototype; encrypted SQLite/MMKV for high-volume production queues
- Network listener: React Native NetInfo

## Backend Environment

```bash
export MONGODB_URI="mongodb://localhost:27017"
export MONGODB_DB_NAME="attendance_db"
export FACE_MATCH_THRESHOLD="0.75"
export LIVENESS_SCORE_THRESHOLD="0.70"
export MAX_OFFLINE_EVENT_AGE_HOURS="72"
```

## Benchmark Table Template

| Metric | Target | Current Evidence |
| --- | --- | --- |
| Model size | <= 20 MB | 3.8 MB ONNX file |
| Recognition + liveness time | < 1000 ms | Needs RN device benchmark |
| Android support | 8.0+ | Needs RN app test |
| iOS support | 12+ | Needs RN app test |
| RAM | 3 GB+ | Needs RN app test |
| Accuracy | > 95% | Needs dataset benchmark |

## Automated Readiness Report

Run this with the FastAPI backend online:

```bash
.venv/bin/python scripts/generate_submission_report.py
```

The generated report is stored at `reports/submission-readiness.json` and captures model size, model checksum, API health, backend tests, mobile TypeScript status, mobile liveness algorithm checks, mobile dependency audit, Expo dependency compatibility, and Expo production config.
