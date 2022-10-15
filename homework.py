import logging
import os
import time
import requests

from dotenv import load_dotenv
from telegram import Bot
from telegram import error as telegram_error

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

STATUS_ERROR = {
    "send_error": "Ошибка при отправке сообщения: ",
    "API": "Ошибка при получении ответа API: ",
    "API_not_correct": "Некорректный ответ API",
    "KeyError": "Некорректный ключ в ответе API",
    "status": "Неопознанный статус домашней работы",
}

last_homework_status = {}


def send_message(bot, message) -> None:
    """Отправка сообщения в Telegram."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID, text=message, mode="MarkdownV2"
        )
    except telegram_error.NetworkError as e:
        logging.error(f"{STATUS_ERROR['send_error']}{e}")
    else:
        logging.info(f"Сообщение отправлено: {message}")


def get_api_answer(current_timestamp) -> dict:
    """Получение ответа API."""
    timestamp = current_timestamp or int(time.time())
    params = {"from_date": timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        error = (
            f'{STATUS_ERROR["API"]}{response.status_code} {response.reason}'
        )
        logging.error(error)
        raise requests.exceptions.HTTPError(error)
    return response.json()


def check_response(response) -> list:
    """Проверка ответа API на наличие новых домашних работ."""
    error = STATUS_ERROR["API_not_correct"]
    if not isinstance(response, dict):
        logging.error(error)
        raise TypeError(error)
    homework = response.get("homeworks")
    if homework is None or not isinstance(homework, list):
        logging.error(error)
        raise TypeError(error)

    return homework


def parse_status(homework) -> str:
    """Получение статуса домашней работы."""
    homework_name = homework.get("homework_name")
    homework_status = homework.get("status")
    if not all([homework_name, homework_status]):
        error_key = STATUS_ERROR["KeyError"]
        logging.error(error_key)
        raise KeyError(error_key)
    if homework_status not in HOMEWORK_STATUSES:
        error_status = STATUS_ERROR["status"]
        logging.error(error_status)
        raise KeyError(error_status)

    if homework_status != last_homework_status.get(homework_name):
        verdict = HOMEWORK_STATUSES[homework_status]
        last_homework_status[homework_name] = homework_status
        return (
            f"Изменился статус проверки работы "
            f'"{homework_name}". {verdict}'
        )
    else:
        logging.debug("Статус не изменился")
    return ""


def check_tokens() -> bool:
    """Проверка наличия токенов."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main_loop(bot, current_timestamp) -> None:
    """Основной цикл программы."""
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            for homework in homeworks:
                message = parse_status(homework)
                if message != "":
                    send_message(bot, message)
                    current_timestamp = response.get("current_date")
        except Exception as e:
            logging.error(f"Ошибка в основном цикле: {e}")
            send_message(bot, f"```Ошибка: {e}```")
        time.sleep(RETRY_TIME)


def main() -> None:
    """Основная логика работы бота."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s, %(levelname)s, %(message)s, %(name)s",
    )

    if not check_tokens():
        logging.critical("Токены не найдены, работа бота невозможна")
        return

    try:
        bot = Bot(token=TELEGRAM_TOKEN)
    except telegram_error.InvalidToken as e:
        logging.critical(f"Некорректный токен, работа прервана: {e}")
        return

    current_timestamp = int(time.time())

    logging.info("main_loop started")
    main_loop(bot, current_timestamp)


if __name__ == "__main__":
    main()
