import telebot
import sqlite3
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, \
    ReplyKeyboardRemove

# Инициализация бота
bot = telebot.TeleBot("8094395413:AAGlIanHK3Ji99-N90Nkinvqk4ikRJlkeQg")


# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS habits
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  habit_name TEXT UNIQUE,
                  created_date TEXT,
                  count INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()


# Добавление пользователя
def add_user(user_id, name):
    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, name) VALUES (?, ?)", (user_id, name))
    conn.commit()
    conn.close()


# Добавление привычки
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
        return False  # Если привычка уже существует
    finally:
        conn.close()


# Получение привычек пользователя
def get_user_habits(user_id):
    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    c.execute("SELECT id, habit_name FROM habits WHERE user_id=?", (user_id,))
    habits = c.fetchall()
    conn.close()
    return habits


# Обновление счетчика привычки
def update_habit_count(habit_id):
    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    c.execute("UPDATE habits SET count = count + 1 WHERE id=?", (habit_id,))
    conn.commit()
    conn.close()


# Получение статистики
def get_stats(user_id):
    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    c.execute("SELECT habit_name, count FROM habits WHERE user_id=?", (user_id,))
    stats = c.fetchall()
    conn.close()
    return stats


# Создание меню
def create_menu():
    menu = ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add(KeyboardButton("Добавить привычку ➕"))
    menu.add(KeyboardButton("Отметить выполнение ✅"))
    menu.add(KeyboardButton("Статистика 📊"))
    return menu


# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    user = message.from_user
    add_user(user.id, user.first_name)
    bot.send_message(
        message.chat.id,
        f"Привет {user.first_name}! Я бот для трекинга привычек.\n\n"
        "Используй кнопки ниже, чтобы управлять своими привычками:",
        reply_markup=create_menu()
    )


# Обработка текстовых сообщений
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    if message.text == "Добавить привычку ➕":
        add_habit_start(message)
    elif message.text == "Отметить выполнение ✅":
        track_habit(message)
    elif message.text == "Статистика 📊":
        show_stats(message)
    else:
        bot.send_message(message.chat.id, "Используй кнопки ниже ⬇️", reply_markup=create_menu())


# Добавление привычки
@bot.message_handler(commands=['add_habit'])
def add_habit_start(message):
    msg = bot.send_message(message.chat.id, "Введите название привычки:", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, add_habit_end)


def add_habit_end(message):
    user_id = message.from_user.id
    habit_name = message.text

    if add_habit(user_id, habit_name):
        bot.send_message(message.chat.id, f"Привычка '{habit_name}' добавлена!", reply_markup=create_menu())
    else:
        bot.send_message(message.chat.id, f"Привычка '{habit_name}' уже существует!", reply_markup=create_menu())


# Отметить выполнение
@bot.message_handler(commands=['track_habit'])
# В функции track_habit
def track_habit(message):
    user_id = message.from_user.id
    habits = get_user_habits(user_id)

    if not habits:
        bot.send_message(message.chat.id, "У вас нет добавленных привычек.", reply_markup=create_menu())
        return

    keyboard = InlineKeyboardMarkup()
    for habit in habits:
        # Проверяем, что habit_name является строкой
        habit_name = str(habit[1])  # Приводим к строке на случай, если это не так
        keyboard.add(InlineKeyboardButton(habit_name, callback_data=f"track_{habit[0]}"))

    bot.send_message(message.chat.id, "Выберите привычку для отметки:", reply_markup=keyboard)


# Обработка inline-кнопок
@bot.callback_query_handler(func=lambda call: call.data.startswith("track_"))
def track_habit_complete(call):
    habit_id = call.data.split("_")[1]  # Получаем ID привычки
    update_habit_count(habit_id)

    # Получаем название привычки
    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    c.execute("SELECT habit_name FROM habits WHERE id=?", (habit_id,))
    habit_name = c.fetchone()[0]
    conn.close()

    bot.answer_callback_query(call.id, f"Привычка '{habit_name}' отмечена! ✅")
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Привычка '{habit_name}' отмечена! ✅"
    )
    bot.send_message(call.message.chat.id, "Что дальше?", reply_markup=create_menu())


# Показать статистику
@bot.message_handler(commands=['stats'])
def show_stats(message):
    user_id = message.from_user.id
    stats = get_stats(user_id)

    if not stats:
        bot.send_message(message.chat.id, "Статистика пуста.", reply_markup=create_menu())
        return

    message_text = "📊 Ваша статистика:\n\n" + "\n".join(
        [f"{habit[0]}: {habit[1]} раз" for habit in stats]
    )
    bot.send_message(message.chat.id, message_text, reply_markup=create_menu())


# Запуск бота
if __name__ == "__main__":
    init_db()
    print("Бот запущен...")
    bot.polling(none_stop=True)
