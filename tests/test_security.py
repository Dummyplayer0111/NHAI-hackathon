import unittest

from fastapi import HTTPException

from app.config import ADMIN_API_KEY
from app.security import require_admin_api_key, sign_payload, verify_signature


class SecurityTest(unittest.TestCase):
    def test_signature_is_stable_for_key_order(self):
        secret = "device-secret"
        payload = {"employeeId": "EMP102", "eventId": "evt_001"}
        reordered = {"eventId": "evt_001", "employeeId": "EMP102"}

        signature = sign_payload(payload, secret)

        self.assertTrue(verify_signature(reordered, secret, signature))

    def test_signature_rejects_tampered_payload(self):
        secret = "device-secret"
        payload = {"employeeId": "EMP102", "faceMatchScore": 0.82}
        signature = sign_payload(payload, secret)

        tampered = {"employeeId": "EMP102", "faceMatchScore": 0.2}

        self.assertFalse(verify_signature(tampered, secret, signature))

    def test_admin_key_accepts_configured_key(self):
        self.assertIsNone(require_admin_api_key(ADMIN_API_KEY))

    def test_admin_key_rejects_invalid_key(self):
        with self.assertRaises(HTTPException) as context:
            require_admin_api_key("wrong-key")

        self.assertEqual(context.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
