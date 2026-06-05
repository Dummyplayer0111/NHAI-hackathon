const fs = require("fs");
const path = require("path");
const {
  withAppBuildGradle,
  withDangerousMod,
  withMainApplication,
  withXcodeProject,
} = require("@expo/config-plugins");

const ANDROID_PACKAGE = "com.nhai.attendance";
const ANDROID_PACKAGE_DIR = path.join("com", "nhai", "attendance");
const IOS_FILES = [
  "NHAIFaceCaptureModule.swift",
  "NHAIFaceCaptureModuleBridge.m",
];

function copyFile(source, target) {
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.copyFileSync(source, target);
}

function withNHAIFaceCapture(config) {
  config = withAndroidFaceCapture(config);
  config = withIosFaceCapture(config);
  return config;
}

function withAndroidFaceCapture(config) {
  config = withDangerousMod(config, [
    "android",
    async (modConfig) => {
      const sourceDir = path.join(modConfig.modRequest.projectRoot, "native", "android");
      const targetDir = path.join(
        modConfig.modRequest.platformProjectRoot,
        "app",
        "src",
        "main",
        "java",
        ...ANDROID_PACKAGE_DIR.split(path.sep),
      );
      copyFile(
        path.join(sourceDir, "NHAIFaceCaptureModule.kt"),
        path.join(targetDir, "NHAIFaceCaptureModule.kt"),
      );
      copyFile(
        path.join(sourceDir, "NHAIFaceCapturePackage.kt"),
        path.join(targetDir, "NHAIFaceCapturePackage.kt"),
      );
      return modConfig;
    },
  ]);

  config = withAppBuildGradle(config, (modConfig) => {
    const dependency = 'implementation("com.google.mlkit:face-detection:16.1.7")';
    if (!modConfig.modResults.contents.includes(dependency)) {
      modConfig.modResults.contents = modConfig.modResults.contents.replace(
        /dependencies\s*\{/,
        `dependencies {\n    ${dependency}`,
      );
    }
    return modConfig;
  });

  config = withMainApplication(config, (modConfig) => {
    const importLine = `import ${ANDROID_PACKAGE}.NHAIFaceCapturePackage`;
    if (!modConfig.modResults.contents.includes(importLine)) {
      modConfig.modResults.contents = modConfig.modResults.contents.replace(
        /(package\s+[^\n]+\n)/,
        `$1\n${importLine}\n`,
      );
    }
    if (!modConfig.modResults.contents.includes("add(NHAIFaceCapturePackage())")) {
      modConfig.modResults.contents = modConfig.modResults.contents.replace(
        /(PackageList\(this\)\.packages\.apply\s*\{\n)/,
        "$1        add(NHAIFaceCapturePackage())\n",
      );
    }
    return modConfig;
  });

  return config;
}

function withIosFaceCapture(config) {
  config = withDangerousMod(config, [
    "ios",
    async (modConfig) => {
      const sourceDir = path.join(modConfig.modRequest.projectRoot, "native", "ios");
      const targetDir = path.join(
        modConfig.modRequest.platformProjectRoot,
        modConfig.modRequest.projectName,
      );
      for (const file of IOS_FILES) {
        copyFile(path.join(sourceDir, file), path.join(targetDir, file));
      }
      return modConfig;
    },
  ]);

  config = withXcodeProject(config, (modConfig) => {
    const projectName = modConfig.modRequest.projectName;
    const project = modConfig.modResults;
    const group = project.findPBXGroupKey({ name: projectName }) ??
      project.findPBXGroupKey({ path: projectName });
    for (const file of IOS_FILES) {
      const filePath = `${projectName}/${file}`;
      if (!project.hasFile(filePath)) {
        project.addSourceFile(filePath, {}, group);
      }
    }
    return modConfig;
  });

  return config;
}

module.exports = withNHAIFaceCapture;
