import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackContext
from database import(
    add_task, delete_task, get_tasks, start_session, stop_session,
    get_active_session, get_total_stat_last_7_days, get_stat_daily_day,
    get_task_stat_last_7_days, get_stat_task_daily_day
)
from enum import Enum, auto
from dashboard import generate_dashboard

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

class State(Enum):
    WAITING_FOR_TASK_NAME = auto()  # Ожидание названия задачи
    WAITING_FOR_TASK_NUMBER = auto()  # Ожидание номера задачи

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.from_user.first_name

    # Создаем список кнопок для клавиатуры
    keyboard = [['▶️', '⏹️', '🔄', '⚙️']]

    # Создаем replay-клавиатуру с помощью ReplyKeyboardMarkup
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    start_message = f'''
        Привет, {user_name}! Я тайм-трекер бот. Создай свою первую задачу и запусти учет времени.
    '''
    await update.message.reply_text(start_message, reply_markup=reply_markup)

#Обработчик команды вызова инлайн-меню
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [InlineKeyboardButton("      Добавить задачу 🆕     ", callback_data= 'add_task')],
        [InlineKeyboardButton("      Удалить задачу 🗑     ", callback_data='delete_task')],
        [InlineKeyboardButton("      Список задач 📋     ", callback_data='list_tasks')],
        [InlineKeyboardButton("      Статистика 📈     ", callback_data='stats')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text('Меню:', reply_markup=reply_markup)

# Обработчик команды /add_task
async def add_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    #Запрашиваем название задачи
    await query.edit_message_text("Введи название задачи:")
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
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    # Получаем список задач
    tasks = get_tasks(user_id)

    if not tasks:
        await update.message.reply_text("У тебя пока нет задач.")
        return ConversationHandler.END

    # Формируем сообщение со списком задач
    tasks_list = "\n".join([f"{i + 1}. {task['name']}" for i, task in enumerate(tasks)])
    await query.edit_message_text(f"Твои задачи:\n{tasks_list}\nВведи номер задачи для удаления:")
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
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    # Получаем список задач из базы данных
    tasks = get_tasks(user_id)

    if not tasks:
        await update.message.reply_text("У тебя пока нет задач.")
        return

    # Формируем сообщение со списком задач
    tasks_list = "\n".join([f"{i + 1}. {task['name']}" for i, task in enumerate(tasks)])
    await query.edit_message_text(f"Твои задачи📋:\n{tasks_list}")

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

    await update.message.reply_text(f'Сейчас активна задача "{active_session["name"]}" 🔄')

#Обработчик команды /stats с созданием inline меню
async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton('Общая статистика за 7 дней', callback_data='total_stat_7')],
        [InlineKeyboardButton('Статистика по задаче за 7 дней', callback_data='total_stat_task_7')],
        [InlineKeyboardButton('📊 Открыть дашборд', callback_data='open_dashboard')],
        [InlineKeyboardButton('Назад', callback_data='back_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Выберите тип статистики:", reply_markup=reply_markup)


# Обработчик команды вызова инлайн-меню
async def back_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton('      Добавить задачу 🆕     ', callback_data='add_task')],
        [InlineKeyboardButton('      Удалить задачу 🗑     ', callback_data='delete_task')],
        [InlineKeyboardButton('      Список задач 📋     ', callback_data='list_tasks')],
        [InlineKeyboardButton('      Статистика 📈     ', callback_data='stats')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text('Меню:', reply_markup=reply_markup)

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

    elif query.data == 'total_stat_task_7':

        # Получаем список задач
        tasks = get_tasks(user_id)

        if not tasks:
            logging.warning(f"У пользователя {user_id} нет задач.")
            await query.edit_message_text("У тебя пока нет задач.")
            return ConversationHandler.END

        # Формируем сообщение со списком задач
        tasks_list = "\n".join([f"{i + 1}. {task['name']}" for i, task in enumerate(tasks)])
        await query.edit_message_text(f"Твои задачи:\n{tasks_list}\nВведи номер задачи для получения статистики:")
        logging.info(f"Переход в состояние WAITING_FOR_TASK_NUMBER для пользователя {user_id}")
        return State.WAITING_FOR_TASK_NUMBER

    elif query.data == "open_dashboard":
            # Обработка кнопки "Открыть дашборд"
        logging.info(f"Пользователь {user_id} запросил дашборд.")
        await _handle_dashboard(query, context, user_id)

#Обработчик вывода графиков статистики
async def _handle_dashboard(query, context, user_id):
    """Обрабатывает запрос на генерацию и отправку дашборда."""
    try:
        # Уведомляем пользователя о начале генерации
        await query.answer("⏳ Генерация дашборда...")
        # Генерируем графики
        images = generate_dashboard(user_id)
        if images:
            # Отправляем изображения пользователю
            for img_bytes in images:
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=img_bytes,
                    caption="Ваша статистика за последние 7 дней"
                )
                img_bytes.close()  # Закрываем байтовый объект
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text="😞 Недостаточно данных для построения отчета.\nПора начинать учиться!"
            )
    except Exception as e:
        logging.error(f"Ошибка при генерации дашборда для пользователя {user_id}: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text="⚠️ Произошла ошибка при генерации дашборда. Попробуйте позже."
        )

#Обработчик ввода номера задачи для вывода статистики по задаче
async def handler_task_number_stat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("Обработчик handler_task_number_stat вызван.")
    user_id = update.message.from_user.id
    task_number = update.message.text

    logging.info(f"Пользователь {user_id} ввёл номер задачи: {task_number}")

    # Проверяем, что введённое значение — число
    if not task_number.isdigit():
        logging.warning(f"Пользователь {user_id} ввёл некорректный номер задачи: {task_number}")
        await update.message.reply_text("Пожалуйста, введи номер задачи числом.")
        return State.WAITING_FOR_TASK_NUMBER

    task_number = int(task_number)

    # Получаем список задач
    tasks = get_tasks(user_id)

    # Проверяем, существует ли задача с таким номером
    if task_number < 1 or task_number > len(tasks):
        logging.warning(f"Пользователь {user_id} ввёл несуществующий номер задачи: {task_number}")
        await update.message.reply_text("Задачи с таким номером не существует.")
        return State.WAITING_FOR_TASK_NUMBER

    # Выводим статистику
    task_id = tasks[task_number - 1]['id']
    stat = get_task_stat_last_7_days(user_id, task_id)
    stat_daily = get_stat_task_daily_day(user_id, task_id)

    days_info = "\n".join(
        f"• {formatted_date}: {data['day_of_week']} ({data['active_time']})"
        for formatted_date, data in stat_daily.items()
    )

    logging.info(f"Статистика для задачи {task_id} пользователя {user_id}: {stat}")
    await update.message.reply_text(
        f'📈Статистика по задаче "{tasks[task_number - 1]["name"]}" за последние 7 дней:\n'
        f'Общее активное время: {stat["total_time_task"]}\n'
        f'Cреднее активное время: {stat["avg_time_task"]}\n\n'
        f'Статистика по дням:\n{days_info}')

    return ConversationHandler.END
