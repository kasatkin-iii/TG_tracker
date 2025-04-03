import sqlite3
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import logging
import pandas as pd
from datetime import datetime, timedelta

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dashboard.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Настройка стиля Seaborn
sns.set_theme(
    style="whitegrid",
    palette="pastel",
    font="DejaVu Sans",
    rc={
        'axes.titlesize': 14,
        'axes.labelsize': 12,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'figure.titlesize': 16
    }
)


def get_dashboard_data(user_id):
    """Получаем все данные для дашборда с точным расчетом времени"""
    conn = None
    try:
        conn = sqlite3.connect('/data/time_tracker.db')

        # 1. Данные по дням (последние 7 дней)
        date_query = """
        WITH RECURSIVE date_range AS (
            SELECT date('now', '-6 days') AS date
            UNION ALL
            SELECT date(date, '+1 day')
            FROM date_range
            WHERE date < date('now')
        )
        SELECT 
            date_range.date,
            COALESCE(SUM(strftime('%s', sessions.end_time) - strftime('%s', sessions.start_time)), 0) AS seconds
        FROM date_range
        LEFT JOIN sessions ON date_range.date = date(sessions.start_time)
                          AND sessions.user_id = ?
                          AND sessions.end_time IS NOT NULL
        GROUP BY date_range.date
        ORDER BY date_range.date
        """

        # 2. Данные по задачам (все время)
        task_query = """
        SELECT 
            tasks.name AS task_name,
            SUM(strftime('%s', sessions.end_time) - strftime('%s', sessions.start_time)) AS seconds
        FROM sessions
        JOIN tasks ON sessions.task_id = tasks.id
        WHERE sessions.user_id = ? AND sessions.end_time IS NOT NULL
        GROUP BY tasks.name
        ORDER BY seconds DESC
        """

        # 3. Точный расчет активности по часам
        hour_query = """
        WITH RECURSIVE hour_intervals AS (
            SELECT 
                sessions.rowid,
                sessions.start_time,
                sessions.end_time,
                sessions.start_time AS interval_start,
                CASE 
                    WHEN datetime(sessions.start_time, 'start of hour', '+1 hour') < sessions.end_time THEN
                        datetime(sessions.start_time, 'start of hour', '+1 hour')
                    ELSE
                        sessions.end_time
                END AS interval_end
            FROM sessions
            WHERE sessions.user_id = ? AND sessions.end_time IS NOT NULL

            UNION ALL

            SELECT 
                h.rowid,
                h.start_time,
                h.end_time,
                h.interval_end AS interval_start,
                CASE 
                    WHEN datetime(h.interval_end, 'start of hour', '+1 hour') < h.end_time THEN
                        datetime(h.interval_end, 'start of hour', '+1 hour')
                    ELSE
                        h.end_time
                END AS interval_end
            FROM hour_intervals h
            WHERE h.interval_end < h.end_time
        )
        SELECT 
            strftime('%H', interval_start) AS hour,
            SUM(strftime('%s', interval_end) - strftime('%s', interval_start)) AS seconds
        FROM hour_intervals
        GROUP BY hour
        ORDER BY hour
        """

        # Выполняем запросы
        daily_data = pd.read_sql(date_query, conn, params=(user_id,))
        task_data = pd.read_sql(task_query, conn, params=(user_id,))
        hour_data = pd.read_sql(hour_query, conn, params=(user_id,))

        # Преобразование данных
        def safe_convert(df, col, convert_fn):
            try:
                return convert_fn(df[col])
            except:
                return df[col]

        daily_data['date'] = safe_convert(daily_data, 'date', pd.to_datetime)
        daily_data['hours'] = daily_data['seconds'] / 3600

        task_data['hours'] = task_data['seconds'] / 3600
        if task_data['seconds'].sum() > 0:
            task_data['percentage'] = task_data['seconds'] / task_data['seconds'].sum() * 100
        else:
            task_data['percentage'] = 0

        hour_data['hour'] = safe_convert(hour_data, 'hour', pd.to_numeric)
        hour_data['hours'] = hour_data['seconds'] / 3600

        return daily_data, task_data, hour_data

    except Exception as e:
        logger.error(f"Ошибка получения данных: {str(e)}", exc_info=True)
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    finally:
        if conn:
            conn.close()


def generate_dashboard(user_id):
    """Генерация финального дашборда с 4 графиками"""
    try:
        logger.info(f"Старт генерации дашборда для user_id={user_id}")

        # Получаем данные
        daily_data, task_data, hour_data = get_dashboard_data(user_id)

        # Создаем фигуру с 4 subplots
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'Дашборд активности', y=1.02)

        # --- График 1: Активность по дням ---
        if not daily_data.empty:
            ax = sns.barplot(
                ax=axes[0, 0],
                x='date',
                y='hours',
                data=daily_data,
                hue='date',
                palette="viridis",
                legend=False,
                dodge=False
            )

            axes[0, 0].set_title('Активность по дням (последние 7 дней)')
            axes[0, 0].set_xlabel('Дата')
            axes[0, 0].set_ylabel('Часы')

            # Форматирование дат
            ax.set_xticklabels(
                [day.strftime('%d.%m') for day in daily_data['date']],
                rotation=45,
                ha='right'
            )

            # Добавляем значения на столбцах
            for p in ax.patches:
                if p.get_height() > 0:
                    ax.annotate(
                        f"{p.get_height():.1f}ч",
                        (p.get_x() + p.get_width() / 2., p.get_height()),
                        ha='center',
                        va='center',
                        xytext=(0, 5),
                        textcoords='offset points'
                    )

        # --- График 2: Распределение по задачам ---
        if not task_data.empty and task_data['seconds'].sum() > 0:
            # Фильтруем задачи с <1% времени
            filtered_tasks = task_data[task_data['percentage'] >= 1].copy()
            other_time = task_data[task_data['percentage'] < 1]['seconds'].sum()

            if other_time > 0:
                other_row = pd.DataFrame([{
                    'task_name': 'Другие',
                    'seconds': other_time,
                    'hours': other_time / 3600,
                    'percentage': other_time / task_data['seconds'].sum() * 100
                }])
                filtered_tasks = pd.concat([filtered_tasks, other_row])

            # Круговая диаграмма
            wedges, _, _ = axes[0, 1].pie(
                filtered_tasks['seconds'],
                labels=None,
                autopct=lambda p: f'{p:.1f}%' if p >= 3 else '',
                startangle=90,
                pctdistance=0.8,
                colors=sns.color_palette("pastel", len(filtered_tasks)),
                textprops={'fontsize': 9}
            )

            axes[0, 1].set_title('Распределение времени по задачам')

            # Легенда с часами
            axes[0, 1].legend(
                wedges,
                [f"{name} ({hours:.1f}ч)" for name, hours in zip(filtered_tasks['task_name'], filtered_tasks['hours'])],
                title="Задачи",
                loc="center left",
                bbox_to_anchor=(1, 0.5),
                fontsize=9
            )

        # --- График 3: Активность по часам (МСК) ---
        if not hour_data.empty:
            # Преобразуем в московское время и создаем полный диапазон часов
            hour_data['hour'] = (hour_data['hour'] + 3) % 24
            all_hours = pd.DataFrame({'hour': range(24)})
            hour_data = pd.merge(all_hours, hour_data, on='hour', how='left').fillna({'hours': 0})

            ax = sns.barplot(
                ax=axes[1, 0],
                x='hour',
                y='hours',
                data=hour_data,
                hue='hour',
                palette="rocket",
                legend=False,
                dodge=False
            )

            axes[1, 0].set_title('Активность по часам (МСК)')
            axes[1, 0].set_xlabel('Час дня')
            axes[1, 0].set_ylabel('Часы')
            axes[1, 0].set_xticks(range(0, 24, 2))

            # Подписи значений
            for p in ax.patches:
                if p.get_height() > 0.1:  # Показываем только >6 минут
                    ax.annotate(
                        f"{p.get_height():.1f}ч",
                        (p.get_x() + p.get_width() / 2., p.get_height()),
                        ha='center',
                        va='center',
                        xytext=(0, 5),
                        textcoords='offset points',
                        fontsize=8
                    )

        # --- График 4: Топ задач за все время ---
        if not task_data.empty:
            top_tasks = task_data.head(10).copy()

            ax = sns.barplot(
                ax=axes[1, 1],
                x='hours',
                y='task_name',
                data=top_tasks,
                hue='task_name',
                palette="viridis",
                legend=False,
                dodge=False
            )

            axes[1, 1].set_title('Топ задач за все время')
            axes[1, 1].set_xlabel('Часы')
            axes[1, 1].set_ylabel('')

            # Подписи справа от столбцов
            for p in ax.patches:
                if p.get_width() > 0.1:  # Показываем только >6 минут
                    ax.annotate(
                        f"{p.get_width():.1f}ч",
                        (p.get_width(), p.get_y() + p.get_height() / 2.),
                        ha='left',
                        va='center',
                        xytext=(5, 0),
                        textcoords='offset points',
                        fontsize=9
                    )

            axes[1, 1].tick_params(axis='y', labelsize=9)

        # Общие настройки
        plt.tight_layout(pad=3.0)

        # Сохраняем в байты
        img_bytes = BytesIO()
        plt.savefig(img_bytes, format='png', dpi=120, bbox_inches='tight')
        img_bytes.seek(0)
        plt.close()

        logger.info("Дашборд успешно сгенерирован")
        return img_bytes

    except Exception as e:
        logger.error(f"Ошибка генерации дашборда: {str(e)}", exc_info=True)
        return None