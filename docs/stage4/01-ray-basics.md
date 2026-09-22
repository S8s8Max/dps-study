# 01 Ray 基礎

## 学習目標

- Ray の役割と `multiprocessing` との違いを説明できる
- `ray.init()` / `ray.shutdown()` でクラスターに接続・切断できる
- `@ray.remote` でリモート関数を定義し `ray.get()` で結果を取得できる
- Ray Dashboard でジョブ状況を確認できる

---

## 1. Ray とは

```
Ray = 分散実行ランタイム

  ┌────────────────────────────────────────────────────────┐
  │  あなたのコード                                         │
  │   result = ray.get([f.remote(x) for x in data])        │
  │     ↑ ここだけ変えればいい                              │
  └──────────────────────┬─────────────────────────────────┘
                         │ Ray が自動で
                 ┌───────▼───────┐
                 │  スケジューラー │← タスクを各ノードに割り振る
                 └───────┬───────┘
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       Worker 0       Worker 1       Worker 2
      (Pi 1)         (Pi 2)         (Pi 3)
```

### multiprocessing との比較

| 項目 | multiprocessing | Ray |
|------|----------------|-----|
| 対象 | 単一マシン | 単一〜複数マシン |
| タスクの依存関係 | 手動管理 | 自動（future の連鎖） |
| ステートフル処理 | Queue + Process | Actor |
| フォールト | なし | タスク自動リトライ |
| Dashboard | なし | Web UI（:8265） |
| 起動コスト | 小 | 中（初回 2–3 秒） |

---

## 2. インストールと起動

```bash
source .venv/bin/activate
pip install -r requirements/stage4.txt
```

> 💾 `ray` + `pandas` + `pyarrow` で 1GB 近く使います。
> microSD の空きを `df -h /` で先に確認してください。

### シングルノード（開発・学習用）

```python
import ray
ray.init()                 # ローカルで Ray を起動
# ... 処理 ...
ray.shutdown()
```

### Pi 3B 向け（メモリ節約）

```python
ray.init(
    num_cpus=4,
    object_store_memory=128 * 1024 * 1024,  # 128MB（デフォルト: RAM の 30%）
)
```

### クラスター（複数ラズパイ）

```bash
# ヘッドノード（pi-master）
ray start --head --num-cpus=4 --object-store-memory=134217728

# ワーカーノード（pi-node1, pi-node2）
ray start --address='192.168.1.100:6379' --num-cpus=4
```

Python から接続：

```python
ray.init(address='auto')   # 起動済みクラスターに接続
```

---

## 3. @ray.remote の基本

### リモート関数（Ray タスク）

```python
@ray.remote
def hello(name: str) -> str:
    import os
    return f"Hello {name} from PID {os.getpid()}"

# .remote() で非同期に実行 → ObjectRef（future）が返る
ref = hello.remote("World")

# ray.get() でブロックして結果を取得
result = ray.get(ref)
print(result)
```

### まとめて投げてまとめて取る

```python
refs = [hello.remote(f"Worker {i}") for i in range(8)]
results = ray.get(refs)   # 8 タスクが並列実行される
```

### ray.put() でデータをオブジェクトストアへ

```python
# 大きなデータを一度だけ共有メモリに置く
data = list(range(1_000_000))
data_ref = ray.put(data)

@ray.remote
def process(data):          # 受け取るのは ObjectRef ではなく実体
    return sum(data)

result = ray.get(process.remote(data_ref))
```

#### 引数に渡した ObjectRef は自動で実体化される（つまずきやすい点）

`f.remote(data_ref)` のように **ObjectRef を引数に直接渡すと、
Ray がタスク実行前に自動で中身を取り出して**関数に渡します。
そのためタスクの中で `ray.get()` を呼ぶ必要はありません。

```python
# ✗ よくある間違い：タスク内で ray.get() を呼ぶ
@ray.remote
def process(data_ref):
    data = ray.get(data_ref)    # data_ref は既に実体なのでエラー
    return sum(data)
```

このとき出るエラーが分かりにくいので注意してください。

```
TypeError: Attempting to call `get` on the value 0, which is not an ray.ObjectRef.
```

`ray.get()` は**リストを渡すと「ObjectRef のリスト」として扱う**ため、
実体化済みのリスト `[0, 1, 2, ...]` を渡すと
先頭要素の `0` を ObjectRef と誤認してこのメッセージになります。
「ObjectRef を渡したつもりなのに 0 と言われる」ときは、この自動実体化を疑ってください。

なお、この自動実体化があっても**転送効率は落ちません**。
オブジェクトストア上の実体を各ワーカーが参照するだけで、
タスクごとにシリアライズし直すことはありません。

---

## 4. Ray Dashboard

Ray 起動時に Web UI が立ち上がる（ポート 8265）。

```bash
# Mac から SSH ポートフォワーディング
ssh -L 8265:localhost:8265 pi@192.168.1.100

# ブラウザで確認
open http://localhost:8265
```

確認できること：
- 実行中・完了・失敗したタスク
- CPU・メモリ使用率
- ノードごとのリソース

---

## 5. 実装：Ray Hello World

`python/stage4/01_ray_hello.py` を実行する。

```bash
python3 python/stage4/01_ray_hello.py
```

### 期待する出力

```
[ray] 初期化
  CPUs: 4  メモリ: 128.0MB
[ray] タスク実行: 8 個を並列
  → Hello 0 from PID 12345 (ノード: ...)
  → Hello 1 from PID 12346 ...
  ...
[ray] 完了: 8 タスク  経過時間: 0.23s
```

---

## 6. まとめ

| API | 説明 |
|-----|------|
| `ray.init()` | ローカル / クラスターを起動・接続 |
| `@ray.remote` | 関数やクラスを分散実行可能にする |
| `f.remote(args)` | タスクを非同期に投入、ObjectRef を返す |
| `ray.get(ref)` | ObjectRef をブロックして結果を取得 |
| `ray.put(obj)` | オブジェクトをオブジェクトストアに置く |
| `ray.wait(refs)` | 完了したタスクを随時取得（バックプレッシャー制御） |

次は Ray タスクを使って並列処理のベンチマークをとる。
