"""
Состояния диалога для конечного автомата (FSM) Telegram бота.
"""

from aiogram.fsm.state import StatesGroup, State


class BotStates(StatesGroup):
    """
    Группа состояний диалога для бота.

    Attributes:
        select_faculty: Состояние выбора факультета
        select_group: Состояние выбора группы
        select_vedomost: Состояние выбора ведомости
        view_vedomost: Состояние просмотра ведомости
        export_vedomost: Состояние экспорта ведомости
        enter_record_book: Состояние ввода номера зачетной книжки
        search_record_book: Состояние поиска по номеру зачетной книжки
        view_student_results: Состояние просмотра результатов студента

        # Состояния для настроек
        settings_menu: Состояние меню настроек
        settings_faculty: Состояние выбора факультета в настройках
        settings_group: Состояние выбора группы в настройках
        settings_record_book: Состояние ввода номера зачетной книжки в настройках
        settings_notifications: Состояние настройки уведомлений
    """
    # Основные состояния
    select_faculty = State()
    select_group = State()
    select_vedomost = State()
    view_vedomost = State()
    export_vedomost = State()

    # Состояния для поиска по зачетной книжке
    enter_record_book = State()
    search_record_book = State()
    view_student_results = State()

    # Состояния для настроек
    settings_menu = State()
    settings_faculty = State()
    settings_group = State()
    settings_record_book = State()
    settings_notifications = State()