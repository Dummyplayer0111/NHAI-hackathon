import cv2
import csv
import numpy as np
import mediapipe as mp
import onnxruntime as ort
from numpy.linalg import norm
from datetime import date, datetime

MODEL_PATH = "MobileFaceNet.onnx"
CSV_FILE = "employees.csv"
ATTENDANCE_FILE = "attendance.csv"
RECOGNITION_THRESHOLD = 0.60
FACE_PAD = 20

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
# Embedding Function
# -----------------------------

def get_embedding(face_img):

    face_img = cv2.resize(face_img, (112, 112))

    face_img = cv2.cvtColor(
        face_img,
        cv2.COLOR_BGR2RGB
    )

    face_img = face_img.astype(np.float32)

    face_img = (face_img - 127.5) / 128.0

    face_img = np.transpose(face_img, (2, 0, 1))

    face_img = np.expand_dims(face_img, axis=0)

    embedding = session.run(
        [output_name],
        {input_name: face_img}
    )[0]

    return embedding.flatten()

# -----------------------------
# Similarity Function
# -----------------------------

def cosine_similarity(a, b):
    return np.dot(a, b) / (
        norm(a) * norm(b)
    )

# -----------------------------
# Attendance Functions
# -----------------------------

def load_todays_attendance():
    """Returns a set of employee IDs already marked today."""

    marked = set()
    today = str(date.today())

    try:

        with open(ATTENDANCE_FILE, "r") as f:

            reader = csv.reader(f)

            for row in reader:

                if len(row) < 3:
                    continue

                if row[2] == today:
                    marked.add(row[0])

    except FileNotFoundError:
        pass

    return marked


def mark_attendance(employee_id, name, marked_today):
    """
    Marks attendance for the employee.
    Returns True if marked, False if already marked today.
    """

    if employee_id in marked_today:
        return False

    today = str(date.today())
    time_now = datetime.now().strftime("%H:%M:%S")

    with open(ATTENDANCE_FILE, "a", newline="") as f:

        writer = csv.writer(f)

        writer.writerow([
            employee_id,
            name,
            today,
            time_now
        ])

    marked_today.add(employee_id)

    return True

# -----------------------------
# Load Employees
# -----------------------------

employees = []

try:

    with open(CSV_FILE, "r") as f:

        reader = csv.reader(f)

        for row in reader:

            if len(row) < 3:
                continue

            stored_embedding = np.array(
                list(map(float, row[2].split(",")))
            )

            emb_norm = np.linalg.norm(stored_embedding)

            if emb_norm > 0:
                stored_embedding = stored_embedding / emb_norm

            employees.append({
                "id": row[0],
                "name": row[1],
                "embedding": stored_embedding
            })

    print(f"Loaded {len(employees)} employee(s).")

except FileNotFoundError:
    print("No employees enrolled yet.")

# -----------------------------
# Load today's attendance
# -----------------------------

marked_today = load_todays_attendance()

print(f"Already marked today: {len(marked_today)} employee(s).")

# -----------------------------
# Camera
# -----------------------------

cap = cv2.VideoCapture(0)

# Holds the current recognized employee
current_employee = None
status_msg = ""
status_color = (255, 255, 255)

print("\nPress A to mark attendance | ESC to quit")

while True:

    ret, frame = cap.read()

    if not ret:
        continue

    rgb = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    results = face_detector.process(rgb)

    current_employee = None

    if results.detections:

        detection = results.detections[0]

        bbox = detection.location_data.relative_bounding_box

        h, w, _ = frame.shape

        x = int(bbox.xmin * w)
        y = int(bbox.ymin * h)
        bw = int(bbox.width * w)
        bh = int(bbox.height * h)

        x = max(0, x)
        y = max(0, y)

        x1 = max(0, x - FACE_PAD)
        y1 = max(0, y - FACE_PAD)
        x2 = min(w, x + bw + FACE_PAD)
        y2 = min(h, y + bh + FACE_PAD)

        face = frame[y1:y2, x1:x2]

        embedding = get_embedding(face)

        emb_norm = np.linalg.norm(embedding)

        if emb_norm > 0:
            embedding = embedding / emb_norm

        best_match = None
        best_score = 0

        for emp in employees:

            score = cosine_similarity(
                embedding,
                emp["embedding"]
            )

            if score > best_score:
                best_score = score
                best_match = emp

        if best_score >= RECOGNITION_THRESHOLD:

            current_employee = best_match

            already_marked = (
                best_match["id"] in marked_today
            )

            label = (
                f"{best_match['name']} ({best_score:.2f})"
                f" [Marked]" if already_marked
                else f"{best_match['name']} ({best_score:.2f})"
                f" - Press A"
            )

            color = (0, 200, 255) if already_marked else (0, 255, 0)

        else:

            label = "Unknown"
            color = (0, 0, 255)

        cv2.rectangle(
            frame,
            (x, y),
            (x + bw, y + bh),
            color,
            2
        )

        cv2.putText(
            frame,
            label,
            (x, y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2
        )

    # Status message overlay (bottom of frame)
    if status_msg:

        cv2.putText(
            frame,
            status_msg,
            (20, frame.shape[0] - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            status_color,
            2
        )

    cv2.imshow("Recognition", frame)

    key = cv2.waitKey(1)

    # -------------------------
    # Mark Attendance on A
    # -------------------------

    if key == ord('a'):

        if current_employee is None:

            status_msg = "No recognized face to mark."
            status_color = (0, 0, 255)

        else:

            marked = mark_attendance(
                current_employee["id"],
                current_employee["name"],
                marked_today
            )

            if marked:

                status_msg = (
                    f"Attendance marked for "
                    f"{current_employee['name']}!"
                )

                status_color = (0, 255, 0)

                print(status_msg)

            else:

                status_msg = (
                    f"{current_employee['name']} "
                    f"already marked today."
                )

                status_color = (0, 200, 255)

                print(status_msg)

    if key == 27:
        break

cap.release()
face_detector.close()
cv2.destroyAllWindows()