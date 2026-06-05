import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();

function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(message);
  }
}

function read(path: string): string {
  return readFileSync(join(root, path), "utf8");
}

assert(existsSync(join(root, "android/app/src/main/java/com/nhai/attendance/NHAIFaceCaptureModule.kt")), "missing generated Android module");
assert(existsSync(join(root, "android/app/src/main/java/com/nhai/attendance/NHAIFaceCapturePackage.kt")), "missing generated Android package");
assert(existsSync(join(root, "ios/NHAIOfflineAttendance/NHAIFaceCaptureModule.swift")), "missing generated iOS Swift module");
assert(existsSync(join(root, "ios/NHAIOfflineAttendance/NHAIFaceCaptureModuleBridge.m")), "missing generated iOS bridge");

const androidGradle = read("android/app/build.gradle");
assert(androidGradle.includes("com.google.mlkit:face-detection:16.1.7"), "missing Android ML Kit face detector dependency");

const mainApplication = read("android/app/src/main/java/in/nhai/offlineattendance/MainApplication.kt");
assert(mainApplication.includes("import com.nhai.attendance.NHAIFaceCapturePackage"), "missing Android package import");
assert(mainApplication.includes("add(NHAIFaceCapturePackage())"), "missing Android package registration");

const xcodeProject = read("ios/NHAIOfflineAttendance.xcodeproj/project.pbxproj");
assert(xcodeProject.includes("NHAIFaceCaptureModule.swift in Sources"), "missing iOS Swift source registration");
assert(xcodeProject.includes("NHAIFaceCaptureModuleBridge.m in Sources"), "missing iOS bridge source registration");

console.log("native prebuild checks passed");
