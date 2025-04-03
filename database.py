import sqlite3
import logging
import locale
from datetime import datetime, timedelta

#Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

#Создание/подключение к БД
def get_db_connections():
    conn = sqlite3.connect('/data/time_tracker.db') #Создаем или подключаемся к созданной БД
    conn.row_factory = sqlite3.Row #Возвращаем результат запроса в виде словаря

    #Включаем внешние ключи
    cursor = conn.cursor()
    cursor.execute('PRAGMA foreign_keys = ON;')
    conn.commit()

    return conn

# Функция для инициализации БД
def init_db():
    conn = get_db_connections()
    cursor = conn.cursor()

    #Включаем русскую локализацию для linux, (Windows - locale.setlocale(locale.LC_TIME, 'Russian_Russia.1251')
    #locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')

    #Создаем таблицы в БД(если они еще не созданы)
    #Таблица задач tasks
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP 
        )
    ''')

    #Таблица сессий sessions
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                start_time DATETIME NOT NULL,
                end_time DATETIME,
                is_active INTEGER DEFAULT 1,  -- 1 = активна, 0 = неактивна
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
            )
        ''')

    conn.commit()  # Сохраняем изменения
    conn.close()  # Закрываем соединение

    #Проверка внешних ключей
    def check_foreign_keys():
        conn = get_db_connections()
        cursor = conn.cursor()
        cursor.execute('PRAGMA foreign_keys;')
        result = cursor.fetchone()
        conn.close()
        return result[0]

    print("Внешние ключи включены:" if check_foreign_keys() else "Внешние ключи отключены.")

# Функция для добавления задачи
def add_task(user_id: int, task_name: str):
    conn = get_db_connections()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO tasks (user_id, name) VALUES (?, ?)', (user_id, task_name))
    conn.commit()
    conn.close()

# Функция для удаления задачи
def delete_task(user_id: int, task_id: int):
    conn = get_db_connections()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tasks WHERE id = ? AND user_id = ?', (task_id, user_id))
    conn.commit()
    conn.close()

# Функция для получения списка задач
def get_tasks(user_id: int):
    conn = get_db_connections()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM tasks WHERE user_id = ? ORDER BY created_at', (user_id,))
    tasks = cursor.fetchall()
    conn.close()
    return tasks

# Функция для запуска сессии
def start_session(user_id: int, task_id: int):
    conn = get_db_connections()
    cursor = conn.cursor()

    # Проверяем, есть ли уже активная сессия
    cursor.execute('SELECT id FROM sessions WHERE user_id = ? AND is_active = 1', (user_id,))
    active_session = cursor.fetchone()

    if active_session:
        conn.close()
        return False  # Сессия уже активна

    # Запускаем новую сессию
    cursor.execute('INSERT INTO sessions (user_id, task_id, start_time) VALUES (?, ?, CURRENT_TIMESTAMP)', (user_id, task_id,))
    conn.commit()
    conn.close()
    return True

# Функция для остановки сессии
def stop_session(user_id: int):
    conn = get_db_connections()
    cursor = conn.cursor()

    # Находим активную сессию пользователя
    cursor.execute('''
        SELECT s.id, t.name
        FROM sessions s
        JOIN tasks t ON s.task_id = t.id
        WHERE s.user_id = ? AND s.is_active = 1
    ''', (user_id,))
    active_session = cursor.fetchone()

    if not active_session:
        conn.close()
        return False  # У пользователя нет активной сессии

    # Останавливаем сессию
    cursor.execute('''
        UPDATE sessions
        SET end_time = CURRENT_TIMESTAMP, is_active = 0
        WHERE id = ?
    ''', (active_session['id'],))
    conn.commit()

    cursor.execute('''
        SELECT strftime('%H:%M:%S', strftime('%s', end_time) - strftime('%s', start_time), 'unixepoch') AS time_diff
        FROM sessions
        WHERE id = ?
    ''', (active_session['id'],))
    time_diff = cursor.fetchone()['time_diff']
    conn.close()
    return {
        'name': active_session['name'],
        'time_diff': time_diff
    }  # Возвращаем с названием задачи и time_diff

# Функция для получения активной сессии
def get_active_session(user_id: int):
    conn = get_db_connections()
    cursor = conn.cursor()

    # Находим активную сессию для пользователя
    cursor.execute('''
        SELECT s.id, t.name
        FROM sessions s
        JOIN tasks t ON s.task_id = t.id
        WHERE s.user_id = ? AND s.is_active = 1
    ''', (user_id,))
    active_session = cursor.fetchone()
    conn.close()
    return active_session

#Функция для преобразования секунд в удобный формат
def seconds_to_hms(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

#Функция для получения общего и среднего времени активности за последние 7 дней
def get_total_stat_last_7_days(user_id: int):
    conn = get_db_connections()
    cursor = conn.cursor()

    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')

    #Находим общее время за 7 дней
    cursor.execute('''
        SELECT COALESCE(SUM(strftime('%s', end_time) - strftime('%s', start_time)),0) AS total_time
        FROM sessions 
        WHERE user_id = ? AND end_time IS NOT NULL AND start_time >= ?
        ''', (user_id, start_date))
    result_total = cursor.fetchone()
    conn.close()


    #Находим среднее время за 7 дней
    result_avg = result_total['total_time']/7

    # Создаем словарь для хранения результатов
    results = {}

    # Добавляем общее время в словарь
    total_seconds = int(result_total['total_time'])
    results['total_time'] = (seconds_to_hms(total_seconds))

    # Добавляем среднее время в словарь
    avg_seconds = int(result_avg)
    results['avg_time'] = (seconds_to_hms(avg_seconds))

    return results

#Функция нахождения активного времени за каждый из 7 дней
def get_stat_daily_day(user_id: int):
    conn = get_db_connections()
    cursor = conn.cursor()

    #Определяем временной диапазон (последние 7 дней)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    #Запрашиваем данные из БД (группируем по дням)
    cursor.execute('''
        SELECT 
            DATE(start_time) AS day, 
            SUM(strftime('%s', end_time) - strftime('%s', start_time)) AS total_seconds
        FROM sessions
        WHERE user_id = ? 
            AND end_time IS NOT NULL 
            AND start_time >= ?
        GROUP BY day
        ORDER BY day DESC
    ''', (user_id, start_date.strftime('%Y-%m-%d %H:%M:%S')))

    db_results = cursor.fetchall()
    conn.close()

    #Готовим структуру для хранения данных
    stats = {}
    for row in db_results:
        day = row['day']  # 'YYYY-MM-DD'
        stats[day] = row['total_seconds'] or 0  # 0, если NULL

    #Генерируем все даты за последние 7 дней (включая дни без активности)
    date_range = [end_date.date() - timedelta(days=i) for i in range(7)]

    #Формируем итоговый результат
    result = {}
    for date in date_range:
        formatted_date = date.strftime('%d %b')  # '05 Jan'
        day_of_week = date.strftime('%A')  # 'Monday'

        #Получаем активное время или 0
        active_seconds = stats.get(date.strftime('%Y-%m-%d'), 0)

        result[formatted_date] = {
            'day_of_week': day_of_week,
            'active_time': seconds_to_hms(active_seconds)
        }

    return result

#Функция для получения общего и среднего времени активности за последние 7 дней по задаче
def get_task_stat_last_7_days(user_id: int, task_id: int):
    conn = get_db_connections()
    cursor = conn.cursor()

    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')

    # Находим общее время за 7 дней
    cursor.execute('''
            SELECT COALESCE(SUM(strftime('%s', end_time) - strftime('%s', start_time)),0) AS total_time_task
            FROM sessions 
            WHERE user_id = ? AND end_time IS NOT NULL AND start_time >= ? AND task_id = ?
            ''', (user_id, start_date, task_id))
    result_total = cursor.fetchone()
    conn.close()

    # Находим среднее время за 7 дней
    result_avg_task = result_total['total_time_task'] / 7

    # Создаем словарь для хранения результатов
    results = {}

    # Добавляем общее время в словарь
    total_seconds = int(result_total['total_time_task'])
    results['total_time_task'] = (seconds_to_hms(total_seconds))

    # Добавляем среднее время в словарь
    avg_seconds = int(result_avg_task)
    results['avg_time_task'] = (seconds_to_hms(avg_seconds))

    return results

#Функция нахождения активного времени по задаче за каждый из 7 дней
def get_stat_task_daily_day(user_id: int, task_id: int):
    conn = get_db_connections()
    cursor = conn.cursor()

    #Определяем временной диапазон (последние 7 дней)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    #Запрашиваем данные из БД (группируем по дням)
    cursor.execute('''
        SELECT 
            DATE(start_time) AS day, 
            SUM(strftime('%s', end_time) - strftime('%s', start_time)) AS total_seconds
        FROM sessions
        WHERE user_id = ? 
            AND end_time IS NOT NULL 
            AND start_time >= ?
            AND task_id = ?
        GROUP BY day
        ORDER BY day DESC
    ''', (user_id, start_date.strftime('%Y-%m-%d %H:%M:%S'), task_id))

    db_results = cursor.fetchall()
    conn.close()

    #Готовим структуру для хранения данных
    stats = {}
    for row in db_results:
        day = row['day']  # 'YYYY-MM-DD'
        stats[day] = row['total_seconds'] or 0  # 0, если NULL

    #Генерируем все даты за последние 7 дней (включая дни без активности)
    date_range = [end_date.date() - timedelta(days=i) for i in range(7)]

    #Формируем итоговый результат
    result = {}
    for date in date_range:
        formatted_date = date.strftime('%d %b')  # '05 Jan'
        day_of_week = date.strftime('%A')  # 'Monday'

        #Получаем активное время или 0
        active_seconds = stats.get(date.strftime('%Y-%m-%d'), 0)

        result[formatted_date] = {
            'day_of_week': day_of_week,
            'active_time': seconds_to_hms(active_seconds)
        }

    return result