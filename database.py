import sqlite3
from datetime import datetime


#Создание/подключение к БД
def get_db_connections():
    conn = sqlite3.connect('time_tracker.db') #Создаем или подключаемся к созданной БД
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