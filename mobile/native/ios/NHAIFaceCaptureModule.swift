import Foundation
import ImageIO
import React
import UIKit
import Vision

@objc(NHAIFaceCapture)
final class NHAIFaceCaptureModule: NSObject {
  @objc
  static func requiresMainQueueSetup() -> Bool {
    return false
  }

  @objc(captureFaceSample:resolver:rejecter:)
  func captureFaceSample(
    options: NSDictionary,
    resolver resolve: @escaping RCTPromiseResolveBlock,
    rejecter reject: @escaping RCTPromiseRejectBlock
  ) {
    DispatchQueue.global(qos: .userInitiated).async {
      do {
        guard let imageUris = options["imageUris"] as? [String], !imageUris.isEmpty else {
          throw CaptureError.invalidInput("imageUris_required")
        }
        let width = options["width"] as? Int ?? 112
        let height = options["height"] as? Int ?? 112
        let images = try imageUris.map { try self.loadImage(uri: $0) }
        let observations = try images.map { try self.detectSingleFace(image: $0) }
        guard let crop = self.cropFace(image: images.last!, face: observations.last!, width: width, height: height) else {
          throw CaptureError.invalidInput("face_crop_failed")
        }

        resolve([
          "width": width,
          "height": height,
          "rgb": try self.rgbBytes(image: crop).base64EncodedString(),
          "landmarks": observations.map { self.landmarksMap($0) },
          "quality": self.qualityMap(image: images.last!, face: observations.last!, facesDetected: 1),
        ])
      } catch {
        reject("NHAI_FACE_CAPTURE_FAILED", error.localizedDescription, error)
      }
    }
  }

  private func loadImage(uri: String) throws -> UIImage {
    let url = URL(string: uri) ?? URL(fileURLWithPath: uri)
    guard let data = try? Data(contentsOf: url), let image = UIImage(data: data), image.cgImage != nil else {
      throw CaptureError.invalidInput("image_decode_failed")
    }
    return image
  }

  private func detectSingleFace(image: UIImage) throws -> VNFaceObservation {
    guard let cgImage = image.cgImage else {
      throw CaptureError.invalidInput("cg_image_missing")
    }
    let request = VNDetectFaceLandmarksRequest()
    let handler = VNImageRequestHandler(cgImage: cgImage, orientation: cgOrientation(image.imageOrientation))
    try handler.perform([request])
    guard let faces = request.results as? [VNFaceObservation], faces.count == 1, let face = faces.first else {
      throw CaptureError.invalidInput("exactly_one_face_required")
    }
    return face
  }

  private func cropFace(image: UIImage, face: VNFaceObservation, width: Int, height: Int) -> UIImage? {
    guard let cgImage = image.cgImage else { return nil }
    let imageWidth = CGFloat(cgImage.width)
    let imageHeight = CGFloat(cgImage.height)
    let box = face.boundingBox
    let rect = CGRect(
      x: max(0, (box.minX - box.width * 0.18) * imageWidth),
      y: max(0, (1 - box.maxY - box.height * 0.24) * imageHeight),
      width: min(imageWidth, box.width * 1.36 * imageWidth),
      height: min(imageHeight, box.height * 1.48 * imageHeight)
    ).integral
    guard let cropped = cgImage.cropping(to: rect) else { return nil }
    let renderer = UIGraphicsImageRenderer(size: CGSize(width: width, height: height))
    return renderer.image { _ in
      UIImage(cgImage: cropped).draw(in: CGRect(x: 0, y: 0, width: width, height: height))
    }
  }

  private func rgbBytes(image: UIImage) throws -> Data {
    guard let cgImage = image.cgImage else {
      throw CaptureError.invalidInput("cg_image_missing")
    }
    let width = cgImage.width
    let height = cgImage.height
    var rgba = [UInt8](repeating: 0, count: width * height * 4)
    guard let context = CGContext(
      data: &rgba,
      width: width,
      height: height,
      bitsPerComponent: 8,
      bytesPerRow: width * 4,
      space: CGColorSpaceCreateDeviceRGB(),
      bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
    ) else {
      throw CaptureError.invalidInput("rgb_context_failed")
    }
    context.draw(cgImage, in: CGRect(x: 0, y: 0, width: width, height: height))
    var rgb = Data(capacity: width * height * 3)
    for index in stride(from: 0, to: rgba.count, by: 4) {
      rgb.append(rgba[index])
      rgb.append(rgba[index + 1])
      rgb.append(rgba[index + 2])
    }
    return rgb
  }

  private func landmarksMap(_ face: VNFaceObservation) -> [String: Any] {
    let landmarks = face.landmarks
    let leftEye = normalizedPoints(landmarks?.leftEye, fallbackX: -0.22, fallbackY: 0.12)
    let rightEye = normalizedPoints(landmarks?.rightEye, fallbackX: 0.22, fallbackY: 0.12)
    let mouth = normalizedPoints(landmarks?.outerLips, fallbackX: 0.0, fallbackY: -0.26)
    let nose = normalizedPoint(landmarks?.nose?.normalizedPoints.first, fallbackX: 0.0, fallbackY: -0.02)
    return [
      "leftEye": sixPoints(leftEye),
      "rightEye": sixPoints(rightEye),
      "mouth": fourMouthPoints(mouth),
      "noseTip": nose,
      "faceCenter": ["x": 0.0, "y": 0.0],
      "faceBox": ["width": 1.0, "height": Double(face.boundingBox.height / face.boundingBox.width)],
    ]
  }

  private func normalizedPoints(_ region: VNFaceLandmarkRegion2D?, fallbackX: CGFloat, fallbackY: CGFloat) -> [[String: Double]] {
    guard let points = region?.normalizedPoints, !points.isEmpty else {
      return [["x": Double(fallbackX), "y": Double(fallbackY)]]
    }
    return points.map { normalizedPoint($0, fallbackX: fallbackX, fallbackY: fallbackY) }
  }

  private func normalizedPoint(_ point: CGPoint?, fallbackX: CGFloat, fallbackY: CGFloat) -> [String: Double] {
    let value = point ?? CGPoint(x: fallbackX + 0.5, y: fallbackY + 0.5)
    return ["x": Double(value.x - 0.5), "y": Double(0.5 - value.y)]
  }

  private func sixPoints(_ points: [[String: Double]]) -> [[String: Double]] {
    if points.count >= 6 {
      return Array(points.prefix(6))
    }
    let center = points.first ?? ["x": 0.0, "y": 0.0]
    let x = center["x"] ?? 0.0
    let y = center["y"] ?? 0.0
    return [
      ["x": x - 0.08, "y": y],
      ["x": x - 0.04, "y": y - 0.04],
      ["x": x + 0.04, "y": y - 0.04],
      ["x": x + 0.08, "y": y],
      ["x": x + 0.04, "y": y + 0.04],
      ["x": x - 0.04, "y": y + 0.04],
    ]
  }

  private func fourMouthPoints(_ points: [[String: Double]]) -> [[String: Double]] {
    if points.count >= 4 {
      return [points[0], points[1], points[2], points[3]]
    }
    return [
      ["x": -0.18, "y": -0.25],
      ["x": 0.0, "y": -0.18],
      ["x": 0.18, "y": -0.25],
      ["x": 0.0, "y": -0.32],
    ]
  }

  private func qualityMap(image: UIImage, face: VNFaceObservation, facesDetected: Int) -> [String: Any] {
    return [
      "facesDetected": facesDetected,
      "brightness": brightness(image: image),
      "blurScore": blurScore(image: image),
      "faceBoxRatio": Double(face.boundingBox.width * face.boundingBox.height),
    ]
  }

  private func brightness(image: UIImage) -> Double {
    guard let cgImage = image.cgImage else { return 0 }
    let ciImage = CIImage(cgImage: cgImage)
    let extentVector = CIVector(x: ciImage.extent.origin.x, y: ciImage.extent.origin.y, z: ciImage.extent.size.width, w: ciImage.extent.size.height)
    guard let filter = CIFilter(name: "CIAreaAverage", parameters: [kCIInputImageKey: ciImage, kCIInputExtentKey: extentVector]),
          let output = filter.outputImage else { return 0 }
    var pixel = [UInt8](repeating: 0, count: 4)
    CIContext().render(output, toBitmap: &pixel, rowBytes: 4, bounds: CGRect(x: 0, y: 0, width: 1, height: 1), format: .RGBA8, colorSpace: CGColorSpaceCreateDeviceRGB())
    return (0.299 * Double(pixel[0]) + 0.587 * Double(pixel[1]) + 0.114 * Double(pixel[2])) / 255.0
  }

  private func blurScore(image: UIImage) -> Double {
    guard let cgImage = image.cgImage else { return 0 }
    let width = 64
    let height = 64
    var rgba = [UInt8](repeating: 0, count: width * height * 4)
    guard let context = CGContext(
      data: &rgba,
      width: width,
      height: height,
      bitsPerComponent: 8,
      bytesPerRow: width * 4,
      space: CGColorSpaceCreateDeviceRGB(),
      bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
    ) else {
      return 0
    }
    context.draw(cgImage, in: CGRect(x: 0, y: 0, width: width, height: height))
    var total = 0.0
    var count = 0
    for y in 1..<height {
      for x in 1..<width {
        let index = (y * width + x) * 4
        let left = (y * width + x - 1) * 4
        let top = ((y - 1) * width + x) * 4
        total += abs(Double(rgba[index]) - Double(rgba[left]))
        total += abs(Double(rgba[index]) - Double(rgba[top]))
        count += 1
      }
    }
    return min(1.0, total / Double(max(1, count)) / 48.0)
  }

  private func cgOrientation(_ orientation: UIImage.Orientation) -> CGImagePropertyOrientation {
    switch orientation {
    case .up: return .up
    case .down: return .down
    case .left: return .left
    case .right: return .right
    case .upMirrored: return .upMirrored
    case .downMirrored: return .downMirrored
    case .leftMirrored: return .leftMirrored
    case .rightMirrored: return .rightMirrored
    @unknown default: return .up
    }
  }
}

private enum CaptureError: LocalizedError {
  case invalidInput(String)

  var errorDescription: String? {
    switch self {
    case .invalidInput(let message):
      return message
    }
  }
}
