import telebot
import sqlite3
from datetime import datetime
import schedule
import time
import threading
import random
from telebot.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)

bot = telebot.TeleBot("8094395413:AAGlIanHK3Ji99-N90Nkinvqk4ikRJlkeQg")  # Замените на ваш токен

# region Database Functions
def init_db():
    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, name TEXT, motivation_time TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS habits
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  habit_name TEXT,
                  created_date TEXT,
                  count INTEGER DEFAULT 0,
                  UNIQUE(user_id, habit_name))''')
    c.execute('''CREATE TABLE IF NOT EXISTS reminders
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  habit_id INTEGER,
                  reminder_time TEXT)''')
    conn.commit()
    conn.close()

def add_user(user_id, name, motivation_time=None):
    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, name, motivation_time) VALUES (?, ?, ?)", (user_id, name, motivation_time))
    conn.commit()
    conn.close()

def add_habit(user_id, habit_name):
    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        c.execute("INSERT INTO habits (user_id, habit_name, created_date) VALUES (?, ?, ?)",
                  (user_id, habit_name, created_date))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user_habits(user_id):
    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    c.execute("SELECT id, habit_name FROM habits WHERE user_id=?", (user_id,))
    habits = c.fetchall()
    conn.close()
    return habits

def update_habit_count(habit_id):
    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    c.execute("UPDATE habits SET count = count + 1 WHERE id=?", (habit_id,))
    conn.commit()
    conn.close()

def get_stats(user_id):
    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    c.execute("SELECT habit_name, count FROM habits WHERE user_id=?", (user_id,))
    stats = c.fetchall()
    conn.close()
    return stats

def delete_habit(habit_id):
    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    c.execute("DELETE FROM habits WHERE id=?", (habit_id,))
    conn.commit()
    conn.close()

def update_habit_name(habit_id, new_name):
    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    c.execute("UPDATE habits SET habit_name=? WHERE id=?", (new_name, habit_id))
    conn.commit()
    conn.close()

def add_reminder(user_id, habit_id, reminder_time):
    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    c.execute("INSERT INTO reminders (user_id, habit_id, reminder_time) VALUES (?, ?, ?)",
              (user_id, habit_id, reminder_time))
    conn.commit()
    conn.close()

def get_user_reminders(user_id):
    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    c.execute("SELECT habit_id, reminder_time FROM reminders WHERE user_id=?", (user_id,))
    reminders = c.fetchall()
    conn.close()
    return reminders

def send_reminder(user_id, habit_name):
    bot.send_message(user_id, f"⏰ Напоминание: Пора выполнить привычку '{habit_name}'!")

def schedule_reminder(user_id, habit_id, reminder_time):
    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    c.execute("SELECT habit_name FROM habits WHERE id=?", (habit_id,))
    habit_name = c.fetchone()[0]
    conn.close()

    # Запланировать напоминание
    schedule.every().day.at(reminder_time).do(send_reminder, user_id, habit_name)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

# Motivation Messages
def send_motivation(user_id):
    motivational_quotes = [
        "Вы можете сделать все, что захотите!",
        "Каждый день - это новый шанс.",
        "Не останавливайтесь, пока не достигнете своей цели!",
        "Ваши усилия не пропадут даром.",
        "Сделайте сегодня то, что другие не хотят, и завтра вы сможете сделать то, что другие не могут."
    ]
    quote = random.choice(motivational_quotes)
    bot.send_message(user_id, quote)

def schedule_motivation(user_id, motivation_time):
    schedule.every().day.at(motivation_time).do(send_motivation, user_id)

# endregion

# region Menu & Handlers
def create_menu():
    menu = ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add(KeyboardButton("Добавить привычку ➕"))
    menu.add(KeyboardButton("Отметить выполнение ✅"))
    menu.add(KeyboardButton("Статистика 📊"))
    menu.add(KeyboardButton("Удалить привычку ❌"))
    menu.add(KeyboardButton("Редактировать привычку ✏️"))
    menu.add(KeyboardButton("Установить напоминание ⏰"))
    menu.add(KeyboardButton("Установить мотивационное сообщение ⏰"))  # Добавлено
    return menu

@bot.message_handler(commands=['start'])
def start(message):
    user = message.from_user
    add_user(user.id, user.first_name)
    bot.send_message(
        message.chat.id,
        f"👋 Привет {user.first_name}! Я помогу тебе отслеживать привычки!\n\n"
        "Используй кнопки ниже для управления:",
        reply_markup=create_menu()
    )

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    if message.text == "Добавить привычку ➕":
        add_habit_start(message)
    elif message.text == "Отметить выполнение ✅":
        track_habit(message)
    elif message.text == "Статистика 📊":
        show_stats(message)
    elif message.text == "Удалить привычку ❌":
        delete_habit_start(message)
    elif message.text == "Редактировать привычку ✏️":
        edit_habit_start(message)
    elif message.text == "Установить напоминание ⏰":
        set_reminder_start(message)
    elif message.text == "Установить мотивационное сообщение ⏰":  # Обработчик установки мотивационного сообщения
        set_motivation_start(message)
    elif message.text == "Назад":
        bot.send_message(message.chat.id, "Команда отменена.", reply_markup=create_menu())
    else:
        bot.send_message(message.chat.id, "⚠️ Используй кнопки ниже ⬇️", reply_markup=create_menu())

# region Habit Management
@bot.message_handler(commands=['add_habit'])
def add_habit_start(message):
    msg = bot.send_message(message.chat.id, "➕ Введите название новой привычки:", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, add_habit_end)

def add_habit_end(message):
    user_id = message.from_user.id
    habit_name = message.text.strip()

    if len(habit_name) < 2:
        bot.send_message(message.chat.id, "❌ Название должно быть не короче 2 символов!", reply_markup=create_menu())
        return

    if add_habit(user_id, habit_name):
        bot.send_message(message.chat.id, f"✅ Привычка '{habit_name}' успешно добавлена!", reply_markup=create_menu())
    else:
        bot.send_message(message.chat.id, f"❌ Привычка '{habit_name}' уже существует!", reply_markup=create_menu())

@bot.message_handler(commands=['track_habit'])
def track_habit(message):
    user_id = message.from_user.id
    habits = get_user_habits(user_id)

    if not habits:
        bot.send_message(message.chat.id, "❌ У вас нет добавленных привычек.", reply_markup=create_menu())
        return

    keyboard = InlineKeyboardMarkup()
    for habit in habits:
        habit_id, habit_name = habit
        keyboard.add(InlineKeyboardButton(
            text=f"✅ {habit_name}",
            callback_data=f"track_{habit_id}"
        ))
    keyboard.add(InlineKeyboardButton("↩️ Назад", callback_data="back_to_menu"))

    bot.send_message(message.chat.id, "📅 Выберите привычку для отметки:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("track_"))
def track_habit_complete(call):
    habit_id = call.data.split("_")[1]

    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    c.execute("SELECT habit_name FROM habits WHERE id=?", (habit_id,))
    habit_name = c.fetchone()[0]
    conn.close()

    update_habit_count(habit_id)

    bot.answer_callback_query(call.id, f"✅ Привычка '{habit_name}' отмечена!")
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"🎉 Привычка '{habit_name}' успешно отмечена!"
    )
    bot.send_message(call.message.chat.id, "🏠 Возвращаемся в главное меню:", reply_markup=create_menu())

@bot.message_handler(commands=['stats'])
def show_stats(message):
    user_id = message.from_user.id
    stats = get_stats(user_id)

    if not stats:
        bot.send_message(message.chat.id, "📊 Статистика пока пуста.", reply_markup=create_menu())
        return

    message_text = "📊 Ваша статистика:\n\n" + "\n".join(
        [f"• {habit[0]}: {habit[1]} раз" for habit in stats]
    )
    bot.send_message(message.chat.id, message_text, reply_markup=create_menu())

# region Delete Habit
def delete_habit_start(message):
    user_id = message.from_user.id
    habits = get_user_habits(user_id)

    if not habits:
        bot.send_message(message.chat.id, "❌ У вас нет добавленных привычек.", reply_markup=create_menu())
        return

    keyboard = InlineKeyboardMarkup()
    for habit in habits:
        habit_id, habit_name = habit
        keyboard.add(InlineKeyboardButton(
            text=f"❌ {habit_name}",
            callback_data=f"delete_{habit_id}"
        ))
    keyboard.add(InlineKeyboardButton("↩️ Назад", callback_data="back_to_menu"))

    bot.send_message(message.chat.id, "🗑️ Выберите привычку для удаления:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_"))
def delete_habit_complete(call):
    habit_id = call.data.split("_")[1]

    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    c.execute("SELECT habit_name FROM habits WHERE id=?", (habit_id,))
    habit_name = c.fetchone()[0]
    conn.close()

    delete_habit(habit_id)

    bot.answer_callback_query(call.id, f"❌ Привычка '{habit_name}' удалена!")
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"🗑️ Привычка '{habit_name}' успешно удалена!"
    )
    bot.send_message(call.message.chat.id, "🏠 Возвращаемся в главное меню:", reply_markup=create_menu())

# region Edit Habit
def edit_habit_start(message):
    user_id = message.from_user.id
    habits = get_user_habits(user_id)

    if not habits:
        bot.send_message(message.chat.id, "❌ У вас нет добавленных привычек.", reply_markup=create_menu())
        return

    keyboard = InlineKeyboardMarkup()
    for habit in habits:
        habit_id, habit_name = habit
        keyboard.add(InlineKeyboardButton(
            text=f"✏️ {habit_name}",
            callback_data=f"edit_{habit_id}"
        ))
    keyboard.add(InlineKeyboardButton("↩️ Назад", callback_data="back_to_menu"))

    bot.send_message(message.chat.id, "✏️ Выберите привычку для редактирования:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_"))
def edit_habit_complete(call):
    habit_id = call.data.split("_")[1]

    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    c.execute("SELECT habit_name FROM habits WHERE id=?", (habit_id,))
    habit_name = c.fetchone()[0]
    conn.close()

    msg = bot.send_message(call.message.chat.id, f"🔄 Введите новое название для привычки '{habit_name}':", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, lambda message, h_id=habit_id: update_habit_end(message, h_id))

def update_habit_end(message, habit_id):
    new_name = message.text.strip()

    if len(new_name) < 2:
        bot.send_message(message.chat.id, "❌ Название должно быть не короче 2 символов!", reply_markup=create_menu())
        return

    update_habit_name(habit_id, new_name)
    bot.send_message(message.chat.id, f"✅ Название привычки успешно обновлено на '{new_name}'!", reply_markup=create_menu())

# endregion

# region Reminder Management
def set_reminder_start(message):
    user_id = message.from_user.id
    habits = get_user_habits(user_id)

    if not habits:
        bot.send_message(message.chat.id, "❌ У вас нет добавленных привычек.", reply_markup=create_menu())
        return

    keyboard = InlineKeyboardMarkup()
    for habit in habits:
        habit_id, habit_name = habit
        keyboard.add(InlineKeyboardButton(
            text=f"⏰ {habit_name}",
            callback_data=f"set_reminder_{habit_id}"
        ))
    keyboard.add(InlineKeyboardButton("↩️ Назад", callback_data="back_to_menu"))

    bot.send_message(message.chat.id, "📅 Выберите привычку для установки напоминания:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_reminder_"))
def set_reminder_complete(call):
    habit_id = call.data.split("_")[2]
    msg = bot.send_message(call.message.chat.id, "🕒 Введите время для напоминания (в формате HH:MM):", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, lambda message, h_id=habit_id: set_reminder_time(message, h_id))

def set_reminder_time(message, habit_id):
    user_id = message.from_user.id
    reminder_time = message.text.strip()

    try:
        # Проверка корректности времени
        datetime.strptime(reminder_time, "%H:%M")
        add_reminder(user_id, habit_id, reminder_time)
        schedule_reminder(user_id, habit_id, reminder_time)
        bot.send_message(message.chat.id, f"✅ Напоминание установлено на {reminder_time}!", reply_markup=create_menu())
    except ValueError:
        bot.send_message(message.chat.id, "❌ Неверный формат времени! Используйте HH:MM.", reply_markup=create_menu())

# endregion

# region Motivation Management
def set_motivation_start(message):
    user_id = message.from_user.id
    msg = bot.send_message(message.chat.id, "🕒 Введите время для получения мотивационных сообщений (в формате HH:MM):", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, lambda msg: set_motivation_time(msg, user_id))

def set_motivation_time(message, user_id):
    motivation_time = message.text.strip()

    try:
        # Проверка корректности времени
        datetime.strptime(motivation_time, "%H:%M")
        add_user(user_id, message.from_user.first_name, motivation_time)
        schedule_motivation(user_id, motivation_time)
        bot.send_message(message.chat.id, f"✅ Мотивационные сообщения будут отправляться в {motivation_time}!", reply_markup=create_menu())
    except ValueError:
        bot.send_message(message.chat.id, "❌ Неверный формат времени! Используйте HH:MM.", reply_markup=create_menu())

# endregion

# region Back to Menu
@bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
def back_to_menu(call):
    bot.send_message(
        chat_id=call.message.chat.id,
        text="🏠 Возвращаемся в главное меню:",
        reply_markup=create_menu()
    )
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)

# endregion

if __name__ == "__main__":
    init_db()
    threading.Thread(target=run_scheduler).start()  # Запуск планировщика в отдельном потоке
    print("🚀 Бот успешно запущен!")
    bot.polling(none_stop=True)
