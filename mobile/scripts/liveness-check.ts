import {
  createReferenceFrames,
  evaluateFaceQuality,
  scoreLivenessChallenge,
} from "../src/services/liveness";

function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(message);
  }
}

for (const challenge of ["blink", "smile", "turn_left", "turn_right"] as const) {
  const score = scoreLivenessChallenge(challenge, createReferenceFrames(challenge));
  assert(score >= 0.7, `${challenge} score too low: ${score}`);
}

const goodQuality = evaluateFaceQuality({
  facesDetected: 1,
  brightness: 0.58,
  blurScore: 0.82,
  faceBoxRatio: 0.38,
});
assert(goodQuality.passed, "good face quality should pass");

const badQuality = evaluateFaceQuality({
  facesDetected: 2,
  brightness: 0.12,
  blurScore: 0.2,
  faceBoxRatio: 0.08,
});
assert(!badQuality.passed, "bad face quality should fail");

console.log("liveness checks passed");
