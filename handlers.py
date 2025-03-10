from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import add_task, delete_task, get_tasks, start_session, stop_session, get_active_session, get_total_stat_last_7_days, get_stat_daily_day
from enum import Enum, auto

class State(Enum):
    WAITING_FOR_TASK_NAME = auto()  # Ожидание названия задачи
    WAITING_FOR_TASK_NUMBER = auto()  # Ожидание номера задачи

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.from_user.first_name
    start_message = f'''
        Привет, {user_name}! Я тайм-трекер бот.
Создай свою первую задачу и запусти учет времени.
    '''
    await update.message.reply_text(start_message)

# Обработчик команды /add_task
async def add_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи название задачи:")
    return State.WAITING_FOR_TASK_NAME

# Обработчик ввода названия задачи
async def receive_task_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    task_name = update.message.text
    user_id = update.message.from_user.id

    # Добавляем задачу в базу данных
    add_task(user_id, task_name)
    await update.message.reply_text(f'Задача "{task_name}" создана!✅')
    return ConversationHandler.END

# Обработчик команды /delete_task
async def delete_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    # Получаем список задач
    tasks = get_tasks(user_id)

    if not tasks:
        await update.message.reply_text("У тебя пока нет задач.")
        return ConversationHandler.END

    # Формируем сообщение со списком задач
    tasks_list = "\n".join([f"{i + 1}. {task['name']}" for i, task in enumerate(tasks)])
    await update.message.reply_text(f"Твои задачи:\n{tasks_list}\nВведи номер задачи для удаления:")
    return State.WAITING_FOR_TASK_NUMBER

# Обработчик ввода номера задачи для удаления
async def receive_task_number_for_deletion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    try:
        task_number = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Введи номер задачи.")
        return State.WAITING_FOR_TASK_NUMBER

    # Получаем список задач
    tasks = get_tasks(user_id)

    # Проверяем, существует ли задача с таким номером
    if task_number < 1 or task_number > len(tasks):
        await update.message.reply_text("Задачи с таким номером не существует.")
        return State.WAITING_FOR_TASK_NUMBER

    # Удаляем задачу
    task_id = tasks[task_number - 1]['id']
    delete_task(user_id, task_id)
    await update.message.reply_text(f'Задача "{tasks[task_number - 1]["name"]}" удалена!❌')
    return ConversationHandler.END

# Обработчик команды /list_tasks
async def list_tasks_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    # Получаем список задач из базы данных
    tasks = get_tasks(user_id)

    if not tasks:
        await update.message.reply_text("У тебя пока нет задач.")
        return

    # Формируем сообщение со списком задач
    tasks_list = "\n".join([f"{i + 1}. {task['name']}" for i, task in enumerate(tasks)])
    await update.message.reply_text(f"Твои задачи📋:\n{tasks_list}")

#Обработчик команды /help
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.from_user.first_name
    message_text = f'''
    {user_name}, все получится!
Немного терпения и удачи и ты со всем справишься!
'''

    await update.message.reply_text(message_text)

# Обработчик команды /start_session
async def start_session_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    # Получаем список задач
    tasks = get_tasks(user_id)

    if not tasks:
        await update.message.reply_text("У тебя пока нет задач.")
        return ConversationHandler.END

    # Формируем сообщение со списком задач
    tasks_list = "\n".join([f"{i + 1}. {task['name']}" for i, task in enumerate(tasks)])
    await update.message.reply_text(f"Твои задачи:\n{tasks_list}\nВведи номер задачи для запуска сессии:")
    return State.WAITING_FOR_TASK_NUMBER

# Обработчик ввода номера задачи для запуска сессии
async def receive_task_number_for_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    try:
        task_number = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Введи номер задачи.")
        return State.WAITING_FOR_TASK_NUMBER

    # Получаем список задач
    tasks = get_tasks(user_id)

    # Проверяем, существует ли задача с таким номером
    if task_number < 1 or task_number > len(tasks):
        await update.message.reply_text("Задачи с таким номером не существует.")
        return State.WAITING_FOR_TASK_NUMBER

    # Запускаем сессию
    task_id = tasks[task_number - 1]['id']
    if start_session(user_id, task_id):
        await update.message.reply_text(f'Сессия для задачи "{tasks[task_number - 1]["name"]}" запущена!▶️')
    else:
        await update.message.reply_text("У тебя уже есть активная сессия.")
    return ConversationHandler.END

#Обработчик команды /stop_session
async def stop_session_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    # Получаем активную сессию пользователя
    active_session = get_active_session(user_id)

    if not active_session:
        await update.message.reply_text("У тебя нет активной сессии.")
        return

    # Останавливаем сессию и получаем результат
    result = stop_session(user_id)

    if result:
        await update.message.reply_text(
                f'Сессия для задачи "{result["name"]}" остановлена! Активное время: {result["time_diff"]}🚫')
    else:
        await update.message.reply_text("У тебя нет активной сессии.")

#Обработчик вызова активной сессии /active_session
async def active_session_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    # Получаем активную сессию пользователя
    active_session = get_active_session(user_id)

    if not active_session:
        await update.message.reply_text("У тебя нет активной сессии.")
        return

    await update.message.reply_text(f'Сейчас активна задача "{active_session["name"]}" ✅')

#Обработчик команды /stats с созданием inline меню
async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Общая статистика за 7 дней", callback_data="total_stat_7")],
        [InlineKeyboardButton("Среднее время за 7 дней", callback_data="avg_time_7")],
        [InlineKeyboardButton("Статистика по дням за 7 дней", callback_data="daily_stats_7")],
        [InlineKeyboardButton("Настроить период", callback_data="custom_period")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите тип статистики:", reply_markup=reply_markup)

#Обработчик вызовов сценария статистики
async def handle_stats_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if query.data == "total_stat_7":
        stats = get_total_stat_last_7_days(user_id)
        daily_day = get_stat_daily_day(user_id)

        days_info = "\n".join(
            f"• {formatted_date}: {data['day_of_week']} ({data['active_time']})"
            for formatted_date, data in daily_day.items()
        )

        await query.edit_message_text(
            f"📈Статистика за последние 7 дней:\n"
            f"Общее активное время: {stats['total_time']}\n"
            f"Cреднее активное время: {stats['avg_time']}\n\n"
            f"Статистика по дням:\n{days_info}"
            )
    # elif query.data == "avg_time_7":
    #     stats = get_avg_time_last_7_days(user_id)
    #     await query.edit_message_text(f"Среднее время за последние 7 дней: {stats}")
    # elif query.data == "daily_stats_7":
    #     stats = get_daily_stats_last_7_days(user_id)
    #     await query.edit_message_text(f"Статистика по дням за последние 7 дней:\n{stats}")
    # elif query.data == "custom_period":
    #     await query.edit_message_text("Введите количество дней (например, 7, 14, 30):")
    #     return State.WAITING_FOR_PERIOD