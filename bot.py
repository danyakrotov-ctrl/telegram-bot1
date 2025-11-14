import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler, CallbackQueryHandler
)

# --- Логирование ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Токен ---
TOKEN = "8226017309:AAE3ZTsQKrJ7Dxlqe62IPbMS8QdPhyt1xuw"

# --- Состояния ---
GET_PHONE_NUMBER, ADD_RECORD, FIND_BY_STATE_NUMBER, ENTER_STATE_NUMBER, ENTER_DATE_TIME, ENTER_DESCRIPTION, ENTER_PHOTO, VIEW_RECORDS = range(8)

# --- Подключение к БД ---
conn = sqlite3.connect('db.sqlite3', check_same_thread=False)
cursor = conn.cursor()

# --- Таблица сообщений ---
cursor.execute('''
CREATE TABLE IF NOT EXISTS telegram_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_phone TEXT,
    state_number TEXT,
    date_time TEXT,
    description TEXT,
    photo_file_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')
conn.commit()

# --- Вспомогательные функции ---
def get_user_name(phone_number):
    cursor.execute("SELECT name FROM users WHERE number = ?", (phone_number,))
    result = cursor.fetchone()
    return result[0] if result else None

def normalize_phone_number(phone_number):
    cleaned_phone = ''.join(filter(str.isdigit, phone_number))
    if len(cleaned_phone) >= 11 and cleaned_phone.startswith('8'):
        normalized_phone = '+' + cleaned_phone.replace('8', '7', 1)
    else:
        normalized_phone = '+' + cleaned_phone
    return normalized_phone

def normalize_state_number(state_number):
    return state_number.strip().upper()

def check_phone_in_db(phone_number):
    normalized_phone = normalize_phone_number(phone_number)
    cursor.execute("SELECT COUNT(*) FROM users WHERE number = ?", (normalized_phone,))
    count = cursor.fetchone()[0]
    return count > 0

def get_equipment_info(state_number):
    cursor.execute("SELECT state_number, brand, model, year FROM equipment WHERE state_number = ?", (state_number,))
    return cursor.fetchone()

def format_record(record):
    state_number, date_time, description, photo_file_id = record
    msg = f"Гос. номер: {state_number}\nДата/Время: {date_time}\nОписание: {description}"
    return msg, photo_file_id

# --- Главное меню ---
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Добавить запись о работе", callback_data="add_record")],
        [InlineKeyboardButton("📊 Мои последние записи", callback_data="last_records")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")],
        [InlineKeyboardButton("🔓 Выйти из учетной записи", callback_data="logout")]
    ])

# --- Обработчики ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Войти в систему", callback_data="start")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Привет! Чтобы войти в систему, отправьте ваш номер телефона.",
        reply_markup=reply_markup
    )
    return GET_PHONE_NUMBER

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Отправьте ваш номер телефона для продолжения.")
    return GET_PHONE_NUMBER

async def process_phone_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    entered_phone = update.message.text.strip()
    normalized_phone = normalize_phone_number(entered_phone)

    if check_phone_in_db(normalized_phone):
        user_name = get_user_name(normalized_phone)
        if user_name:
            context.user_data["user_phone"] = normalized_phone
            await update.message.reply_text(f"Здравствуйте, {user_name}!", reply_markup=main_menu_keyboard())
            return ADD_RECORD
        else:
            await update.message.reply_text("Ошибка авторизации. Не удалось найти ваше имя в базе.")
    else:
        await update.message.reply_text("Ошибка авторизации. Ваш номер телефона не найден в базе данных.")
    return GET_PHONE_NUMBER

async def add_record_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Найти по гос. номеру", callback_data="find_by_state_number")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    await query.edit_message_text("Выберите действие:", reply_markup=InlineKeyboardMarkup(keyboard))
    return FIND_BY_STATE_NUMBER

async def find_by_state_number_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
    await query.edit_message_text("Введите государственный номер техники:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ENTER_STATE_NUMBER

async def process_state_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    entered_state_number = normalize_state_number(update.message.text)
    context.user_data["state_number"] = entered_state_number

    equipment_info = get_equipment_info(entered_state_number)
    if equipment_info:
        state_number, brand, model, year = equipment_info
        keyboard = [
            [InlineKeyboardButton("🕒 Ввести дату и время", callback_data="enter_date_time")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        await update.message.reply_text(
            f"Информация о технике:\nГос. номер: {state_number}\nМарка: {brand}\nМодель: {model}\nГод выпуска: {year}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ENTER_DATE_TIME
    else:
        await update.message.reply_text("Техника не найдена. Введите правильный гос. номер.")
        return ENTER_STATE_NUMBER

async def enter_date_time_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
    await query.edit_message_text("Введите дату и время (например: 11.11.2025 15:30):", reply_markup=InlineKeyboardMarkup(keyboard))
    return ENTER_DATE_TIME

async def process_date_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["date_time"] = update.message.text.strip()
    await update.message.reply_text("Введите описание работы:\n(Вы можете в любой момент нажать 🏠 Главное меню)")
    return ENTER_DESCRIPTION

async def process_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["description"] = update.message.text.strip()
    await update.message.reply_text("Теперь отправьте фото (одно изображение):\n(Вы можете в любой момент нажать 🏠 Главное меню)")
    return ENTER_PHOTO

async def process_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file_id = photo.file_id

    user_phone = context.user_data.get("user_phone")
    state_number = context.user_data.get("state_number")
    date_time = context.user_data.get("date_time")
    description = context.user_data.get("description")

    cursor.execute(
        "INSERT INTO telegram_messages (user_phone, state_number, date_time, description, photo_file_id) VALUES (?, ?, ?, ?, ?)",
        (user_phone, state_number, date_time, description, file_id)
    )
    conn.commit()

    await update.message.reply_text("✅ Запись успешно сохранена!", reply_markup=main_menu_keyboard())
    return ADD_RECORD

async def last_records_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_phone = context.user_data.get("user_phone")
    if not user_phone:
        await query.edit_message_text("Ошибка: номер пользователя не найден.")
        return GET_PHONE_NUMBER

    cursor.execute(
        "SELECT state_number, date_time, description, photo_file_id FROM telegram_messages WHERE user_phone = ? ORDER BY created_at DESC",
        (user_phone,)
    )
    records = cursor.fetchall()
    if not records:
        await query.edit_message_text("У вас пока нет записей.", reply_markup=main_menu_keyboard())
        return ADD_RECORD

    context.user_data["records"] = records
    context.user_data["record_index"] = 0
    await query.message.delete()
    return await send_record(query.message, context)

async def send_record(message, context):
    index = context.user_data["record_index"]
    record = context.user_data["records"][index]
    state_number, date_time, description, photo_file_id = record
    msg_text = f"Гос. номер: {state_number}\nДата/Время: {date_time}\nОписание: {description}"

    keyboard_buttons = []
    if index > 0:
        keyboard_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data="prev_record"))
    if index < len(context.user_data["records"]) - 1:
        keyboard_buttons.append(InlineKeyboardButton("➡️ Далее", callback_data="next_record"))
    keyboard_buttons.append(InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))

    reply_markup = InlineKeyboardMarkup([keyboard_buttons])
    if photo_file_id:
        await message.reply_photo(photo=photo_file_id, caption=msg_text, reply_markup=reply_markup)
    else:
        await message.reply_text(msg_text, reply_markup=reply_markup)
    return VIEW_RECORDS

async def navigate_records(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "next_record":
        context.user_data["record_index"] += 1
    elif query.data == "prev_record":
        context.user_data["record_index"] -= 1
    await query.message.delete()
    return await send_record(query.message, context)

async def go_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_phone = context.user_data.get("user_phone")
    if not user_phone:
        await query.message.reply_text("Ошибка: номер пользователя не найден.")
        return GET_PHONE_NUMBER
    user_name = get_user_name(user_phone)
    await query.message.delete()
    await query.message.chat.send_message(f"Главное меню, {user_name}:", reply_markup=main_menu_keyboard())
    return ADD_RECORD

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.message.reply_text(
        "Вы успешно вышли из учетной записи.\nЧтобы войти снова, введите ваш номер телефона."
    )
    return GET_PHONE_NUMBER

async def help_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    help_text = (
        "ℹ️ *Помощь*\n\n"
        "Этот бот позволяет:\n"
        "• Добавлять записи о работе техники\n"
        "• Просматривать последние записи\n\n"
        "Чтобы добавить запись:\n"
        "1️⃣ Войдите в систему с вашим номером телефона\n"
        "2️⃣ Выберите '📝 Добавить запись о работе'\n"
        "3️⃣ Укажите гос. номер, дату/время, описание и фото\n\n"
        "❗ Изменение или удаление записей возможно только через администратора.\n\n"
        "📞 Для любых вопросов свяжитесь с менеджером: [@krthikf](https://t.me/krthikf)\n\n"
        "Нажмите 🏠 Главное меню, чтобы вернуться."
    )
    keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
    await query.edit_message_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return ADD_RECORD

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Действие отменено.", reply_markup=main_menu_keyboard())
    return ADD_RECORD

# --- Запуск приложения ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            GET_PHONE_NUMBER: [
                MessageHandler(filters.TEXT & (~filters.COMMAND), process_phone_number),
                CallbackQueryHandler(button_callback, pattern="^start$"),
                CallbackQueryHandler(help_button, pattern="^help$")
            ],
            ADD_RECORD: [
                CallbackQueryHandler(add_record_button, pattern="^add_record$"),
                CallbackQueryHandler(last_records_button, pattern="^last_records$"),
                CallbackQueryHandler(help_button, pattern="^help$"),
                CallbackQueryHandler(go_to_main_menu, pattern="^main_menu$"),
                CallbackQueryHandler(logout, pattern="^logout$")  # Кнопка выхода
            ],
            FIND_BY_STATE_NUMBER: [
                CallbackQueryHandler(find_by_state_number_button, pattern="^find_by_state_number$"),
                CallbackQueryHandler(go_to_main_menu, pattern="^main_menu$")
            ],
            ENTER_STATE_NUMBER: [
                MessageHandler(filters.TEXT & (~filters.COMMAND), process_state_number),
                CallbackQueryHandler(go_to_main_menu, pattern="^main_menu$")
            ],
            ENTER_DATE_TIME: [
                CallbackQueryHandler(enter_date_time_button, pattern="^enter_date_time$"),
                MessageHandler(filters.TEXT & (~filters.COMMAND), process_date_time),
                CallbackQueryHandler(go_to_main_menu, pattern="^main_menu$")
            ],
            ENTER_DESCRIPTION: [
                MessageHandler(filters.TEXT & (~filters.COMMAND), process_description)
            ],
            ENTER_PHOTO: [
                MessageHandler(filters.PHOTO, process_photo)
            ],
            VIEW_RECORDS: [
                CallbackQueryHandler(navigate_records, pattern="^(next_record|prev_record)$"),
                CallbackQueryHandler(go_to_main_menu, pattern="^main_menu$")
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conversation_handler)
    app.run_polling()


