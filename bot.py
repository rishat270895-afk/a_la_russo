import asyncio
import logging
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    FSInputFile,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font

# =========================
# CONFIG
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MENU_IMAGE_PATH = os.getenv("MENU_IMAGE_PATH", "menu_today.jpg")
CONSULTATION_PHONE = os.getenv("CONSULTATION_PHONE", "+7 (999) 123-45-67")
CONSULTATION_TEXT = os.getenv(
    "CONSULTATION_TEXT",
    "Для записи на личную консультацию свяжитесь с организатором по телефону:",
)
DB_PATH = Path(os.getenv("DB_PATH", "participants.db"))
EXPORTS_DIR = Path(os.getenv("EXPORTS_DIR", "exports"))
EXPORTS_DIR.mkdir(exist_ok=True)

ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}
ADMIN_RESET_PASSWORD = os.getenv("ADMIN_RESET_PASSWORD", "CHANGE_ME_NOW")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


# =========================
# DATABASE
# =========================
class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_user_id INTEGER NOT NULL UNIQUE,
                    telegram_username TEXT,
                    full_name TEXT NOT NULL,
                    phone TEXT NOT NULL UNIQUE,
                    consent_pd INTEGER NOT NULL,
                    registration_number INTEGER NOT NULL UNIQUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def get_participant_by_telegram_id(self, telegram_user_id: int) -> Optional[dict]:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT * FROM participants WHERE telegram_user_id = ?",
                (telegram_user_id,),
            ).fetchone()
            return dict(row) if row else None

    def get_participant_by_phone(self, phone: str) -> Optional[dict]:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT * FROM participants WHERE phone = ?",
                (phone,),
            ).fetchone()
            return dict(row) if row else None

    def get_next_registration_number(self) -> int:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(registration_number), 0) + 1 AS next_number FROM participants"
            ).fetchone()
            return int(row["next_number"])

    def create_participant(
        self,
        telegram_user_id: int,
        telegram_username: str | None,
        full_name: str,
        phone: str,
        consent_pd: bool,
    ) -> dict:
        existing = self.get_participant_by_telegram_id(telegram_user_id)
        if existing:
            return existing

        existing_phone = self.get_participant_by_phone(phone)
        if existing_phone:
            raise ValueError("Этот номер телефона уже зарегистрирован в системе.")

        registration_number = self.get_next_registration_number()

        with closing(self._connect()) as conn, conn:
            conn.execute(
                """
                INSERT INTO participants (
                    telegram_user_id,
                    telegram_username,
                    full_name,
                    phone,
                    consent_pd,
                    registration_number
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    telegram_user_id,
                    telegram_username,
                    full_name,
                    phone,
                    int(consent_pd),
                    registration_number,
                ),
            )

        return self.get_participant_by_telegram_id(telegram_user_id)

    def get_participants_by_period(self, period: str) -> list[dict]:
        now = datetime.now()

        if period == "today":
            start = datetime(now.year, now.month, now.day, 0, 0, 0)
        elif period == "week":
            start = now - timedelta(days=7)
        elif period == "month":
            start = now - timedelta(days=30)
        else:
            raise ValueError("Неизвестный период выгрузки.")

        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM participants
                WHERE datetime(created_at) >= datetime(?)
                ORDER BY registration_number ASC
                """,
                (start.strftime("%Y-%m-%d %H:%M:%S"),),
            ).fetchall()
            return [dict(row) for row in rows]

    def count_participants(self) -> int:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT COUNT(*) AS total FROM participants").fetchone()
            return int(row["total"])

    def reset_database(self):
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM participants")
            try:
                conn.execute("DELETE FROM sqlite_sequence WHERE name = 'participants'")
            except sqlite3.OperationalError:
                pass


# =========================
# STATES
# =========================
class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_consent = State()
    waiting_for_phone = State()


class AdminStates(StatesGroup):
    waiting_for_reset_password = State()


# =========================
# HELPERS
# =========================
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def normalize_phone(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())

    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]

    if len(digits) == 10:
        digits = "7" + digits

    return "+" + digits if digits else phone.strip()


def participant_info_text(participant: dict) -> str:
    created_at = participant.get("created_at", "")
    return (
        "<b>Ваша информация</b>\n\n"
        f"<b>Имя:</b> {participant['full_name']}\n"
        f"<b>Телефон:</b> {participant['phone']}\n"
        f"<b>Уникальный номер:</b> {participant['registration_number']}\n"
        f"<b>Дата регистрации:</b> {created_at}"
    )


def create_excel_export(participants: list[dict], period_label: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = EXPORTS_DIR / f"participants_{period_label}_{timestamp}.xlsx"

    wb = Workbook()
    ws = wb.active
    ws.title = "Участники"

    headers = [
        "Порядковый номер",
        "Имя",
        "Телефон",
        "Telegram ID",
        "Username",
        "Согласие на ПД",
        "Дата регистрации",
    ]
    ws.append(headers)

    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for participant in participants:
        ws.append(
            [
                participant["registration_number"],
                participant["full_name"],
                participant["phone"],
                participant["telegram_user_id"],
                participant.get("telegram_username") or "",
                "Да" if participant.get("consent_pd") else "Нет",
                participant.get("created_at") or "",
            ]
        )

    widths = {"A": 20, "B": 28, "C": 20, "D": 18, "E": 20, "F": 16, "G": 24}
    for col, width in widths.items():
        ws.column_dimensions[col].width = width

    wb.save(file_path)
    return file_path


# =========================
# KEYBOARDS
# =========================
def start_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Старт")]],
        resize_keyboard=True,
    )


def consent_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Согласен(а)"), KeyboardButton(text="Не согласен(а)")],
            [KeyboardButton(text="Назад")],
        ],
        resize_keyboard=True,
    )


def phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отправить номер телефона", request_contact=True)],
            [KeyboardButton(text="Назад")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def participant_menu_keyboard(is_user_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="Моя информация")],
        [KeyboardButton(text="Меню")],
        [KeyboardButton(text="Запись на личную консультацию")],
    ]
    if is_user_admin:
        rows.append([KeyboardButton(text="Админ меню")])
    rows.append([KeyboardButton(text="Назад")])

    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def admin_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Выгрузка за сегодня")],
            [KeyboardButton(text="Выгрузка за неделю")],
            [KeyboardButton(text="Выгрузка за месяц")],
            [KeyboardButton(text="Сброс базы")],
            [KeyboardButton(text="Меню участника")],
            [KeyboardButton(text="Назад")],
        ],
        resize_keyboard=True,
    )


# =========================
# BOT
# =========================
db = Database(DB_PATH)
dp = Dispatcher(storage=MemoryStorage())


@dp.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext):
    await state.clear()

    if is_admin(message.from_user.id):
        await message.answer(
            "Вы вошли как администратор. Доступны оба режима: участник и администратор.",
            reply_markup=admin_menu_keyboard(),
        )
        await message.answer(
            "Чтобы перейти в обычное пользовательское меню, нажмите кнопку <b>Меню участника</b>."
        )
        return

    await message.answer(
        "Нажмите кнопку <b>Старт</b>, чтобы начать регистрацию.",
        reply_markup=start_keyboard(),
    )


@dp.message(Command("admin"))
@dp.message(F.text == "Админ меню")
async def open_admin_menu(message: Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет доступа к админ-меню.")
        return

    total = db.count_participants()
    await message.answer(
        f"<b>Админ-меню</b>\n\nВсего зарегистрировано: <b>{total}</b>",
        reply_markup=admin_menu_keyboard(),
    )


@dp.message(F.text == "Меню участника")
async def open_participant_menu_as_admin(message: Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        await message.answer("Эта кнопка доступна только администратору.")
        return

    participant = db.get_participant_by_telegram_id(message.from_user.id)
    if participant:
        await message.answer(
            "Открываю меню участника.",
            reply_markup=participant_menu_keyboard(is_user_admin=True),
        )
        await message.answer(participant_info_text(participant))
        return

    await message.answer(
        "Вы еще не зарегистрированы как участник. Нажмите <b>Старт</b>, чтобы пройти регистрацию.",
        reply_markup=start_keyboard(),
    )


@dp.message(F.text == "Старт")
async def start_registration(message: Message, state: FSMContext):
    participant = db.get_participant_by_telegram_id(message.from_user.id)
    if participant:
        await message.answer(
            "Вы уже зарегистрированы. Открываю меню участника.",
            reply_markup=participant_menu_keyboard(is_user_admin=is_admin(message.from_user.id)),
        )
        await message.answer(participant_info_text(participant))
        return

    await state.set_state(RegistrationStates.waiting_for_name)
    await message.answer(
        "Добрый вечер, уважаемый пассажир эксклюзивного экспресса «Бархатный путь»! "
        "Совсем скоро начнется наше путешествие, а пока - давайте знакомиться"
    )
    await message.answer("Пожалуйста, введите ваше имя:", reply_markup=ReplyKeyboardRemove())


@dp.message(RegistrationStates.waiting_for_name, F.text)
async def process_name(message: Message, state: FSMContext):
    guest_name = (message.text or "").strip()
    if not guest_name:
        await message.answer("Имя не должно быть пустым. Введите имя еще раз.")
        return

    await state.update_data(full_name=guest_name)
    await state.set_state(RegistrationStates.waiting_for_consent)

    await message.answer(
        f"{guest_name}, ох, сколько Вас сегодня ждет впереди! "
        "Вечер наполнен изысканными угощениями, подарками, сюрпризами, танцами, музыкой и даже… мистикой! "
        "А для того, чтобы подарок нашел своего адресата, важно получить контакт."
    )
    await message.answer(
        "Пожалуйста, подтвердите согласие на обработку персональных данных.",
        reply_markup=consent_keyboard(),
    )


@dp.message(RegistrationStates.waiting_for_consent, F.text == "Назад")
async def back_to_name_from_consent(message: Message, state: FSMContext):
    await state.set_state(RegistrationStates.waiting_for_name)
    await message.answer("Введите ваше имя еще раз:", reply_markup=ReplyKeyboardRemove())


@dp.message(RegistrationStates.waiting_for_consent, F.text == "Согласен(а)")
async def process_consent_yes(message: Message, state: FSMContext):
    await state.update_data(consent_pd=True)
    await state.set_state(RegistrationStates.waiting_for_phone)
    await message.answer(
        "Спасибо! Теперь отправьте ваш номер телефона кнопкой ниже.",
        reply_markup=phone_keyboard(),
    )


@dp.message(RegistrationStates.waiting_for_consent, F.text == "Не согласен(а)")
async def process_consent_no(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Без согласия на обработку персональных данных завершить регистрацию невозможно.",
        reply_markup=start_keyboard(),
    )


@dp.message(RegistrationStates.waiting_for_phone, F.text == "Назад")
async def back_to_consent_from_phone(message: Message, state: FSMContext):
    await state.set_state(RegistrationStates.waiting_for_consent)
    await message.answer(
        "Вернулись на шаг назад. Подтвердите согласие на обработку персональных данных.",
        reply_markup=consent_keyboard(),
    )


@dp.message(RegistrationStates.waiting_for_phone, F.contact)
async def process_phone_contact(message: Message, state: FSMContext):
    if not message.contact or not message.contact.phone_number:
        await message.answer("Не удалось получить номер телефона. Попробуйте снова.")
        return

    phone = normalize_phone(message.contact.phone_number)
    data = await state.get_data()
    full_name = data.get("full_name")
    consent_pd = data.get("consent_pd", False)

    try:
        participant = db.create_participant(
            telegram_user_id=message.from_user.id,
            telegram_username=message.from_user.username,
            full_name=full_name,
            phone=phone,
            consent_pd=consent_pd,
        )
    except ValueError as error:
        await message.answer(str(error))
        return

    await state.clear()
    await message.answer(
        "✅ Регистрация успешно завершена!\n"
        f"Ваш уникальный номер участника: <b>{participant['registration_number']}</b>",
        reply_markup=participant_menu_keyboard(is_user_admin=is_admin(message.from_user.id)),
    )
    await message.answer("Добро пожаловать в меню участника!")


@dp.message(RegistrationStates.waiting_for_phone)
async def process_phone_invalid(message: Message):
    await message.answer(
        "Пожалуйста, используйте кнопку «Отправить номер телефона» ниже.",
        reply_markup=phone_keyboard(),
    )


@dp.message(F.text == "Моя информация")
async def show_my_info(message: Message):
    participant = db.get_participant_by_telegram_id(message.from_user.id)
    if not participant:
        await message.answer("Сначала пройдите регистрацию.", reply_markup=start_keyboard())
        return

    await message.answer(participant_info_text(participant))


@dp.message(F.text == "Меню")
async def show_evening_menu(message: Message):
    participant = db.get_participant_by_telegram_id(message.from_user.id)
    if not participant:
        await message.answer("Сначала пройдите регистрацию.", reply_markup=start_keyboard())
        return

    if Path(MENU_IMAGE_PATH).exists():
        await message.answer_photo(
            photo=FSInputFile(MENU_IMAGE_PATH),
            caption="Меню на сегодняшний вечер",
        )
    else:
        await message.answer(
            f"Файл с меню не найден. Поместите изображение в файл {MENU_IMAGE_PATH}"
        )


@dp.message(F.text == "Запись на личную консультацию")
async def consultation_info(message: Message):
    participant = db.get_participant_by_telegram_id(message.from_user.id)
    if not participant:
        await message.answer("Сначала пройдите регистрацию.", reply_markup=start_keyboard())
        return

    await message.answer(f"{CONSULTATION_TEXT}\n<b>{CONSULTATION_PHONE}</b>")


async def send_export(message: Message, period_key: str, period_label_ru: str):
    participants = db.get_participants_by_period(period_key)
    file_path = create_excel_export(participants, period_key)

    caption = (
        f"Выгрузка участников за период: <b>{period_label_ru}</b>\n"
        f"Количество записей: <b>{len(participants)}</b>"
    )

    await message.answer_document(FSInputFile(file_path), caption=caption)


@dp.message(F.text == "Выгрузка за сегодня")
async def export_today(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет доступа к этой функции.")
        return
    await send_export(message, "today", "сегодня")


@dp.message(F.text == "Выгрузка за неделю")
async def export_week(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет доступа к этой функции.")
        return
    await send_export(message, "week", "7 дней")


@dp.message(F.text == "Выгрузка за месяц")
async def export_month(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет доступа к этой функции.")
        return
    await send_export(message, "month", "30 дней")


@dp.message(F.text == "Сброс базы")
async def reset_database_request(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет доступа к этой функции.")
        return

    await state.set_state(AdminStates.waiting_for_reset_password)
    await message.answer(
        "Введите пароль для полного сброса базы участников.\n"
        "Внимание: действие необратимо.\n\n"
        "Для отмены нажмите «Назад».",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Назад")]],
            resize_keyboard=True,
        ),
    )


@dp.message(AdminStates.waiting_for_reset_password, F.text == "Назад")
async def cancel_reset_database(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Сброс базы отменен.", reply_markup=admin_menu_keyboard())


@dp.message(AdminStates.waiting_for_reset_password, F.text)
async def process_reset_password(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        await message.answer("У вас нет доступа к этой функции.")
        return

    if message.text.strip() != ADMIN_RESET_PASSWORD:
        await message.answer("Неверный пароль. Попробуйте еще раз или нажмите «Назад».")
        return

    db.reset_database()
    await state.clear()
    await message.answer(
        "✅ База участников успешно очищена. Нумерация новых регистраций начнется заново.",
        reply_markup=admin_menu_keyboard(),
    )


@dp.message(F.text == "Назад")
async def back_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()

    if current_state == RegistrationStates.waiting_for_phone.state:
        await back_to_consent_from_phone(message, state)
        return

    if current_state == RegistrationStates.waiting_for_consent.state:
        await back_to_name_from_consent(message, state)
        return

    if current_state == AdminStates.waiting_for_reset_password.state:
        await cancel_reset_database(message, state)
        return

    await state.clear()

    if is_admin(message.from_user.id):
        await message.answer(
            "Вы находитесь в админ-режиме. При необходимости откройте меню участника отдельной кнопкой.",
            reply_markup=admin_menu_keyboard(),
        )
        return

    participant = db.get_participant_by_telegram_id(message.from_user.id)
    if participant:
        await message.answer(
            "Вы находитесь в главном меню участника.",
            reply_markup=participant_menu_keyboard(is_user_admin=False),
        )
    else:
        await message.answer("Возвращаю вас в начало.", reply_markup=start_keyboard())


@dp.message()
async def fallback_handler(message: Message):
    if is_admin(message.from_user.id):
        await message.answer(
            "Не понял команду. Используйте кнопки админ-меню или /admin.",
            reply_markup=admin_menu_keyboard(),
        )
        return

    participant = db.get_participant_by_telegram_id(message.from_user.id)
    if participant:
        await message.answer(
            "Пожалуйста, используйте кнопки меню.",
            reply_markup=participant_menu_keyboard(is_user_admin=False),
        )
    else:
        await message.answer(
            "Нажмите кнопку «Старт», чтобы начать регистрацию.",
            reply_markup=start_keyboard(),
        )


async def main():
    if not BOT_TOKEN:
        raise ValueError("Укажите BOT_TOKEN в переменных окружения.")

    if not ADMIN_IDS:
        logging.warning("ADMIN_IDS пуст. Админ-меню будет недоступно.")

    if ADMIN_RESET_PASSWORD == "CHANGE_ME_NOW":
        logging.warning("Установите безопасный ADMIN_RESET_PASSWORD.")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
