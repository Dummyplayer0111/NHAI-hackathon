import { FaceQualityInput, LivenessChallenge } from "../types";

export type Point = {
  x: number;
  y: number;
};

export type FaceLandmarks = {
  leftEye: Point[];
  rightEye: Point[];
  mouth: Point[];
  noseTip: Point;
  faceCenter: Point;
  faceBox: {
    width: number;
    height: number;
  };
};

export type FaceQualityResult = {
  passed: boolean;
  score: number;
  reasons: string[];
};

export function eyeAspectRatio(eye: Point[]): number {
  if (eye.length < 6) return 0;
  const verticalA = distance(eye[1], eye[5]);
  const verticalB = distance(eye[2], eye[4]);
  const horizontal = distance(eye[0], eye[3]);
  return horizontal === 0 ? 0 : (verticalA + verticalB) / (2 * horizontal);
}

export function mouthSmileRatio(mouth: Point[]): number {
  if (mouth.length < 4) return 0;
  const width = distance(mouth[0], mouth[2]);
  const height = distance(mouth[1], mouth[3]);
  return height === 0 ? 0 : width / height;
}

export function estimateYaw(landmarks: FaceLandmarks): number {
  const halfWidth = landmarks.faceBox.width / 2;
  if (halfWidth === 0) return 0;
  return (landmarks.noseTip.x - landmarks.faceCenter.x) / halfWidth;
}

export function scoreLivenessChallenge(challenge: LivenessChallenge, frames: FaceLandmarks[]): number {
  if (frames.length === 0) return 0;
  switch (challenge) {
    case "blink":
      return scoreBlink(frames);
    case "smile":
      return scoreSmile(frames);
    case "turn_left":
      return scoreHeadTurn(frames, -1);
    case "turn_right":
      return scoreHeadTurn(frames, 1);
  }
}

export function evaluateFaceQuality(input: FaceQualityInput): FaceQualityResult {
  const reasons: string[] = [];
  if (input.facesDetected !== 1) reasons.push("exactly_one_face_required");
  if (input.brightness < 0.28) reasons.push("low_light");
  if (input.brightness > 0.92) reasons.push("harsh_light");
  if (input.blurScore < 0.45) reasons.push("image_blurry");
  if (input.faceBoxRatio < 0.16) reasons.push("face_too_far");
  if (input.faceBoxRatio > 0.72) reasons.push("face_too_close");

  const penalties = reasons.length * 0.18;
  const normalizedBrightness = 1 - Math.min(Math.abs(input.brightness - 0.58) / 0.58, 1);
  const normalizedBlur = clamp(input.blurScore);
  const normalizedDistance = input.faceBoxRatio >= 0.16 && input.faceBoxRatio <= 0.72 ? 1 : 0.25;
  const score = clamp((normalizedBrightness + normalizedBlur + normalizedDistance) / 3 - penalties);

  return {
    passed: reasons.length === 0,
    score,
    reasons,
  };
}

export function createReferenceFrames(challenge: LivenessChallenge): FaceLandmarks[] {
  const neutral = frame({
    eyeOpen: 0.22,
    smileWidth: 2.7,
    yaw: 0,
  });
  if (challenge === "blink") {
    return [
      neutral,
      frame({ eyeOpen: 0.2, smileWidth: 2.7, yaw: 0 }),
      frame({ eyeOpen: 0.05, smileWidth: 2.7, yaw: 0 }),
      frame({ eyeOpen: 0.21, smileWidth: 2.7, yaw: 0 }),
    ];
  }
  if (challenge === "smile") {
    return [
      neutral,
      frame({ eyeOpen: 0.22, smileWidth: 3.2, yaw: 0 }),
      frame({ eyeOpen: 0.22, smileWidth: 4.2, yaw: 0 }),
    ];
  }
  if (challenge === "turn_left") {
    return [neutral, frame({ eyeOpen: 0.22, smileWidth: 2.7, yaw: -0.36 })];
  }
  return [neutral, frame({ eyeOpen: 0.22, smileWidth: 2.7, yaw: 0.36 })];
}

function scoreBlink(frames: FaceLandmarks[]): number {
  const ratios = frames.map((item) => Math.min(eyeAspectRatio(item.leftEye), eyeAspectRatio(item.rightEye)));
  const minRatio = Math.min(...ratios);
  const maxRatio = Math.max(...ratios);
  const closed = minRatio < 0.11;
  const reopened = maxRatio > 0.18;
  return closed && reopened ? 0.94 : clamp((maxRatio - minRatio) / 0.17);
}

function scoreSmile(frames: FaceLandmarks[]): number {
  const ratios = frames.map((item) => mouthSmileRatio(item.mouth));
  const delta = Math.max(...ratios) - Math.min(...ratios);
  return clamp(delta / 1.1);
}

function scoreHeadTurn(frames: FaceLandmarks[], direction: -1 | 1): number {
  const yaws = frames.map(estimateYaw);
  const best = direction === 1 ? Math.max(...yaws) : Math.abs(Math.min(...yaws));
  return clamp(best / 0.32);
}

function frame(options: { eyeOpen: number; smileWidth: number; yaw: number }): FaceLandmarks {
  const eye = (x: number): Point[] => [
    { x: x - 0.2, y: 0 },
    { x: x - 0.1, y: -options.eyeOpen },
    { x: x + 0.1, y: -options.eyeOpen },
    { x: x + 0.2, y: 0 },
    { x: x + 0.1, y: options.eyeOpen },
    { x: x - 0.1, y: options.eyeOpen },
  ];
  return {
    leftEye: eye(-0.35),
    rightEye: eye(0.35),
    mouth: [
      { x: -options.smileWidth / 2, y: 1 },
      { x: 0, y: 0.78 },
      { x: options.smileWidth / 2, y: 1 },
      { x: 0, y: 1.22 },
    ],
    noseTip: { x: options.yaw * 0.5, y: 0.5 },
    faceCenter: { x: 0, y: 0.5 },
    faceBox: { width: 1, height: 1.2 },
  };
}

function distance(a: Point, b: Point): number {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function clamp(value: number): number {
  return Math.max(0, Math.min(1, value));
}
