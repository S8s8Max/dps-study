# 09 冪等性テストと再構築演習

## 学習目標

- Ansible Playbook の冪等性（何度実行しても同じ結果になること）を実際に確認する
- `changed=0` の意味と重要性を理解する
- Pi を初期状態に戻して、ゼロから完全再構築できることを確認する
- 「コードが唯一の真実（Infrastructure as Code）」の概念を体得する

---

## 1. 概念説明

### 冪等性（べきとうせい）とは

同じ操作を何度繰り返しても、結果が変わらない性質のことです。

```
1回目の実行: Pi を設定する（changed あり）
      ↓
2回目の実行: すでに正しい状態 → 何も変えない（changed=0）
      ↓
100回目の実行: 結果は常に同じ
```

Ansible が冪等性を保証するのは、各タスクが「現在の状態を確認してから、必要な場合のみ変更する」という設計になっているからです。

### Infrastructure as Code（IaC）の価値

```
[従来の方法]                    [IaC の方法]
  手順書を見ながら手動設定    →   git clone して ansible-playbook 実行
  再現性なし・人為ミスあり    →   完全再現可能・自動化
  「以前どう設定したか不明」  →   コードが唯一の記録
```

---

## 2. 冪等性テスト

### 2.1 Playbook を 2 回実行して比較する

```bash
cd ~/dps-study/ansible

# 1回目の実行
ansible-playbook site.yml | tee /tmp/run1.txt

# 2回目の実行
ansible-playbook site.yml | tee /tmp/run2.txt

# changed の数を比較
grep "changed=" /tmp/run1.txt
grep "changed=" /tmp/run2.txt
```

**期待する結果**:

```
# 1回目（初回または設定変更後）
PLAY RECAP ****
pi-master  : ok=XX  changed=XX  unreachable=0  failed=0

# 2回目（冪等性確認）
PLAY RECAP ****
pi-master  : ok=XX  changed=0   unreachable=0  failed=0
```

`changed=0` が確認できたら冪等性テスト合格です。

### 2.2 各ロールの冪等性を個別に確認する

```bash
# common ロールのみ
ansible-playbook site.yml --tags common

# docker ロールのみ
ansible-playbook site.yml --tags docker

# monitoring ロールのみ
ansible-playbook site.yml --tags monitoring
```

> **Note**: タグが設定されていない場合は `--limit` でホストを絞るだけでも確認できます。

---

## 3. 再構築演習（オプション）

> **警告**: この演習では Pi を初期化します。SSH の設定、Docker、モニタリングスタックがすべて削除されます。
> バックアップが必要なデータがある場合は事前にコピーしてください。

### 3.1 事前確認

```bash
# 現在の状態を記録する
ansible pi-master -m command -a "docker ps"
ansible pi-master -m command -a "systemctl list-units --type=service --state=running"

# 管理PCの SSH 鍵が手元にあることを確認
ls -la ~/.ssh/id_ed25519 ~/.ssh/id_ed25519.pub
```

### 3.2 Pi を初期状態に戻す

```bash
# Pi で実行（ssh pi-master）
# Docker コンテナとボリュームを削除
cd /opt/monitoring && sudo docker compose down -v
sudo rm -rf /opt/monitoring

# Docker を削除
sudo apt-get purge -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
sudo rm -rf /var/lib/docker /etc/docker /etc/apt/keyrings/docker.asc
sudo rm /etc/apt/sources.list.d/docker.list

# SSH 設定を元に戻す
sudo cp /etc/ssh/sshd_config.bak /etc/ssh/sshd_config
sudo systemctl restart ssh

# chrony を削除
sudo apt-get purge -y chrony
sudo apt-get autoremove -y
```

> **注意**: SSH 設定を元に戻した後は、パスワード認証が再び有効になります。

### 3.3 Ansible で完全再構築する

初期化後、管理PCから Playbook を実行するだけですべてが再構築されます。

```bash
# 管理PCで実行
cd ~/dps-study/ansible
ansible-playbook site.yml
```

```
PLAY RECAP ****
pi-master  : ok=XX  changed=XX  unreachable=0  failed=0
```

`failed=0` で完了すれば再構築成功です。

### 3.4 動作確認

```bash
# SSH 接続確認
ssh pi-master 'echo "SSH OK"'

# Docker 確認
ssh pi-master 'docker ps'

# モニタリング確認
ssh -N -L 3000:localhost:3000 pi-master &
# ブラウザで http://localhost:3000 にアクセス
```

---

## 4. Stage 0 最終チェックリスト

すべての項目が完了していることを確認してください。

### 環境構築

- [ ] Pi 3B に Raspberry Pi OS Bookworm (arm64) がインストールされている
- [ ] SSH 公開鍵認証でログインできる（パスワード認証なし）
- [ ] `~/.ssh/config` に pi-master の設定がある
- [ ] 静的 IP アドレスが設定されている（docs/hardware.md に記載済み）

### Ansible 自動化

- [ ] `ansible-playbook site.yml` が `failed=0` で完了する
- [ ] 2 回目の実行で `changed=0` になる（冪等性）

### Docker

- [ ] `docker ps` で全コンテナが `Up` 状態
- [ ] `docker compose` コマンドが使える（Compose v2 プラグイン）

### モニタリング

- [ ] Grafana `http://localhost:3000` にログインできる
- [ ] Prometheus Targets で node-exporter が `UP`
- [ ] Node Exporter Full ダッシュボードでメトリクスが表示されている

### コード品質

- [ ] `docs/hardware.md` に実際の IP アドレスが記載されている
- [ ] シークレット（パスワード）がリポジトリにコミットされていない
- [ ] 変更内容をすべて git にコミット済み

---

## 5. まとめ

### Stage 0 で習得したこと

```
01. ハードウェア・OS  → Raspberry Pi の初期設定、ヘッドレスセットアップ
02. Linux 基礎       → ファイル操作、プロセス管理、パッケージ管理
03. ネットワーク     → 静的 IP (nmcli)、TCP/IP、サブネット
04. SSH              → 公開鍵認証、sshd_config 強化
05. 時刻同期         → chrony、NTP、RTC なし環境
06. Ansible          → Inventory、Playbook、Role、冪等性
07. Docker           → コンテナ、arm64 イメージ、Compose v2
08. モニタリング     → Prometheus、Grafana、node-exporter
09. 再構築テスト     → IaC の価値体験、changed=0 確認
```

### Stage 1 へ

Stage 0 の基盤があれば、Stage 1 の Kubernetes (k3s) 導入に進めます。
Pi 3B 1 台での k3s シングルノードから始めます。

```bash
# リポジトリの最新化を確認
git log --oneline -5
git status
```
