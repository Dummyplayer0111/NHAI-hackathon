import os


APP_ENV = os.getenv("APP_ENV", "development")
IS_PRODUCTION = APP_ENV.lower() == "production"
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "dev-admin-key-change-me")
if IS_PRODUCTION and ADMIN_API_KEY == "dev-admin-key-change-me":
    raise RuntimeError("ADMIN_API_KEY must be set to a non-default value in production")

ALLOWED_ORIGINS = tuple(
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
)
ALLOWED_HOSTS = tuple(
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "").split(",")
    if host.strip()
)
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "attendance_db")
MONGODB_TIMEOUT_MS = int(os.getenv("MONGODB_TIMEOUT_MS", "2000"))
FACE_MATCH_THRESHOLD = float(os.getenv("FACE_MATCH_THRESHOLD", "0.75"))
LIVENESS_SCORE_THRESHOLD = float(os.getenv("LIVENESS_SCORE_THRESHOLD", "0.70"))
FACE_QUALITY_SCORE_THRESHOLD = float(os.getenv("FACE_QUALITY_SCORE_THRESHOLD", "0.65"))
MAX_LOCATION_ACCURACY_METERS = float(os.getenv("MAX_LOCATION_ACCURACY_METERS", "100"))
MAX_OFFLINE_EVENT_AGE_HOURS = int(os.getenv("MAX_OFFLINE_EVENT_AGE_HOURS", "72"))
MAX_SYNC_BATCH_SIZE = int(os.getenv("MAX_SYNC_BATCH_SIZE", "100"))
RATE_LIMIT_REQUESTS_PER_MINUTE = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "120"))

MODEL_PATH = os.getenv("MODEL_PATH", "MobileFaceNet.onnx")
MODEL_NAME = os.getenv("MODEL_NAME", "MobileFaceNet")
MODEL_VERSION = os.getenv("MODEL_VERSION", "mobilefacenet-onnx-v1")
MODEL_SHA256 = os.getenv(
    "MODEL_SHA256",
    "6a2722edc8168a7ac3dcb2c21f5649654f8089ab6ee43c59a0a5ddcffca1f726",
)
TARGET_MODEL_SIZE_MB = float(os.getenv("TARGET_MODEL_SIZE_MB", "20"))
MAX_RECOGNITION_TIME_MS = int(os.getenv("MAX_RECOGNITION_TIME_MS", "1000"))

SUPPORTED_LIVENESS_CHALLENGES = tuple(
    challenge.strip()
    for challenge in os.getenv(
        "SUPPORTED_LIVENESS_CHALLENGES",
        "blink,smile,turn_left,turn_right",
    ).split(",")
    if challenge.strip()
)

MIN_ANDROID_VERSION = os.getenv("MIN_ANDROID_VERSION", "8.0")
MIN_IOS_VERSION = os.getenv("MIN_IOS_VERSION", "12.0")
MIN_RAM_GB = int(os.getenv("MIN_RAM_GB", "3"))
