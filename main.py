
from database import (
    get_card,
    is_card_blocked,
    process_authentication,
    reset_expired_counter
)

from ai_bridge import run_face_verification
from mqtt_publisher import publish_servo

def main():
    print("\n=== FACESECURE ATM ===")

    # 1. Simulasi RFID
    card_id = input(
        "Masukkan Card ID: "
    ).strip().upper()

    try:
        # 2. Reset counter jika sudah 24 jam
        reset_expired_counter(card_id)

        # 3. Ambil data kartu dari MySQL
        card = get_card(card_id)

        if card is None:
            print("[ERROR] Kartu tidak terdaftar!")
            return

        # 4. Cek apakah kartu diblokir
        if is_card_blocked(card_id):
            print("[ATM] CARD BLOCKED!")
            print("Kartu tidak dapat digunakan.")
            return

        print("\n=== DATA NASABAH ===")
        print(f"Card ID : {card['card_id']}")
        print(f"Nama    : {card['customer_name']}")
        print(f"Counter : {card['decline_count']}/3")

        # 5. Jalankan FaceNet secara otomatis
        ai_result = run_face_verification(card_id)

        status = ai_result["status"]

        print("\n=== AI RESULT ===")
        print(f"Status : {status}")
        print(f"Reason : {ai_result.get('reason')}")
        print(f"Match  : {ai_result.get('match_count', 0)}")

        # 6. Jangan tambah counter jika AI error
        if status in ("RETRY", "ERROR"):
            print("[ATM] Verifikasi belum berhasil.")
            print("[ATM] Counter tidak berubah.")
            return

        # 1. Proses hasil AI dan update MySQL
        result = process_authentication(
            card_id,
            status
        )

        print("\n=== ATM RESULT ===")
        print(f"Status  : {result['status']}")
        print(f"Counter : {result['decline_count']}/3")

        # 2. Ambil command dari controller
        command = result["command"]

        # 3. Kirim command melalui MQTT
        print(f"\n[ATM] Sending {command} to MQTT...")

        try:
            publish_servo(command)
            print("[ATM] MQTT publish confirmed!")

        except Exception as mqtt_error:
            print(f"[MQTT ERROR] {mqtt_error}")
            print("[WARNING] Counter MySQL sudah diperbarui.")
            print("Jangan ulangi autentikasi hanya untuk mengirim ulang MQTT.")
            return

        # 4. Informasi status kartu
        if result["status"] == "BLOCKED":
            print("[ATM] CARD BLOCKED!")
            print("[ATM] Tidak dapat melakukan transaksi.")

    except Exception as error:
        print(f"[ERROR] {error}")


if __name__ == "__main__":
    main()
