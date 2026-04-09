import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ContentType, ParseMode
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

BOT_TOKEN = "8428046405:AAFISFm6Mm3ZStV93DsyxhZzc9HwMN6n63c"
ADMIN_IDS = {922603146}
RESET_PASSWORD = "12345678"
SOCHI_VIDEO_FILE_ID = "PASTE_VIDEO_FILE_ID_HERE"

DB_PATH = "database.db"
EXPORTS_DIR = Path("exports")
ASSETS_DIR = Path("assets")

TIMING_IMAGE = ASSETS_DIR / "timing.png"
MENU_IMAGE = ASSETS_DIR / "menu.png"
SOCHI_INTRO_IMAGE = ASSETS_DIR / "sochi_intro.png"
LEGEND_AUDIO = ASSETS_DIR / "legend_audio.mp3"
VELVET_SEASON_IMAGE = ASSETS_DIR / "velvet_season.png"
COMPANY_IMAGE = ASSETS_DIR / "company.png"
SOCHI_PRESENTATION = ASSETS_DIR / "sochi_presentation.pdf"
MANAGEMENT_1 = ASSETS_DIR / "management_1.png"
MANAGEMENT_2 = ASSETS_DIR / "management_2.png"
MEETING_IMAGE = ASSETS_DIR / "contact.png"

START_BUTTON = "Старт"
CONSENT_ACCEPT_BUTTON = "Согласен(а)"
CONSENT_DECLINE_BUTTON = "Не согласен(а)"
SEND_PHONE_BUTTON = "Отправить номер телефона"
BACK_BUTTON = "Назад"

YES_BUTTON = "✨ Да"
NO_BUTTON = "🌊 Нет"

ABOUT_COMPANY_BUTTON = "О КОМПАНИИ"
SOCHI_BUTTON = "СОЧИ"
MANAGEMENT_BUTTON = "РУКОВОДСТВО"
MEETING_BUTTON = "ВСТРЕЧА"
BOOK_MEETING_BUTTON = "Записаться на встречу"

ADMIN_MENU_BUTTON = "Админ меню"
EXPORT_TODAY_BUTTON = "Выгрузка: сегодня"
EXPORT_WEEK_BUTTON = "Выгрузка: неделя"
EXPORT_MONTH_BUTTON = "Выгрузка: месяц"
RESET_DB_BUTTON = "Ресет базы"
BROADCAST_BUTTON = "Рассылка"
BROADCAST_SEND_BUTTON = "Отправить всем"
BROADCAST_CANCEL_BUTTON = "Отменить рассылку"

START_GREETING = (
    "Добрый вечер, уважаемый пассажир эксклюзивного экспресса «Бархатный путь»! "
    "Совсем скоро начнется наше путешествие, а пока - давайте знакомиться?"
)
ASK_NAME = "Пожалуйста, введите ваше имя."
NAME_TEXT_TEMPLATE = (
    "{name}, ох, сколько Вас сегодня ждет впереди! "
    "Вечер наполнен изысканными угощениями, подарками, сюрпризами, танцами, музыкой и даже… мистикой!"
)
TIMING_CAPTION = "Как видите, остановки предусмотрены, за это не переживайте"
MENU_CAPTION = (
    "Голод - враг искусства! Перейдем к меню на ужин? "
    "Вы только посмотрите, какое обилие угощений Вас ждет впереди!"
)
SOCHI_TEXT = (
    "А Вы бывали в Сочи? Просто представьте: шум моря, запах цветущих магнолий "
    "и прибой Черного моря… А знаете ли вы легенду о бархатном сезоне?"
)
VELVET_HISTORY_TEXT = (
    "В конце XIX – начале XX века русская аристократия отдыхала в Крыму не летом, "
    "а в апреле-мае, сменяя меховые одежды на бархатные, что изначально дало название сезону. "
    "И только сильно позже сезон сместился на начало осени из-за рекомендаций врачей"
)
VELVET_NEXT_TEXT = (
    "Сегодня окунемся в истории бархатного сезона, и Вы сможете стать свидетелями событий того времени…"
)
CONSENT_TEXT = "Пожалуйста, подтвердите согласие на обработку персональных данных."
ASK_PHONE_TEXT = "Пожалуйста, нажмите кнопку ниже и отправьте номер телефона."
AFTER_REGISTRATION_TEXT = "Фотографии и видео с сегодняшнего события мы вышлем Вам здесь, поэтому не переключайтесь"
ALREADY_REGISTERED_TEXT = "Вы уже зарегистрированы. Ниже доступно меню участника."
ABOUT_COMPANY_CAPTION = (
    "Международное агентство недвижимости NIKA ESTATE\n\n"
    "С 2013 года сопровождаем сделки в премиальном сегменте.\n"
    "Входим в международную ассоциацию AREA.\n\n"
    "Только лучшие предложения на рынке\n"
    "недвижимости в России и за рубежом.\n\n"
    "Семейная резиденция, коммерческий объект, точка выхода на новый рынок или актив с понятной доходностью – любой вопрос, связанный с недвижимостью, мы решаем через экспертизу, аналитику и сервис, в котором важны детали, конфиденциальность и результат.\n\n"
    "NIKA ESTATE – ваш доступ к миру премиальной недвижимости в России и за рубежом.\n\n"
    "Telegram-канал: https://t.me/nikaestate_sochi"
)
MANAGEMENT_1_CAPTION = "Виктор Садыгов, основатель и генеральный директор NIKA ESTATE."
MANAGEMENT_2_CAPTION = "Юлия Нафикова, управляющий партнер, топ брокер и амбассадор NIKA ESTATE, телефон для связи +79182888696."
MEETING_TEXT = "Чтобы записаться на встречу, нажмите кнопку ниже."
MEETING_ACCEPTED_TEXT = "Спасибо за отклик 💛\n\nИнформация принята, и мы уже передали Ваш запрос. С Вами обязательно свяжутся в ближайшее время, чтобы подобрать удобный формат встречи."
ADMIN_ONLY_TEXT = "Эта команда доступна только администратору."
UNKNOWN_TEXT = "Используйте кнопки меню."
EXPORT_EMPTY_TEXT = "За выбранный период зарегистрированных участников нет."
RESET_PASSWORD_TEXT = "Введите пароль для сброса базы."
RESET_SUCCESS_TEXT = "База данных очищена."
RESET_FAILED_TEXT = "Неверный пароль. Ресет отменён."
BROADCAST_PROMPT_TEXT = "Отправьте сообщение для рассылки.\nМожно отправить обычный текст или фото с подписью."
BROADCAST_PREVIEW_TEXT = "Предпросмотр рассылки. Выберите действие:"
BROADCAST_DONE_TEXT = "Рассылка завершена.\nУспешно: {ok}\nНе доставлено: {bad}"
BROADCAST_CANCELLED_TEXT = "Рассылка отменена."

class Registration(StatesGroup):
    waiting_for_name = State()
    waiting_for_legend_answer = State()
    waiting_for_consent = State()
    waiting_for_phone = State()

class AdminReset(StatesGroup):
    waiting_for_password = State()

class AdminBroadcast(StatesGroup):
    waiting_for_content = State()
    waiting_for_confirm = State()

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    with get_connection() as conn:
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(participants)").fetchall()]
        if not columns:
            conn.execute('''
                CREATE TABLE participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tg_id INTEGER NOT NULL UNIQUE,
                    username TEXT,
                    full_name TEXT NOT NULL,
                    phone TEXT NOT NULL UNIQUE,
                    participant_number INTEGER NOT NULL UNIQUE,
                    wants_meeting INTEGER NOT NULL DEFAULT 0,
                    meeting_requested_at TEXT,
                    created_at TEXT NOT NULL
                )
            ''')
            conn.commit()
            return
        if "wants_meeting" not in columns:
            conn.execute("ALTER TABLE participants ADD COLUMN wants_meeting INTEGER NOT NULL DEFAULT 0")
        if "meeting_requested_at" not in columns:
            conn.execute("ALTER TABLE participants ADD COLUMN meeting_requested_at TEXT")
        conn.commit()

def normalize_phone(phone: str) -> str:
    return "".join(ch for ch in phone if ch.isdigit() or ch == "+")

def get_user_by_tg_id(tg_id: int):
    with get_connection() as conn:
        return conn.execute("SELECT * FROM participants WHERE tg_id = ?", (tg_id,)).fetchone()

def get_user_by_phone(phone: str):
    with get_connection() as conn:
        return conn.execute("SELECT * FROM participants WHERE phone = ?", (phone,)).fetchone()

def get_all_user_ids() -> list[int]:
    with get_connection() as conn:
        rows = conn.execute("SELECT tg_id FROM participants").fetchall()
        return [int(row["tg_id"]) for row in rows]

def get_next_number() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT MAX(participant_number) AS max_num FROM participants").fetchone()
        if row is None or row["max_num"] is None:
            return 1
        return int(row["max_num"]) + 1

def create_user(tg_id: int, username: str | None, full_name: str, phone: str) -> int:
    number = get_next_number()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute('''
            INSERT INTO participants (
                tg_id, username, full_name, phone, participant_number,
                wants_meeting, meeting_requested_at, created_at
            ) VALUES (?, ?, ?, ?, ?, 0, NULL, ?)
        ''', (tg_id, username, full_name, phone, number, created_at))
        conn.commit()
    return number

def set_meeting_request(tg_id: int) -> None:
    requested_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute('''
            UPDATE participants
            SET wants_meeting = 1, meeting_requested_at = ?
            WHERE tg_id = ?
        ''', (requested_at, tg_id))
        conn.commit()

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

def export_to_excel(period: str) -> Path | None:
    rows = get_users_for_period(period)
    if not rows:
        return None
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = EXPORTS_DIR / f"participants_{period}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    data = []
    for row in rows:
        data.append({
            "ID": row["id"],
            "Telegram ID": row["tg_id"],
            "Username": row["username"] or "",
            "Имя": row["full_name"],
            "Телефон": row["phone"],
            "Номер участника": row["participant_number"],
            "Хочет встречу": "Да" if int(row["wants_meeting"] or 0) == 1 else "Нет",
            "Дата заявки на встречу": row["meeting_requested_at"] or "",
            "Дата регистрации": row["created_at"],
        })
    pd.DataFrame(data).to_excel(file_path, index=False)
    return file_path

def start_kb(is_admin_user: bool = False) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=START_BUTTON)]]
    if is_admin_user:
        rows.append([KeyboardButton(text=ADMIN_MENU_BUTTON)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

consent_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=CONSENT_ACCEPT_BUTTON)], [KeyboardButton(text=CONSENT_DECLINE_BUTTON)]], resize_keyboard=True)
phone_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=SEND_PHONE_BUTTON, request_contact=True)]], resize_keyboard=True)
legend_answer_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=YES_BUTTON), KeyboardButton(text=NO_BUTTON)]], resize_keyboard=True)
participant_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=ABOUT_COMPANY_BUTTON)], [KeyboardButton(text=SOCHI_BUTTON)], [KeyboardButton(text=MANAGEMENT_BUTTON)], [KeyboardButton(text=MEETING_BUTTON)]], resize_keyboard=True)
meeting_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BOOK_MEETING_BUTTON)], [KeyboardButton(text=BACK_BUTTON)]], resize_keyboard=True)
admin_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=EXPORT_TODAY_BUTTON)], [KeyboardButton(text=EXPORT_WEEK_BUTTON)], [KeyboardButton(text=EXPORT_MONTH_BUTTON)], [KeyboardButton(text=BROADCAST_BUTTON)], [KeyboardButton(text=RESET_DB_BUTTON)], [KeyboardButton(text=BACK_BUTTON)]], resize_keyboard=True)
broadcast_confirm_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BROADCAST_SEND_BUTTON)], [KeyboardButton(text=BROADCAST_CANCEL_BUTTON)]], resize_keyboard=True)

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

async def safe_send_photo(message: Message, path: Path, caption: str | None = None, reply_markup=None):
    if not path.exists():
        await message.answer(f"Файл не найден: {path.name}")
        return
    await message.answer_photo(FSInputFile(path), caption=caption, reply_markup=reply_markup)

async def safe_send_audio(message: Message, path: Path, caption: str | None = None):
    if not path.exists():
        await message.answer(f"Файл не найден: {path.name}")
        return
    await message.answer_audio(FSInputFile(path), caption=caption)

async def safe_send_document(message: Message, path: Path, caption: str | None = None):
    if not path.exists():
        await message.answer(f"Файл не найден: {path.name}")
        return
    await message.answer_document(FSInputFile(path), caption=caption)

async def send_registered_menu(message: Message):
    await message.answer(AFTER_REGISTRATION_TEXT, reply_markup=participant_kb)

async def run_story_until_consent(message: Message, state: FSMContext, name: str):
    await message.answer(NAME_TEXT_TEMPLATE.format(name=name))
    await safe_send_photo(message, TIMING_IMAGE, caption=TIMING_CAPTION)
    await safe_send_photo(message, MENU_IMAGE, caption=MENU_CAPTION)
    await message.answer(SOCHI_TEXT)
    await safe_send_photo(message, SOCHI_INTRO_IMAGE)
    await safe_send_audio(message, LEGEND_AUDIO)
    await message.answer("✨", reply_markup=legend_answer_kb)
    await state.set_state(Registration.waiting_for_legend_answer)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

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
    await message.answer(START_GREETING, reply_markup=ReplyKeyboardRemove())
    await message.answer(ASK_NAME)
    await state.set_state(Registration.waiting_for_name)

@dp.message(Registration.waiting_for_name)
async def save_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if not name:
        await message.answer("Пожалуйста, введите имя текстом.")
        return
    await state.update_data(full_name=name)
    await run_story_until_consent(message, state, name)

@dp.message(Registration.waiting_for_legend_answer, F.text.in_({YES_BUTTON, NO_BUTTON}))
async def process_legend_answer(message: Message, state: FSMContext):
    await message.answer(VELVET_HISTORY_TEXT, reply_markup=ReplyKeyboardRemove())
    await safe_send_photo(message, VELVET_SEASON_IMAGE)
    await message.answer(VELVET_NEXT_TEXT)
    await message.answer(CONSENT_TEXT, reply_markup=consent_kb)
    await state.set_state(Registration.waiting_for_consent)

@dp.message(Registration.waiting_for_legend_answer)
async def wrong_legend_answer(message: Message):
    await message.answer("Пожалуйста, выберите одну из кнопок ниже.", reply_markup=legend_answer_kb)

@dp.message(Registration.waiting_for_consent, F.text == CONSENT_DECLINE_BUTTON)
async def decline_consent(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Без согласия на обработку персональных данных регистрация невозможна.", reply_markup=start_kb(is_admin(message.from_user.id)))

@dp.message(Registration.waiting_for_consent, F.text == CONSENT_ACCEPT_BUTTON)
async def accept_consent(message: Message, state: FSMContext):
    await state.update_data(consent_given=True)
    await state.set_state(Registration.waiting_for_phone)
    await message.answer(ASK_PHONE_TEXT, reply_markup=phone_kb)

@dp.message(Registration.waiting_for_consent)
async def wrong_consent(message: Message):
    await message.answer("Пожалуйста, используйте кнопки согласия ниже.", reply_markup=consent_kb)

@dp.message(Registration.waiting_for_phone)
async def save_phone(message: Message, state: FSMContext):
    if not message.contact:
        await message.answer("Пожалуйста, используйте кнопку «Отправить номер телефона».", reply_markup=phone_kb)
        return
    if message.contact.user_id and message.contact.user_id != message.from_user.id:
        await message.answer("Пожалуйста, отправьте свой номер телефона.")
        return
    existing_by_user = get_user_by_tg_id(message.from_user.id)
    if existing_by_user:
        await state.clear()
        await message.answer(ALREADY_REGISTERED_TEXT, reply_markup=participant_kb)
        return
    phone = normalize_phone(message.contact.phone_number)
    existing_by_phone = get_user_by_phone(phone)
    if existing_by_phone:
        await state.clear()
        await message.answer("Этот номер телефона уже есть в базе. Один человек не может иметь два номера.", reply_markup=start_kb(is_admin(message.from_user.id)))
        return
    data = await state.get_data()
    full_name = data.get("full_name", "Без имени")
    create_user(message.from_user.id, message.from_user.username, full_name, phone)
    await state.clear()
    await send_registered_menu(message)

@dp.message(F.text == ABOUT_COMPANY_BUTTON)
async def participant_about_company(message: Message):
    if not get_user_by_tg_id(message.from_user.id):
        await message.answer("Сначала нужно пройти регистрацию.", reply_markup=start_kb(is_admin(message.from_user.id)))
        return
    await safe_send_photo(message, COMPANY_IMAGE, caption=ABOUT_COMPANY_CAPTION)

@dp.message(F.text == SOCHI_BUTTON)
async def participant_sochi(message: Message):
    if not get_user_by_tg_id(message.from_user.id):
        await message.answer("Сначала нужно пройти регистрацию.", reply_markup=start_kb(is_admin(message.from_user.id)))
        return
    if SOCHI_VIDEO_FILE_ID == "PASTE_VIDEO_FILE_ID_HERE":
        await message.answer("Сначала вставьте настоящий file_id видео в bot.py")
    else:
        await message.answer_video(SOCHI_VIDEO_FILE_ID)
    await safe_send_document(message, SOCHI_PRESENTATION)

@dp.message(F.text == MANAGEMENT_BUTTON)
async def participant_management(message: Message):
    if not get_user_by_tg_id(message.from_user.id):
        await message.answer("Сначала нужно пройти регистрацию.", reply_markup=start_kb(is_admin(message.from_user.id)))
        return
    await safe_send_photo(message, MANAGEMENT_1, caption=MANAGEMENT_1_CAPTION)
    await safe_send_photo(message, MANAGEMENT_2, caption=MANAGEMENT_2_CAPTION)

@dp.message(F.text == MEETING_BUTTON)
async def participant_meeting(message: Message):
    if not get_user_by_tg_id(message.from_user.id):
        await message.answer("Сначала нужно пройти регистрацию.", reply_markup=start_kb(is_admin(message.from_user.id)))
        return
    await safe_send_photo(message, MEETING_IMAGE)
    await message.answer(MEETING_TEXT, reply_markup=meeting_kb)

@dp.message(F.text == BOOK_MEETING_BUTTON)
async def participant_book_meeting(message: Message):
    user = get_user_by_tg_id(message.from_user.id)
    if not user:
        await message.answer("Сначала нужно пройти регистрацию.", reply_markup=start_kb(is_admin(message.from_user.id)))
        return
    set_meeting_request(message.from_user.id)
    await message.answer(MEETING_ACCEPTED_TEXT, reply_markup=participant_kb)

@dp.message(F.text == ADMIN_MENU_BUTTON)
@dp.message(Command("admin"))
async def admin_menu(message: Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        await message.answer(ADMIN_ONLY_TEXT)
        return
    await message.answer("Админ меню. Выберите действие.", reply_markup=admin_kb)

async def process_export(message: Message, period: str):
    if not is_admin(message.from_user.id):
        await message.answer(ADMIN_ONLY_TEXT)
        return
    file_path = export_to_excel(period)
    if file_path is None:
        await message.answer(EXPORT_EMPTY_TEXT)
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
        await message.answer(ADMIN_ONLY_TEXT)
        return
    await state.set_state(AdminReset.waiting_for_password)
    await message.answer(RESET_PASSWORD_TEXT, reply_markup=ReplyKeyboardRemove())

@dp.message(AdminReset.waiting_for_password)
async def process_reset_password(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        await message.answer(ADMIN_ONLY_TEXT)
        return
    if (message.text or "").strip() == RESET_PASSWORD:
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
    await state.set_state(AdminBroadcast.waiting_for_content)
    await message.answer(BROADCAST_PROMPT_TEXT, reply_markup=ReplyKeyboardRemove())

@dp.message(AdminBroadcast.waiting_for_content, F.content_type.in_({ContentType.TEXT, ContentType.PHOTO}))
async def broadcast_capture(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        await message.answer(ADMIN_ONLY_TEXT)
        return
    if message.photo:
        file_id = message.photo[-1].file_id
        caption = message.caption or ""
        await state.update_data(broadcast_type="photo", file_id=file_id, caption=caption)
        await message.answer_photo(file_id, caption=caption)
    else:
        text = message.text or ""
        await state.update_data(broadcast_type="text", text=text)
        await message.answer(text)
    await state.set_state(AdminBroadcast.waiting_for_confirm)
    await message.answer(BROADCAST_PREVIEW_TEXT, reply_markup=broadcast_confirm_kb)

@dp.message(AdminBroadcast.waiting_for_content)
async def broadcast_capture_wrong(message: Message):
    await message.answer("Отправьте текст или фото с подписью.")

@dp.message(AdminBroadcast.waiting_for_confirm, F.text == BROADCAST_CANCEL_BUTTON)
async def broadcast_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(BROADCAST_CANCELLED_TEXT, reply_markup=admin_kb)

@dp.message(AdminBroadcast.waiting_for_confirm, F.text == BROADCAST_SEND_BUTTON)
async def broadcast_send(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        await message.answer(ADMIN_ONLY_TEXT)
        return
    data = await state.get_data()
    users = get_all_user_ids()
    ok = 0
    bad = 0
    for user_id in users:
        try:
            if data.get("broadcast_type") == "photo":
                await bot.send_photo(user_id, data["file_id"], caption=data.get("caption", ""))
            else:
                await bot.send_message(user_id, data.get("text", ""))
            ok += 1
        except Exception:
            bad += 1
    await state.clear()
    await message.answer(BROADCAST_DONE_TEXT.format(ok=ok, bad=bad), reply_markup=admin_kb)

@dp.message(AdminBroadcast.waiting_for_confirm)
async def broadcast_wrong_confirm(message: Message):
    await message.answer("Используйте кнопки ниже.", reply_markup=broadcast_confirm_kb)

@dp.message(F.text == BACK_BUTTON)
async def go_back(message: Message, state: FSMContext):
    await state.clear()
    if is_admin(message.from_user.id):
        await message.answer("Возврат в админ меню.", reply_markup=admin_kb)
        return
    user = get_user_by_tg_id(message.from_user.id)
    if user:
        await message.answer("Меню участника.", reply_markup=participant_kb)
    else:
        await message.answer("Главное меню.", reply_markup=start_kb(is_admin(message.from_user.id)))

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
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
