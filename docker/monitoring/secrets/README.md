# secrets ディレクトリ

このディレクトリに `grafana_admin_password.txt` を手動で作成してください。

```bash
echo "your-secure-password" > grafana_admin_password.txt
chmod 600 grafana_admin_password.txt
```

> **注意**: `*.txt` はすべて `.gitignore` されています。パスワードファイルをコミットしないでください。
