import logging
from telegram.ext import ApplicationBuilder, CommandHandler, ConversationHandler, MessageHandler, filters
from config import BOT_TOKEN
from database import init_db
from handlers import State, start, add_task_handler, receive_task_name, delete_task_handler, receive_task_number_for_deletion, list_tasks_handler, help_handler, start_session_handler, receive_task_number_for_session, stop_session_handler, active_session_handler
# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Инициализация базы данных
init_db()

# Функция для запуска бота
#Проверка на запуск в main.py
if __name__ == '__main__':
    # Создаем объект Application и передаем ему токен бота
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # ConversationHandler для добавления задачи
    add_task_conv = ConversationHandler(
        entry_points=[CommandHandler('add_task', add_task_handler)],
        states={
            State.WAITING_FOR_TASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_task_name)],
        },
        fallbacks=[]
    )

    # ConversationHandler для удаления задачи
    delete_task_conv = ConversationHandler(
        entry_points=[CommandHandler('delete_task', delete_task_handler)],
        states={
            State.WAITING_FOR_TASK_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_task_number_for_deletion)],
        },
        fallbacks=[]
    )

    # ConversationHandler для запуска сессии
    start_session_conv = ConversationHandler(
        entry_points=[CommandHandler('start_session', start_session_handler)],
        states={
            State.WAITING_FOR_TASK_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_task_number_for_session)],
        },
        fallbacks=[]
    )

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler('start', start))
    application.add_handler(add_task_conv)
    application.add_handler(delete_task_conv)
    application.add_handler(CommandHandler('list_tasks', list_tasks_handler))
    application.add_handler(CommandHandler('help', help_handler))
    application.add_handler(start_session_conv)
    application.add_handler(CommandHandler('stop_session', stop_session_handler))
    application.add_handler(CommandHandler('active_task', active_session_handler))
    # Запускаем бота
    application.run_polling()
