# 02 時間窓処理（タンブリング窓）

## 学習目標

- タンブリング窓・スライディング窓・セッション窓の違いを説明できる
- asyncio で固定時間のタンブリング窓を実装できる
- 窓ごとの集計結果を出力できる

---

## 1. 時間窓の種類

### タンブリング窓（Tumbling Window）

```
時間: ───────────────────────────────────────────►
      |   窓1   |   窓2   |   窓3   |   窓4   |
      0s        5s       10s       15s       20s

特徴:
  - 固定長・重複なし
  - 「1分ごとの合計」などに使う
  - 実装がシンプル
```

### スライディング窓（Sliding Window）

```
時間: ─────────────────────────────────────────────►
      |  窓1(0-10s)  |
           |  窓2(2-12s)  |
                |  窓3(4-14s)  |

特徴:
  - 固定長・重複あり（slide 間隔 < 窓幅）
  - 直近の傾向を追いたいときに使う
  - タンブリングより計算コストが高い
```

### セッション窓（Session Window）

```
時間: ──────────────────────────────────────────────►
      ●●● gap ●●●●  gap  ●
      |窓1|    |   窓2  |  |窓3|

特徴:
  - 一定時間イベントがなければ窓を閉じる
  - ユーザーのアクティビティ計測に使う
  - 窓のサイズが動的に変わる
```

---

## 2. タンブリング窓の実装

### 基本アイデア

```python
import time
import asyncio
from collections import defaultdict

WINDOW_SIZE = 5.0  # 5秒

async def tumbling_window_loop():
    window_start = time.time()
    counts = defaultdict(int)

    while True:
        now = time.time()
        if now - window_start >= WINDOW_SIZE:
            # 窓を閉じて集計を出力
            print(f"窓 [{window_start:.0f}-{now:.0f}]: {dict(counts)}")
            counts.clear()
            window_start = now
        
        # 次のイベントを処理 ...
        await asyncio.sleep(0.01)
```

### 整列した窓境界

上のコードは「起動時刻」を基準にする。
実用では「00:00, 05:00, 10:00 ...」のように壁時計に揃えたい。

```python
import math

def next_window_boundary(interval_sec: float) -> float:
    now = time.time()
    return math.ceil(now / interval_sec) * interval_sec

# 5秒窓なら次の 0, 5, 10, 15 ... 秒境界まで待つ
wait_until = next_window_boundary(5.0)
await asyncio.sleep(wait_until - time.time())
```

---

## 3. 実装：タンブリング窓カウンター

`python/stage3/02_tumbling_window.py` を実行する。

### 起動手順

```bash
# NATS が起動済みであること（docker/messaging/compose.yml）
python3 python/stage3/02_tumbling_window.py
```

### 期待する出力

```
[window] NATS 接続: nats://localhost:4222
[window] 窓サイズ: 5 秒

=== 窓 #1  2026-09-21 10:00:05 ===
  sensor=pi-cpu     件数=5  合計=195.3  平均=39.1  最大=52.4
  sensor=pi-memory  件数=5  合計=302.1  平均=60.4  最大=63.1
  sensor=pi-temp    件数=5  合計=256.0  平均=51.2  最大=53.5

=== 窓 #2  2026-09-21 10:00:10 ===
  sensor=pi-cpu     件数=5  合計=188.7  平均=37.7  最大=47.3
  ...
```

---

## 4. データジェネレーター

ラズパイが手元にないときは以下でダミーデータを生成できる。

```bash
# 別ターミナルで実行
python3 - <<'EOF'
import asyncio, random, time
import nats

async def gen():
    nc = await nats.connect("nats://localhost:4222")
    sensors = ["pi-cpu", "pi-memory", "pi-temp"]
    bases = {"pi-cpu": 40.0, "pi-memory": 60.0, "pi-temp": 50.0}
    while True:
        for s in sensors:
            val = bases[s] + random.gauss(0, 5)
            await nc.publish(f"events.sensor.{s}",
                             f'{{"sensor_id":"{s}","value":{val:.1f}}}'.encode())
        await asyncio.sleep(1.0)

asyncio.run(gen())
EOF
```

---

## 5. 窓処理の注意点

### 最後の窓が出力されない問題

ストリームが終了したとき、最後の窓境界に達していなければ集計が出力されない。
対策：プログラム終了時に `flush_window()` を呼ぶ。

```python
try:
    await asyncio.sleep(3600)
except KeyboardInterrupt:
    flush_window()  # 未完了の窓を出力
```

### 空の窓

イベントが来なかった窓は出力するか？
- 監視用途：空の窓も出力（「0件」が情報になる）
- 集計用途：空の窓はスキップでよい場合が多い

---

## 6. まとめ

| 窓の種類 | 重複 | 窓サイズ | 用途 |
|---------|------|---------|------|
| タンブリング | なし | 固定 | 定期集計（1分ごと・1時間ごと） |
| スライディング | あり | 固定 | リアルタイム傾向把握 |
| セッション | - | 動的 | ユーザー行動分析 |

次は **スライディング窓** と **異常検知** を実装する。
