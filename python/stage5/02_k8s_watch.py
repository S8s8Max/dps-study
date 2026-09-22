"""k3s Pod の状態を kubectl で監視するスクリプト。
Kubernetes Python クライアントの代わりに kubectl をサブプロセスで呼ぶ。
（依存を最小にし、kubeconfig があれば Mac/Pi どちらでも動く）

使い方:
  python3 02_k8s_watch.py                      # dps-study namespace を監視
  python3 02_k8s_watch.py --namespace kube-system
"""
import argparse
import json
import subprocess
import sys
import time


def run_kubectl(*args: str) -> str:
    result = subprocess.run(
        ["kubectl", *args],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        return f"[error] {result.stderr.strip()}"
    return result.stdout.strip()


def get_pods(namespace: str) -> list[dict]:
    out = run_kubectl("get", "pods", "-n", namespace, "-o", "json")
    if out.startswith("[error]"):
        print(out)
        return []
    data = json.loads(out)
    pods = []
    for item in data.get("items", []):
        meta = item["metadata"]
        status = item["status"]
        containers = status.get("containerStatuses", [])
        restarts = sum(c.get("restartCount", 0) for c in containers)
        ready_count = sum(1 for c in containers if c.get("ready", False))
        pods.append({
            "name": meta["name"],
            "phase": status.get("phase", "Unknown"),
            "ready": f"{ready_count}/{len(containers)}",
            "restarts": restarts,
            "age": meta.get("creationTimestamp", ""),
        })
    return pods


def print_pods(pods: list[dict]):
    fmt = "{:<40} {:<12} {:<8} {:<8}"
    print(fmt.format("NAME", "PHASE", "READY", "RESTARTS"))
    print("-" * 72)
    for p in pods:
        phase_mark = "✓" if p["phase"] == "Running" else "✗"
        print(fmt.format(
            p["name"][:39],
            f"{phase_mark} {p['phase']}",
            p["ready"],
            p["restarts"],
        ))


def get_events(namespace: str, tail: int = 10) -> list[str]:
    out = run_kubectl(
        "get", "events", "-n", namespace,
        "--sort-by=.lastTimestamp",
        "--field-selector=type!=Normal",   # Warning のみ
    )
    if out.startswith("[error]") or not out:
        return []
    lines = out.split("\n")
    return lines[-tail:] if len(lines) > tail else lines


def watch_loop(namespace: str, interval: float = 5.0):
    print(f"[watch] namespace: {namespace}  更新間隔: {interval}s  (Ctrl-C で終了)\n")
    prev_restarts: dict[str, int] = {}
    try:
        while True:
            pods = get_pods(namespace)
            ts = time.strftime("%H:%M:%S")
            print(f"\n=== {ts} ===")
            print_pods(pods)

            # 再起動を検知して通知
            for p in pods:
                prev = prev_restarts.get(p["name"], 0)
                if p["restarts"] > prev:
                    print(f"\n⚠ [{ts}] {p['name']} が再起動しました "
                          f"(restarts: {prev} → {p['restarts']})")
                prev_restarts[p["name"]] = p["restarts"]

            # Warning イベント
            events = get_events(namespace)
            if events:
                print("\n--- Warning イベント ---")
                for e in events:
                    print(f"  {e}")

            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[watch] 終了")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--namespace", "-n", default="dps-study")
    parser.add_argument("--interval", "-i", type=float, default=5.0)
    args = parser.parse_args()

    # kubectl の疎通確認
    out = run_kubectl("cluster-info", "--request-timeout=3s")
    if out.startswith("[error]"):
        print("kubectl が使えません。kubeconfig を確認してください。")
        print(out)
        sys.exit(1)
    print(out.split("\n")[0])   # クラスター URL だけ表示

    watch_loop(args.namespace, args.interval)


if __name__ == "__main__":
    main()
