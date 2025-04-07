![Логотип бота](/icon/tracker.icon.png)

# Time Tracker Bot

**Telegram-бот для учёта времени и сбора статистики по вашим задачам.**  
Фиксируйте время, потраченное на задачи, отслеживайте регулярность и другие показатели — без ручного ведения таблиц.

## Оглавление
- [Мотивация](#Мотивация)
- [Какие проблемы решает бот?](#Какие-проблемы-решает-бот)
- [Технологии](#Технологии)
- [Функционал](#Функционал)
- [Как попробовать? ](#Как-попробовать)
- [Планы по развитию](#Планы-по-развитию)
- [Обратная связь](#Обратная-связь)
- [Примеры](#Примеры)

## Мотивация
Для гарантированного достижения поставленных результатов важно постоянство.

- Для хорошей физической формы — регулярные тренировки.
- Для успешной сдачи экзаменов — планомерная подготовка. 
- Для овладевания музыкальным инструментом — постоянная практика.

Я столкнулся с проблемой того, что время трачу, усилия прикладываю, но желаемого результата не вижу.
### **💡Идея:** 
Бот внутри мессенджера, в котором можно фиксировать время на задачи и смотреть статистику по ним.


## Какие проблемы решает бот?
### Проблема:
- Люди теряют до **30% времени** из-за отсутствия чёткого трекинга (по данным RescueTime).
- Ручное ведение таблиц отнимает ещё больше времени и демотивирует.
- Сложно анализировать данные: "Сколько часов ушло на проект X?"

### Решение:
- **Автоматический учёт, по нажатию клавиши** через Telegram (куда пользователи итак заходят 20+ раз в день). 
- **Готовая аналитика** *простая* — текстовый формат, *поинтереснее* — виузализация с графиками.
- **Почему не подошли готовые решения** удобство использования в Telegram, практика разработки бота.

## Технологии:
### Основной стек
```python
├── Python 3.13 + python-telegram-bot
|  ├── async/await # асинхронное программиование
|  ├── ConversationHandler # многоступенчатые диалоги
|  └── Inline/ReplyKeyboardMarkup # удобный интерфейс
├── SQLite # хранение данных
├── Docker # для простого деплоя
```
### Структура БД
![Диаграмма](/icon/er-d.png) 

## Функционал:
| Функция                                | Комментарий                       |
|----------------------------------------|-----------------------------------|
| Запустить▶️/остановить⏹️ отсчет времени | Работа с фиксацией времени        |
| Показать активную задачу🔄             | Просмотр активной задачи          |
| Меню ⚙️                                | Показать остальные возможности    |
| Добавить 🆕/удалить 🗑 задачу          | Работа со списком задач           |
| Список задач 📋                        | Посмотреть все добавленные задачи |
| Статистика 📈                          | Просмотр статистики               |


## Как попробовать? 

**В Telegram:** [Тайм трекер бот](https://t.me/Simple_TGtracker_bot)

**Запустить локально:**
- Клонировать репозиторий;
- Добавить свой token в *config.py;*
- Собрать Docker-образ и запустить контейнер.

**файл БД создаётся сам, но удалится после остановки контейнера, если планируется не только тест, создайте постоянное хранилище.*


## Планы по развитию

- **Добавить возможность *"прощать ошибки"*** - корректировать время начала и окончания сессии по задаче, если забыл запустить или остановить сессию вовремя;
- **Добавить кастомизацию статистики** - выбор периода и дополнительных метрик.



## Обратная связь

Нашли баг или есть идея?
Пишите в Issues или мне в Telegram: [@Kasatkin_iii](https://t.me/Kasatkin_iii)


**Цитата из интернета:**
*«Плохая новость в том, что время летит. Хорошая новость в том, что вы пилот» - Майкл Альтшулер (предпрениматель, писатель)*

## Примеры
| ![Старт](/icon/Start.png) | ![Меню](/icon/Menu.png) |
|---------------------------|-------------------------|
| Старт                     | Меню                    |
