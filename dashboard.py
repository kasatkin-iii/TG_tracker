import sqlite3
import pandas as pd
import plotly.express as px
from io import BytesIO


def get_db_connection():
    """Создает соединение с базой данных."""
    return sqlite3.connect('time_tracker.db')


def get_data(user_id):
    """Получает данные из базы данных для конкретного пользователя."""
    conn = get_db_connection()

    # Запрос для данных по дням
    daily_query = '''
        SELECT 
            strftime('%Y-%m-%d', start_time) AS date,
            SUM(strftime('%s', end_time) - strftime('%s', start_time)) AS total_time
        FROM sessions
        WHERE sessions.user_id = ? AND end_time IS NOT NULL AND start_time >= DATE('now', '-7 days')
        GROUP BY date
    '''
    daily_data = pd.read_sql(daily_query, conn, params=(user_id,))

    # Запрос для данных по задачам
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

    conn.close()
    return daily_data, task_data


def generate_dashboard(user_id):
    """Генерирует графики и возвращает их как изображения в байтах."""
    daily_data, task_data = get_data(user_id)

    if daily_data.empty or task_data.empty:
        return None

    # График общего времени по дням
    fig1 = px.bar(
        daily_data,
        x='date',
        y='total_time',
        labels={'date': 'Дата', 'total_time': 'Общее время (сек)'},
        title="Общее время по дням",
        template='plotly_dark',
        color_discrete_sequence=['#00CC96']
    )
    fig1.update_layout(
        plot_bgcolor='#222222',
        paper_bgcolor='#111111',
        font_color='white'
    )

    # Круговая диаграмма по задачам
    fig2 = px.pie(
        task_data,
        names='task_name',
        values='total_time',
        title="Время по задачам",
        template='plotly_dark',
        hole=0.3,
        color_discrete_sequence=px.colors.qualitative.Dark24
    )
    fig2.update_layout(
        plot_bgcolor='#222222',
        paper_bgcolor='#111111',
        font_color='white'
    )

    # Сохраняем графики в байтовые объекты
    img_bytes1 = BytesIO()
    fig1.write_image(img_bytes1, format='png', width=800, height=400)
    img_bytes1.seek(0)

    img_bytes2 = BytesIO()
    fig2.write_image(img_bytes2, format='png', width=800, height=400)
    img_bytes2.seek(0)

    return [img_bytes1, img_bytes2]

