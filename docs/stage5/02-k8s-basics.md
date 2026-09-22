# 02 Kubernetes 基本リソース

## 学習目標

- Pod・Deployment・Service の役割と関係を説明できる
- YAML マニフェストを書いて `kubectl apply` でデプロイできる
- Deployment のレプリカ数を変えてスケールできる

---

## 1. 主要リソースの関係

```
namespace: dps-study
  │
  ├── Deployment (desired state を宣言)
  │     └── ReplicaSet
  │           ├── Pod A  ──┐
  │           ├── Pod B  ──┤── コンテナ × 1〜複数
  │           └── Pod C  ──┘
  │
  └── Service (Pod への安定したエンドポイント)
        → ラベルで Pod を自動的に選択
        → Pod が入れ替わっても IP/DNS が変わらない
```

### Pod

Kubernetes の最小デプロイ単位。1つ以上のコンテナをまとめたもの。
**Pod は使い捨て**。落ちたら Deployment が新しい Pod を起こす。

### Deployment

「Pod をこの状態で N 個常に動かせ」という宣言。
自動再起動・ローリングアップデートを管理する。

### Service

Pod への安定したネットワークエンドポイント。
Pod の IP は変わるが、Service の ClusterIP は固定。

---

## 2. Pod マニフェスト

`k8s/stage5/01-namespace.yaml` + `k8s/stage5/02-pod.yaml` を使う。

```bash
kubectl apply -f k8s/stage5/01-namespace.yaml
kubectl apply -f k8s/stage5/02-pod.yaml
kubectl get pod -n dps-study
kubectl logs hello-pod -n dps-study
```

---

## 3. Deployment マニフェスト

```bash
kubectl apply -f k8s/stage5/03-deployment.yaml
kubectl get deployment -n dps-study
kubectl get pods -n dps-study -o wide    # どのノードで動いているか確認
```

### レプリカ数を変える

```bash
# 宣言的に変更（マニフェストを更新して apply）
# replicas: 3 → replicas: 1 に変えてから:
kubectl apply -f k8s/stage5/03-deployment.yaml

# 命令的に変更（テスト用。マニフェストに反映されない）
kubectl scale deployment hello-deploy --replicas=3 -n dps-study
kubectl get pods -n dps-study -w   # リアルタイムで Pod が増えるのを見る
```

---

## 4. Service マニフェスト

```bash
kubectl apply -f k8s/stage5/04-service.yaml
kubectl get service -n dps-study
```

### Service の種類

| 種類 | 説明 | 用途 |
|------|------|------|
| ClusterIP | クラスター内部のみ | Pod 間通信 |
| NodePort | ノードの IP:ポートで外部公開 | 開発・テスト |
| LoadBalancer | 外部ロードバランサー | 本番（クラウド） |

Pi のラズパイクラスターでは **NodePort** が最も使いやすい。

```bash
# NodePort サービスにアクセス（Pi の IP:30080）
curl http://192.168.1.100:30080
```

---

## 5. リソースの確認コマンド

```bash
# 状態一覧
kubectl get pod,deploy,svc -n dps-study

# YAML 形式で現在の状態を取得
kubectl get deployment hello-deploy -n dps-study -o yaml

# 変更を watching
kubectl get pods -n dps-study -w

# Pod の中に入る
kubectl exec -it <pod-name> -n dps-study -- /bin/sh
```

---

## 6. まとめ

| リソース | 役割 |
|---------|------|
| Pod | 最小実行単位（使い捨て） |
| Deployment | Pod の desired state を宣言・管理 |
| ReplicaSet | 実際にレプリカ数を保つ（Deployment が管理） |
| Service | Pod への安定エンドポイント（ClusterIP / NodePort） |
| Namespace | リソースの論理的な分離（`-n` オプション） |

次は ConfigMap と Secret で設定・秘密情報を管理する。
