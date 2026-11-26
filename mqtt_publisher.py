
import paho.mqtt.client as mqtt

# MQTT Configuration
BROKER = "127.0.0.1"
PORT = 1883
TOPIC = "servo/control"

# Sesuai konfigurasi ESP32 teman
COMMAND_MAP = {
    "CONTINUE": "0",
    "EJECT": "1",
    "RETAIN": "-1"
}


def publish_servo(command):
    if command not in COMMAND_MAP:
        raise ValueError(f"Invalid command: {command}")

    payload = COMMAND_MAP[command]

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="FaceSecure_Laptop"
    )

    try:
        client.connect(BROKER, PORT, 60)
        client.loop_start()

        message = client.publish(
            topic=TOPIC,
            payload=payload,
            qos=1,
            retain=False
        )

        message.wait_for_publish(timeout=5)

        if not message.is_published():
            raise TimeoutError("MQTT publish timeout")

        print(f"[MQTT] Topic   : {TOPIC}")
        print(f"[MQTT] Payload : {payload}")
        print(f"[MQTT] Command : {command}")

    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    command = input(
        "Command (CONTINUE/EJECT/RETAIN): "
    ).strip().upper()

    publish_servo(command)
