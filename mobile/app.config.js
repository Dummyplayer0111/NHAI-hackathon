const appJson = require("./app.json");

const production = process.env.APP_ENV === "production";
const prototypeFlag = process.env.ENABLE_PROTOTYPE_BIOMETRIC_ADAPTER;

module.exports = {
  ...appJson.expo,
  plugins: [
    ...(appJson.expo.plugins ?? []),
    "./plugins/withNHAIFaceCapture",
  ],
  extra: {
    ...appJson.expo.extra,
    enablePrototypeBiometricAdapter:
      prototypeFlag === undefined
        ? !production
        : prototypeFlag === "true",
  },
};
