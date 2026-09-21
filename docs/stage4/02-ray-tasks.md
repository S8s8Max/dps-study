# 02 Ray タスク

## 学習目標

- `ray.wait()` でバックプレッシャーを制御できる
- タスクの依存関係グラフ（DAG）を ObjectRef で表現できる
- Stage 1 のモンテカルロ π 推定と比較してスループットを計測できる

---

## 1. ray.wait() でバックプレッシャー

`ray.get(refs)` は全タスクが完了するまでブロックする。
大量タスクを投入するとメモリが枯渇することがある。
`ray.wait()` で「完了したものから順に処理」できる。

```python
refs = [heavy_task.remote(i) for i in range(1000)]

# 完了したものから順に 1 件ずつ取り出す
while refs:
    done, refs = ray.wait(refs, num_returns=1, timeout=1.0)
    if done:
        result = ray.get(done[0])
        print(result)
```

### バッチ処理でスループットを上げる

```python
BATCH = 16  # 同時投入数

while refs:
    done, refs = ray.wait(refs, num_returns=min(BATCH, len(refs)))
    results = ray.get(done)
    process_batch(results)
```

---

## 2. タスクの依存関係（DAG）

ObjectRef をそのままタスクに渡すと、依存関係が自動で解決される。

```python
@ray.remote
def step_a(x):   return x * 2
@ray.remote
def step_b(x):   return x + 10
@ray.remote
def step_c(a, b): return a + b

# ref_a, ref_b が完了してから step_c が実行される
ref_a = step_a.remote(5)
ref_b = step_b.remote(3)
ref_c = step_c.remote(ref_a, ref_b)   # ref_a=10, ref_b=13 → 23

result = ray.get(ref_c)   # 23
```

Ray がこの依存グラフを自動でスケジュールする。
手動で `ray.get()` を挟む必要がない。

---

## 3. リソース指定

```python
@ray.remote(num_cpus=2, memory=256*1024*1024)
def heavy_task(x):
    ...
```

Pi 3B でコアを使いすぎないように制限できる。

---

## 4. Stage 1 との比較：モンテカルロ π

Stage 1 では `multiprocessing.Pool` で実装した。
今回は Ray で同じアルゴリズムを実装し、スループットを比較する。

```
Stage 1: multiprocessing.Pool.map()
  → プロセス起動コスト: 起動済みプールを再利用
  → ノード間通信: 不可

Stage 4: ray.remote
  → 初回起動: 2–3 秒（レイ本体の起動）
  → ノード間通信: オブジェクトストア経由で透過的
  → 大規模データ: ray.put() で転送コスト削減
```

---

## 5. 実装：並列タスクとベンチマーク

```bash
python3 python/stage4/02_ray_tasks.py
```

### 期待する出力

```
[ray] 初期化完了 (CPUs=4)

=== モンテカルロ π 推定 ===
  直列             : π=3.14159  2.34s
  multiprocessing  : π=3.14161  0.63s  スピードアップ 3.7×
  Ray タスク       : π=3.14158  0.71s  スピードアップ 3.3×
  Ray (ray.wait)   : π=3.14162  0.68s  スピードアップ 3.4×

[備考] Ray の起動コスト（初回のみ）を除くと multiprocessing と同等のスループット
```

---

## 6. まとめ

| API | 用途 |
|-----|------|
| `ray.get(refs)` | 全タスク完了待ち（小〜中規模） |
| `ray.wait(refs, num_returns=N)` | N 件完了したら取り出す（大規模・バックプレッシャー） |
| `f.remote(ref)` | 他タスクの結果を依存として渡す（DAG） |
| `@ray.remote(num_cpus=N)` | リソース要求を指定 |

次は Ray **アクター** でステートフル処理を実装する。
