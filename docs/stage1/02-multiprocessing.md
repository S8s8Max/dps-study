# 02 Python multiprocessing

## 学習目標

- `multiprocessing.Pool` で並列 Map 処理を実行できる
- `Process` と `Queue` でプロセス間通信を実装できる
- Pi 3B の 4 コアを活用して逐次より速い処理を実測できる
- `Pool` の `map`・`starmap`・`imap` の違いを使い分けられる

---

## 1. 概念説明

### multiprocessing モジュールの全体像

```
multiprocessing
├── Process       ─ 個別プロセスの起動・制御
├── Pool          ─ プロセスプール（並列 Map の主役）
├── Queue         ─ プロセス間のキュー通信
├── Pipe          ─ 2 プロセス間の双方向パイプ
└── Value / Array ─ 共有メモリ（注意が必要）
```

### Pool の動作イメージ

```
メインプロセス
  │
  ├─ Pool(4) を作成
  │   ├─ ワーカー1
  │   ├─ ワーカー2
  │   ├─ ワーカー3
  │   └─ ワーカー4
  │
  ├─ pool.map(func, [1,2,3,4,5,6,7,8])
  │   ワーカー1: func(1), func(5)
  │   ワーカー2: func(2), func(6)
  │   ワーカー3: func(3), func(7)
  │   ワーカー4: func(4), func(8)
  │
  └─ 結果を集めて返す: [r1, r2, r3, r4, r5, r6, r7, r8]
```

### map・starmap・imap の違い

| メソッド | 特徴 | 使い方 |
|---|---|---|
| `pool.map(f, iterable)` | 全結果を一度に返す | 結果の順序保証あり |
| `pool.starmap(f, [(a,b), ...])` | 複数引数の関数に使う | タプルをアンパックして渡す |
| `pool.imap(f, iterable)` | 結果をイテレータで返す | メモリ節約（大きなデータに有効）|

---

## 2. 事前確認

```bash
# Python バージョン確認
python3 --version

# multiprocessing は標準ライブラリ（インストール不要）
python3 -c "import multiprocessing; print(multiprocessing.cpu_count())"
# 4

# ワーカープロセス数の上限確認
python3 -c "
from multiprocessing import cpu_count
print(f'コア数: {cpu_count()}')
print(f'推奨 Pool サイズ: {cpu_count()}')
"
```

---

## 3. Pool.map で並列処理する

### 3.1 最もシンプルな例

```python
from multiprocessing import Pool, cpu_count

def square(x):
    return x * x

if __name__ == "__main__":           # Windows/macOS では必須
    with Pool(cpu_count()) as pool:
        results = pool.map(square, range(10))
    print(results)
    # [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]
```

> **重要**: `if __name__ == "__main__":` は必須です。
> これがないと子プロセスが再帰的に起動してフリーズします。

### 3.2 素数探索を並列化する

```bash
# サンプルコードを実行
python3 python/stage1/02_pool_map.py
```

期待する出力：

```
=== 素数探索（0〜50000 を 4 分割）===
逐次処理:    3.21 秒  （5133 個の素数）
Pool.map:    0.89 秒  （5133 個の素数）  ← 3.6x 速い
Pool.imap:   0.91 秒  （5133 個の素数）
```

### 3.3 複数引数の関数は starmap を使う

```python
from multiprocessing import Pool, cpu_count

def power(base, exp):
    return base ** exp

if __name__ == "__main__":
    args = [(2, 10), (3, 8), (5, 6), (7, 5)]
    with Pool(cpu_count()) as pool:
        results = pool.starmap(power, args)
    print(results)
    # [1024, 6561, 15625, 16807]
```

---

## 4. Queue でプロセス間通信する

プロデューサーとコンシューマーを別プロセスで動かすパターンです。

```bash
python3 python/stage1/03_queue_pipeline.py
```

コードの要点：

```python
from multiprocessing import Process, Queue

def producer(queue, items):
    for item in items:
        queue.put(item)
    queue.put(None)           # 終了シグナル

def consumer(queue, results):
    while True:
        item = queue.get()
        if item is None:
            break
        results.put(item * 2)

if __name__ == "__main__":
    q = Queue()
    results = Queue()

    p = Process(target=producer, args=(q, range(100)))
    c = Process(target=consumer, args=(q, results))

    p.start(); c.start()
    p.join(); c.join()
```

---

## 5. よくあるエラーと対処法

### `if __name__ == "__main__":` を忘れた

```
RuntimeError: An attempt has been made to start a new process
before the current process has finished its bootstrapping phase.
```

→ すべての multiprocessing コードをこのガードで囲む。

### プロセス間で渡せないオブジェクト

```
_pickle.PicklingError: Can't pickle <function ...>
```

ラムダ関数やクロージャーはピクルス化できません。

```python
# ✗ ラムダは渡せない
pool.map(lambda x: x * 2, data)

# ✓ トップレベルの関数を定義する
def double(x):
    return x * 2

pool.map(double, data)
```

### Pool のサイズを大きくしすぎた

Pi 3B は 4 コアなので、`Pool(8)` などにしても速くなりません。
メモリも消費するので `cpu_count()` を使うのが安全です。

```python
# ✓ コア数に合わせる
with Pool(cpu_count()) as pool:
    ...
```

---

## 6. まとめと次のステップ

### 今回の学習内容

| 項目 | 習得内容 |
|---|---|
| `Pool.map` | iterable を並列 Map して結果を返す |
| `Pool.starmap` | 複数引数の関数を並列実行 |
| `Pool.imap` | 大きなデータをメモリ効率よく処理 |
| `Queue` | プロセス間でデータを安全に受け渡す |
| ベストプラクティス | `if __name__`、コア数に合わせる、ラムダ不可 |

### 次のステップ

`03-mpi4py.md` では MPI（Message Passing Interface）を使います。
`multiprocessing` はシングルノード向けですが、MPI は将来的なマルチノードへの拡張が可能です。

```bash
cat docs/stage1/03-mpi4py.md
```
