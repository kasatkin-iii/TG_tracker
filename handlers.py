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

    #Кнопка отмена создания задачи
    keyboard = [[InlineKeyboardButton("Отмена", callback_data="cancel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    #Запрашиваем название задачи
    await query.edit_message_text('Введи название задачи:',reply_markup=reply_markup)
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
    keyboard = [
        [InlineKeyboardButton(task['name'], callback_data=f"delete_{task['id']}")] for task in tasks
    ]
    keyboard.append([InlineKeyboardButton("Отмена", callback_data="cancel")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text('Выбери задачу для удаления:', reply_markup=reply_markup)
    return State.WAITING_FOR_TASK_NUMBER

# Обработчик ввода номера задачи для удаления
async def receive_task_for_deletion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Подтверждаем нажатие кнопки

    user_id = query.from_user.id
    task_id = int(query.data.split("_")[1])
    tasks = get_tasks(user_id)

    # Находим задачу по task_id
    task = next((task for task in tasks if task["id"] == task_id), None)

    # Удаляем задачу
    delete_task(user_id, task_id)

    await query.edit_message_text(f'Задача "{task['name']}" удалена!❌')
    return ConversationHandler.END

#Обработчик кнопки "Отмена" для выхода из состояния ожидания данных
async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Подтверждаем нажатие кнопки

    # Возвращаем пользователя в главное меню
    await back_menu_handler(update, context)
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

    #Создаем кнопку "Назад для возврата к главному меню"
    keyboard = [[InlineKeyboardButton("Назад", callback_data="back_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Формируем сообщение со списком задач
    tasks_list = "\n".join([f"{i + 1}. {task['name']}" for i, task in enumerate(tasks)])
    await query.edit_message_text(f"Твои задачи📋:\n{tasks_list}", reply_markup=reply_markup)

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
    keyboard = [
        [InlineKeyboardButton(task['name'], callback_data=f"start_{task['id']}")] for task in tasks
    ]
    keyboard.append([InlineKeyboardButton("Отмена", callback_data="cancel_start")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text('По какой задаче запустить таймер?', reply_markup=reply_markup)
    return State.WAITING_FOR_TASK_NUMBER

# Обработчик ввода номера задачи для запуска сессии
async def receive_task_for_start_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Подтверждаем нажатие кнопки
    user_id = query.from_user.id

    #Методом сплит и int() добываем 'id'
    task_id = int(query.data.split("_")[1])

    # Запускаем сессию
    if start_session(user_id, task_id):

        #Находим активную сессию, для определения 'name'
        active_session = get_active_session(user_id)
        await query.edit_message_text(f'Сессия для задачи "{active_session["name"]}" запущена!▶️')
    else:
        await query.edit_message_text("У тебя уже есть активная сессия.")
    return ConversationHandler.END

#Обработчик отмены запуска сессии
async def cancel_start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Подтверждаем нажатие кнопки

    # Возвращаем пользователя в главное меню
    await query.edit_message_text("Запуск таймера отменен!")
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

#Обработчик команды возврата в главное инлайн-меню
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

    if query.data == 'total_stat_7':
        stats = get_total_stat_last_7_days(user_id)
        daily_day = get_stat_daily_day(user_id)

        # Клавиатура для кнопки назад
        keyboard = [[InlineKeyboardButton("Назад", callback_data='stats')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        days_info = "\n".join(
            f"• {formatted_date}: {data['day_of_week']} ({data['active_time']})"
            for formatted_date, data in daily_day.items()
        )

        await query.edit_message_text(
            f"📈Статистика за последние 7 дней:\n"
            f"Общее активное время: {stats['total_time']}\n"
            f"Cреднее активное время: {stats['avg_time']}\n\n"
            f"Статистика по дням:\n{days_info}",reply_markup=reply_markup
            )

    elif query.data == 'total_stat_task_7':

        # Получаем список задач
        tasks = get_tasks(user_id)

        if not tasks:
            await query.edit_message_text("У тебя пока нет задач.")
            return ConversationHandler.END


        # Формируем сообщение со списком задач
        keyboard = [
            [InlineKeyboardButton(task['name'], callback_data=f"stat_{task['id']}")] for task in tasks
        ]
        keyboard.append([InlineKeyboardButton("Отмена", callback_data="stat")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(f"Для какой задачи вывести статистику?", reply_markup=reply_markup)
        return State.WAITING_FOR_TASK_NUMBER

    elif query.data == "open_dashboard":
            # Обработка кнопки "Открыть дашборд"
        logging.info(f"Пользователь {user_id} запросил дашборд.")
        await _handle_dashboard(query, context, user_id)

#Обработчик вывода графиков статистики
async def _handle_dashboard(query, context, user_id):
   #Обрабатывает запрос на генерацию и отправку дашборда.
    try:
        await query.delete_message()
        generating_message = await context.bot.send_message(
            chat_id=user_id,
            text="⏳ Генерация дашборда..."
        )
        # Генерируем графики
        images = generate_dashboard(user_id)
        if images:

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Назад", callback_data='cancel_dashboard')]
            ])
            # Отправляем изображения пользователю
            await context.bot.send_photo(
                chat_id=user_id,
                photo=images,
                caption="Ваша статистика за последние 7 дней",
                reply_markup = keyboard
            )
            images.close()  # Закрываем байтовый объект
            await generating_message.delete()

        else:
            await context.bot.send_message(
                chat_id=user_id,
                text="😞 Недостаточно данных для построения отчета.\nПора начинать учиться!"
            )
            await generating_message.delete()

    except Exception as e:
        logging.error(f"Ошибка при генерации дашборда для пользователя {user_id}: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text="⚠️ Произошла ошибка при генерации дашборда. Попробуйте позже."
        )
        await generating_message.delete()

async def cancel_dashboard_handler(update, context):
    query = update.callback_query
    await query.answer()

    # Удаляем сообщение с дашбордом
    await query.delete_message()

    # Создаём новое меню статистики
    keyboard = [
        [InlineKeyboardButton('Общая статистика за 7 дней', callback_data='total_stat_7')],
        [InlineKeyboardButton('Статистика по задаче за 7 дней', callback_data='total_stat_task_7')],
        [InlineKeyboardButton('📊 Открыть дашборд', callback_data='open_dashboard')],
        [InlineKeyboardButton('Назад', callback_data='back_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Выберите тип статистики:",
        reply_markup=reply_markup
    )

#Обработчик ввода номера задачи для вывода статистики по задаче
async def handler_task_number_stat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("Обработчик handler_task_number_stat вызван.")
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    task_id = int(query.data.split("_")[1])

    # Находим задачу по task_id
    tasks = get_tasks(user_id)
    task = next((task for task in tasks if task["id"] == task_id), None)

    # Клавиатура для кнопки назад
    keyboard = [[InlineKeyboardButton("Назад", callback_data='stats')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    #Получаем статистику
    stat = get_task_stat_last_7_days(user_id, task_id)
    stat_daily = get_stat_task_daily_day(user_id, task_id)

    days_info = "\n".join(
        f"• {formatted_date}: {data['day_of_week']} ({data['active_time']})"
        for formatted_date, data in stat_daily.items()
    )

    logging.info(f"Статистика для задачи {task_id} пользователя {user_id}: {stat}")
    await query.edit_message_text(
        f'📈Статистика по задаче "{task["name"]}" за последние 7 дней:\n'
        f'Общее активное время: {stat["total_time_task"]}\n'
        f'Cреднее активное время: {stat["avg_time_task"]}\n\n'
        f'Статистика по дням:\n{days_info}', reply_markup=reply_markup)

    return ConversationHandler.END

#Обработчик кнопки отмена выбора задачи для вывода статистики
async def cancel_stat_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Подтверждаем нажатие кнопки

    # Возвращаем пользователя в меню статистики
    await stats_handler(update, context)
    return ConversationHandler.END
