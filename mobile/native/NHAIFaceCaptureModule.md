# NHAIFaceCapture Native Module Contract

Production builds must provide a React Native native module named `NHAIFaceCapture`.

Reference implementations are provided in:

- `mobile/native/android/NHAIFaceCaptureModule.kt`
- `mobile/native/android/NHAIFaceCapturePackage.kt`
- `mobile/native/ios/NHAIFaceCaptureModule.swift`
- `mobile/native/ios/NHAIFaceCaptureModuleBridge.m`

`mobile/plugins/withNHAIFaceCapture.js` copies and registers these files during Expo prebuild.

The JavaScript adapter calls:

```ts
NativeModules.NHAIFaceCapture.captureFaceSample({
  challenge: "blink" | "smile" | "turn_left" | "turn_right",
  width: 112,
  height: 112,
  frames: 3 | 4,
  imageUris: string[],
});
```

`imageUris` is captured from the active front-camera preview immediately before verification. Blink captures four stills; smile and head-turn challenges capture three stills. Native code must process those images in order.

The native module must return:

```ts
{
  width: 112,
  height: 112,
  rgb: number[] | Uint8Array | string,
  landmarks: FaceLandmarks[],
  quality: {
    facesDetected: number,
    brightness: number,
    blurScore: number,
    faceBoxRatio: number,
  },
}
```

`rgb` must contain `112 * 112 * 3` RGB bytes. If returned as a string, it must be base64 encoded.

Recommended native implementation:

1. Decode each `imageUris` file from the front camera.
2. Detect exactly one face in each frame.
3. Align and crop the best/current face frame to `112x112`.
4. Return RGB bytes in row-major RGB order.
5. Return one landmark set per image URI for blink, smile, and head-turn checks.
6. Return normalized landmarks matching `mobile/src/services/liveness.ts`.
7. Return quality metrics before ONNX inference runs.

The JavaScript boundary validates dimensions, RGB length, landmarks, and quality before calling the ONNX and liveness engines.

## Android Integration Notes

Generate the native Android project with:

```bash
npx expo prebuild --platform android --no-install
```

The config plugin copies the Kotlin files, registers `NHAIFaceCapturePackage`, and adds ML Kit face detection:

```gradle
implementation("com.google.mlkit:face-detection:16.1.7")
```

## iOS Integration Notes

Generate the native iOS project with:

```bash
npx expo prebuild --platform ios --no-install
```

The config plugin copies the Swift and Objective-C bridge files into the app target. The iOS implementation uses the built-in Vision framework, so no third-party detector dependency is required.
