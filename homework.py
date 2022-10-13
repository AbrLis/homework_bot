import time
import os
import logging
import requests

import telegram
from dotenv import load_dotenv

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.DEBUG,
)

load_dotenv()


PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_TIME = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}

HOMEWORK_STATUSES = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}

last_homework_status = None


def send_message(bot, message) -> None:
    """Отправка сообщения в Telegram."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except telegram.error.NetworkError as error:
        logging.error(f"Ошибка при отправке сообщения: {error}")
    else:
        logging.info(f"Сообщение отправлено: {message}")


def get_api_answer(current_timestamp) -> dict:
    """Получение ответа API."""
    timestamp = current_timestamp or int(time.time())
    params = {"from_date": timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as error:
        logging.error(f"Ошибка при запросе к API: {error}")
        return {}


def check_response(response) -> list:
    """Проверка ответа API на наличие новых домашних работ."""
    if response.get("homeworks"):
        return response.get("homeworks")
    else:
        logging.error("Не удалось получить список домашних работ")
    return []


def parse_status(homework) -> str:
    """Получение статуса домашней работы."""
    homework_name = homework.get("homework_name")
    homework_status = homework.get("status")
    if (
        homework_status in HOMEWORK_STATUSES
        and homework_status != last_homework_status
    ):
        verdict = HOMEWORK_STATUSES[homework_status]
        return (
            f'Изменился статус проверки работы '
            f'"{homework_name}". {verdict}'
        )
    else:
        logging.debug("Статус не изменился")
    if not homework_status or not homework_name:
        logging.error("Не удалось получить статус проверки работы")
    return ""


def check_tokens() -> bool:
    """Проверка наличия токенов."""
    if not PRACTICUM_TOKEN or not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logging.critical("Не указаны токены")
        return False
    return True


def main():
    """Основная логика работы бота."""

    # ...
    #
    # bot = telegram.Bot(token=TELEGRAM_TOKEN)
    # current_timestamp = int(time.time())
    #
    # ...
    #
    # while True:
    #     try:
    #         response = ...
    #
    #         ...
    #
    #         current_timestamp = ...
    #         time.sleep(RETRY_TIME)
    #
    #     except Exception as error:
    #         message = f"Сбой в работе программы: {error}"
    #         ...
    #         time.sleep(RETRY_TIME)
    #     else:
    #         ...


if __name__ == "__main__":
    main()
