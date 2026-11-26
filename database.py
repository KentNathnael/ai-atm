
import pymysql
from pymysql.cursors import DictCursor
from datetime import timedelta



# Konfigurasi database XAMPP
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "project_es",
    "port": 3306,
    "cursorclass": DictCursor
}


def get_connection():
    return pymysql.connect(**DB_CONFIG)


def get_card(card_id):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT
                    cf.card_id,
                    c.customer_name,
                    c.decline_count,
                    c.window_started_at,
                    c.blocked_until,
                    CASE
                        WHEN cf.face_image IS NULL
                        THEN 'NOT REGISTERED'
                        ELSE 'REGISTERED'
                    END AS face_status
                FROM card_faces cf
                JOIN customers c
                    ON cf.card_id = c.card_id
                WHERE cf.card_id = %s
            """

            cursor.execute(sql, (card_id,))
            result = cursor.fetchone()

            return result

    finally:
        connection.close()



def process_authentication(card_id, ai_result):
    # Hanya terima keputusan AI yang valid
    if ai_result not in ("APPROVED", "DECLINED"):
        raise ValueError("Invalid AI result")

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            # Gunakan waktu dari MySQL server
            cursor.execute("SELECT NOW() AS db_now")
            now = cursor.fetchone()["db_now"]

            # Kunci row selama counter diperbarui
            cursor.execute("""
                SELECT
                    decline_count,
                    window_started_at,
                    blocked_until
                FROM customers
                WHERE card_id = %s
                FOR UPDATE
            """, (card_id,))

            card = cursor.fetchone()

            if card is None:
                raise ValueError("Card not registered")

            count = card["decline_count"]
            window_start = card["window_started_at"]
            blocked_until = card["blocked_until"]

            # 1. Reset setelah periode 24 jam berakhir
            if window_start is not None:
                expiry = window_start + timedelta(hours=24)

                if now >= expiry:
                    count = 0
                    window_start = None
                    blocked_until = None

            # 2. Kartu masih dalam masa blokir
            if blocked_until is not None and now < blocked_until:
                status = "BLOCKED"
                command = "RETAIN"

            # 3. Verifikasi wajah berhasil
            elif ai_result == "APPROVED":
                status = "APPROVED"
                command = "CONTINUE"

            # 4. Verifikasi wajah gagal
            else:
                if window_start is None:
                    window_start = now

                count += 1

                if count >= 3:
                    count = 3
                    blocked_until = (
                        window_start + timedelta(hours=24)
                    )
                    status = "BLOCKED"
                    command = "RETAIN"

                else:
                    status = "DECLINED"
                    command = "EJECT"

            # 5. Simpan hasil terbaru
            cursor.execute("""
                UPDATE customers
                SET
                    decline_count = %s,
                    window_started_at = %s,
                    blocked_until = %s
                WHERE card_id = %s
            """, (
                count,
                window_start,
                blocked_until,
                card_id
            ))

        # Simpan perubahan permanen
        connection.commit()

        return {
            "card_id": card_id,
            "status": status,
            "decline_count": count,
            "command": command,
            "blocked_until": blocked_until
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def is_card_blocked(card_id):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    blocked_until,
                    NOW() AS db_now
                FROM customers
                WHERE card_id = %s
            """, (card_id,))

            card = cursor.fetchone()

            if card is None:
                return False

            blocked_until = card["blocked_until"]

            return (
                blocked_until is not None
                and card["db_now"] < blocked_until
            )

    finally:
        connection.close()


def reset_expired_counter(card_id):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            # Ambil waktu dari MySQL
            cursor.execute("SELECT NOW() AS db_now")
            now = cursor.fetchone()["db_now"]

            # Ambil informasi counter kartu
            cursor.execute("""
                SELECT
                    decline_count,
                    window_started_at
                FROM customers
                WHERE card_id = %s
                FOR UPDATE
            """, (card_id,))

            card = cursor.fetchone()

            if card is None:
                return False

            window_start = card["window_started_at"]

            if window_start is not None:
                expiry = window_start + timedelta(hours=24)

                if now >= expiry:
                    cursor.execute("""
                        UPDATE customers
                        SET
                            decline_count = 0,
                            window_started_at = NULL,
                            blocked_until = NULL
                        WHERE card_id = %s
                    """, (card_id,))

                    connection.commit()

                    print("[DATABASE] Counter reset setelah 24 jam!")
                    return True

        connection.commit()
        return False

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
