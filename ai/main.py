
import cv2
import torch
import numpy as np
import json
import math
import time

from PIL import Image
from pathlib import Path
from facenet_pytorch import MTCNN, InceptionResnetV1


# ==========================================
# 1. INITIALIZATION
# ==========================================

device = torch.device(
    'cuda' if torch.cuda.is_available() else 'cpu'
)

mtcnn = MTCNN(
    image_size=160,
    margin=0,
    keep_all=True,
    device=device
)

model = InceptionResnetV1(
    pretrained='vggface2'
).eval().to(device)


# ==========================================
# 2. CONFIGURATION
# ==========================================

FRAME_COUNT = 10

THRESHOLD = 0.7

MIN_VALID_FRAMES = 8

MATCH_RATIO = 0.8


# ==========================================
# 3. LOAD CUSTOMER DATABASE
# ==========================================

with open("customers.json", "r") as file:
    customers = json.load(file)

database = {}

print("Loading customer database...")

for card_number, image_path in customers.items():

    image = Image.open(image_path).convert("RGB")

    faces = mtcnn(image)

    if faces is None:
        print(f"Face not detected: {card_number}")
        continue

    if faces.ndim == 3:
        faces = faces.unsqueeze(0)

    # Use first detected face in reference image
    with torch.no_grad():
        embedding = model(
            faces[0].unsqueeze(0).to(device)
        )

    database[card_number] = embedding

print("Customer database loaded!")


# ==========================================
# 4. CARD AUTHENTICATION
# ==========================================

card_number = input("Insert ATM card number: ").strip().upper()

if card_number not in database:
    output = {
        "card_id": card_number,
        "status": "ERROR",
        "reason": "CARD_NOT_FOUND"
    }

    print("\nAI_RESULT:" + json.dumps(output), flush=True)
    raise SystemExit


reference_embedding = database[card_number]


# ==========================================
# 5. OPEN WEBCAM
# ==========================================

cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)

if not cap.isOpened():
    output = {
        "card_id": card_number,
        "status": "ERROR",
        "reason": "CAMERA_UNAVAILABLE"
    }

    print("\nAI_RESULT:" + json.dumps(output), flush=True)
    raise SystemExit


# ==========================================
# 6. CAPTURE AND PROCESS 10 FRAMES
# ==========================================

match_count = 0
valid_frames = 0

for frame_number in range(FRAME_COUNT):

    ret, frame = cap.read()

    if not ret:
        break

    rgb = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    webcam_image = Image.fromarray(rgb)

    # Detect all faces
    faces = mtcnn(webcam_image)

    boxes, probs = mtcnn.detect(webcam_image)

    result_text = "No face detected"

    if faces is not None and boxes is not None:

        if faces.ndim == 3:
            faces = faces.unsqueeze(0)

        # Find the largest face bounding box
        areas = []

        for box in boxes:

            x1, y1, x2, y2 = box

            area = (x2 - x1) * (y2 - y1)

            areas.append(area)

        largest_index = int(np.argmax(areas))

        if largest_index < len(faces):

            # Select only the closest face
            selected_face = faces[largest_index]

            # Generate webcam embedding
            with torch.no_grad():

                embedding = model(
                    selected_face.unsqueeze(0).to(device)
                )

            # Compare with card owner's embedding
            distance = torch.norm(
                reference_embedding - embedding
            ).item()

            valid_frames += 1

            # Matching decision
            if distance < THRESHOLD:

                match_count += 1

                result_text = "MATCH"

                color = (0, 255, 0)

            else:

                result_text = "NOT MATCH"

                color = (0, 0, 255)

            # Draw only the selected face
            x1, y1, x2, y2 = map(
                int,
                boxes[largest_index]
            )

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                color,
                2
            )

            cv2.putText(
                frame,
                result_text,
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2
            )

    # Show capture progress
    cv2.putText(
        frame,
        f"Frame: {frame_number + 1}/{FRAME_COUNT}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )

    cv2.imshow("ATM Face Authentication", frame)

    cv2.waitKey(1)

    time.sleep(0.1)

# ==========================================
# CLOSE WEBCAM
# ==========================================

cap.release()
cv2.destroyAllWindows()

# ==========================================
# 7. FINAL AUTHENTICATION DECISION
# ==========================================

required_matches = math.ceil(FRAME_COUNT * MATCH_RATIO)

if valid_frames < MIN_VALID_FRAMES:
    status = "RETRY"
    reason = "INSUFFICIENT_VALID_FRAMES"

elif match_count >= required_matches:
    status = "APPROVED"
    reason = "FACE_MATCHED"

else:
    status = "DECLINED"
    reason = "FACE_NOT_MATCHED"

# ==========================================
# 8. JSON OUTPUT
# ==========================================

output = {
    "card_id": card_number,
    "status": status,
    "match_count": match_count,
    "valid_frames": valid_frames,
    "total_frames": FRAME_COUNT,
    "reason": reason
}

print("\nAI_RESULT:" + json.dumps(output), flush=True)