
import cv2

print("Testing Mac webcam...")

# Menggunakan backend kamera macOS
cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)

print("Camera opened:", cap.isOpened())

if not cap.isOpened():
    print("[ERROR] Kamera tidak bisa dibuka.")
    raise SystemExit

print("[SUCCESS] Kamera berhasil dibuka!")
print("Tekan Q untuk keluar.")

while True:
    ret, frame = cap.read()

    if not ret:
        print("[ERROR] Gagal membaca frame.")
        break

    cv2.imshow("Mac Webcam Test", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
