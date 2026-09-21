"""MQTT サブスクライバー：センサーデータを受信して表示。
使い方:
  python3 04_mqtt_sub.py
"""
import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 1883
TOPIC = "sensor/pi-master/#"


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"[sub] 接続: {BROKER}:{PORT}")
    client.subscribe(TOPIC, qos=1)
    print(f"[sub] 購読: {TOPIC}")


def on_message(client, userdata, msg):
    value = msg.payload.decode()
    print(f"[sub] {msg.topic}: {value}")


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("[sub] 終了")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
