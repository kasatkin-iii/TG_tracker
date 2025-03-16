import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
import sqlite3

# Подключение к базе данных
def get_db_connection():
    return sqlite3.connect('time_tracker.db')

# Функция для получения данных
def get_data():
    conn = get_db_connection()
    query = '''
        SELECT 
            strftime('%Y-%m-%d', start_time) AS date,
            SUM(strftime('%s', end_time) - strftime('%s', start_time)) AS total_time
        FROM sessions
        WHERE end_time IS NOT NULL AND start_time >= DATE('now', '-7 days')
        GROUP BY date
    '''
    daily_data = pd.read_sql(query, conn)

    query = '''
        SELECT 
            tasks.name AS task_name,
            SUM(strftime('%s', end_time) - strftime('%s', start_time)) AS total_time
        FROM sessions
        JOIN tasks ON sessions.task_id = tasks.id
        WHERE end_time IS NOT NULL AND start_time >= DATE('now', '-7 days')
        GROUP BY task_name
    '''
    task_data = pd.read_sql(query, conn)

    conn.close()
    return daily_data, task_data

# Создание дашборда
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Статистика активности за последние 7 дней", style={'textAlign': 'center'}),
    dcc.Graph(id='daily-time-graph'),
    dcc.Graph(id='task-time-graph')
])

@app.callback(
    [Output('daily-time-graph', 'figure'),
     Output('task-time-graph', 'figure')],
    [Input('daily-time-graph', 'relayoutData')]
)
def update_graphs(_):
    daily_data, task_data = get_data()

    # График общего времени по дням
    fig1 = px.bar(
        daily_data,
        x='date',
        y='total_time',
        labels={'date': 'Дата', 'total_time': 'Общее время (сек)'},
        title="Общее время по дням"
    )

    # График времени по задачам
    fig2 = px.pie(
        task_data,
        names='task_name',
        values='total_time',
        title="Время по задачам"
    )

    return fig1, fig2

if __name__ == '__main__':
    app.run_server(debug=True)

