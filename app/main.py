from pathlib import Path
import time
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import (
    ALLOWED_HOSTS,
    ALLOWED_ORIGINS,
    APP_ENV,
    FACE_MATCH_THRESHOLD,
    MAX_RECOGNITION_TIME_MS,
    MIN_ANDROID_VERSION,
    MIN_IOS_VERSION,
    MIN_RAM_GB,
    MODEL_NAME,
    MODEL_PATH,
    MODEL_SHA256,
    MODEL_VERSION,
    RATE_LIMIT_REQUESTS_PER_MINUTE,
    SUPPORTED_LIVENESS_CHALLENGES,
    TARGET_MODEL_SIZE_MB,
)
from app.database import get_db, init_db, mongo_available
from app.repository import (
    get_device,
    get_employee,
    insert_benchmark_report,
    insert_sync_rejection,
    list_attendance,
    list_benchmark_reports,
    upsert_device,
    upsert_employee,
)
from app.schemas import (
    AttendanceAck,
    AttendanceBatchRequest,
    BenchmarkReportRequest,
    BenchmarkReportResponse,
    DeviceRegisterRequest,
    EmployeeEnrollRequest,
    OfflineProfileResponse,
    SignedAttendanceEvent,
    model_to_wire_dict,
)
from app.security import generate_secret, hash_secret, require_admin_api_key
from app.service import store_verified_attendance, validate_attendance_event


app = FastAPI(
    title="NHAI Offline Attendance Backend",
    description="Backend trust layer for offline face/liveness attendance sync.",
    version="1.0.0",
)

if ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(ALLOWED_ORIGINS),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Admin-API-Key", "X-Device-Secret"],
    )

if ALLOWED_HOSTS:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(ALLOWED_HOSTS))


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response


app.add_middleware(SecurityHeadersMiddleware)


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60
        self.hits = {}

    async def dispatch(self, request, call_next):
        client = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - self.window_seconds
        client_hits = [hit for hit in self.hits.get(client, []) if hit >= window_start]
        if len(client_hits) >= self.requests_per_minute:
            return JSONResponse(
                {"detail": "rate_limit_exceeded"},
                status_code=429,
            )
        client_hits.append(now)
        self.hits[client] = client_hits
        return await call_next(request)


app.add_middleware(
    InMemoryRateLimitMiddleware,
    requests_per_minute=RATE_LIMIT_REQUESTS_PER_MINUTE,
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health():
    mongodb = "connected" if mongo_available() else "unavailable"
    status = "ok" if mongodb == "connected" else "degraded"
    return {"status": status, "mongodb": mongodb, "environment": APP_ENV}


def model_metadata():
    model_path = Path(MODEL_PATH)
    size_mb = model_path.stat().st_size / (1024 * 1024) if model_path.exists() else None
    return {
        "name": MODEL_NAME,
        "version": MODEL_VERSION,
        "format": "onnx",
        "path": MODEL_PATH,
        "sha256": MODEL_SHA256,
        "sizeMb": round(size_mb, 2) if size_mb is not None else None,
        "targetSizeMb": TARGET_MODEL_SIZE_MB,
        "withinTargetSize": size_mb is not None and size_mb <= TARGET_MODEL_SIZE_MB,
        "embeddingSize": 128,
        "inputShape": [1, 3, 112, 112],
        "openSourceRuntime": "onnxruntime-react-native or onnxruntime-mobile",
    }


@app.get("/model/metadata")
def get_model_metadata():
    return model_metadata()


@app.get("/system/requirements")
def get_system_requirements():
    return {
        "frameworkCompatibility": {
            "mobile": "React Native",
            "androidMinVersion": MIN_ANDROID_VERSION,
            "iosMinVersion": MIN_IOS_VERSION,
            "minimumRamGb": MIN_RAM_GB,
        },
        "performanceTargets": {
            "maxRecognitionAndLivenessMs": MAX_RECOGNITION_TIME_MS,
            "targetModelSizeMb": TARGET_MODEL_SIZE_MB,
            "accuracyTarget": ">95%",
        },
        "offlineMode": {
            "backendCallsDuringOfflineAuth": 0,
            "localRecordStatus": "pending",
            "syncWhenNetworkReturns": True,
            "purgeOnlyAfterServerAck": True,
        },
        "liveness": {
            "supportedChallenges": list(SUPPORTED_LIVENESS_CHALLENGES),
            "runsOnDevice": True,
        },
        "model": model_metadata(),
    }


@app.post("/employees/enroll", dependencies=[Depends(require_admin_api_key)])
def enroll_employee(payload: EmployeeEnrollRequest):
    db = get_db()
    upsert_employee(
        db,
        payload.employee_id,
        payload.name,
        payload.project_id,
        payload.face_template,
    )
    return {"status": "success", "employeeId": payload.employee_id}


@app.post("/devices/register", dependencies=[Depends(require_admin_api_key)])
def register_device(payload: DeviceRegisterRequest):
    db = get_db()
    employee = get_employee(db, payload.employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="employee_not_found")
    if employee["project_id"] != payload.project_id:
        raise HTTPException(status_code=400, detail="project_mismatch")

    secret = generate_secret()
    upsert_device(
        db,
        payload.device_id,
        payload.employee_id,
        payload.project_id,
        secret,
    )

    return {
        "status": "success",
        "deviceId": payload.device_id,
        "deviceSecret": secret,
    }


@app.get("/offline-profile/{employee_id}", response_model=OfflineProfileResponse)
def get_offline_profile(
    employee_id: str,
    device_id: str = Query(..., alias="deviceId"),
    x_device_secret: Optional[str] = Header(None, alias="X-Device-Secret"),
):
    db = get_db()
    employee = get_employee(db, employee_id)
    device = get_device(db, device_id)

    if not employee:
        raise HTTPException(status_code=404, detail="employee_not_found")
    if not device:
        raise HTTPException(status_code=404, detail="device_not_registered")
    if device["employee_id"] != employee_id:
        raise HTTPException(status_code=403, detail="device_employee_mismatch")
    if device["project_id"] != employee["project_id"]:
        raise HTTPException(status_code=400, detail="project_mismatch")
    if not x_device_secret:
        raise HTTPException(status_code=401, detail="missing_device_secret")
    if hash_secret(x_device_secret) != device["secret_hash"]:
        raise HTTPException(status_code=401, detail="invalid_device_secret")

    return OfflineProfileResponse(
        employeeId=employee["employee_id"],
        name=employee["name"],
        projectId=employee["project_id"],
        deviceId=device_id,
        faceTemplate=employee["face_template"],
        faceMatchThreshold=FACE_MATCH_THRESHOLD,
        model=model_metadata(),
        livenessChallenges=list(SUPPORTED_LIVENESS_CHALLENGES),
    )


def sync_one(event: SignedAttendanceEvent, device_secret: str) -> AttendanceAck:
    event_payload = model_to_wire_dict(
        event,
        exclude_none=True,
    )
    signature = event_payload.pop("signature")

    db = get_db()
    valid, reason = validate_attendance_event(
        db,
        event_payload,
        signature,
        device_secret,
    )
    if not valid:
        insert_sync_rejection(db, event_payload, reason)
        return AttendanceAck(
            eventId=event.event_id,
            status="rejected",
            purgeAllowed=False,
            reason=reason,
        )

    ack_id = store_verified_attendance(db, event_payload, signature)
    return AttendanceAck(
        eventId=event.event_id,
        status="success",
        serverAckId=ack_id,
        purgeAllowed=True,
    )


@app.post("/sync/attendance", response_model=AttendanceAck)
def sync_attendance(
    event: SignedAttendanceEvent,
    x_device_secret: Optional[str] = Header(None, alias="X-Device-Secret"),
):
    if not x_device_secret:
        raise HTTPException(status_code=401, detail="missing_device_secret")
    return sync_one(event, x_device_secret)


@app.post("/sync/attendance/batch")
def sync_attendance_batch(
    payload: AttendanceBatchRequest,
    x_device_secret: Optional[str] = Header(None, alias="X-Device-Secret"),
):
    if not x_device_secret:
        raise HTTPException(status_code=401, detail="missing_device_secret")
    return {
        "results": [
            sync_one(event, x_device_secret)
            for event in payload.events
        ]
    }


@app.post("/sync/benchmark", response_model=BenchmarkReportResponse)
def sync_benchmark_report(
    payload: BenchmarkReportRequest,
    x_device_secret: Optional[str] = Header(None, alias="X-Device-Secret"),
):
    if not x_device_secret:
        raise HTTPException(status_code=401, detail="missing_device_secret")

    db = get_db()
    employee = get_employee(db, payload.employee_id)
    device = get_device(db, payload.device_id)
    if not employee:
        return BenchmarkReportResponse(status="rejected", accepted=False, reason="employee_not_found")
    if not device:
        return BenchmarkReportResponse(status="rejected", accepted=False, reason="device_not_registered")
    if device["employee_id"] != payload.employee_id:
        return BenchmarkReportResponse(status="rejected", accepted=False, reason="device_employee_mismatch")
    if device["project_id"] != payload.project_id or employee["project_id"] != payload.project_id:
        return BenchmarkReportResponse(status="rejected", accepted=False, reason="project_mismatch")
    if hash_secret(x_device_secret) != device["secret_hash"]:
        return BenchmarkReportResponse(status="rejected", accepted=False, reason="invalid_device_secret")
    if payload.model_version != MODEL_VERSION:
        return BenchmarkReportResponse(status="rejected", accepted=False, reason="model_version_mismatch")
    if payload.model_sha256 != MODEL_SHA256:
        return BenchmarkReportResponse(status="rejected", accepted=False, reason="model_checksum_mismatch")
    if payload.max_ms > MAX_RECOGNITION_TIME_MS or not payload.within_target:
        return BenchmarkReportResponse(status="rejected", accepted=False, reason="benchmark_above_target")
    if APP_ENV.lower() == "production" and payload.biometric_engine != "onnx":
        return BenchmarkReportResponse(status="rejected", accepted=False, reason="production_requires_onnx_engine")

    benchmark_id = insert_benchmark_report(
        db,
        model_to_wire_dict(payload, exclude_none=True),
    )
    return BenchmarkReportResponse(
        status="success",
        accepted=True,
        benchmarkId=benchmark_id,
    )


@app.get("/benchmarks", dependencies=[Depends(require_admin_api_key)])
def get_benchmark_reports(device_id: Optional[str] = Query(None, alias="deviceId")):
    db = get_db()
    return {"items": list_benchmark_reports(db, device_id)}


@app.get("/attendance", dependencies=[Depends(require_admin_api_key)])
def get_attendance(employee_id: Optional[str] = Query(None, alias="employeeId")):
    db = get_db()
    rows = list_attendance(db, employee_id)
    return {"items": rows}
