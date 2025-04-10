"""
Клавиатуры для настройки профиля пользователя.
"""

import logging
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database_manager import DatabaseManager

# Инициализация логирования
logger = logging.getLogger(__name__)


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """
    Создание инлайн-клавиатуры для меню настроек.

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками настроек
    """
    try:
        keyboard_builder = InlineKeyboardBuilder()

        # Добавляем кнопки настроек
        keyboard_builder.add(
            InlineKeyboardButton(
                text="🏫 Изменить факультет",
                callback_data="settings_faculty"
            )
        )

        keyboard_builder.add(
            InlineKeyboardButton(
                text="👥 Изменить группу",
                callback_data="settings_group"
            )
        )

        keyboard_builder.add(
            InlineKeyboardButton(
                text="📝 Изменить номер зачетки",
                callback_data="settings_record_book"
            )
        )

        keyboard_builder.add(
            InlineKeyboardButton(
                text="🔔 Настройка уведомлений",
                callback_data="settings_notifications"
            )
        )

        # Кнопка возврата в главное меню
        keyboard_builder.add(
            InlineKeyboardButton(
                text="🏠 Вернуться в главное меню",
                callback_data="settings_back"
            )
        )

        # Размещаем кнопки в одну колонку
        keyboard_builder.adjust(1)

        return keyboard_builder.as_markup()

    except Exception as e:
        logger.error(f"Ошибка при создании клавиатуры настроек: {e}")
        return InlineKeyboardBuilder().as_markup()


async def get_faculty_settings_keyboard(db_manager: DatabaseManager) -> InlineKeyboardMarkup:
    """
    Создание инлайн-клавиатуры для выбора факультета в настройках.

    Args:
        db_manager: Менеджер базы данных

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками факультетов
    """
    try:
        keyboard_builder = InlineKeyboardBuilder()

        # Получаем список факультетов из базы данных
        faculties = db_manager.get_faculties()

        if not faculties:
            logger.warning("Не удалось получить список факультетов из базы данных")
            # Добавляем только кнопку "Назад"
            keyboard_builder.add(
                InlineKeyboardButton(
                    text="« Назад",
                    callback_data="faculty_settings_back"
                )
            )
            return keyboard_builder.as_markup()

        # Добавляем кнопки для каждого факультета
        for faculty in faculties:
            keyboard_builder.add(
                InlineKeyboardButton(
                    text=faculty['name'],
                    callback_data=f"faculty_settings_{faculty['id']}"
                )
            )

        # Добавляем кнопку "Назад"
        keyboard_builder.add(
            InlineKeyboardButton(
                text="« Назад",
                callback_data="faculty_settings_back"
            )
        )

        # Размещаем кнопки в одну колонку
        keyboard_builder.adjust(1)

        return keyboard_builder.as_markup()

    except Exception as e:
        logger.error(f"Ошибка при создании клавиатуры выбора факультета: {e}")
        return InlineKeyboardBuilder().as_markup()


async def get_group_settings_keyboard(db_manager: DatabaseManager, faculty_id: str) -> InlineKeyboardMarkup:
    """
    Создание инлайн-клавиатуры для выбора группы в настройках.

    Args:
        db_manager: Менеджер базы данных
        faculty_id: ID факультета

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками групп
    """
    try:
        keyboard_builder = InlineKeyboardBuilder()

        # Получаем список групп для факультета из базы данных
        groups = db_manager.get_groups(faculty_id)

        if not groups:
            logger.warning(f"Не удалось получить список групп для факультета {faculty_id} из базы данных")
            # Добавляем только кнопку "Назад"
            keyboard_builder.add(
                InlineKeyboardButton(
                    text="« Назад",
                    callback_data="group_settings_back"
                )
            )
            return keyboard_builder.as_markup()

        # Добавляем кнопки для каждой группы
        for group in groups:
            keyboard_builder.add(
                InlineKeyboardButton(
                    text=group['name'],
                    callback_data=f"group_settings_{group['id']}"
                )
            )

        # Добавляем кнопку "Назад"
        keyboard_builder.add(
            InlineKeyboardButton(
                text="« Назад",
                callback_data="group_settings_back"
            )
        )

        # Размещаем кнопки в две колонки, кроме кнопки "Назад"
        keyboard_builder.adjust(2, 2, 1)

        return keyboard_builder.as_markup()

    except Exception as e:
        logger.error(f"Ошибка при создании клавиатуры выбора группы: {e}")
        return InlineKeyboardBuilder().as_markup()


def get_notification_settings_keyboard(notify_enabled: bool = True) -> InlineKeyboardMarkup:
    """
    Создание инлайн-клавиатуры для настройки уведомлений.

    Args:
        notify_enabled: Текущее состояние уведомлений (включены/выключены)

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками настройки уведомлений
    """
    try:
        keyboard_builder = InlineKeyboardBuilder()

        # Добавляем кнопки включения/выключения уведомлений
        keyboard_builder.add(
            InlineKeyboardButton(
                text="🔔 Включить уведомления" if not notify_enabled else "🔔 Уведомления включены",
                callback_data="notifications_enable"
            )
        )

        keyboard_builder.add(
            InlineKeyboardButton(
                text="🔕 Отключить уведомления" if notify_enabled else "🔕 Уведомления отключены",
                callback_data="notifications_disable"
            )
        )

        # Добавляем кнопку "Назад"
        keyboard_builder.add(
            InlineKeyboardButton(
                text="« Назад",
                callback_data="notifications_back"
            )
        )

        # Размещаем кнопки в одну колонку
        keyboard_builder.adjust(1)

        return keyboard_builder.as_markup()

    except Exception as e:
        logger.error(f"Ошибка при создании клавиатуры настройки уведомлений: {e}")
        return InlineKeyboardBuilder().as_markup()