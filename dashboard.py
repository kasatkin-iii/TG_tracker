import sqlite3
import matplotlib

matplotlib.use('Agg')  # Важно для headless-режима
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns
import pandas as pd
from io import BytesIO
import logging
from typing import Tuple, Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_db_connection() -> sqlite3.Connection:
    """Создает и возвращает соединение с базой данных."""
    try:
        conn = sqlite3.connect('/data/time_tracker.db')
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(f"Ошибка подключения к БД: {e}")
        raise


def safe_get_data(query: str, conn: sqlite3.Connection, params: tuple) -> pd.DataFrame:
    """Безопасное выполнение SQL-запроса с возвратом DataFrame."""
    try:
        df = pd.read_sql(query, conn, params=params)
        return df
    except Exception as e:
        logger.error(f"Ошибка выполнения запроса: {e}\nЗапрос: {query}")
        return pd.DataFrame()


def get_data(user_id: int) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Получает и обрабатывает данные для дашборда."""
    conn = None  # Явная инициализация
    try:
        conn = get_db_connection()

        # Запросы с явным указанием типов данных
        daily_query = """
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
        """
        daily_data = safe_get_data(daily_query, conn, (user_id,))

        task_query = """
        SELECT 
            tasks.name AS task_name,
            COALESCE(SUM(strftime('%s', end_time) - strftime('%s', start_time)), 0) AS total_time
        FROM sessions
        JOIN tasks ON sessions.task_id = tasks.id
        WHERE sessions.user_id = ? AND end_time IS NOT NULL AND start_time >= DATE('now', '-7 days')
        GROUP BY task_name;
        """
        task_data = safe_get_data(task_query, conn, (user_id,))

        hour_query = """
        SELECT 
            strftime('%H', start_time) AS hour,
            COALESCE(SUM(strftime('%s', end_time) - strftime('%s', start_time)), 0) AS total_time_seconds
        FROM sessions
        WHERE user_id = ? AND end_time IS NOT NULL
        GROUP BY hour
        ORDER BY hour;
        """
        hour_data = safe_get_data(hour_query, conn, (user_id,))

        total_task_query = """
        SELECT 
            tasks.name AS task_name,
            COALESCE(SUM(strftime('%s', end_time) - strftime('%s', start_time)), 0) AS total_time
        FROM sessions
        JOIN tasks ON sessions.task_id = tasks.id
        WHERE sessions.user_id = ? AND end_time IS NOT NULL
        GROUP BY task_name
        ORDER BY total_time DESC;
        """
        total_task_data = safe_get_data(total_task_query, conn, (user_id,))

        # Преобразование типов данных
        if not daily_data.empty:
            daily_data['date'] = pd.to_datetime(daily_data['date'], errors='coerce')
            daily_data['total_time_seconds'] = pd.to_numeric(daily_data['total_time_seconds'], errors='coerce').fillna(
                0)

        if not task_data.empty:
            task_data['total_time'] = pd.to_numeric(task_data['total_time'], errors='coerce').fillna(0)

        if not hour_data.empty:
            hour_data['hour'] = pd.to_numeric(hour_data['hour'], errors='coerce').fillna(0)
            hour_data['total_time_seconds'] = pd.to_numeric(hour_data['total_time_seconds'], errors='coerce').fillna(0)

        if not total_task_data.empty:
            total_task_data['total_time'] = pd.to_numeric(total_task_data['total_time'], errors='coerce').fillna(0)

        return daily_data, task_data, hour_data, total_task_data


    except Exception as e:
        logger.error(f"Ошибка в get_data: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    finally:
        if conn:
            conn.close()


def seconds_to_hh_mm(seconds: int) -> str:
    """Преобразует секунды в формат 'часы:минуты'."""
    try:
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"
    except (ValueError, TypeError):
        return "00:00"


def create_plot_image() -> BytesIO:
    """Создает и возвращает байтовый объект для изображения."""
    img_bytes = BytesIO()
    plt.savefig(img_bytes, format='png', dpi=300, bbox_inches='tight')
    img_bytes.seek(0)
    plt.close('all')  # Важно для очистки памяти
    return img_bytes


def generate_dashboard(user_id: int) -> Optional[BytesIO]:
    """Генерирует дашборд с 4 графиками."""
    try:
        logger.info(f"Начало генерации дашборда для user_id={user_id}")

        # Получаем и проверяем данные
        daily_data, task_data, hour_data, total_task_data = get_data(user_id)

        if (daily_data.empty or task_data.empty or
                hour_data.empty or total_task_data.empty):
            logger.warning("Один из датафреймов пуст")
            return None

        # Настройка стиля (исправленная версия)
        sns.set_theme(style="whitegrid", palette="pastel", font="DejaVu Sans")
        plt.rcParams['font.family'] = 'DejaVu Sans'

        # Создаем сетку графиков
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Дашборд активности', fontsize=20, y=1.02)

        # График 1: Общее время по дням (с исправлениями)
        try:
            if not daily_data.empty:
                # Явное преобразование типов
                daily_data['date'] = pd.to_datetime(daily_data['date'])
                daily_data['total_time_seconds'] = pd.to_numeric(daily_data['total_time_seconds'])

                # Сортировка по дате
                daily_data = daily_data.sort_values('date')

                # Исправленный способ установки форматера
                ax = sns.barplot(
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

                # Правильное форматирование дат на оси X
                locator = plt.MaxNLocator(len(daily_data))
                axes[0, 0].xaxis.set_major_locator(locator)
                axes[0, 0].xaxis.set_major_formatter(
                    plt.FixedFormatter(daily_data['date'].dt.strftime('%d.%m')
                    )
                )
                axes[0, 0].tick_params(axis='x', rotation=45)
        except Exception as e:
            logger.error(f"Ошибка в графике 1: {e}")
            axes[0, 0].clear()
            axes[0, 0].text(0.5, 0.5, 'Ошибка данных', ha='center', va='center')
            axes[0, 0].set_title('Общее время по дням (ошибка)', fontsize=16)

        # График 2: Время по задачам (с дополнительными проверками)
        try:
            if not task_data.empty:
                task_data['total_time'] = pd.to_numeric(task_data['total_time'])
                total_sum = task_data['total_time'].sum()

                if total_sum > 0:
                    # Нормализация данных для круговой диаграммы
                    task_data = task_data[task_data['total_time'] > 0].copy()
                    task_data['percentage'] = task_data['total_time'] / total_sum * 100

                    wedges, _, _ = axes[0, 1].pie(
                        task_data['total_time'],
                        labels=None,
                        autopct=lambda p: f'{p:.1f}%' if p > 3 else '',
                        colors=sns.color_palette('pastel'),
                        startangle=90,
                        pctdistance=0.85,
                        textprops={'fontsize': 10}
                    )
                    axes[0, 1].legend(
                        wedges,
                        task_data['task_name'],
                        title="Задачи",
                        loc="center left",
                        bbox_to_anchor=(1, 0.5),
                        fontsize=10
                    )
                axes[0, 1].set_title('Время по задачам', fontsize=16)
            else:
                axes[0, 1].text(0.5, 0.5, 'Нет данных', ha='center', va='center')
                axes[0, 1].set_title('Время по задачам', fontsize=16)
        except Exception as e:
            logger.error(f"Ошибка в графике 2: {e}")
            axes[0, 1].clear()
            axes[0, 1].text(0.5, 0.5, 'Ошибка данных', ha='center', va='center')
            axes[0, 1].set_title('Время по задачам (ошибка)', fontsize=16)

        # График 3: Активность по часам (с преобразованием типов)
        try:
            if not hour_data.empty:
                hour_data['hour'] = pd.to_numeric(hour_data['hour'])
                hour_data['total_time_seconds'] = pd.to_numeric(hour_data['total_time_seconds'])

                # Преобразование в московское время
                hour_data['hour'] = (hour_data['hour'] + 3) % 24
                hour_data = hour_data.sort_values('hour')

                total_seconds = hour_data['total_time_seconds'].sum()
                if total_seconds > 0:
                    hour_data['percentage'] = hour_data['total_time_seconds'] / total_seconds * 100

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
                axes[1, 0].set_xticks(range(0, 24, 2))
            else:
                axes[1, 0].text(0.5, 0.5, 'Нет данных', ha='center', va='center')
                axes[1, 0].set_title('Активность по часам (МСК)', fontsize=16)
        except Exception as e:
            logger.error(f"Ошибка в графике 3: {e}")
            axes[1, 0].clear()
            axes[1, 0].text(0.5, 0.5, 'Ошибка данных', ha='center', va='center')
            axes[1, 0].set_title('Активность по часам (ошибка)', fontsize=16)

        # График 4: Общее время по задачам (с защитой от ошибок)
        try:
            if not total_task_data.empty:
                total_task_data['total_time'] = pd.to_numeric(total_task_data['total_time'])

                sns.barplot(
                    ax=axes[1, 1],
                    x='task_name',
                    y='total_time',
                    data=total_task_data,
                    hue='task_name',
                    palette='viridis',
                    legend=False
                )

                # Форматирование оси Y
                axes[1, 1].yaxis.set_major_formatter(
                    ticker.FuncFormatter(lambda x, _: seconds_to_hh_mm(x))
                )
                axes[1, 1].set_title('Общее время по задачам', fontsize=16)
                axes[1, 1].set_xlabel('Задача', fontsize=14)
                axes[1, 1].set_ylabel('Время (часы:минуты)', fontsize=14)

                # Автоматический поворот подписей
                axes[1, 1].tick_params(axis='x', rotation=45, labelsize=10)
            else:
                axes[1, 1].text(0.5, 0.5, 'Нет данных', ha='center', va='center')
                axes[1, 1].set_title('Общее время по задачам', fontsize=16)
        except Exception as e:
            logger.error(f"Ошибка в графике 4: {e}")
            axes[1, 1].clear()
            axes[1, 1].text(0.5, 0.5, 'Ошибка данных', ha='center', va='center')
            axes[1, 1].set_title('Общее время по задачам (ошибка)', fontsize=16)

        plt.tight_layout(pad=3.0)
        return create_plot_image()

    except Exception as e:
        logger.error(f"Критическая ошибка в generate_dashboard: {e}", exc_info=True)
        return None


