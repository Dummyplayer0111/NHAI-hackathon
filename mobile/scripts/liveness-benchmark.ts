import { performance } from "perf_hooks";
import { writeFileSync, mkdirSync } from "fs";
import { join } from "path";

import {
  createReferenceFrames,
  evaluateFaceQuality,
  scoreLivenessChallenge,
} from "../src/services/liveness";

const iterations = 1000;
const challenges = ["blink", "smile", "turn_left", "turn_right"] as const;
const timings: number[] = [];

for (let index = 0; index < iterations; index += 1) {
  const started = performance.now();
  for (const challenge of challenges) {
    scoreLivenessChallenge(challenge, createReferenceFrames(challenge));
  }
  evaluateFaceQuality({
    facesDetected: 1,
    brightness: 0.58,
    blurScore: 0.82,
    faceBoxRatio: 0.38,
  });
  timings.push(performance.now() - started);
}

timings.sort((a, b) => a - b);
const report = {
  iterations,
  checksPerIteration: challenges.length + 1,
  averageMs: average(timings),
  p95Ms: percentile(timings, 0.95),
  maxMs: timings[timings.length - 1],
  targetMs: 1000,
  withinTarget: timings[timings.length - 1] < 1000,
};

mkdirSync("../reports", { recursive: true });
writeFileSync(join("..", "reports", "mobile-liveness-benchmark.json"), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report));

function average(values: number[]): number {
  return round(values.reduce((sum, value) => sum + value, 0) / values.length);
}

function percentile(values: number[], quantile: number): number {
  return round(values[Math.floor((values.length - 1) * quantile)]);
}

function round(value: number): number {
  return Math.round(value * 1000) / 1000;
}
