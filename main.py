import logging
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
)
from config import BOT_TOKEN
from database import init_db
from handlers import (
    State, start, add_task_handler, receive_task_name, delete_task_handler, receive_task_number_for_deletion,
    list_tasks_handler, help_handler, start_session_handler, receive_task_number_for_session,
    stop_session_handler, active_session_handler, stats_handler, handle_stats_selection, handler_task_number_stat,
    menu_handler, back_menu_handler)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Инициализация базы данных
init_db()

# Функция для запуска бота
if __name__ == '__main__':
    # Создаем объект Application и передаем ему токен бота
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # ConversationHandler для добавления задачи
    add_task_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_task_handler, pattern='add_task'),
    ],
    states={
        State.WAITING_FOR_TASK_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_task_name),
        ],
    },
    fallbacks=[],
    )

    # ConversationHandler для удаления задачи
    delete_task_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(delete_task_handler, pattern='delete_task')
        ],
        states={
            State.WAITING_FOR_TASK_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_task_number_for_deletion)],
        },
        fallbacks=[]
    )

    # ConversationHandler для запуска сессии
    start_session_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Text('▶️'), start_session_handler)],
        states={
            State.WAITING_FOR_TASK_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_task_number_for_session)],
        },
        fallbacks=[]
    )

    # ConversationHandler для получения статистики по задаче
    stats_task_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_stats_selection, pattern='^total_stat_task_7$')],
        states={
            State.WAITING_FOR_TASK_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler_task_number_stat)],
        },
        fallbacks=[],
        name='stats_task_conv',  # Имя для логирования
        persistent=False,  # Сохранять состояние между перезапусками
    )

    logging.info(f'ConversationHandler stats_task_conv зарегистрирован.')

    # Регистрируем обработчики команд
    application.add_handler(stats_task_conv)
    application.add_handler(CommandHandler('start', start))
    application.add_handler(add_task_conv)
    application.add_handler(delete_task_conv)
    application.add_handler(CallbackQueryHandler(list_tasks_handler, pattern='list_tasks'))
    application.add_handler(CommandHandler('help', help_handler))
    application.add_handler(start_session_conv)
    application.add_handler(CallbackQueryHandler(stats_handler, pattern='stats'))
    application.add_handler(CallbackQueryHandler(back_menu_handler, pattern='back_menu'))
    application.add_handler(MessageHandler(filters.Text('⏹️'), stop_session_handler))
    application.add_handler(MessageHandler(filters.Text('🔄'), active_session_handler))
    application.add_handler(MessageHandler(filters.Text('⚙️'), menu_handler))
    application.add_handler(CallbackQueryHandler(handle_stats_selection))

    # Запускаем бота
    application.run_polling()
