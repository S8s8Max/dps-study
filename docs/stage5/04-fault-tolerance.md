# 04 耐障害性

## 学習目標

- liveness probe と readiness probe の違いを説明できる
- Pod がクラッシュしたとき k3s が自動再起動することを確認できる
- ローリングアップデートで無停止デプロイできる
- リソースリクエスト・リミットを設定できる

---

## 1. 自動再起動（restartPolicy）

Kubernetes はデフォルトで Pod がクラッシュすると自動再起動する。

```yaml
spec:
  restartPolicy: Always   # デフォルト（Deployment は常に Always）
  # OnFailure: 異常終了時のみ再起動（Job 向け）
  # Never: 再起動しない（バッチ完了を待つ場合）
```

### 確認

```bash
# Pod を意図的にクラッシュさせる
kubectl exec -n dps-study <pod-name> -- kill 1

# 再起動されるのを見る
kubectl get pods -n dps-study -w
# RESTARTS カウントが増えることを確認
```

---

## 2. Liveness Probe（生死確認）

Pod が「生きているか」を定期的に確認し、失敗が続いたら **再起動** する。

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 10   # 起動後 10 秒待ってから開始
  periodSeconds: 10         # 10 秒ごとにチェック
  failureThreshold: 3       # 3 回連続失敗で再起動
```

### HTTP の代わりに TCP・exec も使える

```yaml
# TCP ポートが開いていることを確認
livenessProbe:
  tcpSocket:
    port: 4222   # NATS

# コマンドの終了コードで確認
livenessProbe:
  exec:
    command: ["python3", "-c", "import requests; requests.get('http://localhost:8080/health')"]
```

---

## 3. Readiness Probe（準備完了確認）

Pod が「リクエストを受け付けられるか」を確認し、
失敗中は **Service から切り離す**（トラフィックが流れなくなる）。
再起動はしない。

```yaml
readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
  failureThreshold: 3
```

### liveness vs readiness の違い

```
liveness:  失敗 → 再起動（Pod が固まった・デッドロックした）
readiness: 失敗 → Service から除外（起動中・DB 接続待ち）

起動中は readiness が失敗し続ける → Service に載らない
起動完了すると readiness が成功 → Service に追加
```

---

## 4. ローリングアップデート

Deployment のデフォルト更新戦略。

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 1    # 同時に落とせる Pod 数
    maxSurge: 1          # 一時的に余分に起動できる Pod 数
```

### 更新手順

```bash
# イメージを更新（マニフェストを変更して apply）
kubectl apply -f k8s/stage5/06-probes-deployment.yaml

# 更新状況を確認
kubectl rollout status deployment/pipeline-worker -n dps-study

# 更新履歴
kubectl rollout history deployment/pipeline-worker -n dps-study

# ロールバック
kubectl rollout undo deployment/pipeline-worker -n dps-study
```

---

## 5. リソースリクエスト・リミット（Pi 3B 必須）

```yaml
resources:
  requests:
    memory: "64Mi"    # スケジューラーが保証するメモリ
    cpu: "250m"       # 0.25 コア（1000m = 1 コア）
  limits:
    memory: "128Mi"   # これを超えたら OOMKilled で再起動
    cpu: "500m"       # これを超えても再起動しない（スロットル）
```

Pi 3B（1GB）では **全 Pod の requests 合計が 900MB 未満** になるように設計する。

```bash
# 現在の使用量確認（metrics-server が必要）
kubectl top pods -n dps-study
```

---

## 6. 実装：ヘルスチェックサーバー

`python/stage5/01_health_server.py` は `/health` と `/ready` エンドポイントを持つサーバー。
このサーバーを k3s にデプロイして probe の挙動を確認する。

```bash
# イメージをビルド（Pi 上で）
docker build -t health-server:latest docker/stage5/

# k3s にデプロイ
kubectl apply -f k8s/stage5/06-probes-deployment.yaml

# probe の確認
kubectl describe pod -n dps-study | grep -A 10 "Liveness\|Readiness"

# /health を落として再起動を観察
kubectl exec -n dps-study <pod> -- curl -X POST localhost:8080/fail
kubectl get pods -n dps-study -w
```

---

## 7. まとめ

| 機能 | 設定 | 失敗時の動作 |
|------|------|------------|
| 自動再起動 | `restartPolicy: Always` | クラッシュ → 即再起動 |
| Liveness probe | `livenessProbe:` | 失敗3回 → 再起動 |
| Readiness probe | `readinessProbe:` | 失敗 → Service から除外 |
| ローリングアップデート | `strategy: RollingUpdate` | 旧 Pod を1つずつ置き換え |
| OOM 防止 | `resources.limits.memory` | 超過 → OOMKilled で再起動 |

次は Stage 2–4 のアプリを k3s にデプロイする。
