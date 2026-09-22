# 03 設定管理（ConfigMap・Secret）

## 学習目標

- ConfigMap でアプリの設定を Pod から分離できる
- Secret で秘密情報をリポジトリに入れずに管理できる
- 環境変数・ボリュームマウントの 2 通りで Pod に渡せる

---

## 1. なぜ設定を分離するか

```
悪い例（ハードコード）:
  コード内: NATS_URL = "nats://192.168.1.100:4222"
  → IP が変わったらイメージをビルドし直し

良い例（ConfigMap）:
  ConfigMap: NATS_URL=nats://nats-service:4222
  → ConfigMap を更新するだけ。イメージは変えない
```

「**12-factor app**」原則: 設定は環境から注入する。

---

## 2. ConfigMap

### 作成

```yaml
# k8s/stage5/05-configmap-secret.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: pipeline-config
  namespace: dps-study
data:
  NATS_URL: "nats://nats-service:4222"
  WINDOW_SEC: "5"
  LOG_LEVEL: "INFO"
```

```bash
kubectl apply -f k8s/stage5/05-configmap-secret.yaml
kubectl get configmap -n dps-study
kubectl describe configmap pipeline-config -n dps-study
```

### Pod で環境変数として参照

```yaml
spec:
  containers:
    - name: worker
      image: my-worker:latest
      envFrom:
        - configMapRef:
            name: pipeline-config   # ConfigMap の全キーを env に展開

      # または個別に参照:
      env:
        - name: NATS_URL
          valueFrom:
            configMapKeyRef:
              name: pipeline-config
              key: NATS_URL
```

### ボリュームとしてマウント（設定ファイル）

```yaml
spec:
  volumes:
    - name: config-vol
      configMap:
        name: pipeline-config
  containers:
    - name: worker
      volumeMounts:
        - name: config-vol
          mountPath: /etc/config
      # → /etc/config/NATS_URL, /etc/config/WINDOW_SEC が作られる
```

---

## 3. Secret

パスワード・トークン・証明書などを保存する。
ConfigMap と同じ構造だが base64 エンコードされる（暗号化ではないことに注意）。

### 作成（コマンドライン）

```bash
# base64 エンコードせず直接指定（--from-literal）
kubectl create secret generic grafana-secret \
  --from-literal=GF_SECURITY_ADMIN_PASSWORD=supersecret \
  -n dps-study

# ファイルから
kubectl create secret generic tls-secret \
  --from-file=tls.crt=./server.crt \
  --from-file=tls.key=./server.key \
  -n dps-study
```

### YAML で作成（値は base64 エンコード）

```bash
echo -n 'supersecret' | base64   # → c3VwZXJzZWNyZXQ=
```

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: grafana-secret
  namespace: dps-study
type: Opaque
data:
  GF_SECURITY_ADMIN_PASSWORD: c3VwZXJzZWNyZXQ=
```

### Pod で使う

```yaml
env:
  - name: GF_SECURITY_ADMIN_PASSWORD
    valueFrom:
      secretKeyRef:
        name: grafana-secret
        key: GF_SECURITY_ADMIN_PASSWORD
```

---

## 4. Secret のセキュリティ注意

| 対策 | 説明 |
|------|------|
| リポジトリに入れない | Secret YAML は `.gitignore` に追加 |
| RBAC で参照を制限 | Secret を使える ServiceAccount だけに権限付与 |
| 暗号化保存 | k3s は etcd 暗号化や外部シークレットマネージャーと連携可 |
| ログに出さない | `echo $PASSWORD` のような操作を避ける |

```bash
# .gitignore に追加
echo "k8s/stage5/*-secret.yaml" >> .gitignore
```

---

## 5. Docker Compose との比較

| Docker Compose | k3s |
|----------------|-----|
| `.env` ファイル | ConfigMap |
| `secrets:` | Secret |
| `environment:` | `env:` / `envFrom:` |
| `volumes:` | ConfigMap / PersistentVolume |

---

## 6. まとめ

| リソース | 用途 | 保存される値 |
|---------|------|------------|
| ConfigMap | 設定・フラグ・接続先 | 平文 |
| Secret | パスワード・トークン・証明書 | base64（RBAC 制御） |

次は **耐障害性**（liveness/readiness probe・ローリングアップデート）を学ぶ。
