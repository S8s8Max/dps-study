"""k3s 学習用ヘルスチェックサーバー。
/health  → liveness probe 用（200 OK / 500）
/ready   → readiness probe 用（200 OK / 503）
/fail    → POST で liveness を意図的に失敗させる（再起動の確認用）
/toggle  → POST で readiness を切り替える（Service 除外の確認用）

使い方（直接起動）:
  pip install aiohttp
  python3 01_health_server.py

使い方（Docker/k3s）:
  docker build -t health-server:latest docker/stage5/
  docker run -p 8080:8080 health-server:latest
"""
import asyncio
import os
import signal
import time
from aiohttp import web

PORT = int(os.getenv("PORT", "8080"))

# 状態フラグ（グローバル）
live = True
ready = False


async def startup_delay():
    """起動直後は 'ready' を False にして readiness probe を意図的に失敗させる。"""
    global ready
    delay = int(os.getenv("STARTUP_DELAY", "5"))
    print(f"[server] {delay}s の起動待ちをシミュレート...")
    await asyncio.sleep(delay)
    ready = True
    print("[server] ready = True → Readiness probe が通るようになった")


async def health_handler(request: web.Request) -> web.Response:
    if not live:
        return web.Response(status=500, text="UNHEALTHY\n")
    return web.Response(text="OK\n")


async def ready_handler(request: web.Request) -> web.Response:
    if not ready:
        return web.Response(status=503, text="NOT READY\n")
    return web.Response(text="READY\n")


async def fail_handler(request: web.Request) -> web.Response:
    """POST /fail → liveness を失敗させる（k3s が再起動するのを確認）。"""
    global live
    live = False
    print("[server] live = False → Liveness probe が失敗し始めた（k3s が再起動する）")
    return web.Response(text="Liveness set to FAIL\n")


async def toggle_handler(request: web.Request) -> web.Response:
    """POST /toggle → readiness を切り替える（Service への追加/除外を確認）。"""
    global ready
    ready = not ready
    status = "READY" if ready else "NOT READY"
    print(f"[server] ready = {ready} → {status}")
    return web.Response(text=f"Readiness toggled: {status}\n")


async def info_handler(request: web.Request) -> web.Response:
    return web.Response(
        text=(
            f"hostname: {os.uname().nodename}\n"
            f"pid: {os.getpid()}\n"
            f"live: {live}\n"
            f"ready: {ready}\n"
            f"uptime: {time.monotonic():.1f}s\n"
        )
    )


async def main():
    global ready
    app = web.Application()
    app.router.add_get("/health", health_handler)
    app.router.add_get("/ready", ready_handler)
    app.router.add_post("/fail", fail_handler)
    app.router.add_post("/toggle", toggle_handler)
    app.router.add_get("/info", info_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"[server] 起動: port={PORT}")
    print(f"  GET  /health  → liveness probe")
    print(f"  GET  /ready   → readiness probe")
    print(f"  POST /fail    → liveness を失敗させる")
    print(f"  POST /toggle  → readiness を切り替える")
    print(f"  GET  /info    → 状態確認\n")

    asyncio.create_task(startup_delay())

    # SIGTERM で graceful shutdown
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()
    loop.add_signal_handler(signal.SIGTERM, stop_event.set)

    try:
        await stop_event.wait()
    except asyncio.CancelledError:
        pass
    finally:
        print("[server] SIGTERM 受信 → graceful shutdown")
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
