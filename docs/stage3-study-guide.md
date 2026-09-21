# Stage 3 学習ガイド：状態を持つストリーム処理

## 目標

Stage 2 で学んだメッセージングの上に **ステートフル処理** を加える。
リアルタイムデータを時間窓で集計し、Redpanda（Kafka 互換）で永続化・再処理できるようにする。

## 依存グラフ

```mermaid
graph LR
  A[01 ストリーム概念] --> B[02 タンブリング窓]
  B --> C[03 スライディング窓]
  B --> D[04 Redpanda 入門]
  C --> E[05 ステートフルパイプライン]
  D --> E
```

## ステップ一覧

| ステップ | テーマ | ドキュメント | コード |
|---------|--------|--------------|--------|
| 01 | ストリーム処理の概念 | `docs/stage3/01-stream-concepts.md` | `python/stage3/01_stateful_counter.py` |
| 02 | タンブリング窓 | `docs/stage3/02-time-windows.md` | `python/stage3/02_tumbling_window.py` |
| 03 | スライディング窓と異常検知 | `docs/stage3/03-sliding-window.md` | `python/stage3/03_sliding_window.py` |
| 04 | Redpanda 入門 | `docs/stage3/04-redpanda.md` | `python/stage3/04_redpanda_producer.py` / `04_redpanda_consumer.py` |
| 05 | ステートフルパイプライン | `docs/stage3/05-stateful-pipeline.md` | `python/stage3/05_stream_processor.py` |

## Stage 2 との違い

| 項目 | Stage 2 | Stage 3 |
|------|---------|---------|
| 処理モデル | ステートレス（各メッセージ独立） | ステートフル（過去を参照・集計） |
| 時間の扱い | 意識しない | イベント時刻・処理時刻・遅延データ |
| データ永続化 | なし | Redpanda トピック（オフセット管理） |
| 再処理 | 不可 | オフセットを戻して再処理可能 |

## ハードウェア注意

Redpanda は Raspberry Pi 3B（1GB RAM）で動作しますが余裕は少ない。

- `--smp 1`（使用コア数を 1 に制限）
- `--memory 512M`（Redpanda 自身のメモリ使用量を制限）
- **スワップ 512MB 以上を推奨**（`sudo dphys-swapfile` で設定）

Pi 4（2GB+）があれば快適に動作する。
