"""
Бэкенд навыка в Yandex Cloud Functions.
Принимает фразу от Алисы и кладёт команду в очередь Message Queue,
откуда её забирает agent.py на компьютере.

Переменные окружения функции:
    QUEUE_URL              — URL очереди Message Queue
    AWS_ACCESS_KEY_ID      — идентификатор статического ключа сервисного аккаунта
    AWS_SECRET_ACCESS_KEY  — секретный ключ
    SKILL_ID               — ID навыка; запросы от других навыков игнорируются
"""

import json
import os

import boto3

sqs = boto3.client(
    "sqs",
    endpoint_url="https://message-queue.api.cloud.yandex.net",
    region_name="ru-central1",
)

COMMANDS = [
    # (ключевые слова, команда для агента, ответ Алисы)
    (["заблокируй", "заблокировать", "блокируй", "экран"], "lock", "Блокирую экран"),
    (["выключи", "выключить", "выруби"], "shutdown", "Выключаю компьютер"),
]


def reply(event, text, end_session=False):
    return {
        "version": event.get("version", "1.0"),
        "session": event.get("session", {}),
        "response": {"text": text, "end_session": end_session},
    }


def handler(event, context):
    session = event.get("session", {})
    skill_id = os.environ.get("SKILL_ID")
    if skill_id and session.get("skill_id") != skill_id:
        return reply(event, "Доступ запрещён", end_session=True)

    words = event.get("request", {}).get("nlu", {}).get("tokens", [])

    for keywords, cmd, text in COMMANDS:
        if any(w in words for w in keywords):
            try:
                sqs.send_message(QueueUrl=os.environ["QUEUE_URL"], MessageBody=json.dumps({"cmd": cmd}))
            except Exception as e:
                print(f"send_message failed: {e!r}")
                return reply(event, "Не получилось отправить команду компьютеру")
            return reply(event, text, end_session=True)

    if session.get("new"):
        return reply(event, "Теперь вы можете управлять компьютером! Скажите «заблокируй экран» или «выключи компьютер».")
    return reply(event, "Неизвестная команда. Скажите «заблокируй экран» или «выключи компьютер».")
