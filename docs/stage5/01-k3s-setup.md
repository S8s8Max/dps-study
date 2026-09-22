# 01 k3s セットアップ

## 学習目標

- k3s をラズパイにインストールしてシングルノードクラスターを起動できる
- ワーカーノードをクラスターに追加できる
- `kubectl` の基本コマンドでクラスター状態を確認できる

---

## 1. k3s とは

```
Kubernetes（フル）:
  - etcd + API サーバー + スケジューラー + ... = 多数のプロセス
  - 最小 2GB RAM
  - arm64 対応だが重い

k3s（軽量版）:
  - シングルバイナリ（~100MB）
  - デフォルト DB は SQLite（etcd 不要）
  - containerd 内蔵
  - arm64 ネイティブ対応
  - 最小 512MB RAM
  → Raspberry Pi に最適
```

---

## 2. マスターノードのセットアップ（pi-master）

```bash
# k3s インストール（arm64 自動検出）
curl -sfL https://get.k3s.io | sh -

# 起動確認
sudo systemctl status k3s
sudo kubectl get nodes
```

出力例：
```
NAME        STATUS   ROLES                  AGE   VERSION
pi-master   Ready    control-plane,master   30s   v1.29.x+k3s1
```

### kubeconfig を一般ユーザーで使えるようにする

```bash
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $USER ~/.kube/config
chmod 600 ~/.kube/config
kubectl get nodes   # sudo なしで使えるようになる
```

---

## 3. ワーカーノードの追加（pi-node1, pi-node2）

```bash
# マスターで: トークンを確認
sudo cat /var/lib/rancher/k3s/server/node-token

# ワーカーで: マスターに接続
curl -sfL https://get.k3s.io | K3S_URL=https://192.168.1.100:6443 \
  K3S_TOKEN=<上のトークン> sh -
```

### 接続確認（マスターで）

```bash
kubectl get nodes -o wide
```

```
NAME        STATUS   ROLES                  AGE   VERSION
pi-master   Ready    control-plane,master   5m    v1.29.x+k3s1
pi-node1    Ready    <none>                 30s   v1.29.x+k3s1
pi-node2    Ready    <none>                 25s   v1.29.x+k3s1
```

---

## 4. 基本的な kubectl コマンド

```bash
# クラスター全体の状態
kubectl get nodes
kubectl get pods --all-namespaces    # 全 Pod（k3s 内部含む）
kubectl cluster-info

# リソース一覧
kubectl get all                      # デフォルト namespace
kubectl get all -n kube-system       # k3s 内部

# 詳細情報
kubectl describe node pi-master
kubectl describe pod <pod-name>

# ログ
kubectl logs <pod-name>
kubectl logs -f <pod-name>           # tail -f 相当

# 削除
kubectl delete pod <pod-name>
kubectl delete -f manifest.yaml
```

---

## 5. k3s のリソース使用量を確認

```bash
# k3s プロセスのメモリ
ps aux | grep k3s | awk '{print $6/1024 " MB"}'

# ノードのリソース使用状況
kubectl top nodes     # metrics-server が必要（k3s にデフォルト内蔵）
kubectl top pods -A
```

---

## 6. k3s の停止・アンインストール

```bash
# マスターで停止
sudo /usr/local/bin/k3s-uninstall.sh

# ワーカーで停止
sudo /usr/local/bin/k3s-agent-uninstall.sh
```

---

## 7. シングルノードで学ぶ場合

複数の Pi がなくても、`pi-master` 1 台のみでほぼすべての概念を学べる。
ワーカーがない場合、Pod はマスターノードにスケジュールされる。

```bash
# マスターノードへの Pod スケジューリングを許可（デフォルトで許可済み）
kubectl taint nodes pi-master node-role.kubernetes.io/control-plane:NoSchedule-
```

---

## 8. まとめ

| コマンド | 説明 |
|---------|------|
| `curl -sfL https://get.k3s.io \| sh -` | マスターインストール |
| `kubectl get nodes` | ノード一覧 |
| `kubectl get pods -A` | 全 Pod 一覧 |
| `kubectl describe <resource> <name>` | 詳細情報 |
| `kubectl logs <pod>` | Pod ログ |

次は Kubernetes の基本リソース（Pod・Deployment・Service）を学ぶ。
