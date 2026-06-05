import hashlib
import json
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "MobileFaceNet.onnx"
MOBILE_MODEL = ROOT / "mobile" / "assets" / "models" / "MobileFaceNet.onnx"
REPORT = ROOT / "reports" / "submission-readiness.json"
API_BASE_URL = "http://127.0.0.1:8000"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: List[str], cwd: Path) -> Dict:
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return {
        "command": " ".join(command),
        "exitCode": completed.returncode,
        "durationMs": round((time.perf_counter() - started) * 1000, 2),
        "outputTail": completed.stdout[-1000:],
    }


def fetch(path: str) -> Dict:
    started = time.perf_counter()
    with urllib.request.urlopen(f"{API_BASE_URL}{path}", timeout=5) as response:
        body = json.loads(response.read())
    return {
        "path": path,
        "status": response.status,
        "durationMs": round((time.perf_counter() - started) * 1000, 2),
        "body": body,
    }


def main() -> None:
    REPORT.parent.mkdir(exist_ok=True)
    model_size_mb = MODEL.stat().st_size / (1024 * 1024)
    mobile_model_size_mb = MOBILE_MODEL.stat().st_size / (1024 * 1024)
    model_hash = sha256(MODEL)
    mobile_hash = sha256(MOBILE_MODEL)

    checks = {
        "backendTests": run([".venv/bin/python", "-m", "unittest", "discover", "-s", "tests"], ROOT),
        "pythonDependencies": run([".venv/bin/pip", "check"], ROOT),
        "mobileTypecheck": run(["npm", "run", "typecheck"], ROOT / "mobile"),
        "mobileLivenessCheck": run(["npm", "run", "test:liveness"], ROOT / "mobile"),
        "mobileCaptureCheck": run(["npm", "run", "test:capture"], ROOT / "mobile"),
        "mobileNativePrebuildCheck": run(["npm", "run", "test:native-prebuild"], ROOT / "mobile"),
        "mobileLivenessBenchmark": run(["npm", "run", "benchmark:liveness"], ROOT / "mobile"),
        "mobileAudit": run(["npm", "audit", "--audit-level=moderate"], ROOT / "mobile"),
        "expoCompatibility": run(["npx", "expo", "install", "--check"], ROOT / "mobile"),
        "expoProductionConfig": run(
            ["env", "APP_ENV=production", "npx", "expo", "config", "--type", "public"],
            ROOT / "mobile",
        ),
    }

    api = {
        "health": fetch("/health"),
        "modelMetadata": fetch("/model/metadata"),
        "systemRequirements": fetch("/system/requirements"),
    }

    benchmark_path = ROOT / "reports" / "mobile-liveness-benchmark.json"
    liveness_benchmark = (
        json.loads(benchmark_path.read_text(encoding="utf-8"))
        if benchmark_path.exists()
        else None
    )

    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "model": {
            "path": str(MODEL.relative_to(ROOT)),
            "mobilePath": str(MOBILE_MODEL.relative_to(ROOT)),
            "sizeMb": round(model_size_mb, 2),
            "mobileSizeMb": round(mobile_model_size_mb, 2),
            "targetSizeMb": 20,
            "withinTarget": model_size_mb <= 20 and mobile_model_size_mb <= 20,
            "sha256": model_hash,
            "mobileSha256": mobile_hash,
            "artifactsMatch": model_hash == mobile_hash,
        },
        "api": api,
        "checks": checks,
        "livenessBenchmark": liveness_benchmark,
        "summary": {
            "allAutomatedChecksPassed": all(check["exitCode"] == 0 for check in checks.values()),
            "backendReachable": api["health"]["status"] == 200,
            "modelIntegrityVerified": model_hash == mobile_hash,
            "livenessBenchmarkWithinTarget": bool(
                liveness_benchmark and liveness_benchmark.get("withinTarget")
            ),
        },
    }
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(REPORT)


if __name__ == "__main__":
    main()
