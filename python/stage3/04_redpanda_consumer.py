"""Redpanda コンシューマー：コンシューマーグループでメッセージを読む。
使い方:
  # 1 インスタンス目: パーティション 0 担当
  python3 04_redpanda_consumer.py
  # 2 インスタンス目（別ターミナル）: パーティション 1 担当
  python3 04_redpanda_consumer.py
  # 3 インスタンス目（別ターミナル）: パーティション 2 担当
  python3 04_redpanda_consumer.py
"""
import asyncio
import json
from aiokafka import AIOKafkaConsumer
from aiokafka.structs import TopicPartition

BOOTSTRAP = "localhost:19092"
TOPIC = "sensor-events"
GROUP_ID = "sensor-consumers"


async def main():
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=BOOTSTRAP,
        group_id=GROUP_ID,
        auto_offset_reset="latest",  # 起動後の新着のみ
        value_deserializer=lambda v: json.loads(v.decode()),
        key_deserializer=lambda k: k.decode() if k else None,
    )
    await consumer.start()

    # 担当パーティションを表示
    assigned: set[TopicPartition] = consumer.assignment()
    parts = sorted(tp.partition for tp in assigned) if assigned else []
    print(f"[consumer] Redpanda 接続: {BOOTSTRAP}")
    print(f"[consumer] グループ: {GROUP_ID}")
    print(f"[consumer] 担当パーティション: {parts}")
    print("[consumer] 待機中... (Ctrl-C で終了)\n")

    count = 0
    try:
        async for msg in consumer:
            count += 1
            v = msg.value
            print(
                f"[consumer] #{count:<4} "
                f"partition={msg.partition}  offset={msg.offset:<6} "
                f"key={msg.key:<12} "
                f"sensor={v.get('sensor_id','?'):<12} "
                f"value={v.get('value', '?')}"
            )
    except KeyboardInterrupt:
        print(f"\n[consumer] 終了: {count} 件受信")
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(main())
