"""MQTT パブリッシャー：センサーデータ（模擬 or 実際の Pi メトリクス）を送信。
使い方:
  python3 04_mqtt_pub.py            # 模擬データ
  python3 04_mqtt_pub.py --real     # 実際の Pi メトリクス
"""
import argparse
import random
import subprocess
import time
import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 1883
INTERVAL = 5.0


def read_cpu_temp() -> float:
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return int(f.read().strip()) / 1000
    except FileNotFoundError:
        return round(random.uniform(45, 70), 1)


def read_cpu_usage() -> float:
    try:
        result = subprocess.run(
            ["top", "-bn1"], capture_output=True, text=True, timeout=3
        )
        for line in result.stdout.splitlines():
            if "Cpu(s)" in line or "%Cpu" in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if "us" in p or p == "us,":
                        return round(float(parts[i - 1].replace(",", ".")), 1)
    except Exception:
        pass
    return round(random.uniform(10, 90), 1)


def read_memory_usage() -> float:
    try:
        result = subprocess.run(["free"], capture_output=True, text=True, timeout=3)
        lines = result.stdout.splitlines()
        parts = lines[1].split()
        return round(int(parts[2]) / int(parts[1]) * 100, 1)
    except Exception:
        return round(random.uniform(40, 80), 1)


def main(use_real: bool):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(BROKER, PORT)
    client.loop_start()
    print(f"[pub] 接続: {BROKER}:{PORT}  ({'実メトリクス' if use_real else '模擬データ'})")

    try:
        while True:
            if use_real:
                cpu = read_cpu_usage()
                mem = read_memory_usage()
                temp = read_cpu_temp()
            else:
                cpu = round(random.uniform(10, 90), 1)
                mem = round(random.uniform(40, 80), 1)
                temp = round(random.uniform(45, 70), 1)

            for topic, value in [
                ("sensor/pi-master/cpu", cpu),
                ("sensor/pi-master/memory", mem),
                ("sensor/pi-master/temperature", temp),
            ]:
                client.publish(topic, str(value), qos=1)
                print(f"[pub] {topic} = {value}")

            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print("[pub] 終了")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--real", action="store_true", help="実際の Pi メトリクスを使う")
    args = parser.parse_args()
    main(args.real)
