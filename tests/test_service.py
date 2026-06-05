import unittest
from datetime import datetime, timezone

from app.repository import insert_attendance, upsert_device, upsert_employee
from app.security import sign_payload
from app.config import MODEL_VERSION
from app.service import signature_payload, validate_attendance_event


class FakeCursor(list):
    def sort(self, key, direction):
        reverse = direction == -1
        return FakeCursor(sorted(self, key=lambda row: row.get(key), reverse=reverse))


class FakeCollection:
    def __init__(self):
        self.rows = []

    def update_one(self, query, update, upsert=False):
        row = self.find_one(query)
        if row is None:
            row = {}
            self.rows.append(row)
        row.update(update.get("$setOnInsert", {}))
        row.update(update.get("$set", {}))
        for key, value in update.get("$max", {}).items():
            row[key] = max(row.get(key, value), value)

    def find_one(self, query):
        for row in self.rows:
            if all(row.get(key) == value for key, value in query.items()):
                return row
        return None

    def insert_one(self, row):
        self.rows.append(row)

    def find(self, query):
        return FakeCursor(
            row
            for row in self.rows
            if all(row.get(key) == value for key, value in query.items())
        )


class FakeDb:
    def __init__(self):
        self.employees = FakeCollection()
        self.devices = FakeCollection()
        self.attendance_logs = FakeCollection()
        self.benchmark_reports = FakeCollection()


class AttendanceValidationTest(unittest.TestCase):
    def setUp(self):
        self.db = FakeDb()
        upsert_employee(
            self.db,
            "EMP102",
            "Ramesh",
            "NH44-PKG07",
            {"embedding": [0.1, 0.2]},
        )
        upsert_device(
            self.db,
            "DEVICE123",
            "EMP102",
            "NH44-PKG07",
            "secret",
        )

    def base_event(self):
        return {
            "eventId": "evt_001",
            "employeeId": "EMP102",
            "deviceId": "DEVICE123",
            "projectId": "NH44-PKG07",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latitude": 12.9716,
            "longitude": 77.5946,
            "locationAccuracyMeters": 12,
            "faceMatchScore": 0.82,
            "livenessPassed": True,
            "livenessScore": 0.91,
            "faceQualityPassed": True,
            "faceQualityScore": 0.88,
            "faceQualityReasons": [],
            "challenge": ["blink"],
            "modelVersion": MODEL_VERSION,
            "biometricEngine": "prototype",
            "deviceSequence": 1,
            "syncStatus": "pending",
        }

    def test_accepts_valid_signed_event(self):
        event = self.base_event()
        signature = sign_payload(signature_payload(event), "secret")

        valid, reason = validate_attendance_event(
            self.db,
            event,
            signature,
            "secret",
        )

        self.assertTrue(valid)
        self.assertEqual(reason, "ok")

    def test_rejects_low_face_score(self):
        event = self.base_event()
        event["faceMatchScore"] = 0.3
        signature = sign_payload(signature_payload(event), "secret")

        valid, reason = validate_attendance_event(
            self.db,
            event,
            signature,
            "secret",
        )

        self.assertFalse(valid)
        self.assertEqual(reason, "face_score_below_threshold")

    def test_rejects_invalid_device_secret(self):
        event = self.base_event()
        signature = sign_payload(signature_payload(event), "secret")

        valid, reason = validate_attendance_event(
            self.db,
            event,
            signature,
            "wrong-secret",
        )

        self.assertFalse(valid)
        self.assertEqual(reason, "invalid_device_secret")

    def test_rejects_low_liveness_score(self):
        event = self.base_event()
        event["livenessScore"] = 0.2
        signature = sign_payload(signature_payload(event), "secret")

        valid, reason = validate_attendance_event(
            self.db,
            event,
            signature,
            "secret",
        )

        self.assertFalse(valid)
        self.assertEqual(reason, "liveness_score_below_threshold")

    def test_rejects_model_version_mismatch(self):
        event = self.base_event()
        event["modelVersion"] = "unknown-model"
        signature = sign_payload(signature_payload(event), "secret")

        valid, reason = validate_attendance_event(
            self.db,
            event,
            signature,
            "secret",
        )

        self.assertFalse(valid)
        self.assertEqual(reason, "model_version_mismatch")

    def test_rejects_failed_face_quality(self):
        event = self.base_event()
        event["faceQualityPassed"] = False
        event["faceQualityReasons"] = ["image_blurry"]
        signature = sign_payload(signature_payload(event), "secret")

        valid, reason = validate_attendance_event(
            self.db,
            event,
            signature,
            "secret",
        )

        self.assertFalse(valid)
        self.assertEqual(reason, "face_quality_failed")

    def test_rejects_poor_location_accuracy(self):
        event = self.base_event()
        event["locationAccuracyMeters"] = 250
        signature = sign_payload(signature_payload(event), "secret")

        valid, reason = validate_attendance_event(
            self.db,
            event,
            signature,
            "secret",
        )

        self.assertFalse(valid)
        self.assertEqual(reason, "location_accuracy_too_low")

    def test_rejects_missing_face_quality(self):
        event = self.base_event()
        event.pop("faceQualityPassed")
        signature = sign_payload(signature_payload(event), "secret")

        valid, reason = validate_attendance_event(
            self.db,
            event,
            signature,
            "secret",
        )

        self.assertFalse(valid)
        self.assertEqual(reason, "missing_face_quality")

    def test_rejects_missing_location_accuracy(self):
        event = self.base_event()
        event.pop("locationAccuracyMeters")
        signature = sign_payload(signature_payload(event), "secret")

        valid, reason = validate_attendance_event(
            self.db,
            event,
            signature,
            "secret",
        )

        self.assertFalse(valid)
        self.assertEqual(reason, "missing_location_accuracy")

    def test_rejects_replayed_device_sequence(self):
        self.db.devices.update_one(
            {"device_id": "DEVICE123"},
            {"$set": {"last_sequence": 10}},
        )
        event = self.base_event()
        event["deviceSequence"] = 10
        signature = sign_payload(signature_payload(event), "secret")

        valid, reason = validate_attendance_event(
            self.db,
            event,
            signature,
            "secret",
        )

        self.assertFalse(valid)
        self.assertEqual(reason, "device_sequence_replay")

    def test_insert_advances_last_device_sequence(self):
        event = self.base_event()
        event["deviceSequence"] = 42

        insert_attendance(self.db, event, "signature")

        device = self.db.devices.find_one({"device_id": "DEVICE123"})
        self.assertEqual(device["last_sequence"], 42)


if __name__ == "__main__":
    unittest.main()
