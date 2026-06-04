import cv2
import csv
import numpy as np
import mediapipe as mp
import onnxruntime as ort
from numpy.linalg import norm

MODEL_PATH = "MobileFaceNet.onnx"
CSV_FILE = "employees.csv"
DUPLICATE_THRESHOLD = 0.75
FRAMES_REQUIRED = 5

# -----------------------------
# MobileFaceNet
# -----------------------------

session = ort.InferenceSession(MODEL_PATH)

input_name = session.get_inputs()[0].name
output_name = session.get_outputs()[0].name

# -----------------------------
# MediaPipe Face Detection
# -----------------------------

mp_face = mp.solutions.face_detection

face_detector = mp_face.FaceDetection(
    model_selection=0,
    min_detection_confidence=0.7
)

# -----------------------------
# Employee Details
# -----------------------------

employee_id = input("Employee ID: ")
name = input("Employee Name: ")

# -----------------------------
# Similarity Function
# -----------------------------

def cosine_similarity(a, b):
    return np.dot(a, b) / (
        norm(a) * norm(b)
    )

# -----------------------------
# Embedding Function
# -----------------------------

def get_embedding(face_img):

    face_img = cv2.resize(
        face_img,
        (112, 112)
    )

    face_img = cv2.cvtColor(
        face_img,
        cv2.COLOR_BGR2RGB
    )

    face_img = face_img.astype(
        np.float32
    )

    face_img = (
        face_img - 127.5
    ) / 128.0

    face_img = np.transpose(
        face_img,
        (2, 0, 1)
    )

    face_img = np.expand_dims(
        face_img,
        axis=0
    )

    embedding = session.run(
        [output_name],
        {input_name: face_img}
    )[0]

    return embedding.flatten()

# -----------------------------
# Camera
# -----------------------------

cap = cv2.VideoCapture(0)

print("\nLook at camera and press S")

collecting = False
embeddings_collected = []

while True:

    ret, frame = cap.read()

    if not ret:
        break

    rgb = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    results = face_detector.process(rgb)

    face = None

    if results.detections:

        detection = results.detections[0]

        bbox = (
            detection
            .location_data
            .relative_bounding_box
        )

        h, w, _ = frame.shape

        x = int(bbox.xmin * w)
        y = int(bbox.ymin * h)

        bw = int(bbox.width * w)
        bh = int(bbox.height * h)

        x = max(0, x)
        y = max(0, y)

        pad = 20

        x1 = max(0, x - pad)
        y1 = max(0, y - pad)

        x2 = min(w, x + bw + pad)
        y2 = min(h, y + bh + pad)

        face = frame[y1:y2, x1:x2]

        cv2.rectangle(
            frame,
            (x, y),
            (x + bw, y + bh),
            (0, 255, 0),
            2
        )

    # -------------------------
    # Collect frames when S held
    # -------------------------

    if collecting and face is not None:

        embedding = get_embedding(face)

        emb_norm = np.linalg.norm(embedding)

        if emb_norm > 0:
            embedding = embedding / emb_norm

        embeddings_collected.append(embedding)

        count = len(embeddings_collected)

        cv2.putText(
            frame,
            f"Capturing... {count}/{FRAMES_REQUIRED}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 255),
            2
        )

    elif not collecting:

        label = (
            "Press S to Save"
            if face is not None
            else "No face detected"
        )

        cv2.putText(
            frame,
            label,
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )

    cv2.imshow("Enrollment", frame)

    key = cv2.waitKey(1)

    # -------------------------
    # Start collecting on S
    # -------------------------

    if key == ord('s') and not collecting:

        if face is None:
            print("No face detected.")
        else:
            collecting = True
            embeddings_collected = []
            print(f"\nCollecting {FRAMES_REQUIRED} frames...")

    # -------------------------
    # Process after enough frames
    # -------------------------

    if collecting and len(embeddings_collected) >= FRAMES_REQUIRED:

        collecting = False

        # Average and re-normalize
        avg_embedding = np.mean(embeddings_collected, axis=0)

        avg_norm = np.linalg.norm(avg_embedding)

        if avg_norm > 0:
            avg_embedding = avg_embedding / avg_norm

        already_registered = False
        best_score = 0
        best_name = None

        try:

            with open(CSV_FILE, "r") as f:

                reader = csv.reader(f)

                for row in reader:

                    if len(row) < 3:
                        continue

                    if row[0] == employee_id:

                        print(
                            f"ERROR: Employee ID "
                            f"{employee_id} "
                            f"already exists."
                        )

                        already_registered = True
                        break

                    stored_embedding = np.array(
                        list(
                            map(float, row[2].split(","))
                        )
                    )

                    norm_val = np.linalg.norm(stored_embedding)

                    if norm_val > 0:
                        stored_embedding = stored_embedding / norm_val

                    score = cosine_similarity(
                        avg_embedding,
                        stored_embedding
                    )

                    print(
                        f"Comparing with "
                        f"{row[1]} -> "
                        f"{score:.4f}"
                    )

                    if score > best_score:
                        best_score = score
                        best_name = row[1]

        except FileNotFoundError:
            pass

        # -------------------------
        # Best Match Check
        # -------------------------

        if (
            best_score >= DUPLICATE_THRESHOLD
            and not already_registered
        ):

            print(
                f"\nERROR: Face already "
                f"registered as {best_name}"
            )

            print(
                f"Best Similarity: "
                f"{best_score:.4f}"
            )

            already_registered = True

        if not already_registered:

            with open(CSV_FILE, "a", newline="") as f:

                writer = csv.writer(f)

                writer.writerow([
                    employee_id,
                    name,
                    ",".join(map(str, avg_embedding))
                ])

            print("\nEmployee Enrolled Successfully")

        break

    if key == 27:
        break

cap.release()
face_detector.close()
cv2.destroyAllWindows()