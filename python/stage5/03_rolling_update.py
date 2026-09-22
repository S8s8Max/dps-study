"""ローリングアップデートと耐障害性のデモスクリプト。
kubectl を使ってデプロイ・スケール・ロールバックを自動で実行し、
各ステップで Pod の状態を表示する。

使い方:
  python3 03_rolling_update.py --namespace dps-study
"""
import argparse
import subprocess
import sys
import time


def kubectl(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["kubectl", *args],
        capture_output=True, text=True, check=False,
    )
    if check and result.returncode != 0:
        print(f"[error] {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def wait_for_rollout(deployment: str, namespace: str, timeout: int = 120):
    print(f"  ローリングアップデート待機中...")
    result = subprocess.run(
        ["kubectl", "rollout", "status", f"deployment/{deployment}",
         "-n", namespace, f"--timeout={timeout}s"],
        check=False,
    )
    if result.returncode != 0:
        print(f"  [!] タイムアウトまたはエラー")
        return False
    return True


def show_pods(namespace: str):
    out = kubectl("get", "pods", "-n", namespace,
                  "-o", "custom-columns=NAME:.metadata.name,"
                  "STATUS:.status.phase,RESTARTS:.status.containerStatuses[0].restartCount,"
                  "NODE:.spec.nodeName", check=False)
    print(out or "  (Pod なし)")


def step(title: str):
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--namespace", "-n", default="dps-study")
    parser.add_argument("--deployment", "-d", default="hello-deploy")
    args = parser.parse_args()

    ns = args.namespace
    deploy = args.deployment

    # ── ステップ 1: 初期デプロイ ──
    step("1. 初期デプロイ (replicas=2)")
    kubectl("apply", "-f", "k8s/stage5/01-namespace.yaml")
    kubectl("apply", "-f", "k8s/stage5/03-deployment.yaml")
    wait_for_rollout(deploy, ns)
    show_pods(ns)
    input("\n  Enter で次のステップへ...")

    # ── ステップ 2: スケールアウト ──
    step("2. スケールアウト (replicas=2 → 4)")
    kubectl("scale", f"deployment/{deploy}", "--replicas=4", "-n", ns)
    wait_for_rollout(deploy, ns)
    show_pods(ns)
    input("\n  Enter で次のステップへ...")

    # ── ステップ 3: Pod を強制削除（自動再起動の確認）──
    step("3. Pod を強制削除 → 自動再起動の確認")
    pods = kubectl("get", "pods", "-n", ns, "-l", f"app={deploy}",
                   "-o", "jsonpath={.items[0].metadata.name}", check=False)
    if pods:
        victim = pods.split()[0]
        print(f"  Pod '{victim}' を削除...")
        kubectl("delete", "pod", victim, "-n", ns)
        print("  3秒後の状態:")
        time.sleep(3)
        show_pods(ns)
        print("\n  Deployment が新しい Pod を作成したことを確認")
    else:
        print("  Pod が見つかりません")
    input("\n  Enter で次のステップへ...")

    # ── ステップ 4: ローリングアップデート ──
    step("4. ローリングアップデート（image タグを変更して apply）")
    print("  注意: マニフェストの image を変更してから apply してください")
    print("  例:   busybox:1.37 → busybox:1.36")
    print()
    print("  現在の Revision 履歴:")
    history = kubectl("rollout", "history", f"deployment/{deploy}", "-n", ns, check=False)
    print(history)
    input("\n  Enter でロールバックのデモへ...")

    # ── ステップ 5: ロールバック ──
    step("5. ロールバック（前のリビジョンに戻す）")
    kubectl("rollout", "undo", f"deployment/{deploy}", "-n", ns)
    wait_for_rollout(deploy, ns)
    print("  ロールバック後の状態:")
    show_pods(ns)

    print("\n  ロールバック後の Revision 履歴:")
    history = kubectl("rollout", "history", f"deployment/{deploy}", "-n", ns, check=False)
    print(history)
    input("\n  Enter でクリーンアップへ...")

    # ── ステップ 6: クリーンアップ ──
    step("6. クリーンアップ")
    ans = input("  デプロイしたリソースを削除しますか？ [y/N] ")
    if ans.lower() == "y":
        kubectl("delete", "-f", "k8s/stage5/03-deployment.yaml", check=False)
        print("  削除完了")
    else:
        print("  スキップ")

    print("\n[demo] 完了")


if __name__ == "__main__":
    main()
