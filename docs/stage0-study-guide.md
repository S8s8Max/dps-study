# ステージ0 学習ガイド — クラスタを扱える状態にする

## ステージ0 の目標

ラズパイ1台を、分散処理の学習に使える「きちんと管理されたサーバー」として整備する。
具体的には次の状態を目指す：

- SSH で安全に接続できる
- Ansible で設定変更を自動化・再現できる
- Docker でアプリケーションをコンテナとして動かせる
- Prometheus + Grafana でリソース使用状況を監視できる
- 上記すべてを Ansible Playbook 1回で再構築できる（冪等性）

## なぜステージ0が必要か

分散処理の本題（並列計算・メッセージング・ストリーム処理）に入る前に、
「ノードを自由に設定・管理できる」スキルが必要になる。

具体的には、ステージ1以降で次のような場面が何度も来る：

| 場面 | 必要なスキル |
|------|------------|
| 全ワーカーに同じパッケージをインストールしたい | Ansible |
| ワーカープロセスをコンテナとして分離・管理したい | Docker |
| どのノードが重いか、ネットワークが詰まっていないか確認したい | 監視（Prometheus/Grafana）|
| ノードが壊れたとき、同じ状態に素早く復元したい | Ansible（冪等性）|

## 学習マップ

```
01 ハードウェア・OS
   └─> 02 Linux 基本操作
           └─> 03 ネットワーク設定
                   └─> 04 SSH（鍵認証）
                           └─> 05 時刻同期（chrony）
                                   └─> 06 Ansible
                                           ├─> 07 Docker
                                           └─> 08 監視スタック
                                                   └─> 09 冪等性テスト（総仕上げ）
```

各ステップは前のステップの知識・設定を前提とする。スキップしないこと。

## 各ステップの概要

### 01. ハードウェア準備と OS 初期セットアップ
**教材：** `docs/stage0/01-hardware-os.md`

| 項目 | 内容 |
|------|------|
| 学ぶこと | microSD への OS 書き込み、初回起動、ホスト名・ユーザー設定 |
| 使うツール | Raspberry Pi Imager（手元 Mac）|
| 完了条件 | `ssh pi-master` で接続できる |
| 想定時間 | 1〜2時間 |

---

### 02. Linux 基本操作
**教材：** `docs/stage0/02-linux-basics.md`

| 項目 | 内容 |
|------|------|
| 学ぶこと | ファイル操作・パーミッション・プロセス管理・パッケージ管理（apt）|
| 使うツール | bash、apt、systemctl、journalctl |
| 完了条件 | パッケージのインストール・サービスの起動/停止を自分で行える |
| 想定時間 | 2〜3時間 |

---

### 03. ネットワーク設定
**教材：** `docs/stage0/03-network.md`

| 項目 | 内容 |
|------|------|
| 学ぶこと | IP アドレス・サブネット・ルーティングの基本、nmcli で IP を固定する |
| 使うツール | nmcli、ip、ping、ss |
| 完了条件 | ラズパイに固定 IP が設定され、再起動後も維持される |
| 想定時間 | 1〜2時間 |

---

### 04. SSH 設定
**教材：** `docs/stage0/04-ssh.md`

| 項目 | 内容 |
|------|------|
| 学ぶこと | 公開鍵認証の仕組み、`~/.ssh/config` による接続の簡略化、パスワード認証の無効化 |
| 使うツール | ssh-keygen、ssh-copy-id、sshd_config |
| 完了条件 | パスワードなしで `ssh pi-master` と打つだけで接続できる |
| 想定時間 | 1〜2時間 |

---

### 05. 時刻同期（chrony）
**教材：** `docs/stage0/05-time-sync.md`

| 項目 | 内容 |
|------|------|
| 学ぶこと | 分散システムで時刻がずれると何が起きるか、chrony による NTP 同期 |
| 使うツール | chronyc、timedatectl |
| 完了条件 | `chronyc tracking` で時刻同期が安定していることを確認できる |
| 想定時間 | 30分〜1時間 |

---

### 06. Ansible による自動化
**教材：** `docs/stage0/06-ansible.md`

| 項目 | 内容 |
|------|------|
| 学ぶこと | Ansible のアーキテクチャ、インベントリ・Playbook・ロールの書き方、冪等性 |
| 使うツール | ansible、ansible-playbook、ansible-lint |
| 完了条件 | `ansible-playbook site.yml` で共通設定（パッケージ・chrony・SSH）が適用される |
| 想定時間 | 3〜4時間 |

**このステップで作成する Ansible ロール：**
- `roles/common`：パッケージ更新、タイムゾーン設定、chrony、SSH hardening

---

### 07. Docker のセットアップ
**教材：** `docs/stage0/07-docker.md`

| 項目 | 内容 |
|------|------|
| 学ぶこと | コンテナの概念、Docker のインストール、基本操作、Docker Compose |
| 使うツール | docker、docker compose |
| 完了条件 | `docker run hello-world` が動き、Ansible で Docker をインストールできる |
| 想定時間 | 2〜3時間 |

**このステップで作成する Ansible ロール：**
- `roles/docker`：Docker インストール・ユーザー設定

---

### 08. 監視スタック（Prometheus + Grafana）
**教材：** `docs/stage0/08-monitoring.md`

| 項目 | 内容 |
|------|------|
| 学ぶこと | メトリクス監視の仕組み、node_exporter・Prometheus・Grafana の構成 |
| 使うツール | docker compose、Grafana UI |
| 完了条件 | Grafana ダッシュボードで CPU・メモリ・ディスク使用率を確認できる |
| 想定時間 | 2〜3時間 |

**RAM 1GB への配慮：** メモリ使用量の上限設定・軽量化オプションを明記する。

**このステップで作成するもの：**
- `roles/monitoring`：node_exporter のインストール
- `docker/monitoring/compose.yml`：Prometheus + Grafana

---

### 09. 冪等性テストとクラスタ再構築演習
**教材：** `docs/stage0/09-rebuild-test.md`

| 項目 | 内容 |
|------|------|
| 学ぶこと | Ansible の冪等性検証、microSD 初期化からの完全再構築手順 |
| 使うツール | ansible-playbook（2回目実行）、Raspberry Pi Imager |
| 完了条件 | Playbook の2回目実行で `changed=0`、OS 再インストールから復旧できる |
| 想定時間 | 2〜3時間 |

---

## 完了チェックリスト

ステージ0修了の判定基準：

- [ ] `ssh pi-master` でパスワードなし接続できる
- [ ] `ansible all -m ping` が `pong` を返す
- [ ] `ansible-playbook ansible/site.yml` が最後まで通る
- [ ] 2回目実行で `changed=0` になる
- [ ] `http://pi-master:3000` で Grafana ダッシュボードが開く
- [ ] OS を再インストールして Playbook を流したら元の状態に戻る

## 参考資料

- [Raspberry Pi 公式ドキュメント](https://www.raspberrypi.com/documentation/)
- [Ansible Getting Started](https://docs.ansible.com/ansible/latest/getting_started/index.html)
- [Docker 公式ドキュメント（arm64）](https://docs.docker.com/engine/install/debian/)
- [Prometheus 公式ドキュメント](https://prometheus.io/docs/introduction/overview/)
- [Grafana 公式ドキュメント](https://grafana.com/docs/)
