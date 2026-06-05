export type CameraCaptureSource = {
  takePictureAsync(options?: {
    quality?: number;
    skipProcessing?: boolean;
    exif?: boolean;
  }): Promise<{ uri?: string }>;
};

export async function captureImageUris(camera: CameraCaptureSource, frames: number): Promise<string[]> {
  const imageUris: string[] = [];
  for (let index = 0; index < frames; index += 1) {
    const picture = await camera.takePictureAsync({
      quality: 0.8,
      skipProcessing: false,
      exif: false,
    });
    if (!picture.uri) {
      throw new Error("camera_capture_uri_missing");
    }
    imageUris.push(picture.uri);
    if (index < frames - 1) {
      await wait(140);
    }
  }
  return imageUris;
}

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
