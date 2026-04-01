import asyncio
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from aiogram import Bot, Dispatcher, F
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
from aiogram.client.default import DefaultBotProperties


# =========================
# НАСТРОЙКИ — ЗАПОЛНИТЕ ПЕРЕД ЗАПУСКОМ
# =========================
BOT_TOKEN = "8428046405:AAFISFm6Mm3ZStV93DsyxhZzc9HwMN6n63c"
ADMIN_IDS = [922603146]  # Вставьте сюда свой Telegram ID, можно несколько
RESET_PASSWORD = "12345678"  # Пароль для полного сброса базы

CONSULTATION_TEXT = (
    "А Вы готовы к знакомству с Сочи по-настоящему? Тогда ждём Вас на консультацию: +79660316371  Диана.\n"
    "Мы поможем подобрать удобное время."
)

MENU_IMAGE_PATH = "assets/menu.jpg"
DB_PATH = "database.db"
EXPORTS_DIR = "exports"


# =========================
# ТЕКСТЫ
# =========================
START_GREETING = (
    "Добрый вечер, уважаемый пассажир эксклюзивного экспресса «Бархатный путь»! "
    "Совсем скоро начнется наше путешествие, а пока - давайте знакомиться"
)

NAME_FOLLOWUP_TEMPLATE = (
    "«{name}», ох, сколько Вас сегодня ждет впереди! "
    "Вечер наполнен изысканными угощениями, подарками, сюрпризами, танцами, музыкой "
    "и даже… мистикой! А для того, чтобы подарок нашел своего адресата, важно получить контакт."
)

CONSENT_TEXT = (
    "Пожалуйста, подтвердите согласие на обработку персональных данных, "
    "чтобы мы могли завершить регистрацию."
)

ASK_NAME_TEXT = "Пожалуйста, введите ваше имя."
ASK_PHONE_TEXT = "Нажмите кнопку ниже и отправьте номер телефона."
REG_SUCCESS_TEMPLATE = (
    "Регистрация успешно завершена.\n"
    "Ваш уникальный номер участника: <b>№{number}</b>.\n"
    "Добро пожаловать на вечер!"
)
ALREADY_REGISTERED_TEMPLATE = (
    "Вы уже зарегистрированы.\n"
    "Ваш уникальный номер участника: <b>№{number}</b>.\n"
    "Ниже доступно меню участника."
)
DECLINED_TEXT = (
    "Без согласия на обработку персональных данных завершить регистрацию нельзя.\n"
    "Если передумаете, нажмите /start и начните заново."
)
PHONE_ALREADY_USED_TEXT = (
    "Этот номер телефона уже зарегистрирован в системе. "
    "Один участник не может получить два номера. Если это ошибка, обратитесь к администратору."
)
CONTACT_REQUIRED_TEXT = "Пожалуйста, используйте кнопку отправки контакта."
MENU_CAPTION = "Меню на сегодняшний вечер."
NO_MENU_IMAGE_TEXT = "Файл меню не найден. Загрузите картинку в assets/menu.jpg."
ADMIN_ONLY_TEXT = "Эта команда доступна только администратору."
ADMIN_MENU_TEXT = "Панель администратора. Выберите действие."
RESET_PROMPT_TEXT = "Введите пароль для полного ресета базы."
RESET_SUCCESS_TEXT = "База данных очищена."
RESET_FAILED_TEXT = "Неверный пароль. Ресет отменен."
EXPORT_EMPTY_TEXT = "За выбранный период зарегистрированных участников нет."
UNKNOWN_TEXT = "Пожалуйста, используйте кнопки меню."


# =========================
# СОСТОЯНИЯ
# =========================
class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_consent = State()
    waiting_for_phone = State()


class AdminStates(StatesGroup):
    waiting_for_reset_password = State()


# =========================
# БАЗА ДАННЫХ
# =========================
class Database:
    def __init__(self, path: str):
        self.path = path
        self._init_db()

    def connect(self):
        return sqlite3.connect(self.path)

    def _init_db(self):
        with self.connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_user_id INTEGER NOT NULL UNIQUE,
                    telegram_username TEXT,
                    full_name TEXT NOT NULL,
                    phone TEXT NOT NULL UNIQUE,
                    participant_number INTEGER NOT NULL UNIQUE,
                    consent_given INTEGER NOT NULL DEFAULT 0,
                    registered_at TEXT NOT NULL
                )
                """
            )
            con.commit()

    def get_by_telegram_id(self, telegram_user_id: int):
        with self.connect() as con:
            cur = con.execute(
                """
                SELECT id, telegram_user_id, telegram_username, full_name, phone,
                       participant_number, consent_given, registered_at
                FROM participants
                WHERE telegram_user_id = ?
                """,
                (telegram_user_id,),
            )
            return cur.fetchone()

    def get_by_phone(self, phone: str):
        with self.connect() as con:
            cur = con.execute(
                """
                SELECT id, telegram_user_id, telegram_username, full_name, phone,
                       participant_number, consent_given, registered_at
                FROM participants
                WHERE phone = ?
                """,
                (phone,),
            )
            return cur.fetchone()

    def next_participant_number(self) -> int:
        with self.connect() as con:
            cur = con.execute("SELECT MAX(participant_number) FROM participants")
            value = cur.fetchone()[0]
            return 1 if value is None else value + 1

    def create_participant(
        self,
        telegram_user_id: int,
        telegram_username: str | None,
        full_name: str,
        phone: str,
        consent_given: bool,
    ) -> int:
        participant_number = self.next_participant_number()
        registered_at = datetime.now().isoformat(timespec="seconds")

        with self.connect() as con:
            con.execute(
                """
                INSERT INTO participants (
                    telegram_user_id,
                    telegram_username,
                    full_name,
                    phone,
                    participant_number,
                    consent_given,
                    registered_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    telegram_user_id,
                    telegram_username,
                    full_name,
                    phone,
                    participant_number,
                    1 if consent_given else 0,
                    registered_at,
                ),
            )
            con.commit()

        return participant_number

    def list_for_period(self, period: str):
        now = datetime.now()

        if period == "today":
            start_dt = datetime(now.year, now.month, now.day)
        elif period == "week":
            start_dt = now - timedelta(days=7)
        elif period == "month":
            start_dt = now - timedelta(days=30)
        else:
            raise ValueError("Unsupported period")

        with self.connect() as con:
            cur = con.execute(
                """
                SELECT id, telegram_user_id, telegram_username, full_name, phone,
                       participant_number, consent_given, registered_at
                FROM participants
                ORDER BY participant_number ASC
                """
            )
            rows = cur.fetchall()

        result = []
        for row in rows:
            registered_at = datetime.fromisoformat(row[7])
            if registered_at >= start_dt:
                result.append(row)
        return result

    def reset(self):
        with self.connect() as con:
            con.execute("DELETE FROM participants")
            con.execute("DELETE FROM sqlite_sequence WHERE name='participants'")
            con.commit()


db = Database(DB_PATH)
os.makedirs(EXPORTS_DIR, exist_ok=True)


# =========================
# КНОПКИ
# =========================
def start_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text="Старт")]]
    if is_admin:
        rows.append([KeyboardButton(text="Админ меню")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def consent_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Согласен(а)")],
            [KeyboardButton(text="Не согласен(а)")],
        ],
        resize_keyboard=True,
    )


def phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отправить номер телефона", request_contact=True)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def participant_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Моя информация")],
            [KeyboardButton(text="Меню вечера")],
            [KeyboardButton(text="Запись на личную консультацию")],
            [KeyboardButton(text="Назад")],
        ],
        resize_keyboard=True,
    )


def admin_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Выгрузка: сегодня")],
            [KeyboardButton(text="Выгрузка: за неделю")],
            [KeyboardButton(text="Выгрузка: за месяц")],
            [KeyboardButton(text="Ресет базы")],
            [KeyboardButton(text="Назад")],
        ],
        resize_keyboard=True,
    )


# =========================
# ВСПОМОГАТЕЛЬНОЕ
# =========================
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def normalize_phone(raw: str) -> str:
    return raw.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")


def export_to_excel(rows, period_name: str) -> str:
    file_path = os.path.join(
        EXPORTS_DIR,
        f"participants_{period_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
    )

    data = []
    for row in rows:
        data.append(
            {
                "ID": row[0],
                "Telegram user ID": row[1],
                "Username": row[2] or "",
                "Имя": row[3],
                "Телефон": row[4],
                "Номер участника": row[5],
                "Согласие": "Да" if row[6] else "Нет",
                "Дата регистрации": row[7],
            }
        )

    df = pd.DataFrame(data)
    df.to_excel(file_path, index=False)
    return file_path


def participant_info_text(row) -> str:
    return (
        "<b>Ваши данные</b>\n"
        f"Имя: {row[3]}\n"
        f"Телефон: {row[4]}\n"
        f"Номер участника: №{row[5]}\n"
        f"Дата регистрации: {row[7]}"
    )


# =========================
# ИНИЦИАЛИЗАЦИЯ БОТА
# =========================
if "PASTE_YOUR_BOT_TOKEN_HERE" in BOT_TOKEN:
    raise RuntimeError(
        "Откройте файл bot.py и вставьте реальный BOT_TOKEN в переменную BOT_TOKEN."
    )

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher(storage=MemoryStorage())


# =========================
# ОБРАБОТЧИКИ
# =========================
@dp.message(CommandStart())
async def command_start(message: Message, state: FSMContext):
    await state.clear()

    existing = db.get_by_telegram_id(message.from_user.id)
    if existing:
        await message.answer(
            ALREADY_REGISTERED_TEMPLATE.format(number=existing[5]),
            reply_markup=participant_menu_keyboard(),
        )
        return

    await message.answer(
        "Нажмите кнопку ниже, чтобы начать регистрацию.",
        reply_markup=start_keyboard(is_admin(message.from_user.id)),
    )


@dp.message(Command("admin"))
async def admin_command(message: Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        await message.answer(ADMIN_ONLY_TEXT)
        return
    await message.answer(ADMIN_MENU_TEXT, reply_markup=admin_menu_keyboard())


@dp.message(F.text == "Старт")
async def start_registration(message: Message, state: FSMContext):
    existing = db.get_by_telegram_id(message.from_user.id)
    if existing:
        await message.answer(
            ALREADY_REGISTERED_TEMPLATE.format(number=existing[5]),
            reply_markup=participant_menu_keyboard(),
        )
        return

    await message.answer(START_GREETING, reply_markup=ReplyKeyboardRemove())
    await message.answer(ASK_NAME_TEXT)
    await state.set_state(RegistrationStates.waiting_for_name)


@dp.message(RegistrationStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if not name:
        await message.answer(ASK_NAME_TEXT)
        return

    await state.update_data(full_name=name)
    await message.answer(NAME_FOLLOWUP_TEMPLATE.format(name=name))
    await message.answer(CONSENT_TEXT, reply_markup=consent_keyboard())
    await state.set_state(RegistrationStates.waiting_for_consent)


@dp.message(RegistrationStates.waiting_for_consent, F.text == "Согласен(а)")
async def consent_accepted(message: Message, state: FSMContext):
    await state.update_data(consent_given=True)
    await message.answer(ASK_PHONE_TEXT, reply_markup=phone_keyboard())
    await state.set_state(RegistrationStates.waiting_for_phone)


@dp.message(RegistrationStates.waiting_for_consent, F.text == "Не согласен(а)")
async def consent_declined(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        DECLINED_TEXT,
        reply_markup=start_keyboard(is_admin(message.from_user.id)),
    )


@dp.message(RegistrationStates.waiting_for_consent)
async def consent_fallback(message: Message):
    await message.answer("Пожалуйста, выберите один из вариантов согласия.")


@dp.message(RegistrationStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    if not message.contact:
        await message.answer(CONTACT_REQUIRED_TEXT, reply_markup=phone_keyboard())
        return

    if message.contact.user_id and message.contact.user_id != message.from_user.id:
        await message.answer("Нужно отправить свой номер телефона.", reply_markup=phone_keyboard())
        return

    existing_user = db.get_by_telegram_id(message.from_user.id)
    if existing_user:
        await state.clear()
        await message.answer(
            ALREADY_REGISTERED_TEMPLATE.format(number=existing_user[5]),
            reply_markup=participant_menu_keyboard(),
        )
        return

    phone = normalize_phone(message.contact.phone_number)
    existing_phone = db.get_by_phone(phone)
    if existing_phone:
        await message.answer(PHONE_ALREADY_USED_TEXT, reply_markup=participant_menu_keyboard())
        await state.clear()
        return

    data = await state.get_data()
    participant_number = db.create_participant(
        telegram_user_id=message.from_user.id,
        telegram_username=message.from_user.username,
        full_name=data["full_name"],
        phone=phone,
        consent_given=True,
    )

    await state.clear()
    await message.answer(
        REG_SUCCESS_TEMPLATE.format(number=participant_number),
        reply_markup=participant_menu_keyboard(),
    )


@dp.message(F.text == "Моя информация")
async def my_info(message: Message):
    row = db.get_by_telegram_id(message.from_user.id)
    if not row:
        await message.answer(
            "Вы еще не зарегистрированы.",
            reply_markup=start_keyboard(is_admin(message.from_user.id)),
        )
        return

    await message.answer(participant_info_text(row), reply_markup=participant_menu_keyboard())


@dp.message(F.text == "Меню вечера")
async def evening_menu(message: Message):
    if not Path(MENU_IMAGE_PATH).exists():
        await message.answer(NO_MENU_IMAGE_TEXT, reply_markup=participant_menu_keyboard())
        return

    await message.answer_photo(
        photo=FSInputFile(MENU_IMAGE_PATH),
        caption=MENU_CAPTION,
        reply_markup=participant_menu_keyboard(),
    )


@dp.message(F.text == "Запись на личную консультацию")
async def consultation(message: Message):
    await message.answer(CONSULTATION_TEXT, reply_markup=participant_menu_keyboard())


@dp.message(F.text == "Назад")
async def back_button(message: Message, state: FSMContext):
    await state.clear()

    existing = db.get_by_telegram_id(message.from_user.id)
    if existing:
        await message.answer("Возвращаю вас в меню участника.", reply_markup=participant_menu_keyboard())
        return

    if is_admin(message.from_user.id):
        await message.answer("Возвращаю вас в стартовое меню.", reply_markup=start_keyboard(True))
        return

    await message.answer("Возвращаю вас в стартовое меню.", reply_markup=start_keyboard(False))


@dp.message(F.text == "Админ меню")
async def open_admin_menu(message: Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        await message.answer(ADMIN_ONLY_TEXT)
        return
    await message.answer(ADMIN_MENU_TEXT, reply_markup=admin_menu_keyboard())


@dp.message(F.text == "Выгрузка: сегодня")
async def export_today(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer(ADMIN_ONLY_TEXT)
        return

    rows = db.list_for_period("today")
    if not rows:
        await message.answer(EXPORT_EMPTY_TEXT)
        return

    file_path = export_to_excel(rows, "today")
    await message.answer_document(FSInputFile(file_path), caption="Выгрузка за сегодня.")


@dp.message(F.text == "Выгрузка: за неделю")
async def export_week(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer(ADMIN_ONLY_TEXT)
        return

    rows = db.list_for_period("week")
    if not rows:
        await message.answer(EXPORT_EMPTY_TEXT)
        return

    file_path = export_to_excel(rows, "week")
    await message.answer_document(FSInputFile(file_path), caption="Выгрузка за неделю.")


@dp.message(F.text == "Выгрузка: за месяц")
async def export_month(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer(ADMIN_ONLY_TEXT)
        return

    rows = db.list_for_period("month")
    if not rows:
        await message.answer(EXPORT_EMPTY_TEXT)
        return

    file_path = export_to_excel(rows, "month")
    await message.answer_document(FSInputFile(file_path), caption="Выгрузка за месяц.")


@dp.message(F.text == "Ресет базы")
async def ask_reset_password(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer(ADMIN_ONLY_TEXT)
        return

    await message.answer(RESET_PROMPT_TEXT)
    await state.set_state(AdminStates.waiting_for_reset_password)


@dp.message(AdminStates.waiting_for_reset_password)
async def process_reset_password(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        await message.answer(ADMIN_ONLY_TEXT)
        return

    if (message.text or "").strip() == RESET_PASSWORD:
        db.reset()
        await message.answer(RESET_SUCCESS_TEXT, reply_markup=admin_menu_keyboard())
    else:
        await message.answer(RESET_FAILED_TEXT, reply_markup=admin_menu_keyboard())

    await state.clear()


@dp.message()
async def fallback(message: Message):
    existing = db.get_by_telegram_id(message.from_user.id)
    if existing:
        await message.answer(UNKNOWN_TEXT, reply_markup=participant_menu_keyboard())
    else:
        await message.answer(
            UNKNOWN_TEXT,
            reply_markup=start_keyboard(is_admin(message.from_user.id)),
        )


async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
