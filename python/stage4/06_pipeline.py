"""Ray + Dask 統合パイプライン：Ray でリアルタイム集計、Dask でバッチレポート。
使い方:
  python3 06_pipeline.py
  (Ctrl-C で停止するとバッチレポートを出力)
"""
import csv
import math
import os
import random
import sys
import tempfile
import time
import dask.dataframe as dd
import ray


# ── Ray Actor: 5 秒タンブリング窓集計 ──

@ray.remote
class WindowActor:
    def __init__(self):
        self._buf: list[dict] = []

    def add(self, record: dict):
        self._buf.append(record)

    def flush(self) -> list[dict]:
        data = list(self._buf)
        self._buf.clear()
        return data


# ── Ray タスク: センサー値の前処理 ──

@ray.remote
def preprocess(sensor_id: str, raw_value: float) -> dict:
    return {
        "sensor_id": sensor_id,
        "value": round(max(0.0, min(100.0, raw_value)), 2),
        "timestamp": time.time(),
    }


# ── センサーデータ生成 ──

def next_sensor_event() -> tuple[str, float]:
    sensors = ["pi-cpu", "pi-memory", "pi-temp"]
    bases = {"pi-cpu": 40.0, "pi-memory": 60.0, "pi-temp": 50.0}
    s = random.choice(sensors)
    spike = random.random() < 0.02
    val = bases[s] + (random.gauss(0, 5) if not spike else random.uniform(80, 100))
    return s, val


# ── タンブリング窓の集計表示 ──

def print_window(window_num: int, records: list[dict]):
    if not records:
        return
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n--- 窓 #{window_num}  {ts} ---")
    by_sensor: dict[str, list[float]] = {}
    for r in records:
        by_sensor.setdefault(r["sensor_id"], []).append(r["value"])
    for sensor in sorted(by_sensor):
        vals = by_sensor[sensor]
        mean = sum(vals) / len(vals)
        stdev = (sum((v - mean) ** 2 for v in vals) / max(1, len(vals) - 1)) ** 0.5
        print(f"  {sensor:<12}: 件数={len(vals):3d}  平均={mean:.1f}  σ={stdev:.1f}")


# ── Dask バッチ集計 ──

def run_dask_report(csv_path: str):
    print("\n=== Dask バッチレポート ===")
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        print("  (データなし)")
        return

    df = dd.read_csv(csv_path)
    full = df.compute()
    if full.empty:
        print("  (データなし)")
        return

    total = len(full)
    t_start = time.strftime("%H:%M:%S", time.localtime(full["timestamp"].min()))
    t_end = time.strftime("%H:%M:%S", time.localtime(full["timestamp"].max()))
    print(f"  総件数: {total:,}")
    print(f"  期間: {t_start} 〜 {t_end}\n")

    summary = full.groupby("sensor_id")["value"].agg(["count", "mean", "max", "std"])
    summary.columns = ["count", "mean", "max", "stdev"]

    # 3σ 異常数
    means = full.groupby("sensor_id")["value"].mean()
    stds = full.groupby("sensor_id")["value"].std()
    full["z"] = full.apply(
        lambda r: abs(r["value"] - means.get(r["sensor_id"], 0))
                  / (stds.get(r["sensor_id"], 1) or 1),
        axis=1,
    )
    anomaly_counts = full[full["z"] > 3].groupby("sensor_id").size()

    print("  センサー別統計:")
    header = f"  {'sensor_id':<14} {'count':>6} {'mean':>7} {'max':>7} {'anomalies':>10}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for sensor in sorted(summary.index):
        s = summary.loc[sensor]
        n_anom = anomaly_counts.get(sensor, 0)
        print(f"  {sensor:<14} {int(s['count']):>6} {s['mean']:>7.1f} "
              f"{s['max']:>7.1f} {n_anom:>10}")

    report_path = csv_path.replace(".csv", "_report.csv")
    summary.to_csv(report_path)
    print(f"\n  レポート保存: {report_path}")


# ── メインループ ──

def main():
    WINDOW_SEC = 5.0

    ray.init(
        num_cpus=4,
        object_store_memory=128 * 1024 * 1024,
        ignore_reinit_error=True,
    )
    print("[pipeline] Ray 初期化完了")

    actor = WindowActor.remote()
    tmp_csv = tempfile.mktemp(suffix=".csv", prefix="stage4_pipeline_")
    csv_file = open(tmp_csv, "w", newline="")
    writer = csv.DictWriter(csv_file, fieldnames=["sensor_id", "value", "timestamp"])
    writer.writeheader()

    print(f"[pipeline] CSVログ: {tmp_csv}")
    print("[pipeline] リアルタイム集計中... (Ctrl-C で停止してバッチレポートを出力)\n")

    window_num = 0
    window_start = time.monotonic()

    try:
        while True:
            # センサーイベントを前処理して Actor へ
            sensor_id, raw_val = next_sensor_event()
            record_ref = preprocess.remote(sensor_id, raw_val)
            record = ray.get(record_ref)
            actor.add.remote(record)
            writer.writerow(record)

            # 窓時間が経過したら集計
            now = time.monotonic()
            if now - window_start >= WINDOW_SEC:
                window_num += 1
                records = ray.get(actor.flush.remote())
                print_window(window_num, records)
                window_start = now

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n[pipeline] Ctrl-C 受信 → バッチレポートを実行...")
        # 未フラッシュ分を書き出す
        records = ray.get(actor.flush.remote())
        for r in records:
            writer.writerow(r)
        csv_file.flush()
        csv_file.close()
        run_dask_report(tmp_csv)
    finally:
        if not csv_file.closed:
            csv_file.close()
        ray.shutdown()
        print("\n[pipeline] 終了")


if __name__ == "__main__":
    main()
