# Security And Production Readiness

This system handles personnel authentication and attendance, so the production deployment must be treated as a security-sensitive government workload.

## Implemented Controls

- Admin-only backend routes require `X-Admin-API-Key`.
- Production mode refuses to start with the default admin key.
- Device profile download requires `X-Device-Secret`.
- Device secrets are hashed before storage in MongoDB.
- Offline attendance records are HMAC-SHA256 signed by the mobile device.
- Backend verifies device, employee, project, timestamp, duplicate event ID, face score, liveness result, liveness score, model version, and HMAC before storage.
- Backend enforces monotonic `deviceSequence` values per registered device to reduce replay/reordering risk.
- Benchmark reports are authenticated with device secret and checked against registered employee/device/project plus model version and checksum.
- Backend returns `purgeAllowed: true` only after accepted MongoDB insert.
- Rejected sync attempts are logged to `sync_rejections`.
- API responses include defensive HTTP headers.
- Optional CORS and trusted-host allowlists are configured through environment variables.
- Basic in-process rate limiting is included for prototype protection.
- Mobile app stores device session and pending attendance queue in platform secure storage.
- Mobile app has a separate biometric engine boundary so production builds can disable the prototype adapter.
- Mobile app has a face-capture boundary for native camera crop/landmark extraction, plus a documented `NHAIFaceCapture` native module contract and payload validator.
- Mobile liveness scoring includes blink EAR, smile ratio, head-turn yaw, and face-quality checks before signing attendance.
- Production backend policy rejects non-ONNX biometric engine evidence when `APP_ENV=production`.
- Mobile dependency audit currently reports zero vulnerabilities.

## Required Production Environment

Set these values for any non-local deployment:

```bash
export APP_ENV="production"
export ADMIN_API_KEY="<strong-random-admin-key>"
export MONGODB_URI="<mongodb-atlas-or-private-mongodb-uri>"
export MONGODB_DB_NAME="attendance_db"
export ALLOWED_ORIGINS="https://your-admin-domain.example"
export ALLOWED_HOSTS="api.your-domain.example"
export FACE_MATCH_THRESHOLD="0.75"
export LIVENESS_SCORE_THRESHOLD="0.70"
export RATE_LIMIT_REQUESTS_PER_MINUTE="120"
```

An example is provided in `.env.example`. The backend can be containerized with `Dockerfile` and `docker-compose.yml`; do not deploy with the example admin key.

## Recommended Production Additions

For a real government rollout, add these around the prototype:

- API Gateway or AWS WAF for rate limiting, IP allowlisting, bot filtering, and request logging.
- Managed secrets through AWS Secrets Manager or Parameter Store.
- TLS termination with HSTS at the load balancer/API gateway.
- MongoDB Atlas private endpoint or VPC-hosted MongoDB with encrypted storage and backups.
- Device attestation:
  - Android Play Integrity API
  - iOS DeviceCheck/App Attest
- Certificate pinning in the mobile app.
- Jailbreak/root detection signal in sync metadata.
- Signed model manifest with checksum verification before enabling offline authentication.
- Backend `/model/metadata` and offline profile responses expose the model SHA-256 checksum.
- Mobile profile download rejects backend profiles whose model version/checksum do not match the bundled model.
- Role-based admin portal instead of static admin API key.
- Central audit log export to SIEM.
- Formal biometric accuracy evaluation:
  - false accept rate
  - false reject rate
  - demographic and lighting split
  - spoof test cases using print/photo/screen/video attacks

## Mobile Production Switch

`mobile/app.json` currently enables the prototype biometric adapter:

```json
"enablePrototypeBiometricAdapter": true
```

For production, set it to `false`. The app will route through `mobile/src/services/onnxFaceEngine.ts`, which loads bundled `MobileFaceNet.onnx` through `onnxruntime-react-native`, preprocesses `112x112` RGB face crops, and compares the embedding with the offline template.

Production builds can enforce this with:

```bash
APP_ENV=production ENABLE_PROTOTYPE_BIOMETRIC_ADAPTER=false npm run android
```

`mobile/app.config.js` defaults the prototype adapter to disabled whenever `APP_ENV=production`.

## Data Retention

The intended retention model is:

- Mobile stores only active offline profile and pending attendance queue.
- Mobile deletes pending records only after `purgeAllowed: true`.
- Backend stores accepted attendance logs and rejection audit events.
- Backend retention policy should be configured according to NHAI/Datalake data governance rules.
