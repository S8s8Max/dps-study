# 05 分散パイプライン

## 学習目標

- Ray タスク（リアルタイム処理）と Dask（バッチ集計）を組み合わせられる
- スループット・レイテンシを Ray と Dask で計測して比較できる
- Stage 4 全体の学習チェックリストを確認できる

---

## 1. Ray vs Dask の使い分け

```
Ray:
  ✓ リアルタイム・低レイテンシが必要
  ✓ ステートフル処理（Actor）
  ✓ ML モデルの推論・学習（Ray Serve / Ray Train）
  ✓ 動的なタスクグラフ

Dask:
  ✓ バッチ処理・大規模データ
  ✓ pandas/NumPy の既存コードをそのままスケール
  ✓ 静的な DAG（ETL パイプライン）
  ✓ データサイエンス・EDA
```

組み合わせ例：
- Ray Actor でリアルタイムにデータを集約 → 定期的に Dask で集計レポートを生成

---

## 2. パイプライン全体図

```
【リアルタイム側（Ray）】               【バッチ側（Dask）】

センサーデータ生成                     定期バッチ集計
   ↓ Ray タスク（変換・フィルタ）         ↑
Ray アクター（5秒窓集計）  →  CSV 保存  → Dask DataFrame で
   ↓                                       統計・異常履歴を集計
 stdout（リアルタイム表示）                  ↓
                                        レポート出力
```

---

## 3. 起動手順

```bash
python3 python/stage4/06_pipeline.py
```

両モードが同一スクリプトに統合されている。

- `ray` 側：センサーデータを Ray タスクで変換し Actor で集計（Ctrl-C まで継続）
- `dask` 側：収集した CSV を Dask で集計して最終レポートを出力

---

## 4. 期待する出力

```
[pipeline] Ray 初期化 (CPUs=4)
[pipeline] Actor 起動: 4 シャード

--- リアルタイム集計（5秒窓）---
窓 #1  2026-09-21 10:00:05
  pi-cpu    件数=5  平均=39.8  σ=4.2
  pi-memory 件数=5  平均=60.1  σ=1.3
  pi-temp   件数=5  平均=51.2  σ=0.9

窓 #2  2026-09-21 10:00:10
  pi-cpu    件数=5  平均=41.2  σ=3.8
  ...

^C
[pipeline] Ctrl-C 受信 → Dask バッチ集計を実行...

=== Dask バッチレポート ===
  総件数: 150
  期間: 2026-09-21 10:00:00 〜 10:00:50

  センサー別統計:
  sensor_id    count  mean    max     anomalies
  pi-cpu         50   40.1    87.3        2
  pi-memory      50   60.2    64.1        0
  pi-temp        50   51.0    53.9        0

[pipeline] レポート保存: /tmp/stage4_report.csv
```

---

## 5. Ray クラスターへの拡張

Pi 3B が複数台あれば以下でクラスター化できる。

```bash
# pi-master:
ray start --head --num-cpus=4 --object-store-memory=134217728

# pi-node1, pi-node2:
ray start --address='192.168.1.100:6379' --num-cpus=4

# スクリプトを変更
ray.init(address='auto')   # ローカル起動から変更
```

同じコード（`@ray.remote`）が自動で複数ノードに分散される。

---

## 6. Stage 4 完了チェックリスト

- [ ] `ray.init()` でローカル Ray を起動できた
- [ ] `@ray.remote` 関数でタスクを非同期に投入できた
- [ ] `ray.wait()` でバックプレッシャーを制御できた
- [ ] Ray Actor でステートフル処理を実装できた（`03_ray_actors.py`）
- [ ] `dask.delayed` でカスタム並列ワークフローを作れた
- [ ] `dask.dataframe` で複数 CSV をまとめて集計できた
- [ ] Ray と Dask を組み合わせたパイプラインを動かせた
- [ ] （任意）Ray クラスターで複数ラズパイに分散できた

---

## 7. まとめと次のステップ

### Stage 4 で習得したこと

| 項目 | 習得内容 |
|------|---------|
| Ray タスク | `@ray.remote`・`ray.get`・`ray.wait`・DAG |
| Ray アクター | ステートフル分散オブジェクト・シャーディング |
| Dask delayed | カスタム並列ワークフロー・遅延評価 |
| Dask DataFrame | pandas の自動並列化・パーティション |
| 組み合わせ | Ray でリアルタイム→ Dask でバッチ集計 |

### Stage 5 へ

Stage 5 では **k3s**（軽量 Kubernetes）を使って、ここまでのアプリを
コンテナオーケストレーションで運用する。

```
Stage 4: Python プロセスを直接実行
  ↓
Stage 5: コンテナ化 → k3s でデプロイ・スケール・自動再起動
```

```bash
cat docs/stage5-study-guide.md
```
