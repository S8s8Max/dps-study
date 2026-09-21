# 08 モニタリング（Prometheus + Grafana）

## 学習目標

- Prometheus のアーキテクチャ（Pull 型メトリクス収集）を理解する
- node-exporter でホストメトリクスを公開する方法を学ぶ
- Grafana でダッシュボードを作成し可視化する
- Docker Compose で複数コンテナを一括管理する方法を習得する
- Ansible でモニタリングスタックのデプロイを自動化する

---

## 1. 概念説明

### モニタリングとは

システムの健全性を継続的に計測・記録・可視化することです。
「今何が起きているか」「過去にどんな問題があったか」を把握できます。

```
┌─────────────────────────────────────────────────────────┐
│                    Pi 3B (pi-master)                    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Docker Compose ネットワーク         │   │
│  │  ┌──────────────┐    ┌──────────────┐           │   │
│  │  │ node-exporter│    │  Prometheus  │           │   │
│  │  │   :9100      │◄───│   :9090      │           │   │
│  │  │              │    │  (Pull型)    │           │   │
│  │  └──────────────┘    └──────┬───────┘           │   │
│  │                             │                   │   │
│  │                      ┌──────▼───────┐           │   │
│  │                      │   Grafana    │           │   │
│  │                      │   :3000      │           │   │
│  │                      └──────────────┘           │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
         ▲
         │ ブラウザでアクセス（SSH ポートフォワード経由）
    macOS 管理PC
```

### Prometheus の Pull 型アーキテクチャ

Prometheus は **自分から** ターゲットにアクセスしてメトリクスを取得（Pull）します。
Push 型と比べて、ターゲット側の設定が不要でシンプルです。

```
┌──────────────┐   GET /metrics   ┌──────────────┐
│  Prometheus  │ ──────────────► │ node-exporter│
│              │ ◄────────────── │              │
└──────────────┘   テキスト形式   └──────────────┘
                   メトリクス返却
```

### 3コンポーネントの役割

| コンポーネント | 役割 | ポート |
|---|---|---|
| **node-exporter** | OS・ハードウェアのメトリクスを公開 | 9100 |
| **Prometheus** | メトリクスを収集・保存・クエリ | 9090 |
| **Grafana** | メトリクスを可視化・ダッシュボード作成 | 3000 |

---

## 2. 事前確認

### Docker が動いていることを確認する

```bash
# pi-master で実行
docker ps
# CONTAINER ID   IMAGE   COMMAND   CREATED   STATUS   PORTS   NAMES
# （空でもOK）
```

### ディスク空き容量を確認する

```bash
df -h /
# Filesystem      Size  Used Avail Use% Mounted on
# /dev/mmcblk0p2   30G   5G   24G  18% /
# Avail が 5GB 以上あることを確認
```

### メモリを確認する

```bash
free -h
# total        used        free
# Mem:   926Mi        XXXMi       YYYMi
# Pi 3B は 1GB。used が 700MB 以上の場合は他のプロセスを止めること
```

---

## 3. 手動で動かしてみる（理解のため）

自動化の前に手動で一度動かすことで、何が起きているかを理解します。

### 3.1 ディレクトリ構造を作る

```bash
sudo mkdir -p /opt/monitoring/prometheus
sudo mkdir -p /opt/monitoring/grafana/provisioning/datasources
sudo mkdir -p /opt/monitoring/secrets
```

### 3.2 Grafana パスワードファイルを作る

```bash
# 安全なパスワードを設定する（例: ランダム文字列）
echo "change_this_secure_password" | sudo tee /opt/monitoring/secrets/grafana_admin_password.txt
sudo chmod 600 /opt/monitoring/secrets/grafana_admin_password.txt
```

> **セキュリティ注意**: パスワードは必ず変更してください。このファイルは `.gitignore` 済みで、リポジトリにはコミットされません。

### 3.3 設定ファイルをコピーする

```bash
# リポジトリから Pi へコピー（管理PCで実行）
rsync -av ~/dps-study/docker/monitoring/ pi-master:/opt/monitoring/
```

### 3.4 コンテナを起動する

```bash
# pi-master で実行
cd /opt/monitoring
sudo docker compose up -d
```

### 3.5 動作確認

```bash
# コンテナが起動しているか確認
docker ps
# CONTAINER ID   IMAGE                       STATUS
# xxx            grafana/grafana:11.2.2      Up X seconds
# yyy            prom/prometheus:v2.54.1     Up X seconds
# zzz            prom/node-exporter:v1.8.2   Up X seconds

# node-exporter のメトリクスを確認
curl http://localhost:9100/metrics | head -20
# # HELP go_gc_duration_seconds A summary of the pause duration of garbage collection cycles.
# ...

# Prometheus の状態を確認
curl http://localhost:9090/-/healthy
# Prometheus Server is Healthy.
```

---

## 4. ブラウザからアクセスする（SSH ポートフォワード）

Pi 3B は GUI がないため、**管理PC のブラウザ**から SSH ポートフォワード経由でアクセスします。

### 4.1 SSH ポートフォワードトンネルを張る

管理PC（macOS）のターミナルで実行します。

```bash
# Grafana（3000番）をローカルに転送
ssh -L 3000:localhost:3000 pi-master

# または -N フラグでコマンド実行なしのトンネルのみ
ssh -N -L 3000:localhost:3000 pi-master &
```

`~/.ssh/config` に追加しておくと便利です（[04-ssh.md](04-ssh.md) 参照）:

```
Host pi-master
    HostName 192.168.1.100
    User pi
    IdentityFile ~/.ssh/id_ed25519
    LocalForward 3000 localhost:3000
    LocalForward 9090 localhost:9090
```

この設定があれば `ssh pi-master` するだけでポートフォワードが有効になります。

### 4.2 Grafana にログインする

ブラウザで `http://localhost:3000` にアクセスします。

```
ユーザー名: admin
パスワード: （3.2 で設定したパスワード）
```

### 4.3 Prometheus UI を確認する

ブラウザで `http://localhost:9090` にアクセスします。

- **Status > Targets**: node-exporter が UP になっているか確認

```
Status > Targets
node-exporter (1/1 up)
  Endpoint: http://node-exporter:9100/metrics
  State: UP
```

---

## 5. Grafana でダッシュボードを作る

### 5.1 Node Exporter Full ダッシュボードをインポートする

Grafana コミュニティが公開している既成のダッシュボードを使います。

1. Grafana にログイン
2. 左メニュー → **Dashboards** → **Import**
3. Dashboard ID に `1860` を入力して **Load**
4. Prometheus データソースを選択して **Import**

これだけで CPU・メモリ・ディスク・ネットワークの詳細なダッシュボードが表示されます。

### 5.2 基本的なクエリを試す（PromQL）

Prometheus の **Explore** でクエリを試してみましょう。

```promql
# CPU 使用率（%）
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# メモリ使用率（%）
100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)

# ディスク使用率（%）
100 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"} * 100)
```

---

## 6. Ansible で自動化する

手動手順を Ansible Playbook に落とし込みます。

### 6.1 site.yml の確認

```yaml
# ansible/site.yml
- name: 全ノード共通設定
  hosts: all
  become: true
  roles:
    - common
    - docker
    - monitoring   # ← 追加済み
```

### 6.2 Playbook を実行する

```bash
# 管理PCのリポジトリディレクトリで実行
cd ~/dps-study/ansible

# まず --check でドライランして変更点を確認
ansible-playbook site.yml --check --diff

# 実行
ansible-playbook site.yml
```

### 6.3 パスワードを変数で渡す（ansible-vault）

デフォルト値 `"changeme"` を本番用パスワードに上書きするには:

```bash
# vault で暗号化されたファイルを作る
ansible-vault create ansible/group_vars/all_secret.yml
```

```yaml
# all_secret.yml の内容（ansible-vault で編集）
grafana_admin_password: "your-secure-password-here"
```

```bash
# vault パスワードを使って実行
ansible-playbook site.yml --ask-vault-pass
```

> **セキュリティ**: `all_secret.yml` は暗号化されていますが、念のため `.gitignore` に追加することを推奨します。パスワード平文のファイルは絶対にコミットしないでください。

---

## 7. よくあるエラーと対処法

### コンテナが起動しない

```bash
# ログを確認する
docker compose -f /opt/monitoring/compose.yml logs

# よくある原因
# 1. メモリ不足 → free -h で確認
# 2. ポートが使用中 → ss -tlnp | grep 3000
# 3. パスワードファイルがない → ls -la /opt/monitoring/secrets/
```

### Prometheus が node-exporter を見つけられない

```bash
# Prometheus ターゲットの状態を確認
curl http://localhost:9090/api/v1/targets | python3 -m json.tool

# 同じ Docker ネットワークにいるか確認
docker network inspect monitoring
```

### Grafana に接続できない

```bash
# SSH ポートフォワードが有効か確認
ss -tlnp | grep 3000   # macOS ならローカルでポートが開いているか確認

# Grafana コンテナのログを確認
docker logs grafana
```

### 再起動後にコンテナが起動しない

```yaml
# compose.yml の restart ポリシーを確認
restart: unless-stopped  # 手動 stop しない限り自動再起動
```

---

## 8. まとめと次のステップ

### 今回の学習内容

| 項目 | 習得内容 |
|---|---|
| Pull 型モニタリング | Prometheus が自分からターゲットへ取得しに行く仕組み |
| node-exporter | ホスト OS のメトリクスをコンテナから公開する方法 |
| Docker Compose | 複数コンテナを YAML で定義・一括管理する方法 |
| Grafana | データソース設定・ダッシュボードインポート |
| SSH ポートフォワード | Pi の Web UI に安全にアクセスする方法 |
| Ansible 自動化 | モニタリングスタックのデプロイを Playbook で再現可能にする |
| secrets 管理 | パスワードをファイル・ansible-vault で安全に扱う方法 |

### Stage 0 完了チェックリスト

- [ ] `docker ps` で 3 コンテナが `Up` 状態になっている
- [ ] `http://localhost:3000` で Grafana にログインできる
- [ ] Prometheus Targets で node-exporter が `UP` になっている
- [ ] Node Exporter Full ダッシュボードで CPU/メモリが表示されている
- [ ] `ansible-playbook site.yml` を再実行して `changed=0` になる（冪等性）

### 次のステップ（Stage 1 以降）

Stage 0 が完了したら `docs/stage0/09-rebuild-test.md` で冪等性テストを実施します。
その後 Stage 1 では Kubernetes (k3s) の導入に進みます。

```bash
# 次のドキュメントへ
cat docs/stage0/09-rebuild-test.md
```
