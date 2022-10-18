import logging
import os
import time

import requests
from dotenv import load_dotenv
from telegram import Bot
from telegram import error as telegram_error

from exceptions import BotException, BotKeyError, BotTypeError

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
    "JSON_error": "Ошибка при преобразовании ответа API в JSON",
}

last_homework_status = {}

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter("%(asctime)s, %(levelname)s, %(message)s, %(name)s")
)
logger.addHandler(handler)


def send_message(bot, message) -> bool:
    """Отправка сообщения в Telegram."""
    try:
        logger.info("Попытка отправки сообщения")
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
    except Exception as e:
        logger.error(f"{STATUS_ERROR['send_error']}: {e}")
        return False
    else:
        logger.info(f"Сообщение отправлено: {message}")
        return True


def get_api_answer(current_timestamp) -> dict:
    """Получение ответа API."""
    timestamp = current_timestamp or int(time.time())
    params = {"from_date": timestamp}
    logger.debug("Попытка получения ответа API")
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        raise BotException(
            f'{STATUS_ERROR["API"]} Ожидался ответ со статусом 200,\n'
            f"получено: {response.status_code} {response.reason}"
        )
    logger.debug("Ответ API получен")
    try:
        logger.debug("Попытка преобразования ответа API в JSON")
        response = response.json()
    except Exception:
        raise BotException(f"{STATUS_ERROR['JSON_error']}: {response.text}")
    logger.debug("Ответ API преобразован в JSON")
    return response


def check_response(response) -> list:
    """Проверка ответа API на наличие новых домашних работ."""
    error = STATUS_ERROR["API_not_correct"]
    if not isinstance(response, dict):
        raise BotTypeError(error)
    homework = response.get("homeworks")
    if homework is None or not isinstance(homework, list):
        raise BotKeyError(error)
    return homework


def parse_status(homework) -> str:
    """Получение статуса домашней работы."""
    homework_name = homework.get("homework_name")
    homework_status = homework.get("status")
    if not all((homework_name, homework_status)):
        raise BotKeyError(STATUS_ERROR["KeyError"])
    if homework_status not in HOMEWORK_STATUSES:
        raise BotException(STATUS_ERROR["status"])
    if homework_status != last_homework_status.get(homework_name):
        verdict = HOMEWORK_STATUSES[homework_status]
        last_homework_status[homework_name] = homework_status
        return (
            f"Изменился статус проверки работы "
            f'"{homework_name}". {verdict}'
        )
    else:
        logger.debug("Статус не изменился")
    return ""


def check_tokens() -> bool:
    """Проверка наличия токенов."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main_loop(bot, current_timestamp) -> None:
    """Основной цикл программы."""
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            for homework in homeworks:
                message = parse_status(homework)
                if message and send_message(bot, message):
                    current_timestamp = response.get("current_date")
        except Exception as e:
            logger.error(f"Ошибка в основном цикле: {e}")
            send_message(bot, f"Ошибка: {e}")
        finally:
            time.sleep(RETRY_TIME)


def main() -> None:
    """Инициализация бота и запуск основного цикла."""
    if not check_tokens():
        logger.critical("Токены не найдены, работа бота невозможна")
        return

    try:
        logger.info("Попытка запуска бота")
        bot = Bot(token=TELEGRAM_TOKEN)
    except telegram_error.InvalidToken as e:
        logger.critical(f"Некорректный токен, работа прервана: {e}")
        return
    else:
        logger.info("Бот запущен")

    current_timestamp = int(time.time())

    logger.info("main_loop started")
    main_loop(bot, current_timestamp)


if __name__ == "__main__":
    main()
