"""
Агент на компьютере: забирает команды Алисы из очереди Yandex Message Queue и выполняет их.
Входящие подключения не нужны — агент сам ходит в Яндекс, поэтому работает с серым IP и без VPN.

Установка:  pip install -r agent/requirements.txt
Настройка:  скопируйте config.example.json в config.json и впишите свои значения
Запуск:     python agent/agent.py      — с консолью (удобно для проверки)
            pythonw agent/agent.py     — в фоне, без окна (так запускает автозагрузка)
Лог:        agent/agent.log
"""

import ctypes
import json
import logging
import os
import sys
import time
from pathlib import Path

import boto3

HERE = Path(__file__).parent
CONFIG_PATH = HERE / "config.json"
LOG_PATH = HERE / "agent.log"

# Бесплатно — 100 000 запросов в месяц. Один цикл (ожидание 20 с + пауза 10 с) = ~89 000 запросов в месяц.
WAIT_SECONDS = 20                           # long polling: команда во время ожидания приходит мгновенно
MAX_AGE_SECONDS = 60                        # старые команды (например, пока ПК был выключен) пропускаем

handlers = [logging.FileHandler(LOG_PATH, encoding="utf-8")]
if sys.stderr is not None:                  # под pythonw консоли нет
    handlers.append(logging.StreamHandler())
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", handlers=handlers)


def lock_windows():
    ctypes.windll.user32.LockWorkStation()


def disable_pc():
    os.system("shutdown /s /t 1")


ACTIONS = {
    "lock": lock_windows,
    "shutdown": disable_pc,
}


def single_instance():
    """Не даёт запустить второй экземпляр агента."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    mutex = kernel32.CreateMutexW(None, False, "Local\\AlicePcControlAgent")
    if ctypes.get_last_error() == 183:      # ERROR_ALREADY_EXISTS
        logging.info("Агент уже запущен, выхожу")
        sys.exit(0)
    return mutex


def load_config():
    if not CONFIG_PATH.exists():
        logging.error("Нет файла %s — скопируйте config.example.json и впишите свои значения", CONFIG_PATH)
        sys.exit(1)
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def main():
    _mutex = single_instance()
    cfg = load_config()
    pause = cfg.get("pause_seconds", 10)
    sqs = boto3.client(
        "sqs",
        endpoint_url="https://message-queue.api.cloud.yandex.net",
        region_name="ru-central1",
        aws_access_key_id=cfg["access_key_id"],
        aws_secret_access_key=cfg["secret_access_key"],
    )

    def handle(msg):
        # удаляем сразу, чтобы команда не выполнилась повторно (например, после выключения)
        sqs.delete_message(QueueUrl=cfg["queue_url"], ReceiptHandle=msg["ReceiptHandle"])

        age = time.time() - int(msg["Attributes"]["SentTimestamp"]) / 1000
        cmd = json.loads(msg["Body"]).get("cmd")
        if age > MAX_AGE_SECONDS:
            logging.info("Пропускаю устаревшую команду %s (%.0f с назад)", cmd, age)
            return
        action = ACTIONS.get(cmd)
        if action is None:
            logging.warning("Неизвестная команда: %s", cmd)
            return
        logging.info("Выполняю: %s", cmd)
        action()

    logging.info("Агент запущен, жду команды Алисы...")
    while True:
        try:
            resp = sqs.receive_message(
                QueueUrl=cfg["queue_url"],
                WaitTimeSeconds=WAIT_SECONDS,
                MaxNumberOfMessages=10,
                AttributeNames=["SentTimestamp"],
            )
        except Exception as e:
            logging.error("Нет связи с очередью: %r. Повтор через 15 с", e)
            time.sleep(15)
            continue

        messages = resp.get("Messages", [])
        for msg in messages:
            try:
                handle(msg)
            except Exception as e:
                logging.error("Ошибка при выполнении команды: %r", e)
        if not messages:
            time.sleep(pause)


if __name__ == "__main__":
    main()
