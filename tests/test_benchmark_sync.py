import unittest

from app.config import MODEL_SHA256, MODEL_VERSION
from app.main import sync_benchmark_report
from app.repository import upsert_device, upsert_employee

from tests.test_service import FakeDb


class BenchmarkSyncTest(unittest.TestCase):
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

    def report(self):
        return {
            "employeeId": "EMP102",
            "deviceId": "DEVICE123",
            "projectId": "NH44-PKG07",
            "appVersion": "1.0.0",
            "modelVersion": MODEL_VERSION,
            "modelSha256": MODEL_SHA256,
            "biometricEngine": "onnx",
            "deviceInfo": {
                "platform": "android",
                "osVersion": "14",
                "model": "Midrange Test Device",
                "ramGb": 4,
            },
            "iterations": 100,
            "averageMs": 420,
            "p95Ms": 610,
            "maxMs": 740,
            "targetMs": 1000,
            "withinTarget": True,
            "capturedAt": "2026-06-05T09:30:00Z",
        }

    def test_accepts_valid_benchmark_report(self):
        from app import main
        original_get_db = main.get_db
        main.get_db = lambda: self.db
        try:
            response = sync_benchmark_report(
                main.BenchmarkReportRequest(**self.report()),
                x_device_secret="secret",
            )
        finally:
            main.get_db = original_get_db

        self.assertTrue(response.accepted)
        self.assertEqual(response.status, "success")

    def test_rejects_model_checksum_mismatch(self):
        from app import main
        payload = self.report()
        payload["modelSha256"] = "bad"
        original_get_db = main.get_db
        main.get_db = lambda: self.db
        try:
            response = sync_benchmark_report(
                main.BenchmarkReportRequest(**payload),
                x_device_secret="secret",
            )
        finally:
            main.get_db = original_get_db

        self.assertFalse(response.accepted)
        self.assertEqual(response.reason, "model_checksum_mismatch")

    def test_rejects_slow_benchmark(self):
        from app import main
        payload = self.report()
        payload["maxMs"] = 1300
        original_get_db = main.get_db
        main.get_db = lambda: self.db
        try:
            response = sync_benchmark_report(
                main.BenchmarkReportRequest(**payload),
                x_device_secret="secret",
            )
        finally:
            main.get_db = original_get_db

        self.assertFalse(response.accepted)
        self.assertEqual(response.reason, "benchmark_above_target")


if __name__ == "__main__":
    unittest.main()
