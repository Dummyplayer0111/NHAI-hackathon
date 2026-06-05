from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator

from app.config import MAX_SYNC_BATCH_SIZE, SUPPORTED_LIVENESS_CHALLENGES


class EmployeeEnrollRequest(BaseModel):
    employee_id: str = Field(..., alias="employeeId")
    name: str
    project_id: str = Field(..., alias="projectId")
    face_template: Any = Field(..., alias="faceTemplate")

    class Config:
        allow_population_by_field_name = True


class DeviceRegisterRequest(BaseModel):
    employee_id: str = Field(..., alias="employeeId")
    device_id: str = Field(..., alias="deviceId")
    project_id: str = Field(..., alias="projectId")

    class Config:
        allow_population_by_field_name = True


class OfflineProfileResponse(BaseModel):
    employee_id: str = Field(..., alias="employeeId")
    name: str
    project_id: str = Field(..., alias="projectId")
    device_id: str = Field(..., alias="deviceId")
    face_template: Any = Field(..., alias="faceTemplate")
    face_match_threshold: float = Field(..., alias="faceMatchThreshold")
    model: Dict[str, Any]
    liveness_challenges: List[str] = Field(..., alias="livenessChallenges")

    class Config:
        allow_population_by_field_name = True


class AttendanceEvent(BaseModel):
    event_id: str = Field(..., alias="eventId")
    employee_id: str = Field(..., alias="employeeId")
    device_id: str = Field(..., alias="deviceId")
    project_id: str = Field(..., alias="projectId")
    timestamp: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_accuracy_meters: Optional[float] = Field(None, alias="locationAccuracyMeters")
    face_match_score: float = Field(..., alias="faceMatchScore")
    liveness_passed: bool = Field(..., alias="livenessPassed")
    liveness_score: Optional[float] = Field(None, alias="livenessScore")
    face_quality_passed: Optional[bool] = Field(None, alias="faceQualityPassed")
    face_quality_score: Optional[float] = Field(None, alias="faceQualityScore")
    face_quality_reasons: List[str] = Field(default_factory=list, alias="faceQualityReasons")
    challenge: List[str]
    model_version: Optional[str] = Field(None, alias="modelVersion")
    app_version: Optional[str] = Field(None, alias="appVersion")
    biometric_engine: Optional[str] = Field(None, alias="biometricEngine")
    device_sequence: Optional[int] = Field(None, alias="deviceSequence")
    sync_status: Optional[str] = Field(None, alias="syncStatus")

    class Config:
        allow_population_by_field_name = True

    @validator("face_match_score")
    def validate_face_match_score(cls, value):
        if value < 0 or value > 1:
            raise ValueError("faceMatchScore must be between 0 and 1")
        return value

    @validator("liveness_score")
    def validate_liveness_score(cls, value):
        if value is not None and (value < 0 or value > 1):
            raise ValueError("livenessScore must be between 0 and 1")
        return value

    @validator("face_quality_score")
    def validate_face_quality_score(cls, value):
        if value is not None and (value < 0 or value > 1):
            raise ValueError("faceQualityScore must be between 0 and 1")
        return value

    @validator("location_accuracy_meters")
    def validate_location_accuracy(cls, value):
        if value is not None and value < 0:
            raise ValueError("locationAccuracyMeters cannot be negative")
        return value

    @validator("biometric_engine")
    def validate_biometric_engine(cls, value):
        if value is not None and value not in {"prototype", "onnx"}:
            raise ValueError("biometricEngine must be prototype or onnx")
        return value

    @validator("challenge")
    def validate_challenge(cls, value):
        if not value:
            raise ValueError("at least one liveness challenge is required")
        unknown = sorted(set(value) - set(SUPPORTED_LIVENESS_CHALLENGES))
        if unknown:
            raise ValueError(f"unsupported liveness challenge(s): {unknown}")
        return value


class SignedAttendanceEvent(AttendanceEvent):
    signature: str


class AttendanceBatchRequest(BaseModel):
    events: List[SignedAttendanceEvent]

    @validator("events")
    def validate_batch_size(cls, value):
        if not value:
            raise ValueError("events cannot be empty")
        if len(value) > MAX_SYNC_BATCH_SIZE:
            raise ValueError(f"batch cannot contain more than {MAX_SYNC_BATCH_SIZE} events")
        return value


class AttendanceAck(BaseModel):
    event_id: str = Field(..., alias="eventId")
    status: str
    server_ack_id: Optional[str] = Field(None, alias="serverAckId")
    purge_allowed: bool = Field(False, alias="purgeAllowed")
    reason: Optional[str] = None

    class Config:
        allow_population_by_field_name = True


class DeviceInfo(BaseModel):
    platform: str
    os_version: str = Field(..., alias="osVersion")
    model: str
    ram_gb: Optional[float] = Field(None, alias="ramGb")

    class Config:
        allow_population_by_field_name = True


class BenchmarkReportRequest(BaseModel):
    employee_id: str = Field(..., alias="employeeId")
    device_id: str = Field(..., alias="deviceId")
    project_id: str = Field(..., alias="projectId")
    app_version: str = Field(..., alias="appVersion")
    model_version: str = Field(..., alias="modelVersion")
    model_sha256: str = Field(..., alias="modelSha256")
    biometric_engine: str = Field(..., alias="biometricEngine")
    device_info: DeviceInfo = Field(..., alias="deviceInfo")
    iterations: int
    average_ms: float = Field(..., alias="averageMs")
    p95_ms: float = Field(..., alias="p95Ms")
    max_ms: float = Field(..., alias="maxMs")
    target_ms: float = Field(..., alias="targetMs")
    within_target: bool = Field(..., alias="withinTarget")
    captured_at: str = Field(..., alias="capturedAt")

    class Config:
        allow_population_by_field_name = True

    @validator("biometric_engine")
    def validate_biometric_engine(cls, value):
        if value not in {"prototype", "onnx"}:
            raise ValueError("biometricEngine must be prototype or onnx")
        return value

    @validator("iterations")
    def validate_iterations(cls, value):
        if value <= 0:
            raise ValueError("iterations must be positive")
        return value

    @validator("average_ms", "p95_ms", "max_ms", "target_ms")
    def validate_timings(cls, value):
        if value < 0:
            raise ValueError("timing values cannot be negative")
        return value


class BenchmarkReportResponse(BaseModel):
    status: str
    benchmark_id: Optional[str] = Field(None, alias="benchmarkId")
    accepted: bool
    reason: Optional[str] = None

    class Config:
        allow_population_by_field_name = True


def model_to_wire_dict(model: BaseModel, exclude_none: bool = False) -> Dict[str, Any]:
    return model.dict(by_alias=True, exclude_none=exclude_none)
