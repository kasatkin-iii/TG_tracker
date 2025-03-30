import sqlite3
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns
import pandas as pd
from io import BytesIO


def get_db_connection():
    """Создает соединение с базой данных."""
    return sqlite3.connect('../data/time_tracker.db')


def get_data(user_id):
    """Получает данные из базы данных для конкретного пользователя."""
    conn = get_db_connection()

    # Запрос для данных по дням
    daily_query = '''
        WITH RECURSIVE date_range AS (
            SELECT DATE('now', '-6 days') AS date
            UNION ALL
            SELECT DATE(date, '+1 day')
            FROM date_range
            WHERE date < DATE('now')
        )
        SELECT 
            date_range.date,
            COALESCE(SUM(strftime('%s', end_time) - strftime('%s', start_time)), 0) AS total_time_seconds
        FROM date_range
        LEFT JOIN sessions ON date_range.date = strftime('%Y-%m-%d', sessions.start_time)
                          AND sessions.user_id = ?
                          AND sessions.end_time IS NOT NULL
        GROUP BY date_range.date
        ORDER BY date_range.date;
    '''
    daily_data = pd.read_sql(daily_query, conn, params=(user_id,))

    # Запрос для данных по задачам за последние 7 дней
    task_query = '''
        SELECT 
            tasks.name AS task_name,
            SUM(strftime('%s', end_time) - strftime('%s', start_time)) AS total_time
        FROM sessions
        JOIN tasks ON sessions.task_id = tasks.id
        WHERE sessions.user_id = ? AND end_time IS NOT NULL AND start_time >= DATE('now', '-7 days')
        GROUP BY task_name
    '''
    task_data = pd.read_sql(task_query, conn, params=(user_id,))

    # Запрос для данных по часам
    hour_query = '''
        SELECT 
            strftime('%H', start_time) AS hour,
            SUM(strftime('%s', end_time) - strftime('%s', start_time)) AS total_time_seconds
        FROM sessions
        WHERE user_id = ? AND end_time IS NOT NULL
        GROUP BY hour
        ORDER BY hour;
    '''
    hour_data = pd.read_sql(hour_query, conn, params=(user_id,))

    # Запрос для общего времени по задачам за всё время
    total_task_query = '''
        SELECT 
            tasks.name AS task_name,
            SUM(strftime('%s', end_time) - strftime('%s', start_time)) AS total_time
        FROM sessions
        JOIN tasks ON sessions.task_id = tasks.id
        WHERE sessions.user_id = ? AND end_time IS NOT NULL
        GROUP BY task_name
        ORDER BY total_time DESC;
    '''
    total_task_data = pd.read_sql(total_task_query, conn, params=(user_id,))

    conn.close()
    return daily_data, task_data, hour_data, total_task_data

def seconds_to_hh_mm(seconds):
    """Преобразует секунды в формат 'часы:минуты'."""
    seconds = int(seconds)  # Преобразуем в целое число
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"

def generate_dashboard(user_id):
    """Генерирует дашборд с 4 графиками и возвращает изображение в байтах."""
    daily_data, task_data, hour_data, total_task_data = get_data(user_id)

    if daily_data.empty or task_data.empty or hour_data.empty or total_task_data.empty:
        return None

    # Настройка стиля Seaborn
    sns.set_theme(style="whitegrid", palette="pastel")

    # Создаем сетку 2x2 для графиков
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Дашборд активности', fontsize=20, y=1.02)

    # Преобразуем даты в формат datetime
    daily_data['date'] = pd.to_datetime(daily_data['date'])

    # График 1: Общее время по дням
    sns.barplot(
        ax=axes[0, 0],
        x='date',
        y='total_time_seconds',
        data=daily_data,
        hue='date',
        palette='viridis',
        legend=False
    )
    axes[0, 0].set_title('Общее время по дням', fontsize=16)
    axes[0, 0].set_xlabel('Дата', fontsize=14)
    axes[0, 0].set_ylabel('Время (сек)', fontsize=14)
    axes[0, 0].tick_params(axis='x', rotation=45)

    # График 2: Время по задачам (круговая диаграмма)
    wedges, texts, autotexts = axes[0, 1].pie(
        task_data['total_time'],
        labels=None,  # Убираем labels с диаграммы
        autopct='%1.1f%%',
        colors=sns.color_palette('pastel'),
        startangle=90,
        pctdistance=0.85
    )
    axes[0, 1].set_title('Время по задачам', fontsize=16)

    # Добавляем легенду с названиями задач
    axes[0, 1].legend(
        wedges,
        task_data['task_name'],
        title="Задачи",
        loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1)  # Размещаем легенду справа от диаграммы
    )

    # График 3: Активность по часам (в процентах)
    total_seconds = hour_data['total_time_seconds'].sum()
    hour_data['percentage'] = (hour_data['total_time_seconds'] / total_seconds) * 100

    # Преобразуем время в московское (UTC+3)
    hour_data['hour'] = (hour_data['hour'].astype(int) + 3) % 24

    sns.barplot(
        ax=axes[1, 0],
        x='hour',
        y='percentage',
        data=hour_data,
        hue='hour',
        palette='viridis',
        legend=False
    )
    axes[1, 0].set_title('Активность по часам (МСК)', fontsize=16)
    axes[1, 0].set_xlabel('Час (МСК)', fontsize=14)
    axes[1, 0].set_ylabel('Процент активности', fontsize=14)

    # График 4: Общее время по задачам за всё время
    sns.barplot(
        ax=axes[1, 1],
        x='task_name',
        y='total_time',
        data=total_task_data,
        hue='task_name',
        palette='viridis',
        legend=False
    )
    axes[1, 1].set_title('Общее время по задачам', fontsize=16)
    axes[1, 1].set_xlabel('Задача', fontsize=14)
    axes[1, 1].set_ylabel('Время (часы:минуты)', fontsize=14)

    # Форматируем ось Y (время) в формат hh:mm
    def sec_to_hh_mm_formatter(x, pos):
        return seconds_to_hh_mm(x)

    axes[1, 1].yaxis.set_major_formatter(ticker.FuncFormatter(sec_to_hh_mm_formatter))

    # Поворачиваем подписи задач на 45 градусов
    axes[1, 1].tick_params(axis='x', rotation=45)

    # Улучшаем отступы между графиками
    plt.tight_layout()

    # Сохраняем график в байтовый объект
    img_bytes = BytesIO()
    plt.savefig(img_bytes, format='png', dpi=300, bbox_inches='tight')
    img_bytes.seek(0)
    plt.close()

    return img_bytes



