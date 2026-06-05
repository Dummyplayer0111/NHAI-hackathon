package com.nhai.attendance

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Color
import android.net.Uri
import com.facebook.react.bridge.Arguments
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import com.facebook.react.bridge.ReadableArray
import com.facebook.react.bridge.ReadableMap
import com.google.android.gms.tasks.Tasks
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.face.Face
import com.google.mlkit.vision.face.FaceDetection
import com.google.mlkit.vision.face.FaceDetectorOptions
import com.google.mlkit.vision.face.FaceLandmark
import java.io.File
import java.util.Base64
import kotlin.math.max
import kotlin.math.min

class NHAIFaceCaptureModule(private val context: ReactApplicationContext) :
  ReactContextBaseJavaModule(context) {
  override fun getName(): String = "NHAIFaceCapture"

  private val detector = FaceDetection.getClient(
    FaceDetectorOptions.Builder()
      .setPerformanceMode(FaceDetectorOptions.PERFORMANCE_MODE_ACCURATE)
      .setLandmarkMode(FaceDetectorOptions.LANDMARK_MODE_ALL)
      .setClassificationMode(FaceDetectorOptions.CLASSIFICATION_MODE_ALL)
      .build()
  )

  @ReactMethod
  fun captureFaceSample(options: ReadableMap, promise: Promise) {
    Thread {
      try {
        val imageUris = options.getArray("imageUris") ?: throw IllegalArgumentException("imageUris_required")
        val width = options.getInt("width")
        val height = options.getInt("height")
        val bitmaps = decodeBitmaps(imageUris)
        val detections = bitmaps.map { bitmap ->
          Tasks.await(detector.process(InputImage.fromBitmap(bitmap, 0)))
        }
        val faces = detections.map { faces ->
          if (faces.size != 1) throw IllegalArgumentException("exactly_one_face_required")
          faces[0]
        }
        val crop = cropFace(bitmaps.last(), faces.last(), width, height)
        val response = Arguments.createMap()
        response.putInt("width", width)
        response.putInt("height", height)
        response.putString("rgb", Base64.getEncoder().encodeToString(rgbBytes(crop)))
        response.putArray("landmarks", Arguments.makeNativeArray(faces.map { landmarksMap(it) }))
        response.putMap("quality", qualityMap(bitmaps.last(), faces.last(), detections.last().size))
        promise.resolve(response)
      } catch (error: Exception) {
        promise.reject("NHAI_FACE_CAPTURE_FAILED", error.message, error)
      }
    }.start()
  }

  private fun decodeBitmaps(imageUris: ReadableArray): List<Bitmap> {
    return (0 until imageUris.size()).map { index ->
      val uri = Uri.parse(imageUris.getString(index))
      val path = uri.path ?: throw IllegalArgumentException("image_uri_path_missing")
      BitmapFactory.decodeFile(File(path).absolutePath)
        ?: throw IllegalArgumentException("image_decode_failed")
    }
  }

  private fun cropFace(source: Bitmap, face: Face, width: Int, height: Int): Bitmap {
    val box = face.boundingBox
    val padX = (box.width() * 0.18).toInt()
    val padY = (box.height() * 0.24).toInt()
    val left = max(0, box.left - padX)
    val top = max(0, box.top - padY)
    val right = min(source.width, box.right + padX)
    val bottom = min(source.height, box.bottom + padY)
    val cropped = Bitmap.createBitmap(source, left, top, right - left, bottom - top)
    return Bitmap.createScaledBitmap(cropped, width, height, true)
  }

  private fun rgbBytes(bitmap: Bitmap): ByteArray {
    val out = ByteArray(bitmap.width * bitmap.height * 3)
    var offset = 0
    for (y in 0 until bitmap.height) {
      for (x in 0 until bitmap.width) {
        val color = bitmap.getPixel(x, y)
        out[offset++] = Color.red(color).toByte()
        out[offset++] = Color.green(color).toByte()
        out[offset++] = Color.blue(color).toByte()
      }
    }
    return out
  }

  private fun landmarksMap(face: Face): Map<String, Any> {
    val box = face.boundingBox
    fun point(type: Int): Map<String, Double> {
      val landmark = face.getLandmark(type)?.position
      return mapOf(
        "x" to (((landmark?.x ?: box.centerX().toFloat()) - box.centerX()) / box.width().toDouble()),
        "y" to (((landmark?.y ?: box.centerY().toFloat()) - box.centerY()) / box.height().toDouble())
      )
    }
    val leftEye = point(FaceLandmark.LEFT_EYE)
    val rightEye = point(FaceLandmark.RIGHT_EYE)
    val mouthLeft = point(FaceLandmark.MOUTH_LEFT)
    val mouthRight = point(FaceLandmark.MOUTH_RIGHT)
    val mouthBottom = point(FaceLandmark.MOUTH_BOTTOM)
    val nose = point(FaceLandmark.NOSE_BASE)
    return mapOf(
      "leftEye" to eyePoints(leftEye),
      "rightEye" to eyePoints(rightEye),
      "mouth" to mouthPoints(mouthLeft, mouthRight, mouthBottom),
      "noseTip" to nose,
      "faceCenter" to mapOf("x" to 0.0, "y" to 0.0),
      "faceBox" to mapOf("width" to 1.0, "height" to box.height().toDouble() / box.width().toDouble())
    )
  }

  private fun eyePoints(center: Map<String, Double>): List<Map<String, Double>> {
    val x = center["x"] ?: 0.0
    val y = center["y"] ?: 0.0
    return listOf(
      mapOf("x" to x - 0.08, "y" to y),
      mapOf("x" to x - 0.04, "y" to y - 0.04),
      mapOf("x" to x + 0.04, "y" to y - 0.04),
      mapOf("x" to x + 0.08, "y" to y),
      mapOf("x" to x + 0.04, "y" to y + 0.04),
      mapOf("x" to x - 0.04, "y" to y + 0.04)
    )
  }

  private fun mouthPoints(
    left: Map<String, Double>,
    right: Map<String, Double>,
    bottom: Map<String, Double>
  ): List<Map<String, Double>> {
    val centerX = ((left["x"] ?: 0.0) + (right["x"] ?: 0.0)) / 2.0
    val centerY = (bottom["y"] ?: 0.3) - 0.08
    return listOf(left, mapOf("x" to centerX, "y" to centerY), right, bottom)
  }

  private fun qualityMap(bitmap: Bitmap, face: Face, facesDetected: Int): com.facebook.react.bridge.WritableMap {
    val quality = Arguments.createMap()
    quality.putInt("facesDetected", facesDetected)
    quality.putDouble("brightness", brightness(bitmap))
    quality.putDouble("blurScore", blurScore(bitmap))
    quality.putDouble(
      "faceBoxRatio",
      (face.boundingBox.width().toDouble() * face.boundingBox.height().toDouble()) /
        (bitmap.width.toDouble() * bitmap.height.toDouble())
    )
    return quality
  }

  private fun brightness(bitmap: Bitmap): Double {
    var total = 0.0
    val step = max(1, bitmap.width / 64)
    var count = 0
    for (y in 0 until bitmap.height step step) {
      for (x in 0 until bitmap.width step step) {
        val color = bitmap.getPixel(x, y)
        total += (0.299 * Color.red(color) + 0.587 * Color.green(color) + 0.114 * Color.blue(color)) / 255.0
        count += 1
      }
    }
    return total / count
  }

  private fun blurScore(bitmap: Bitmap): Double {
    var total = 0.0
    var count = 0
    val step = max(1, bitmap.width / 64)
    for (y in step until bitmap.height step step) {
      for (x in step until bitmap.width step step) {
        val current = Color.red(bitmap.getPixel(x, y))
        val left = Color.red(bitmap.getPixel(x - step, y))
        val top = Color.red(bitmap.getPixel(x, y - step))
        total += kotlin.math.abs(current - left) + kotlin.math.abs(current - top)
        count += 1
      }
    }
    return min(1.0, total / max(1, count) / 48.0)
  }
}
