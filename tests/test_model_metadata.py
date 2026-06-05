import unittest

from app.config import MODEL_SHA256
from app.main import model_metadata


class ModelMetadataTest(unittest.TestCase):
    def test_model_metadata_exposes_checksum_and_size_target(self):
        metadata = model_metadata()

        self.assertEqual(metadata["sha256"], MODEL_SHA256)
        self.assertTrue(metadata["withinTargetSize"])
        self.assertLessEqual(metadata["sizeMb"], metadata["targetSizeMb"])


if __name__ == "__main__":
    unittest.main()
