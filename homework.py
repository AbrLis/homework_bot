import time
import os
import logging
import requests

from telegram import Bot, error
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

last_homework_status = {}


def send_message(bot, message) -> None:
    """Отправка сообщения в Telegram."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except error.NetworkError as e:
        logging.error(f"Ошибка при отправке сообщения: {e}")
    else:
        logging.info(f"Сообщение отправлено: {message}")


def get_api_answer(current_timestamp) -> dict:
    """Получение ответа API."""
    timestamp = current_timestamp or int(time.time())
    params = {"from_date": timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        logging.error(
            f"Ошибка при получении ответа API: {response.status_code}"
        )
        raise requests.exceptions.HTTPError()
    return response.json()


def check_response(response) -> list:
    """Проверка ответа API на наличие новых домашних работ."""
    if not isinstance(response, dict):
        logging.error("Некорректный ответ API")
        raise TypeError()
    homework = response.get("homeworks")
    if not homework or not isinstance(homework, list):
        logging.error("Некорректный ответ API")
        raise TypeError()

    return homework


def parse_status(homework) -> str:
    """Получение статуса домашней работы."""
    homework_name = homework.get("homework_name")
    homework_status = homework.get("status")
    if not all([homework_name, homework_status]):
        logging.error("Некорректный ключ в ответе API")
        raise KeyError("Некорректный ключ в ответе API")
    if homework_status not in HOMEWORK_STATUSES:
        logging.error("Неопознанный статус домашней работы")
        raise ValueError("Неопознанный статус домашней работы")

    if (
        homework_status in HOMEWORK_STATUSES
        and homework_status != last_homework_status.get(homework_name)
    ):
        verdict = HOMEWORK_STATUSES[homework_status]
        last_homework_status[homework_name] = homework_status
        return (
            f"Изменился статус проверки работы "
            f'"{homework_name}". {verdict}'
        )
    else:
        logging.debug("Статус не изменился")
    if not homework_status or not homework_name:
        logging.error("Не удалось получить статус проверки работы")
    return ""


def check_tokens() -> bool:
    """Проверка наличия токенов."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    days = 15
    secund_in_period = days * 24 * 60 * 60

    if not check_tokens():
        logging.critical("Не удалось получить токены, работа бота невозможна")
        return

    try:
        bot = Bot(token=TELEGRAM_TOKEN)
    except error.InvalidToken as e:
        logging.critical(f"Ошибка при создании бота: {e}")
        return

    current_timestamp = int(time.time()) - secund_in_period

    while True:
        try:
            response = get_api_answer(current_timestamp)
        except requests.exceptions.HTTPError:
            response = {}
        if len(response):
            try:
                homeworks = check_response(response)
            except TypeError:
                homeworks = []
            for homework in homeworks:
                try:
                    message = parse_status(homework)
                except (KeyError, ValueError):
                    message = ""
                if message != "":
                    send_message(bot, message)
            current_timestamp = response.get("current_date")
        time.sleep(RETRY_TIME)


if __name__ == "__main__":
    main()
