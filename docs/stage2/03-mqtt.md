# 03 MQTT

## 学習目標

- MQTT のブローカーモデルを理解し、Mosquitto を Docker で起動できる
- トピック階層（`sensor/pi-master/cpu`）を設計できる
- QoS レベル 0/1/2 の違いを理解する
- `paho-mqtt` で Publish / Subscribe を実装できる
- Pi の CPU 温度を定期送信するスクリプトを動かせる

---

## 1. 概念説明

### MQTT とは

MQTT（Message Queuing Telemetry Transport）は IoT 向けに設計された軽量な Pub/Sub プロトコルです。
HTTP より **はるかに小さいヘッダー（2 バイト〜）** で動くため、センサーや組み込みデバイスに向いています。

```
【MQTT のアーキテクチャ】

  デバイス A      ブローカー      サブスクライバー
  (Publisher)     (Mosquitto)     (Subscriber)
      │                │                │
      │─ Publish ─────►│                │
      │  topic=sensor/cpu               │
      │  payload=42.5                   │
      │                │─ Deliver ─────►│ (sensor/# を購読)
      │                │                │
```

### トピックの設計

MQTT のトピックは `/` で区切った階層構造です。

```
sensor/pi-master/cpu        ← Pi master の CPU 使用率
sensor/pi-master/memory     ← Pi master のメモリ使用率
sensor/pi-master/temperature ← Pi master の CPU 温度
sensor/+/cpu                ← 全ノードの CPU（+ は 1 レベルのワイルドカード）
sensor/#                    ← sensor 以下すべて（# は複数レベルのワイルドカード）
```

### QoS レベル

| QoS | 意味 | 配送保証 | 重複 | 用途 |
|---|---|---|---|---|
| **0** | 最大 1 回 | なし | なし | センサーの速報値 |
| **1** | 最低 1 回 | あり | あり（可能性）| 重要なイベント |
| **2** | 厳密に 1 回 | あり | なし | 決済・命令 |

---

## 2. Mosquitto を Docker で起動する

```bash
# docker/messaging ディレクトリへ移動
cd ~/dps-study/docker/messaging

# Mosquitto ブローカーを起動
docker compose up -d mosquitto

# 起動確認
docker ps | grep mosquitto
# CONTAINER ID   IMAGE                STATUS
# xxx            eclipse-mosquitto    Up X seconds
```

### Mosquitto の設定確認

```bash
# ブローカーのログを確認
docker logs mosquitto

# ポート確認（1883: MQTT, 9001: WebSocket）
ss -tlnp | grep 1883
```

---

## 3. paho-mqtt のインストール

```bash
pip install paho-mqtt

python3 -c "import paho.mqtt.client; print('OK')"
# OK
```

---

## 4. MQTT で Pub/Sub する

### 4.1 サブスクライバーを先に起動する

**ターミナル 1（サブスクライバー）:**

```bash
python3 python/stage2/04_mqtt_sub.py
```

**ターミナル 2（パブリッシャー）:**

```bash
python3 python/stage2/04_mqtt_pub.py
```

期待する出力：

```
# サブスクライバー
[sub] 接続: localhost:1883
[sub] 購読: sensor/pi-master/#
[sub] sensor/pi-master/cpu: 42.5
[sub] sensor/pi-master/memory: 61.3
[sub] sensor/pi-master/temperature: 55.2

# パブリッシャー
[pub] sensor/pi-master/cpu = 42.5
[pub] sensor/pi-master/memory = 61.3
[pub] sensor/pi-master/temperature = 55.2
```

### 4.2 コマンドラインツールでも確認できる

```bash
# Docker コンテナから mosquitto_sub で購読
docker exec mosquitto mosquitto_sub -t "sensor/#" -v

# 別ターミナルから送信
docker exec mosquitto mosquitto_pub -t "sensor/test" -m "hello"
```

---

## 5. Pi の実際のメトリクスを送信する

Pi 3B で以下のコマンドでメトリクスを取得できます：

```bash
# CPU 温度（°C）
cat /sys/class/thermal/thermal_zone0/temp
# 55000 → 55.0°C（1000 で割る）

# CPU 使用率（%）
top -bn1 | grep "Cpu(s)" | awk '{print $2}'

# メモリ使用率
free | awk 'NR==2{printf "%.1f", $3/$2*100}'
```

これらを自動送信するスクリプト `04_mqtt_pub.py` を使います：

```bash
# Pi 3B の実際のメトリクスを 5 秒ごとに送信
python3 python/stage2/04_mqtt_pub.py --real
```

---

## 6. よくあるエラーと対処法

### `Connection refused` エラー

```
paho.mqtt.client.socket.error: [Errno 111] Connection refused
```

→ Mosquitto コンテナが起動しているか確認する

```bash
docker ps | grep mosquitto
docker logs mosquitto
```

### メッセージが届かない

- `SUBSCRIBE` のトピックとパブリッシャーのトピックが一致しているか確認
- ワイルドカード（`+`、`#`）を確認

```bash
# デバッグ: 全メッセージを表示
docker exec mosquitto mosquitto_sub -t "#" -v
```

### QoS 1/2 で重複配送される

QoS 1 では再送時に同じメッセージが 2 回届くことがあります。
冪等な処理（同じメッセージを 2 回処理しても結果が変わらない）を設計します。

---

## 7. まとめと次のステップ

### 今回の学習内容

| 項目 | 習得内容 |
|---|---|
| MQTT の仕組み | ブローカー経由の Pub/Sub |
| トピック設計 | 階層構造・ワイルドカード |
| QoS | 0（速報）/ 1（重要）/ 2（厳密）|
| paho-mqtt | connect・publish・subscribe |

### 次のステップ

`04-nats.md` では NATS を使います。
MQTT より高スループットで、Request/Reply も組み込みでサポートしています。

```bash
cat docs/stage2/04-nats.md
```
