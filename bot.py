import asyncio
import logging
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
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove

# =========================
# НАСТРОЙКИ
# =========================
BOT_TOKEN = "8428046405:AAFISFm6Mm3ZStV93DsyxhZzc9HwMN6n63c"
ADMIN_IDS = {922603146}
RESET_PASSWORD = "12345678"
CONSULTATION_TEXT = "А Вы готовы к знакомству с Сочи по-настоящему? Тогда ждём Вас на консультацию?"
MENU_DESCRIPTION_TEXT = "Голод - враг искусства! Перейдем к меню на ужин? Вы только посмотрите, какое обилие угощений Вас ждет впереди!"
MEETING_LINK = "https://t.me/bulygina_diana"
MENU_IMAGE_PATH = "assets/menu.jpg"
DB_PATH = "database.db"
EXPORTS_DIR = Path("exports")

# =========================
# ТЕКСТЫ И КНОПКИ
# =========================
START_BUTTON = "Старт"
MEETING_BUTTON = "Прийти на встречу"
BACK_BUTTON = "Назад"

CONSENT_ACCEPT_BUTTON = "Согласен(а)"
CONSENT_DECLINE_BUTTON = "Не согласен(а)"
SEND_PHONE_BUTTON = "Отправить номер телефона"

ADMIN_MENU_BUTTON = "Админ меню"
EXPORT_TODAY_BUTTON = "Выгрузка: сегодня"
EXPORT_WEEK_BUTTON = "Выгрузка: неделя"
EXPORT_MONTH_BUTTON = "Выгрузка: месяц"
RESET_DB_BUTTON = "Ресет базы"
BROADCAST_BUTTON = "Рассылка"
BROADCAST_CONFIRM_BUTTON = "Отправить всем"
BROADCAST_CANCEL_BUTTON = "Отменить рассылку"

START_GREETING = (
    "Добрый вечер, уважаемый пассажир эксклюзивного экспресса «Бархатный путь»! "
    "Совсем скоро начнется наше путешествие, а пока - давайте знакомиться"
)

NAME_TEXT_TEMPLATE = (
    '{name}, ох, сколько Вас сегодня ждет впереди! '
    'Вечер наполнен изысканными угощениями, подарками, сюрпризами, танцами, музыкой '
    'и даже… мистикой! А для того, чтобы подарок нашел своего адресата, важно получить контакт.'
)

CONSENT_TEXT = (
    "Пожалуйста, подтвердите согласие на обработку персональных данных. "
    "После этого отправьте номер телефона."
)

ALREADY_REGISTERED_TEMPLATE = (
    "Вы уже зарегистрированы. Ваш уникальный номер участника: <b>№{number}</b>."
)

INFO_TEMPLATE = (
    "<b>Информация о вас</b>\n"
    "Имя: {name}\n"
    "Телефон: {phone}\n"
    "Номер участника: №{number}\n"
    "Дата регистрации: {created_at}"
)


# =========================
# СОСТОЯНИЯ
# =========================
class Registration(StatesGroup):
    waiting_for_name = State()
    waiting_for_consent = State()
    waiting_for_phone = State()


class AdminReset(StatesGroup):
    waiting_for_password = State()


class AdminBroadcast(StatesGroup):
    waiting_for_content = State()
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
        row = conn.execute("SELECT * FROM participants WHERE tg_id = ?", (tg_id,)).fetchone()
        return row



def get_user_by_phone(phone: str):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM participants WHERE phone = ?", (phone,)).fetchone()
        return row



def get_all_user_ids() -> list[int]:
    with get_connection() as conn:
        rows = conn.execute("SELECT tg_id FROM participants ORDER BY participant_number ASC").fetchall()
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
        conn.execute(
            """
            INSERT INTO participants (tg_id, username, full_name, phone, participant_number, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (tg_id, username, full_name, phone, number, created_at),
        )
        conn.commit()
    return number



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
        rows = conn.execute(
            "SELECT * FROM participants WHERE created_at >= ? ORDER BY participant_number ASC",
            (start_dt,),
        ).fetchall()
        return rows



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

    data = []
    for row in rows:
        data.append(
            {
                "ID": row["id"],
                "Telegram ID": row["tg_id"],
                "Username": row["username"] or "",
                "Имя": row["full_name"],
                "Телефон": row["phone"],
                "Номер участника": row["participant_number"],
                "Дата регистрации": row["created_at"],
            }
        )

    df = pd.DataFrame(data)
    df.to_excel(file_path, index=False)
    return file_path


# =========================
# КНОПКИ
# =========================
def start_kb(is_admin_user: bool = False) -> ReplyKeyboardMarkup:
    buttons = [[KeyboardButton(text=START_BUTTON)]]
    if is_admin_user:
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

meeting_kb = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text=MEETING_BUTTON, url=MEETING_LINK)]]
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

broadcast_confirm_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BROADCAST_CONFIRM_BUTTON)],
        [KeyboardButton(text=BROADCAST_CANCEL_BUTTON)],
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


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = get_user_by_tg_id(message.from_user.id)
    if user:
        await message.answer(
            ALREADY_REGISTERED_TEMPLATE.format(number=user["participant_number"]),
            reply_markup=meeting_kb,
        )
        return

    await message.answer("Нажмите кнопку ниже, чтобы начать.", reply_markup=start_kb(is_admin(message.from_user.id)))


@dp.message(F.text == START_BUTTON)
async def start_registration(message: Message, state: FSMContext):
    user = get_user_by_tg_id(message.from_user.id)
    if user:
        await message.answer(
            ALREADY_REGISTERED_TEMPLATE.format(number=user["participant_number"]),
            reply_markup=meeting_kb,
        )
        return

    await message.answer(START_GREETING, reply_markup=ReplyKeyboardRemove())
    await message.answer("Введите ваше имя:")
    await state.set_state(Registration.waiting_for_name)


@dp.message(Registration.waiting_for_name)
async def save_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if not name:
        await message.answer("Пожалуйста, введите имя текстом.")
        return

    await state.update_data(full_name=name)
    await message.answer(NAME_TEXT_TEMPLATE.format(name=name))
    await message.answer(CONSENT_TEXT, reply_markup=consent_kb)
    await state.set_state(Registration.waiting_for_consent)


@dp.message(Registration.waiting_for_consent, F.text == CONSENT_DECLINE_BUTTON)
async def decline_consent(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Без согласия на обработку персональных данных регистрация невозможна.",
        reply_markup=start_kb(is_admin(message.from_user.id)),
    )


@dp.message(Registration.waiting_for_consent, F.text == CONSENT_ACCEPT_BUTTON)
async def accept_consent(message: Message, state: FSMContext):
    await state.update_data(consent_given=True)
    await state.set_state(Registration.waiting_for_phone)
    await message.answer(
        "Пожалуйста, нажмите кнопку ниже и отправьте номер телефона.",
        reply_markup=phone_kb,
    )


@dp.message(Registration.waiting_for_consent)
async def wrong_consent(message: Message):
    await message.answer("Пожалуйста, выберите один из вариантов согласия кнопкой ниже.")


@dp.message(Registration.waiting_for_phone)
async def save_phone(message: Message, state: FSMContext):
    if not message.contact:
        await message.answer("Пожалуйста, используйте кнопку «Отправить номер телефона».")
        return

    contact = message.contact
    if contact.user_id and contact.user_id != message.from_user.id:
        await message.answer("Пожалуйста, отправьте свой номер телефона, а не чужой.")
        return

    existing_by_user = get_user_by_tg_id(message.from_user.id)
    if existing_by_user:
        await state.clear()
        await message.answer(
            ALREADY_REGISTERED_TEMPLATE.format(number=existing_by_user["participant_number"]),
            reply_markup=meeting_kb,
        )
        return

    phone = normalize_phone(contact.phone_number)
    existing_by_phone = get_user_by_phone(phone)
    if existing_by_phone:
        await message.answer(
            "Этот номер телефона уже есть в базе. Один человек не может иметь два номера.",
            reply_markup=start_kb(is_admin(message.from_user.id)),
        )
        await state.clear()
        return

    data = await state.get_data()
    full_name = data.get("full_name", "Без имени")
    create_user(
        tg_id=message.from_user.id,
        username=message.from_user.username,
        full_name=full_name,
        phone=phone,
    )

    await state.clear()
    path = Path(MENU_IMAGE_PATH)
    if path.exists():
        await message.answer_photo(FSInputFile(path), caption=MENU_DESCRIPTION_TEXT)
    else:
        await message.answer("Файл меню не найден. Положите картинку по пути assets/menu.jpg")

    await message.answer(CONSULTATION_TEXT, reply_markup=meeting_kb)


@dp.message(F.text == BACK_BUTTON)
async def go_back(message: Message, state: FSMContext):
    await state.clear()
    user = get_user_by_tg_id(message.from_user.id)
    if user:
        await message.answer(CONSULTATION_TEXT, reply_markup=meeting_kb)
    else:
        await message.answer("Главное меню.", reply_markup=start_kb(is_admin(message.from_user.id)))


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
    await message.answer("Введите пароль для сброса базы.")
    await state.set_state(AdminReset.waiting_for_password)


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

    await state.set_state(AdminBroadcast.waiting_for_content)
    await message.answer(
        "Отправьте сообщение для рассылки.\n\n"
        "Можно отправить:\n"
        "- обычный текст\n"
        "- фото с подписью\n\n"
        "После этого я покажу предпросмотр и спрошу подтверждение.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=BROADCAST_CANCEL_BUTTON)]],
            resize_keyboard=True,
        ),
    )


@dp.message(AdminBroadcast.waiting_for_content, F.text == BROADCAST_CANCEL_BUTTON)
async def broadcast_cancel_from_input(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Рассылка отменена.", reply_markup=admin_kb)


@dp.message(AdminBroadcast.waiting_for_content)
async def broadcast_preview(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        await message.answer("Эта команда доступна только администратору.")
        return

    data_to_store: dict[str, str] = {}

    if message.photo:
        photo = message.photo[-1]
        data_to_store = {
            "type": "photo",
            "photo_file_id": photo.file_id,
            "caption": message.caption or "",
        }
        await message.answer("Предпросмотр рассылки:")
        await message.answer_photo(photo.file_id, caption=message.caption or "")

    elif message.text:
        text = message.text.strip()
        if not text:
            await message.answer("Пустое сообщение. Отправьте текст или фото с подписью.")
            return
        data_to_store = {
            "type": "text",
            "text": text,
        }
        await message.answer("Предпросмотр рассылки:")
        await message.answer(text)

    else:
        await message.answer("Поддерживается только текст или фото с подписью.")
        return

    await state.update_data(**data_to_store)
    await state.set_state(AdminBroadcast.waiting_for_confirmation)
    await message.answer(
        "Подтвердить рассылку?",
        reply_markup=broadcast_confirm_kb,
    )


@dp.message(AdminBroadcast.waiting_for_confirmation, F.text == BROADCAST_CANCEL_BUTTON)
async def broadcast_cancel_from_confirm(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Рассылка отменена.", reply_markup=admin_kb)


@dp.message(AdminBroadcast.waiting_for_confirmation, F.text == BROADCAST_CONFIRM_BUTTON)
async def broadcast_send(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        await message.answer("Эта команда доступна только администратору.")
        return

    user_ids = get_all_user_ids()
    if not user_ids:
        await state.clear()
        await message.answer("В базе нет зарегистрированных участников.", reply_markup=admin_kb)
        return

    data = await state.get_data()
    send_type = data.get("type")

    success_count = 0
    failed_count = 0

    for user_id in user_ids:
        try:
            if send_type == "photo":
                await bot.send_photo(
                    chat_id=user_id,
                    photo=data["photo_file_id"],
                    caption=data.get("caption", ""),
                )
            else:
                await bot.send_message(
                    chat_id=user_id,
                    text=data.get("text", ""),
                )
            success_count += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed_count += 1

    await state.clear()
    await message.answer(
        "Рассылка завершена.\n"
        f"Успешно отправлено: {success_count}\n"
        f"Не доставлено: {failed_count}",
        reply_markup=admin_kb,
    )


@dp.message(AdminBroadcast.waiting_for_confirmation)
async def broadcast_wrong_confirmation(message: Message):
    await message.answer(
        "Используйте кнопки ниже: отправить всем или отменить рассылку.",
        reply_markup=broadcast_confirm_kb,
    )


@dp.message()
async def fallback(message: Message):
    user = get_user_by_tg_id(message.from_user.id)
    if user:
        await message.answer(CONSULTATION_TEXT, reply_markup=meeting_kb)
    else:
        await message.answer("Нажмите /start для начала работы.", reply_markup=start_kb(is_admin(message.from_user.id)))


async def main():
    init_db()
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
