# ラズパイ分散処理学習リポジトリ

Raspberry Pi を使って分散処理を段階的に学ぶための、教材と実行コードを管理するリポジトリです。

## 学習ステージ一覧

| ステージ | テーマ | 状態 |
|---------|--------|------|
| **ステージ0** | クラスタを扱える状態にする（Linux・ネットワーク・SSH・Ansible・Docker・監視）| ✅ 完了 |
| **ステージ1** | 並列計算の基本（multiprocessing、mpi4py）| ✅ 完了 |
| **ステージ2** | メッセージングとパイプライン（ZeroMQ、MQTT/NATS）| ✅ 完了 |
| **ステージ3** | 状態を持つストリーム処理（パーティショニング、時間窓、Redpanda）| ✅ 完了 |
| **ステージ4** | 分散フレームワーク（Ray、Dask）| ✅ 完了 |
| **ステージ5** | オーケストレーションと耐障害性（k3s）| ✅ 完了 |
| **ステージ6** | 分散システムの理論（Raft、CAP、論理時計）| ✅ 完了 |

**最終目標：** カメラ映像や暗号資産の約定データなど、データ量が多くリアルタイム性のある処理を分散システムで扱えるようになる。

## 前提環境

| 項目 | 内容 |
|------|------|
| ハードウェア | Raspberry Pi 3 Model B（詳細は `docs/hardware.md` 参照）|
| OS | Raspberry Pi OS Lite 64-bit（Bookworm 以降）|
| アーキテクチャ | arm64（aarch64）|
| 管理用PC | macOS |
| ネットワーク管理 | NetworkManager（`nmcli`）|

## ステージ0 の進め方

ステージ0は以下の9ステップで構成されています。**01 から順番に**進めてください。

```
docs/stage0/
├── 01-hardware-os.md     ハードウェア準備と OS 初期セットアップ
├── 02-linux-basics.md    Linux 基本操作
├── 03-network.md         ネットワーク設定（固定IP・nmcli）
├── 04-ssh.md             SSH 設定（鍵認証・セキュリティ）
├── 05-time-sync.md       時刻同期（chrony）
├── 06-ansible.md         Ansible による自動化
├── 07-docker.md          Docker のセットアップと基本操作
├── 08-monitoring.md      監視スタック（Prometheus・Grafana）
└── 09-rebuild-test.md    冪等性テスト・クラスタ再構築演習
```

全体の設計図は [`docs/stage0-study-guide.md`](docs/stage0-study-guide.md) を参照してください。

### Ansible Playbook の使い方

ステージ0の後半（06 以降）では Ansible を使って環境構築を自動化します。

```bash
# 手元の Mac 上で実行

# 1. Ansible のインストール（初回のみ）
brew install ansible

# 2. インベントリの編集（ラズパイの IP アドレスを設定）
vi ansible/inventory/hosts.yml

# 3. 全ノードへの疎通確認
ansible all -m ping

# 4. 全設定の適用
ansible-playbook ansible/site.yml

# 5. 冪等性の確認（2回目は changed=0 になるはず）
ansible-playbook ansible/site.yml
```

## ディレクトリ構成

```
.
├── README.md                      # このファイル
├── docs/
│   ├── hardware.md                # 機種・台数・IP・役割の表
│   ├── stage0-study-guide.md      # ステージ0の全体計画（設計図）
│   └── stage0/
│       ├── 01-hardware-os.md
│       ├── 02-linux-basics.md
│       ├── 03-network.md
│       ├── 04-ssh.md
│       ├── 05-time-sync.md
│       ├── 06-ansible.md
│       ├── 07-docker.md
│       ├── 08-monitoring.md
│       └── 09-rebuild-test.md
├── ansible/
│   ├── ansible.cfg
│   ├── inventory/hosts.yml
│   ├── group_vars/
│   ├── site.yml
│   └── roles/
│       ├── common/                # パッケージ・タイムゾーン・chrony・SSH設定
│       ├── docker/
│       └── monitoring/            # node_exporter・Prometheus・Grafana
├── docker/
│   └── monitoring/compose.yml
└── logs/                          # 学習ログ（自由に記録してください）
```

## 学習ログの残し方

`logs/` ディレクトリに自由に記録を残してください。

```bash
# 例：日付ごとにファイルを作る
echo "## 2026-09-21\n- 01-hardware-os を完了\n- SSH の鍵認証でつまずいた" >> logs/2026-09.md
```

## 参考資料

- [Raspberry Pi 公式ドキュメント](https://www.raspberrypi.com/documentation/)
- [Ansible 公式ドキュメント](https://docs.ansible.com/)
- [Docker 公式ドキュメント](https://docs.docker.com/)
