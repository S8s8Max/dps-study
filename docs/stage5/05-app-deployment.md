# 05 アプリデプロイ

## 学習目標

- Stage 2 の NATS を k3s の Deployment としてデプロイできる
- Stage 3 のパイプラインワーカーを k3s で動かせる
- `kubectl rollout` でローリングアップデートを実行できる
- Stage 5 の完了チェックリストを確認できる

---

## 1. デプロイ全体図

```
namespace: dps-study

  ┌────────────────────────────────────────────────────────┐
  │  NATS Deployment            NATS Service               │
  │  (1 replica)          →    ClusterIP:4222              │
  │  image: nats:alpine         NodePort:30222             │
  └───────────────────────────────────────┬────────────────┘
                                          │ NATS PUB/SUB
  ┌───────────────────────────────────────▼────────────────┐
  │  Pipeline Worker Deployment      ConfigMap             │
  │  (3 replicas)             ←      NATS_URL              │
  │  image: pipeline-worker:latest   WINDOW_SEC=5          │
  │  resources: 128Mi/0.5cpu                               │
  └────────────────────────────────────────────────────────┘
```

---

## 2. NATS のデプロイ

```bash
kubectl apply -f k8s/stage5/07-nats.yaml
kubectl get pod,svc -n dps-study -l app=nats

# NATS に接続確認（Pi 上で）
nats pub test "hello" --server nats://192.168.1.100:30222
```

---

## 3. Pipeline Worker のデプロイ

### イメージをビルドする

```bash
# Pi 上で（arm64 ネイティブ）
docker build -t pipeline-worker:v1.0 docker/stage5/

# または Mac からクロスコンパイル
docker buildx build --platform linux/arm64 \
  -t pipeline-worker:v1.0 docker/stage5/ --load
```

### k3s にインポート

k3s は containerd を使うので `docker images` は見えない。

```bash
# ローカルイメージを k3s に渡す
docker save pipeline-worker:v1.0 | sudo k3s ctr images import -
sudo k3s ctr images ls | grep pipeline
```

### デプロイ

```bash
kubectl apply -f k8s/stage5/08-pipeline.yaml
kubectl get pods -n dps-study -l app=pipeline-worker

# 3 Pod 全てが Running になるのを確認
kubectl rollout status deployment/pipeline-worker -n dps-study
```

---

## 4. ローリングアップデートの実演

```bash
# v2 イメージをビルド（コードを少し変えて）
docker save pipeline-worker:v2.0 | sudo k3s ctr images import -

# マニフェストの image: を v2.0 に更新して apply
kubectl apply -f k8s/stage5/08-pipeline.yaml

# 更新の様子を観察
kubectl rollout status deployment/pipeline-worker -n dps-study -w

# 履歴確認
kubectl rollout history deployment/pipeline-worker -n dps-study

# v1 にロールバック
kubectl rollout undo deployment/pipeline-worker -n dps-study
```

---

## 5. スケールアウト

```bash
# ワーカーを 3 → 5 に増やす（k3s が自動でノードに配置）
kubectl scale deployment pipeline-worker --replicas=5 -n dps-study
kubectl get pods -n dps-study -o wide   # どのノードに配置されたか確認
```

---

## 6. Pod の障害確認

```bash
# ワーカー Pod を 1 つ強制終了
kubectl delete pod <pod-name> -n dps-study

# Deployment が自動で新しい Pod を起動することを確認
kubectl get pods -n dps-study -w
```

---

## 7. ログの確認

```bash
# 1 つの Pod のログ
kubectl logs <pod-name> -n dps-study -f

# Deployment 全 Pod のログをまとめて（selector を使う）
kubectl logs -l app=pipeline-worker -n dps-study --prefix=true
```

---

## 8. クリーンアップ

```bash
# namespace ごと削除（全リソースが消える）
kubectl delete namespace dps-study

# または個別に削除
kubectl delete -f k8s/stage5/
```

---

## 9. Stage 5 完了チェックリスト

- [ ] k3s をシングルノードで起動できた
- [ ] `kubectl get nodes/pods` でクラスター状態を確認できた
- [ ] Pod / Deployment / Service を YAML で定義してデプロイできた
- [ ] ConfigMap でアプリの設定を注入できた
- [ ] Secret でパスワードを安全に管理できた
- [ ] Liveness / Readiness probe を設定できた
- [ ] Pod クラッシュ → 自動再起動を確認できた
- [ ] ローリングアップデートで無停止更新できた
- [ ] `kubectl rollout undo` でロールバックできた
- [ ] NATS + Pipeline Worker を k3s にデプロイできた
- [ ] （任意）ワーカーノードを追加してスケールアウトできた

---

## 10. まとめと次のステップ

### Stage 5 で習得したこと

| 項目 | 習得内容 |
|------|---------|
| k3s セットアップ | インストール・ノード追加・kubeconfig |
| 基本リソース | Pod / Deployment / Service / Namespace |
| 設定管理 | ConfigMap / Secret |
| 耐障害性 | Probe・自動再起動・リソース制限 |
| 運用 | ローリングアップデート・ロールバック・スケール |

### Stage 6 へ

Stage 6 では **分散システムの理論**（Raft・CAP 定理・論理時計）を学ぶ。
実装してきたシステムが「なぜそう設計されているか」を理論面から理解する。

```
Stage 5: 「どう動かすか」（運用・オーケストレーション）
  ↓
Stage 6: 「なぜそう設計するか」（理論・証明）
  例: Redpanda のレプリカはなぜ奇数か（Raft のクォーラム）
      NATS の at-least-once はなぜ存在するか（ネットワーク分断）
```

```bash
cat docs/stage6-study-guide.md
```
