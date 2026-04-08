from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

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
    ReplyKeyboardRemove,
)

# =========================
# НАСТРОЙКИ
# =========================
BOT_TOKEN = "PASTE_BOT_TOKEN_HERE"
ADMIN_IDS = {123456789}
RESET_PASSWORD = "1234"
CHANNEL_LINK = "https://t.me/your_channel_here"

DB_PATH = "database.db"
EXPORTS_DIR = Path("exports")
ASSETS_DIR = Path("assets")

TIMING_IMAGE_PATH = ASSETS_DIR / "timing.png"
MENU_IMAGE_PATH = ASSETS_DIR / "menu.png"
SOCHI_QUESTION_IMAGE_PATH = ASSETS_DIR / "sochi_question.png"
SEASON_HISTORY_IMAGE_PATH = ASSETS_DIR / "season_history.png"
COMPANY_IMAGE_PATH = ASSETS_DIR / "company.png"
LEADERSHIP_IMAGE_1_PATH = ASSETS_DIR / "leadership_1.png"
LEADERSHIP_IMAGE_2_PATH = ASSETS_DIR / "leadership_2.png"
CONTACT_IMAGE_PATH = ASSETS_DIR / "contact.png"
SOCHI_VIDEO_PATH = ASSETS_DIR / "sochi_video.mp4"
SOCHI_PRESENTATION_PATH = ASSETS_DIR / "sochi_presentation.pptx"

# Telegram-бот не может менять фон чата у пользователя.
# Поэтому фон «бота» можно только положить файлом в проект для ручного использования,
# но автоматически применить его через код нельзя.
BOT_BACKGROUND_IMAGE_PATH = ASSETS_DIR / "bot_background.png"

# =========================
# ТЕКСТЫ И КНОПКИ
# =========================
START_BUTTON = "Старт"
BACK_BUTTON = "Назад"

CONSENT_ACCEPT_BUTTON = "Согласен(а)"
CONSENT_DECLINE_BUTTON = "Не согласен(а)"
SEND_PHONE_BUTTON = "Отправить номер телефона"

ABOUT_COMPANY_BUTTON = "О КОМПАНИИ"
SOCHI_BUTTON = "СОЧИ"
LEADERSHIP_BUTTON = "РУКОВОДСТВО"
CONTACT_BUTTON = "СВЯЗАТЬСЯ"

ADMIN_MENU_BUTTON = "Админ меню"
EXPORT_TODAY_BUTTON = "Выгрузка: сегодня"
EXPORT_WEEK_BUTTON = "Выгрузка: неделя"
EXPORT_MONTH_BUTTON = "Выгрузка: месяц"
RESET_DB_BUTTON = "Ресет базы"
BROADCAST_BUTTON = "Рассылка"

YES_BUTTON = "ДА"
NO_BUTTON = "НЕТ"
SEND_TO_ALL_BUTTON = "Отправить всем"
CANCEL_BROADCAST_BUTTON = "Отменить рассылку"

START_GREETING = (
    "Добрый вечер, уважаемый пассажир эксклюзивного экспресса «Бархатный путь»! "
    "Совсем скоро начнется наше путешествие, а пока - давайте знакомиться?"
)

ASK_NAME_TEXT = "Пожалуйста, введите ваше имя."

NAME_TEXT_TEMPLATE = (
    "{name}, ох, сколько Вас сегодня ждет впереди! "
    "Вечер наполнен изысканными угощениями, подарками, сюрпризами, танцами, музыкой и даже… мистикой!"
)

TIMING_CAPTION = "Как видите, остановки предусмотрены, за это не переживайте"
MENU_CAPTION = (
    "Голод - враг искусства! Перейдем к меню на ужин? "
    "Вы только посмотрите, какое обилие угощений Вас ждет впереди!"
)
SOCHI_PRE_TEXT = (
    "А Вы бывали в Сочи? Просто представьте: шум моря, запах цветущих магнолий "
    "и прибой Черного моря… А знаете ли вы легенду о бархатном сезоне?"
)
SEASON_LEGEND_TEXT = (
    "В конце XIX – начале XX века русская аристократия отдыхала в Крыму не летом, а в апреле-мае, "
    "сменяя меховые одежды на бархатные, что изначально дало название сезону. "
    "И только сильно позже сезон сместился на начало осени из-за рекомендаций врачей"
)
SEASON_FINAL_TEXT = (
    "Сегодня окунемся в истории бархатного сезона, и Вы сможете стать свидетелями событий того времени…"
)
CONSENT_TEXT = (
    "Пожалуйста, подтвердите согласие на обработку персональных данных, "
    "чтобы мы могли завершить регистрацию."
)
ASK_PHONE_TEXT = "Пожалуйста, нажмите кнопку ниже и отправьте номер телефона."
AFTER_REGISTRATION_TEXT = (
    "Фотографии и видео с сегодняшнего события мы вышлем Вам здесь, поэтому не переключайтесь"
)
ALREADY_REGISTERED_TEXT = "Вы уже зарегистрированы. Ниже доступно меню участника."
DECLINED_CONSENT_TEXT = (
    "Без согласия на обработку персональных данных регистрация невозможна. "
    "Если передумаете, нажмите /start и начните заново."
)
PHONE_ALREADY_USED_TEXT = (
    "Этот номер телефона уже зарегистрирован в системе. Один человек не может иметь два номера."
)
INVALID_PHONE_TEXT = "Пожалуйста, используйте кнопку «Отправить номер телефона»."

COMPANY_CAPTION = (
    "Международное агентство недвижимости NIKA ESTATE\n\n"
    "С 2013 года сопровождаем сделки в премиальном сегменте.\n"
    "Входим в международную ассоциацию AREA.\n\n"
    "Только лучшие предложения на рынке\n"
    "недвижимости в России и за рубежом.\n\n"
    "Семейная резиденция, коммерческий объект, точка выхода на новый рынок "
    "или актив с понятной доходностью – любой вопрос, связанный с недвижимостью, "
    "мы решаем через экспертизу, аналитику и сервис, в котором важны детали, конфиденциальность и результат.\n\n"
    "NIKA ESTATE – ваш доступ к миру премиальной недвижимости в России и за рубежом."
)

CONTACT_TEXT = "Для связи перейдите по кнопке ниже."
ADMIN_MENU_TEXT = "Панель администратора. Выберите действие."
ADMIN_ONLY_TEXT = "Эта команда доступна только администратору."
ENTER_RESET_PASSWORD_TEXT = "Введите пароль для полного ресета базы."
RESET_SUCCESS_TEXT = "База данных очищена."
RESET_FAILED_TEXT = "Неверный пароль. Ресет отменён."
EXPORT_EMPTY_TEXT = "За выбранный период зарегистрированных участников нет."
UNKNOWN_TEXT = "Используйте кнопки меню ниже."
BROADCAST_PROMPT_TEXT = (
    "Отправьте сообщение для рассылки.\n"
    "Можно отправить обычный текст или фото с подписью."
)
BROADCAST_PREVIEW_TEXT = "Предпросмотр рассылки. Отправить всем?"
BROADCAST_CANCELLED_TEXT = "Рассылка отменена."
BROADCAST_EMPTY_TEXT = "Невозможно сделать пустую рассылку."
NO_MENU_FILE_TEXT = "Файл меню не найден. Добавьте assets/menu.png"

# =========================
# СОСТОЯНИЯ
# =========================
class Registration(StatesGroup):
    waiting_for_name = State()
    waiting_for_season_answer = State()
    waiting_for_consent = State()
    waiting_for_phone = State()


class AdminReset(StatesGroup):
    waiting_for_password = State()


class AdminBroadcast(StatesGroup):
    waiting_for_message = State()
    waiting_for_confirmation = State()


# =========================
# БАЗА
# =========================
def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
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


def create_user(tg_id: int, username: str | None, full_name: str, phone: str) -> int:
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
        rows = conn.execute("SELECT tg_id FROM participants ORDER BY participant_number ASC").fetchall()
        return [row["tg_id"] for row in rows]


def get_period_start(period: str) -> datetime:
    now = datetime.now()
    if period == "today":
        return datetime(now.year, now.month, now.day)
    if period == "week":
        return now - timedelta(days=7)
    if period == "month":
        return now - timedelta(days=30)
    raise ValueError("Unknown period")


def get_users_for_period(period: str) -> list[sqlite3.Row]:
    start_dt = get_period_start(period).strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM participants WHERE created_at >= ? ORDER BY participant_number ASC",
            (start_dt,),
        ).fetchall()


def reset_db() -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM participants")
        conn.execute("DELETE FROM sqlite_sequence WHERE name='participants'")
        conn.commit()


# =========================
# EXCEL
# =========================
def export_to_excel(period: str) -> Path | None:
    rows = get_users_for_period(period)
    if not rows:
        return None

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = EXPORTS_DIR / f"participants_{period}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    data = [
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
    pd.DataFrame(data).to_excel(file_path, index=False)
    return file_path


# =========================
# КЛАВИАТУРЫ
# =========================
def start_kb(is_admin_user: bool = False) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=START_BUTTON)]]
    if is_admin_user:
        rows.append([KeyboardButton(text=ADMIN_MENU_BUTTON)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


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
        [KeyboardButton(text=ABOUT_COMPANY_BUTTON)],
        [KeyboardButton(text=SOCHI_BUTTON)],
        [KeyboardButton(text=LEADERSHIP_BUTTON)],
        [KeyboardButton(text=CONTACT_BUTTON)],
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

season_question_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text=YES_BUTTON, callback_data="season_answer_yes"),
            InlineKeyboardButton(text=NO_BUTTON, callback_data="season_answer_no"),
        ]
    ]
)

contact_inline_kb = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Открыть Telegram", url=CHANNEL_LINK)]]
)

broadcast_confirm_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=SEND_TO_ALL_BUTTON)],
        [KeyboardButton(text=CANCEL_BROADCAST_BUTTON)],
    ],
    resize_keyboard=True,
)


# =========================
# БОТ
# =========================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def send_if_exists_photo(message: Message, path: Path, caption: str | None = None, reply_markup=None) -> None:
    if path.exists():
        await message.answer_photo(FSInputFile(path), caption=caption, reply_markup=reply_markup)
    else:
        fallback_text = caption or f"Файл не найден: {path.name}"
        await message.answer(fallback_text, reply_markup=reply_markup)


async def send_main_participant_menu(message: Message) -> None:
    await message.answer(AFTER_REGISTRATION_TEXT, reply_markup=participant_kb)


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

    await state.clear()
    await message.answer(START_GREETING, reply_markup=ReplyKeyboardRemove())
    await message.answer(ASK_NAME_TEXT)
    await state.set_state(Registration.waiting_for_name)


@dp.message(Registration.waiting_for_name)
async def save_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if not name:
        await message.answer(ASK_NAME_TEXT)
        return

    await state.update_data(full_name=name)
    await message.answer(NAME_TEXT_TEMPLATE.format(name=name))
    await send_if_exists_photo(message, TIMING_IMAGE_PATH, TIMING_CAPTION)
    await send_if_exists_photo(message, MENU_IMAGE_PATH, MENU_CAPTION)
    await message.answer(SOCHI_PRE_TEXT)
    await send_if_exists_photo(message, SOCHI_QUESTION_IMAGE_PATH, reply_markup=season_question_kb)
    await state.set_state(Registration.waiting_for_season_answer)


@dp.callback_query(Registration.waiting_for_season_answer, F.data.in_({"season_answer_yes", "season_answer_no"}))
async def handle_season_answer(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(SEASON_LEGEND_TEXT)
    await send_if_exists_photo(callback.message, SEASON_HISTORY_IMAGE_PATH)
    await callback.message.answer(SEASON_FINAL_TEXT)
    await callback.message.answer(CONSENT_TEXT, reply_markup=consent_kb)
    await state.set_state(Registration.waiting_for_consent)


@dp.message(Registration.waiting_for_consent, F.text == CONSENT_DECLINE_BUTTON)
async def decline_consent(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(DECLINED_CONSENT_TEXT, reply_markup=start_kb(is_admin(message.from_user.id)))


@dp.message(Registration.waiting_for_consent, F.text == CONSENT_ACCEPT_BUTTON)
async def accept_consent(message: Message, state: FSMContext):
    await state.update_data(consent_given=True)
    await state.set_state(Registration.waiting_for_phone)
    await message.answer(ASK_PHONE_TEXT, reply_markup=phone_kb)


@dp.message(Registration.waiting_for_consent)
async def wrong_consent(message: Message):
    await message.answer("Пожалуйста, выберите один из вариантов согласия кнопкой ниже.")


@dp.message(Registration.waiting_for_phone)
async def save_phone(message: Message, state: FSMContext):
    if not message.contact or not message.contact.phone_number:
        await message.answer(INVALID_PHONE_TEXT, reply_markup=phone_kb)
        return

    if message.contact.user_id and message.contact.user_id != message.from_user.id:
        await message.answer("Пожалуйста, отправьте свой номер телефона.", reply_markup=phone_kb)
        return

    existing_by_user = get_user_by_tg_id(message.from_user.id)
    if existing_by_user:
        await state.clear()
        await message.answer(ALREADY_REGISTERED_TEXT, reply_markup=participant_kb)
        return

    phone = normalize_phone(message.contact.phone_number)
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
    await message.answer(AFTER_REGISTRATION_TEXT, reply_markup=participant_kb)


@dp.message(F.text == ABOUT_COMPANY_BUTTON)
async def about_company(message: Message):
    await send_if_exists_photo(message, COMPANY_IMAGE_PATH, COMPANY_CAPTION, reply_markup=participant_kb)


@dp.message(F.text == SOCHI_BUTTON)
async def sochi_info(message: Message):
    if SOCHI_VIDEO_PATH.exists():
        await message.answer_video(FSInputFile(SOCHI_VIDEO_PATH), reply_markup=participant_kb)
    else:
        await message.answer("Видео о Сочи пока не добавлено.", reply_markup=participant_kb)

    if SOCHI_PRESENTATION_PATH.exists():
        await message.answer_document(FSInputFile(SOCHI_PRESENTATION_PATH), reply_markup=participant_kb)
    else:
        await message.answer("Презентация о Сочи пока не добавлена.", reply_markup=participant_kb)


@dp.message(F.text == LEADERSHIP_BUTTON)
async def leadership_info(message: Message):
    await send_if_exists_photo(message, LEADERSHIP_IMAGE_1_PATH, reply_markup=participant_kb)
    await send_if_exists_photo(message, LEADERSHIP_IMAGE_2_PATH, reply_markup=participant_kb)


@dp.message(F.text == CONTACT_BUTTON)
async def contact_info(message: Message):
    if CONTACT_IMAGE_PATH.exists():
        await message.answer_photo(FSInputFile(CONTACT_IMAGE_PATH), caption=CONTACT_TEXT, reply_markup=contact_inline_kb)
    else:
        await message.answer(CONTACT_TEXT, reply_markup=contact_inline_kb)


@dp.message(F.text == BACK_BUTTON)
async def go_back(message: Message, state: FSMContext):
    await state.clear()
    user = get_user_by_tg_id(message.from_user.id)
    if user:
        await message.answer("Меню участника.", reply_markup=participant_kb)
    else:
        await message.answer("Главное меню.", reply_markup=start_kb(is_admin(message.from_user.id)))


@dp.message(F.text == ADMIN_MENU_BUTTON)
@dp.message(Command("admin"))
async def admin_menu(message: Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        await message.answer(ADMIN_ONLY_TEXT)
        return
    await message.answer(ADMIN_MENU_TEXT, reply_markup=admin_kb)


async def process_export(message: Message, period: str):
    if not is_admin(message.from_user.id):
        await message.answer(ADMIN_ONLY_TEXT)
        return

    file_path = export_to_excel(period)
    if file_path is None:
        await message.answer(EXPORT_EMPTY_TEXT, reply_markup=admin_kb)
        return

    await message.answer_document(FSInputFile(file_path), caption=f"Выгрузка: {period}", reply_markup=admin_kb)


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
        await message.answer(ADMIN_ONLY_TEXT)
        return
    await message.answer(ENTER_RESET_PASSWORD_TEXT)
    await state.set_state(AdminReset.waiting_for_password)


@dp.message(AdminReset.waiting_for_password)
async def confirm_reset(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        await message.answer(ADMIN_ONLY_TEXT)
        return

    if message.text == RESET_PASSWORD:
        reset_db()
        await message.answer(RESET_SUCCESS_TEXT, reply_markup=admin_kb)
    else:
        await message.answer(RESET_FAILED_TEXT, reply_markup=admin_kb)
    await state.clear()


@dp.message(F.text == BROADCAST_BUTTON)
async def broadcast_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer(ADMIN_ONLY_TEXT)
        return

    await state.clear()
    await state.set_state(AdminBroadcast.waiting_for_message)
    await message.answer(BROADCAST_PROMPT_TEXT, reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BACK_BUTTON)]], resize_keyboard=True
    ))


@dp.message(AdminBroadcast.waiting_for_message)
async def broadcast_capture(message: Message, state: FSMContext):
    if message.text == BACK_BUTTON:
        await state.clear()
        await message.answer(BROADCAST_CANCELLED_TEXT, reply_markup=admin_kb)
        return

    text = (message.caption or message.text or "").strip()
    photo_file_id = message.photo[-1].file_id if message.photo else None

    if not text and not photo_file_id:
        await message.answer(BROADCAST_EMPTY_TEXT)
        return

    await state.update_data(broadcast_text=text, broadcast_photo=photo_file_id)

    if photo_file_id:
        await message.answer_photo(photo=photo_file_id, caption=text or None)
    else:
        await message.answer(text)

    await state.set_state(AdminBroadcast.waiting_for_confirmation)
    await message.answer(BROADCAST_PREVIEW_TEXT, reply_markup=broadcast_confirm_kb)


@dp.message(AdminBroadcast.waiting_for_confirmation, F.text == CANCEL_BROADCAST_BUTTON)
async def broadcast_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(BROADCAST_CANCELLED_TEXT, reply_markup=admin_kb)


@dp.message(AdminBroadcast.waiting_for_confirmation, F.text == SEND_TO_ALL_BUTTON)
async def broadcast_send(message: Message, state: FSMContext):
    data = await state.get_data()
    text = data.get("broadcast_text", "")
    photo_file_id = data.get("broadcast_photo")
    user_ids = get_all_user_ids()

    if not user_ids:
        await state.clear()
        await message.answer("В базе нет зарегистрированных участников.", reply_markup=admin_kb)
        return

    success_count = 0
    failed_count = 0

    for user_id in user_ids:
        try:
            if photo_file_id:
                await bot.send_photo(user_id, photo_file_id, caption=text or None)
            else:
                await bot.send_message(user_id, text)
            success_count += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed_count += 1

    await state.clear()
    await message.answer(
        f"Рассылка завершена.\nУспешно: {success_count}\nНе доставлено: {failed_count}",
        reply_markup=admin_kb,
    )


@dp.message(AdminBroadcast.waiting_for_confirmation)
async def broadcast_confirmation_fallback(message: Message):
    await message.answer("Выберите: «Отправить всем» или «Отменить рассылку».")


@dp.message()
async def fallback(message: Message):
    user = get_user_by_tg_id(message.from_user.id)
    if user:
        await message.answer(UNKNOWN_TEXT, reply_markup=participant_kb)
    else:
        await message.answer("Нажмите /start для начала работы.", reply_markup=start_kb(is_admin(message.from_user.id)))


async def main():
    init_db()
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
