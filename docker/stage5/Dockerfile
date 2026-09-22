# ヘルスチェックサーバー（python/stage5/01_health_server.py）の Docker イメージ
# arm64 ネイティブ対応（Raspberry Pi 用）
FROM python:3.13-slim

WORKDIR /app

COPY requirements/stage5.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY python/stage5/01_health_server.py ./health_server.py

ENV PORT=8080
EXPOSE 8080

# k3s の SIGTERM を受け取って graceful shutdown するため
STOPSIGNAL SIGTERM

CMD ["python3", "health_server.py"]
