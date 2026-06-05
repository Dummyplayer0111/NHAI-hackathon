# Hackathon Compliance Check

Title: Develop a mobile based secure offline facial recognition and liveness detection system for remote locations.

## Current Status

This repository now includes a FastAPI/MongoDB backend, Python ML proof-of-concept, and React Native/Expo mobile prototype. The mobile app demonstrates the full offline-to-online flow with secure local storage, liveness challenge UI, signed pending records, and sync/purge behavior.

## Requirement Mapping

| Requirement | Current Implementation | Status |
| --- | --- | --- |
| Offline facial recognition | `recognize.py` performs local face embedding and cosine comparison using `MobileFaceNet.onnx`; `mobile/src/services/onnxFaceEngine.ts` implements the React Native ONNX Runtime adapter and MobileFaceNet preprocessing; `mobile/src/services/faceCapture.ts` captures a front-camera image burst, calls the `NHAIFaceCapture` native bridge, and validates returned 112x112 RGB crops. | Production adapter and bridge contract implemented; platform detector module/device validation required |
| Offline liveness detection | Mobile UI supports blink, smile, turn-left, and turn-right challenges; `mobile/src/services/liveness.ts` implements EAR blink, smile ratio, yaw, and face-quality scoring; backend validates challenge, liveness flag, liveness score, and face quality; `mobile/src/services/faceCaptureCamera.ts` captures challenge frames; `mobile/src/services/faceCapturePayload.ts` validates native landmark payloads. | Core algorithm, camera burst, and native payload validation implemented; native camera landmark extraction required for production |
| React Native Android+iOS compatibility | `mobile/` contains an Expo React Native app configured for Android and iOS. | Implemented as prototype |
| Model under about 20 MB | `MobileFaceNet.onnx` is about 3.8 MB. `/model/metadata` reports this. | Meets target |
| Recognition plus liveness under 1 second | `/system/requirements` exposes the target; `/sync/benchmark` stores authenticated device benchmark evidence; readiness report captures liveness benchmark. | Automated benchmark evidence implemented; physical Android/iOS benchmark still required |
| Mid-range device support | Requirements documented: Android 8+, iOS 12+, 3 GB RAM; `/sync/benchmark` can store device evidence. | Needs physical mobile benchmark capture |
| Open-source tech only | FastAPI, MongoDB driver, ONNX Runtime path, OpenCV/MediaPipe Python prototype. | Meets backend/prototype intent |
| Sync and purge | `POST /sync/attendance` and `/sync/attendance/batch` return `purgeAllowed: true` only after validated MongoDB insert. | Implemented |
| Duplicate/fake log rejection | Backend rejects duplicate event IDs, project mismatch, device mismatch, bad timestamp, low face/liveness score, invalid HMAC. | Implemented |
| AWS server scope | FastAPI app can be deployed on AWS EC2/ECS/Elastic Beanstalk with MongoDB Atlas or self-hosted MongoDB. | Backend ready |
| Technical documentation | `README.md`, `docs/TECHNICAL_DOCUMENTATION.md`, `docs/SECURITY_AND_PRODUCTION_READINESS.md`, and this compliance file. | Implemented |
| Presentation/PDF | `docs/PRESENTATION_OUTLINE.md` provides the slide structure. | Outline implemented; final PPT/PDF export still needed |

## Backend Role

The backend is not the offline AI engine. It is the online trust system:

1. Enroll employee and store face template.
2. Register employee device and issue device secret.
3. Send offline profile and model constraints to the app.
4. Receive signed attendance records after network returns.
5. Verify employee, device, project, timestamp, score, liveness, model version, duplicate event ID, and HMAC signature.
6. Store accepted logs in MongoDB.
7. Return purge permission.

## Remaining Work For Full Hackathon Submission

1. Implement the Android/iOS `NHAIFaceCapture` native module described in `mobile/native/NHAIFaceCaptureModule.md`.
2. Benchmark on mid-range Android and iOS devices:
   - model size
   - inference time
   - liveness time
   - total authentication time
   - memory usage
   - accuracy/FAR/FRR across outdoor lighting
3. Prepare final PPT/PDF with architecture, model details, benchmarks, demo flow, and limitations.
