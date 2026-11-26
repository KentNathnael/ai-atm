
import subprocess
import sys
import json
from pathlib import Path

# Lokasi folder model AI
AI_DIR = Path(__file__).resolve().parent / "ai"


def run_face_verification(card_id):
    print(f"\n[AI] Starting FaceNet for {card_id}...")

    # Jalankan model teman lo sebagai proses terpisah
    process = subprocess.run(
        [sys.executable, "main.py"],
        cwd=AI_DIR,
        input=card_id + "\n",
        text=True,
        capture_output=True
    )

    # Cari output AI_RESULT dari model
    result_line = None

    for line in process.stdout.splitlines():
        if "AI_RESULT:" in line:
            result_line = line.split("AI_RESULT:", 1)[1].strip()
            break

    if result_line is None:
        print("\n=== AI DEBUG ===")
        print("Exit code:", process.returncode)
        print("STDOUT:", repr(process.stdout))
        print("STDERR:", repr(process.stderr))

        raise RuntimeError(
            "Model tidak menghasilkan AI_RESULT"
        )

    # Ubah JSON menjadi Python dictionary
    result = json.loads(result_line)

    # Validasi hasil model
    if result.get("card_id") != card_id:
        raise RuntimeError("Card ID AI tidak sesuai")

    valid_status = (
        "APPROVED",
        "DECLINED",
        "RETRY",
        "ERROR"
    )

    if result.get("status") not in valid_status:
        raise RuntimeError("Status AI tidak valid")

    return result


# Testing AI Bridge secara terpisah
if __name__ == "__main__":
    card_id = input("Masukkan Card ID: ").strip().upper()

    try:
        result = run_face_verification(card_id)

        print("\n=== AI RESULT ===")
        print(json.dumps(result, indent=4))

    except Exception as error:
        print(f"[ERROR] {error}")
