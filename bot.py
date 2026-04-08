import asyncio
import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

# =========================================================
# НАСТРОЙКИ — ЗАМЕНИТЕ ПОД СЕБЯ
# =========================================================
BOT_TOKEN = "8428046405:AAFISFm6Mm3ZStV93DsyxhZzc9HwMN6n63c"
ADMIN_IDS = {922603146}
RESET_PASSWORD = "12345678"
CONTACT_URL = "https://t.me/nikaestate_sochi"

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database.db"
EXPORTS_DIR = BASE_DIR / "exports"
ASSETS_DIR = BASE_DIR / "assets"

# ФАЙЛЫ: загрузите их в /opt/bot/assets/ с такими именами
TIMING_IMAGE = ASSETS_DIR / "timing.png"
MENU_IMAGE = ASSETS_DIR / "menu.png"
SOCHI_IMAGE = ASSETS_DIR / "sochi_intro.png"
LEGEND_AUDIO = ASSETS_DIR / "legend_audio.mp3"
VELVET_SEASON_IMAGE = ASSETS_DIR / "velvet_season.png"
COMPANY_IMAGE = ASSETS_DIR / "company.png"
SOCHI_VIDEO = ASSETS_DIR / "sochi_video.mp4"
SOCHI_PRESENTATION = ASSETS_DIR / "sochi_presentation.pdf"
MANAGEMENT_IMAGE_1 = ASSETS_DIR / "management_1.png"
MANAGEMENT_IMAGE_2 = ASSETS_DIR / "management_2.png"
CONTACT_IMAGE = ASSETS_DIR / "contact.png"

# =========================================================
# ТЕКСТЫ / КНОПКИ
# =========================================================
START_BUTTON = "Старт"
BACK_BUTTON = "Назад"

CONSENT_ACCEPT_BUTTON = "Согласен(а)"
CONSENT_DECLINE_BUTTON = "Не согласен(а)"
SEND_PHONE_BUTTON = "Отправить номер телефона"

PARTICIPANT_COMPANY = "О КОМПАНИИ"
PARTICIPANT_SOCHI = "СОЧИ"
PARTICIPANT_MANAGEMENT = "РУКОВОДСТВО"
PARTICIPANT_CONTACT = "СВЯЗАТЬСЯ"

ADMIN_MENU_BUTTON = "Админ меню"
EXPORT_TODAY_BUTTON = "Выгрузка: сегодня"
EXPORT_WEEK_BUTTON = "Выгрузка: неделя"
EXPORT_MONTH_BUTTON = "Выгрузка: месяц"
RESET_DB_BUTTON = "Ресет базы"
BROADCAST_BUTTON = "Рассылка"

YES_BUTTON = "ДА"
NO_BUTTON = "НЕТ"
CONFIRM_BROADCAST_BUTTON = "Отправить всем"
CANCEL_BROADCAST_BUTTON = "Отменить рассылку"

START_GREETING = (
    "Добрый вечер, уважаемый пассажир эксклюзивного экспресса «Бархатный путь»! "
    "Совсем скоро начнется наше путешествие, а пока - давайте знакомиться?"
)

ASK_NAME = "Пожалуйста, введите ваше имя."

NAME_TEXT_TEMPLATE = (
    "{name}, ох, сколько Вас сегодня ждет впереди! Вечер наполнен изысканными угощениями, "
    "подарками, сюрпризами, танцами, музыкой и даже… мистикой!"
)

TIMING_CAPTION = "Как видите, остановки предусмотрены, за это не переживайте"
MENU_CAPTION = (
    "Голод - враг искусства! Перейдем к меню на ужин? Вы только посмотрите, какое обилие "
    "угощений Вас ждет впереди!"
)
SOCHI_TEXT = (
    "А Вы бывали в Сочи? Просто представьте: шум моря, запах цветущих магнолий и прибой "
    "Черного моря… А знаете ли вы легенду о бархатном сезоне?"
)
LEGEND_TEXT = (
    "В конце XIX – начале XX века русская аристократия отдыхала в Крыму не летом, а в апреле-мае, "
    "сменяя меховые одежды на бархатные, что изначально дало название сезону. И только сильно позже "
    "сезон сместился на начало осени из-за рекомендаций врачей"
)
TODAY_HISTORY_TEXT = (
    "Сегодня окунемся в истории бархатного сезона, и Вы сможете стать свидетелями событий того времени…"
)
CONSENT_TEXT = (
    "Пожалуйста, подтвердите согласие на обработку персональных данных, чтобы мы могли завершить регистрацию."
)
ASK_PHONE_TEXT = "Пожалуйста, нажмите кнопку ниже и отправьте номер телефона."
DECLINE_CONSENT_TEXT = "Без согласия на обработку персональных данных регистрация невозможна."
PHOTOS_VIDEO_TEXT = "Фотографии и видео с сегодняшнего события мы вышлем Вам здесь, поэтому не переключайтесь"

COMPANY_CAPTION = (
    "Международное агентство недвижимости NIKA ESTATE\n\n"
    "С 2013 года сопровождаем сделки в премиальном сегменте.\n"
    "Входим в международную ассоциацию AREA.\n\n"
    "Только лучшие предложения на рынке\n"
    "недвижимости в России и за рубежом.\n\n"
    "Семейная резиденция, коммерческий объект, точка выхода на новый рынок или актив с понятной доходностью – "
    "любой вопрос, связанный с недвижимостью, мы решаем через экспертизу, аналитику и сервис, в котором важны детали, "
    "конфиденциальность и результат.\n\n"
    "NIKA ESTATE – ваш доступ к миру премиальной недвижимости в России и за рубежом."
)

CONTACT_TEXT = "Чтобы связаться с нами, нажмите кнопку ниже."
MISSING_FILE_TEXT_TEMPLATE = "Файл не найден: {filename}"
PHONE_ALREADY_USED_TEXT = "Этот номер уже есть в базе. Один человек не может получить два номера."
ALREADY_REGISTERED_TEXT = "Вы уже зарегистрированы. Ниже доступны материалы и кнопки." 
UNKNOWN_TEXT = "Используйте кнопки меню ниже."

# =========================================================
# СОСТОЯНИЯ
# =========================================================
class Registration(StatesGroup):
    waiting_for_name = State()
    waiting_for_legend_answer = State()
    waiting_for_consent = State()
    waiting_for_phone = State()


class AdminReset(StatesGroup):
    waiting_for_password = State()


class AdminBroadcast(StatesGroup):
    waiting_for_message = State()
    waiting_for_confirmation = State()


# =========================================================
# БАЗА
# =========================================================

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER NOT NULL UNIQUE,
                username TEXT,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL UNIQUE,
                participant_number INTEGER NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def normalize_phone(phone: str) -> str:
    return "".join(ch for ch in phone if ch.isdigit() or ch == "+")


def get_user_by_tg_id(tg_id: int):
    with get_connection() as conn:
        return conn.execute("SELECT * FROM participants WHERE tg_id = ?", (tg_id,)).fetchone()


def get_user_by_phone(phone: str):
    with get_connection() as conn:
        return conn.execute("SELECT * FROM participants WHERE phone = ?", (phone,)).fetchone()


def get_next_number() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT MAX(participant_number) AS max_num FROM participants").fetchone()
        return 1 if row is None or row["max_num"] is None else int(row["max_num"]) + 1


def create_user(tg_id: int, username: Optional[str], full_name: str, phone: str) -> int:
    number = get_next_number()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO participants (tg_id, username, full_name, phone, participant_number, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (tg_id, username, full_name, phone, number, created_at),
        )
        conn.commit()
    return number


def get_all_user_ids() -> list[int]:
    with get_connection() as conn:
        rows = conn.execute("SELECT tg_id FROM participants").fetchall()
        return [int(row["tg_id"]) for row in rows]


def get_period_start(period: str) -> datetime:
    now = datetime.now()
    if period == "today":
        return datetime(now.year, now.month, now.day)
    if period == "week":
        return now - timedelta(days=7)
    if period == "month":
        return now - timedelta(days=30)
    raise ValueError("Unknown period")


def get_users_for_period(period: str):
    start_dt = get_period_start(period).strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM participants WHERE created_at >= ? ORDER BY participant_number ASC",
            (start_dt,),
        ).fetchall()


def export_to_excel(period: str) -> Optional[Path]:
    rows = get_users_for_period(period)
    if not rows:
        return None

    file_path = EXPORTS_DIR / f"participants_{period}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    df = pd.DataFrame(
        [
            {
                "ID": row["id"],
                "Telegram ID": row["tg_id"],
                "Username": row["username"] or "",
                "Имя": row["full_name"],
                "Телефон": row["phone"],
                "Номер участника": row["participant_number"],
                "Дата регистрации": row["created_at"],
            }
            for row in rows
        ]
    )
    df.to_excel(file_path, index=False)
    return file_path


def reset_db() -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM participants")
        conn.execute("DELETE FROM sqlite_sequence WHERE name='participants'")
        conn.commit()


# =========================================================
# КЛАВИАТУРЫ
# =========================================================

def start_kb(is_admin: bool = False) -> ReplyKeyboardMarkup:
    buttons = [[KeyboardButton(text=START_BUTTON)]]
    if is_admin:
        buttons.append([KeyboardButton(text=ADMIN_MENU_BUTTON)])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


consent_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=CONSENT_ACCEPT_BUTTON)],
        [KeyboardButton(text=CONSENT_DECLINE_BUTTON)],
    ],
    resize_keyboard=True,
)

phone_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=SEND_PHONE_BUTTON, request_contact=True)]],
    resize_keyboard=True,
)

participant_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=PARTICIPANT_COMPANY)],
        [KeyboardButton(text=PARTICIPANT_SOCHI)],
        [KeyboardButton(text=PARTICIPANT_MANAGEMENT)],
        [KeyboardButton(text=PARTICIPANT_CONTACT)],
    ],
    resize_keyboard=True,
)

admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=EXPORT_TODAY_BUTTON)],
        [KeyboardButton(text=EXPORT_WEEK_BUTTON)],
        [KeyboardButton(text=EXPORT_MONTH_BUTTON)],
        [KeyboardButton(text=BROADCAST_BUTTON)],
        [KeyboardButton(text=RESET_DB_BUTTON)],
        [KeyboardButton(text=BACK_BUTTON)],
    ],
    resize_keyboard=True,
)

legend_choice_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text=YES_BUTTON, callback_data="legend_answer"),
            InlineKeyboardButton(text=NO_BUTTON, callback_data="legend_answer"),
        ]
    ]
)

contact_link_kb = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Перейти", url=CONTACT_URL)]]
)

broadcast_confirm_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text=CONFIRM_BROADCAST_BUTTON, callback_data="broadcast_confirm")],
        [InlineKeyboardButton(text=CANCEL_BROADCAST_BUTTON, callback_data="broadcast_cancel")],
    ]
)


# =========================================================
# БОТ
# =========================================================
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def safe_send_photo(message: Message, path: Path, caption: Optional[str] = None, reply_markup=None) -> None:
    if not path.exists():
        await message.answer(MISSING_FILE_TEXT_TEMPLATE.format(filename=path.name))
        return
    await message.answer_photo(FSInputFile(path), caption=caption, reply_markup=reply_markup)


async def safe_send_document(message: Message, path: Path, caption: Optional[str] = None) -> None:
    if not path.exists():
        await message.answer(MISSING_FILE_TEXT_TEMPLATE.format(filename=path.name))
        return
    await message.answer_document(FSInputFile(path), caption=caption)


async def safe_send_video(message: Message, path: Path, caption: Optional[str] = None) -> None:
    if not path.exists():
        await message.answer(MISSING_FILE_TEXT_TEMPLATE.format(filename=path.name))
        return
    await message.answer_video(FSInputFile(path), caption=caption)


async def safe_send_audio(message: Message, path: Path, caption: Optional[str] = None) -> None:
    if not path.exists():
        await message.answer(MISSING_FILE_TEXT_TEMPLATE.format(filename=path.name))
        return
    await message.answer_audio(FSInputFile(path), caption=caption)


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = get_user_by_tg_id(message.from_user.id)
    if user:
        await message.answer(ALREADY_REGISTERED_TEXT, reply_markup=participant_kb)
        return
    await message.answer("Нажмите кнопку ниже, чтобы начать.", reply_markup=start_kb(is_admin(message.from_user.id)))


@dp.message(F.text == START_BUTTON)
async def start_registration(message: Message, state: FSMContext):
    user = get_user_by_tg_id(message.from_user.id)
    if user:
        await message.answer(ALREADY_REGISTERED_TEXT, reply_markup=participant_kb)
        return
    await message.answer(START_GREETING)
    await message.answer(ASK_NAME)
    await state.set_state(Registration.waiting_for_name)


@dp.message(Registration.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if not name:
        await message.answer(ASK_NAME)
        return

    await state.update_data(full_name=name)
    await message.answer(NAME_TEXT_TEMPLATE.format(name=name))
    await safe_send_photo(message, TIMING_IMAGE, caption=TIMING_CAPTION)
    await message.answer(MENU_CAPTION)
    await safe_send_photo(message, MENU_IMAGE)
    await message.answer(SOCHI_TEXT)
    await safe_send_photo(message, SOCHI_IMAGE, reply_markup=legend_choice_kb)
    await safe_send_audio(message, LEGEND_AUDIO)
    await state.set_state(Registration.waiting_for_legend_answer)


@dp.callback_query(F.data == "legend_answer")
async def handle_legend_answer(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != Registration.waiting_for_legend_answer.state:
        await callback.answer()
        return

    await callback.answer()
    if callback.message:
        await callback.message.answer(LEGEND_TEXT)
        await safe_send_photo(callback.message, VELVET_SEASON_IMAGE)
        await callback.message.answer(TODAY_HISTORY_TEXT)
        await callback.message.answer(CONSENT_TEXT, reply_markup=consent_kb)
        await state.set_state(Registration.waiting_for_consent)


@dp.message(Registration.waiting_for_consent, F.text == CONSENT_DECLINE_BUTTON)
async def decline_consent(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(DECLINE_CONSENT_TEXT, reply_markup=start_kb(is_admin(message.from_user.id)))


@dp.message(Registration.waiting_for_consent, F.text == CONSENT_ACCEPT_BUTTON)
async def accept_consent(message: Message, state: FSMContext):
    await state.update_data(consent_given=True)
    await state.set_state(Registration.waiting_for_phone)
    await message.answer(ASK_PHONE_TEXT, reply_markup=phone_kb)


@dp.message(Registration.waiting_for_consent)
async def wrong_consent(message: Message):
    await message.answer("Пожалуйста, выберите один из вариантов кнопкой ниже.", reply_markup=consent_kb)


@dp.message(Registration.waiting_for_phone)
async def save_phone(message: Message, state: FSMContext):
    if not message.contact:
        await message.answer("Пожалуйста, используйте кнопку «Отправить номер телефона».", reply_markup=phone_kb)
        return

    contact = message.contact
    if contact.user_id and contact.user_id != message.from_user.id:
        await message.answer("Пожалуйста, отправьте свой номер телефона.", reply_markup=phone_kb)
        return

    if get_user_by_tg_id(message.from_user.id):
        await state.clear()
        await message.answer(ALREADY_REGISTERED_TEXT, reply_markup=participant_kb)
        return

    phone = normalize_phone(contact.phone_number)
    if get_user_by_phone(phone):
        await state.clear()
        await message.answer(PHONE_ALREADY_USED_TEXT, reply_markup=start_kb(is_admin(message.from_user.id)))
        return

    data = await state.get_data()
    create_user(
        tg_id=message.from_user.id,
        username=message.from_user.username,
        full_name=data.get("full_name", "Без имени"),
        phone=phone,
    )
    await state.clear()
    await message.answer(PHOTOS_VIDEO_TEXT, reply_markup=participant_kb)


# =========================================================
# УЧАСТНИКИ
# =========================================================
@dp.message(F.text == PARTICIPANT_COMPANY)
async def participant_company(message: Message):
    await safe_send_photo(message, COMPANY_IMAGE, caption=COMPANY_CAPTION)


@dp.message(F.text == PARTICIPANT_SOCHI)
async def participant_sochi(message: Message):
    await safe_send_video(message, SOCHI_VIDEO)
    await safe_send_document(message, SOCHI_PRESENTATION)


@dp.message(F.text == PARTICIPANT_MANAGEMENT)
async def participant_management(message: Message):
    await safe_send_photo(message, MANAGEMENT_IMAGE_1)
    await safe_send_photo(message, MANAGEMENT_IMAGE_2)


@dp.message(F.text == PARTICIPANT_CONTACT)
async def participant_contact(message: Message):
    await safe_send_photo(message, CONTACT_IMAGE)
    await message.answer(CONTACT_TEXT, reply_markup=contact_link_kb)


# =========================================================
# АДМИНКА
# =========================================================
@dp.message(F.text == ADMIN_MENU_BUTTON)
@dp.message(Command("admin"))
async def admin_menu(message: Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        await message.answer("Эта команда доступна только администратору.")
        return
    await message.answer("Админ меню. Выберите действие.", reply_markup=admin_kb)


async def process_export(message: Message, period: str):
    if not is_admin(message.from_user.id):
        await message.answer("Эта команда доступна только администратору.")
        return
    file_path = export_to_excel(period)
    if file_path is None:
        await message.answer("За выбранный период зарегистрированных участников нет.")
        return
    await message.answer_document(FSInputFile(file_path), caption=f"Выгрузка: {period}")


@dp.message(F.text == EXPORT_TODAY_BUTTON)
async def export_today(message: Message):
    await process_export(message, "today")


@dp.message(F.text == EXPORT_WEEK_BUTTON)
async def export_week(message: Message):
    await process_export(message, "week")


@dp.message(F.text == EXPORT_MONTH_BUTTON)
async def export_month(message: Message):
    await process_export(message, "month")


@dp.message(F.text == RESET_DB_BUTTON)
async def ask_reset_password(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Эта команда доступна только администратору.")
        return
    await state.set_state(AdminReset.waiting_for_password)
    await message.answer("Введите пароль для сброса базы.")


@dp.message(AdminReset.waiting_for_password)
async def confirm_reset(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        await message.answer("Эта команда доступна только администратору.")
        return
    if message.text == RESET_PASSWORD:
        reset_db()
        await message.answer("База данных очищена.", reply_markup=admin_kb)
    else:
        await message.answer("Неверный пароль. Ресет отменён.", reply_markup=admin_kb)
    await state.clear()


@dp.message(F.text == BROADCAST_BUTTON)
async def broadcast_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Эта команда доступна только администратору.")
        return
    await state.set_state(AdminBroadcast.waiting_for_message)
    await message.answer(
        "Отправьте сообщение для рассылки. Можно отправить текст или фото с подписью."
    )


@dp.message(AdminBroadcast.waiting_for_message)
async def broadcast_prepare(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        await message.answer("Эта команда доступна только администратору.")
        return

    if message.photo:
        file_id = message.photo[-1].file_id
        caption = message.caption or ""
        await state.update_data(broadcast_type="photo", file_id=file_id, caption=caption)
        await message.answer_photo(file_id, caption=caption, reply_markup=broadcast_confirm_kb)
        await state.set_state(AdminBroadcast.waiting_for_confirmation)
        return

    text = (message.text or "").strip()
    if not text:
        await message.answer("Сообщение пустое. Отправьте текст или фото с подписью.")
        return

    await state.update_data(broadcast_type="text", text=text)
    await message.answer(text, reply_markup=broadcast_confirm_kb)
    await state.set_state(AdminBroadcast.waiting_for_confirmation)


@dp.callback_query(F.data == "broadcast_cancel")
async def broadcast_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Рассылка отменена")
    if callback.message:
        await callback.message.answer("Рассылка отменена.", reply_markup=admin_kb)


@dp.callback_query(F.data == "broadcast_confirm")
async def broadcast_confirm(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Рассылка запущена")
    if not is_admin(callback.from_user.id):
        await state.clear()
        return

    data = await state.get_data()
    user_ids = get_all_user_ids()
    success_count = 0
    failed_count = 0

    for user_id in user_ids:
        try:
            if data.get("broadcast_type") == "photo":
                await bot.send_photo(user_id, data["file_id"], caption=data.get("caption", ""))
            else:
                await bot.send_message(user_id, data.get("text", ""))
            success_count += 1
        except Exception:
            failed_count += 1

    await state.clear()
    if callback.message:
        await callback.message.answer(
            f"Рассылка завершена.\nУспешно отправлено: {success_count}\nНе доставлено: {failed_count}",
            reply_markup=admin_kb,
        )


@dp.message(F.text == BACK_BUTTON)
async def go_back(message: Message, state: FSMContext):
    await state.clear()
    if is_admin(message.from_user.id):
        await message.answer("Возврат в меню администратора.", reply_markup=admin_kb)
    else:
        await message.answer("Возврат в меню.", reply_markup=participant_kb)


@dp.message()
async def fallback(message: Message):
    user = get_user_by_tg_id(message.from_user.id)
    if user:
        await message.answer(UNKNOWN_TEXT, reply_markup=participant_kb)
    else:
        await message.answer("Нажмите /start для начала.", reply_markup=start_kb(is_admin(message.from_user.id)))


async def main():
    logging.basicConfig(level=logging.INFO)
    init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
