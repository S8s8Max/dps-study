# Python 環境のセットアップ（Stage 1 以降で必須）

Stage 1 以降は Python パッケージを追加インストールします。
**ラズパイ上でいきなり `pip install` すると失敗します。** 先にこのページを読んでください。

## なぜ `pip install` が失敗するのか

Raspberry Pi OS Bookworm（Debian 12）以降では、次のエラーが出ます。

```console
$ pip install pyzmq
error: externally-managed-environment

× This environment is externally managed
╰─> To install Python packages system-wide, try apt install
    python3-xyz, where xyz is the package you are trying to
    install.
```

これは不具合ではなく **PEP 668** という仕様です。

OS 自体が Python で動く部分を持っているため（`apt` の内部処理など）、
システムの Python に `pip` で勝手にパッケージを入れると、
バージョン衝突で **OS のコマンドが壊れる** ことがあります。
それを防ぐために、システムの Python は「外部管理下（externally managed）」として
保護されるようになりました。

## 解決策：仮想環境（venv）を使う

プロジェクト専用の Python 環境を作り、そこにインストールします。
システムの Python には一切触れないので安全です。

```bash
# リポジトリのルートで実行
cd ~/dps-study

# 1. 仮想環境を作る（初回のみ）
python3 -m venv .venv

# 2. 有効化する（ログインするたびに必要）
source .venv/bin/activate

# プロンプトの先頭に (.venv) が付けば成功
# (.venv) pi@pi-master:~/dps-study $
```

有効化した状態なら `pip install` がそのまま通ります。

```bash
# 進めているステージの分だけ入れる（推奨）
pip install -r requirements/stage1.txt

# 全ステージ分をまとめて入れる場合
pip install -r requirements.txt
```

### 抜けるとき

```bash
deactivate
```

### 注意：有効化はシェルごと

`source .venv/bin/activate` は**そのシェルの中だけ**有効です。
SSH を切って入り直したら、もう一度実行してください。

```bash
# 毎回打つのが面倒なら .bashrc の末尾に追記してもよい
echo 'cd ~/dps-study && source .venv/bin/activate' >> ~/.bashrc
```

> ⚠️ ただし上記を入れると**ログインのたびに自動で `cd` する**ようになります。
> 戻したいときは `~/.bashrc` の該当行を削除してください。

## ラズパイ向けの補足

### numpy は apt から入れるほうが速い

`pip install numpy` は環境によってはソースからのビルドになり、
Pi 3B では**30 分以上**かかることがあります。
apt 版（ビルド済み）を再利用すると速いです。

```bash
# システム側に numpy を入れる
sudo apt install -y python3-numpy

# システムのパッケージも見える venv を作る
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
```

`--system-site-packages` を付けると、venv の中から apt で入れた
パッケージも見えるようになります（venv 側に同名パッケージを入れると
そちらが優先されます）。

### mpi4py は先に OpenMPI が必要

`mpi4py` はビルド時に OpenMPI のヘッダを参照します。

```bash
sudo apt install -y libopenmpi-dev openmpi-bin
pip install -r requirements/stage1.txt
```

### Stage 4（Ray・Dask）はストレージを食う

`ray` + `pyarrow` + `pandas` で **1GB 近く**消費します。
microSD の空き容量を先に確認してください。

```bash
df -h /
```

容量が厳しい場合は `ray[default]` ではなく `ray`（最小構成）を使います。
教材のコードは最小構成で動きます（Ray Dashboard だけ使えません）。

## 動作確認

```bash
source .venv/bin/activate

# どの Python を使っているか確認
which python3
# /home/pi/dps-study/.venv/bin/python3  ← venv の中なら OK

# 入っているパッケージ一覧
pip list
```

## やってはいけない回避策

`--break-system-packages` を付けると PEP 668 の保護を無視できます。

```bash
# ⚠️ 推奨しない
pip install --break-system-packages pyzmq
```

名前のとおり**システムのパッケージを壊す可能性**があります。
実際に `apt` が動かなくなる事故が起きうるため、この教材では使いません。
venv を使ってください。

## ステージ別の必要パッケージ

| ステージ | 必要なもの | ファイル |
|---------|-----------|---------|
| Stage 0 | なし（Ansible は Mac 側） | — |
| Stage 1 | mpi4py、numpy | `requirements/stage1.txt` |
| Stage 2 | pyzmq、paho-mqtt、nats-py | `requirements/stage2.txt` |
| Stage 3 | aiokafka | `requirements/stage3.txt` |
| Stage 4 | ray、dask、pandas、pyarrow | `requirements/stage4.txt` |
| Stage 5 | aiohttp | `requirements/stage5.txt` |
| Stage 6 | なし（標準ライブラリのみ） | — |
