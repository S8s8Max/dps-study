"""Dask DataFrame：CSV を自動パーティション化して pandas と同じ API で集計。
使い方:
  python3 05_dask_dataframe.py
"""
import math
import os
import random
import shutil
import tempfile
import time
import dask.dataframe as dd
import pandas as pd


def generate_csv_files(out_dir: str, n_files: int = 4, n_rows_each: int = 2500):
    """学習用の CSV ファイルを複数生成する。"""
    os.makedirs(out_dir, exist_ok=True)
    sensors = ["pi-cpu", "pi-memory", "pi-temp"]
    bases = {"pi-cpu": 40.0, "pi-memory": 60.0, "pi-temp": 50.0}

    for f_idx in range(n_files):
        rows = []
        base_ts = 1700000000 + f_idx * n_rows_each
        for i in range(n_rows_each):
            s = sensors[i % len(sensors)]
            spike = random.random() < 0.01
            val = bases[s] + (random.gauss(0, 5) if not spike else random.uniform(80, 100))
            rows.append({
                "timestamp": base_ts + i,
                "sensor_id": s,
                "value": round(max(0.0, val), 2),
            })
        pd.DataFrame(rows).to_csv(os.path.join(out_dir, f"data_{f_idx:02d}.csv"), index=False)


def main():
    tmpdir = tempfile.mkdtemp(prefix="stage4_dask_")
    try:
        # ── CSV ファイル生成 ──
        n_files = 4
        n_rows = 2500
        print(f"[dask] CSV ファイル生成: {n_files} ファイル × {n_rows} 行")
        generate_csv_files(tmpdir, n_files, n_rows)

        pattern = os.path.join(tmpdir, "*.csv")

        # ── Dask DataFrame で読み込み ──
        print(f"\n[dask] 読み込み: {pattern}")
        df = dd.read_csv(pattern)
        print(f"  パーティション数: {df.npartitions}")
        print(f"  カラム: {list(df.columns)}")

        # ── pandas と同じ API で集計 ──
        print("\n[dask] センサーごとの集計 (.groupby().mean().compute())")
        t0 = time.perf_counter()
        sensor_mean = df.groupby("sensor_id")["value"].mean().compute()
        t1 = time.perf_counter()
        print(sensor_mean.to_string())
        print(f"  compute 時間: {t1-t0:.3f}s\n")

        print("[dask] センサーごとの件数・最大値・最小値")
        summary = df.groupby("sensor_id")["value"].agg(
            ["count", "mean", "max", "min"]
        ).compute()
        print(summary.round(2).to_string())

        # ── フィルタリング（pandas と同じ構文）──
        print("\n[dask] フィルタリング: value > 70")
        t0 = time.perf_counter()
        high = df[df["value"] > 70].compute()
        t1 = time.perf_counter()
        print(f"  {len(high)} 件検出  compute 時間: {t1-t0:.3f}s")
        if not high.empty:
            print(high.nlargest(5, "value")[["sensor_id", "value", "timestamp"]].to_string(index=False))

        # ── 異常値の検出（z スコア）──
        print("\n[dask] 異常値検出（センサーごとに 3σ 超え）")
        means = df.groupby("sensor_id")["value"].mean().compute().to_dict()
        stds = df.groupby("sensor_id")["value"].std().compute().to_dict()

        t0 = time.perf_counter()
        # pandas で後処理（Dask の compute 後）
        full = df.compute()
        full["z_score"] = full.apply(
            lambda row: abs(row["value"] - means.get(row["sensor_id"], 0))
                        / (stds.get(row["sensor_id"], 1) or 1),
            axis=1,
        )
        anomalies = full[full["z_score"] > 3.0].sort_values("z_score", ascending=False)
        t1 = time.perf_counter()
        print(f"  {len(anomalies)} 件検出  時間: {t1-t0:.3f}s")
        if not anomalies.empty:
            print(anomalies.head(5)[["sensor_id", "value", "z_score"]].round(2).to_string(index=False))

        # ── Dask vs pandas の速度比較 ──
        print("\n=== Dask vs pandas: groupby 集計比較 ===")
        pandas_df = full.drop(columns=["z_score"])

        print("[pandas] groupby mean")
        t0 = time.perf_counter()
        pandas_result = pandas_df.groupby("sensor_id")["value"].mean()
        t_pandas = time.perf_counter() - t0
        print(f"  {t_pandas*1000:.1f}ms")

        ddf = dd.from_pandas(pandas_df, npartitions=4)
        print("[dask] groupby mean (threaded)")
        t0 = time.perf_counter()
        dask_result = ddf.groupby("sensor_id")["value"].mean().compute(scheduler="threads")
        t_dask = time.perf_counter() - t0
        print(f"  {t_dask*1000:.1f}ms")
        print(f"\n  [備考] 小規模データ（{len(pandas_df):,} 行）では pandas が速い。"
              "  Dask の効果は数百万行以上で現れる。")

    finally:
        shutil.rmtree(tmpdir)
        print("\n[dask] 一時ファイル削除完了")


if __name__ == "__main__":
    main()
