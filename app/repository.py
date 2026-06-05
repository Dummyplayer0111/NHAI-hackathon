from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional

from app.security import hash_secret


def normalize_doc(doc: Optional[Dict]) -> Optional[Dict]:
    if not doc:
        return None
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


def upsert_employee(db, employee_id: str, name: str, project_id: str, face_template: Any) -> None:
    db.employees.update_one(
        {"employee_id": employee_id},
        {
            "$set": {
                "employee_id": employee_id,
                "name": name,
                "project_id": project_id,
                "face_template": face_template,
                "active": True,
                "updated_at": datetime.now(timezone.utc),
            },
            "$setOnInsert": {"created_at": datetime.now(timezone.utc)},
        },
        upsert=True,
    )


def get_employee(db, employee_id: str) -> Optional[Dict]:
    return normalize_doc(
        db.employees.find_one({"employee_id": employee_id, "active": True})
    )


def upsert_device(db, device_id: str, employee_id: str, project_id: str, secret: str) -> None:
    db.devices.update_one(
        {"device_id": device_id},
        {
            "$set": {
                "device_id": device_id,
                "employee_id": employee_id,
                "project_id": project_id,
                "secret_hash": hash_secret(secret),
                "active": True,
                "updated_at": datetime.now(timezone.utc),
            },
            "$setOnInsert": {"created_at": datetime.now(timezone.utc)},
            "$max": {"last_sequence": 0},
        },
        upsert=True,
    )


def get_device(db, device_id: str) -> Optional[Dict]:
    return normalize_doc(
        db.devices.find_one({"device_id": device_id, "active": True})
    )


def event_exists(db, event_id: str) -> bool:
    return db.attendance_logs.find_one({"event_id": event_id}) is not None


def insert_attendance(db, event: Dict[str, Any], signature: str) -> str:
    ack_id = f"ack_{uuid.uuid4().hex}"
    db.attendance_logs.insert_one(
        {
            "event_id": event["eventId"],
            "employee_id": event["employeeId"],
            "device_id": event["deviceId"],
            "project_id": event["projectId"],
            "event_timestamp": event["timestamp"],
            "latitude": event.get("latitude"),
            "longitude": event.get("longitude"),
            "location_accuracy_meters": event.get("locationAccuracyMeters"),
            "face_match_score": event["faceMatchScore"],
            "liveness_passed": event["livenessPassed"],
            "liveness_score": event.get("livenessScore"),
            "face_quality_passed": event.get("faceQualityPassed"),
            "face_quality_score": event.get("faceQualityScore"),
            "face_quality_reasons": event.get("faceQualityReasons", []),
            "challenge": event["challenge"],
            "model_version": event.get("modelVersion"),
            "app_version": event.get("appVersion"),
            "biometric_engine": event.get("biometricEngine"),
            "device_sequence": event.get("deviceSequence"),
            "signature": signature,
            "server_ack_id": ack_id,
            "received_at": datetime.now(timezone.utc),
            "raw_payload": event,
        }
    )
    if event.get("deviceSequence") is not None:
        db.devices.update_one(
            {"device_id": event["deviceId"]},
            {"$max": {"last_sequence": event["deviceSequence"]}},
        )
    return ack_id


def insert_sync_rejection(db, event: Dict[str, Any], reason: str) -> None:
    db.sync_rejections.insert_one(
        {
            "event_id": event.get("eventId"),
            "employee_id": event.get("employeeId"),
            "device_id": event.get("deviceId"),
            "project_id": event.get("projectId"),
            "reason": reason,
            "received_at": datetime.now(timezone.utc),
        }
    )


def insert_benchmark_report(db, report: Dict[str, Any]) -> str:
    benchmark_id = f"bench_{uuid.uuid4().hex}"
    db.benchmark_reports.insert_one(
        {
            "benchmark_id": benchmark_id,
            "employee_id": report["employeeId"],
            "device_id": report["deviceId"],
            "project_id": report["projectId"],
            "app_version": report["appVersion"],
            "model_version": report["modelVersion"],
            "model_sha256": report["modelSha256"],
            "biometric_engine": report["biometricEngine"],
            "device_info": report["deviceInfo"],
            "iterations": report["iterations"],
            "average_ms": report["averageMs"],
            "p95_ms": report["p95Ms"],
            "max_ms": report["maxMs"],
            "target_ms": report["targetMs"],
            "within_target": report["withinTarget"],
            "captured_at": report["capturedAt"],
            "received_at": datetime.now(timezone.utc),
        }
    )
    return benchmark_id


def list_benchmark_reports(db, device_id: Optional[str] = None) -> List[Dict]:
    query = {"device_id": device_id} if device_id else {}
    cursor = db.benchmark_reports.find(query).sort("received_at", -1)
    return [normalize_doc(row) for row in cursor]


def list_attendance(db, employee_id: Optional[str] = None) -> List[Dict]:
    query = {"employee_id": employee_id} if employee_id else {}
    cursor = db.attendance_logs.find(query).sort("received_at", -1)
    return [normalize_doc(row) for row in cursor]
