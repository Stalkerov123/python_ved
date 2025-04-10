"""
Клавиатуры для работы с ведомостями.
"""

import logging
import math
from typing import List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from models.vedomosti import VedomostInfo
from bot.config import BUTTON_LABELS, MAX_ITEMS_PER_PAGE

# Инициализация логирования
logger = logging.getLogger(__name__)


async def get_vedomosti_keyboard(vedomosti: List[VedomostInfo], page: int = 1) -> InlineKeyboardMarkup:
    """
    Создание инлайн-клавиатуры для выбора ведомости с пагинацией.

    Args:
        vedomosti: Список объектов ведомостей
        page: Номер страницы

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками ведомостей
    """
    try:
        if not vedomosti:
            return None

        # Определяем индексы для текущей страницы
        total_pages = math.ceil(len(vedomosti) / MAX_ITEMS_PER_PAGE)
        page = max(1, min(page, total_pages))
        start_idx = (page - 1) * MAX_ITEMS_PER_PAGE
        end_idx = min(start_idx + MAX_ITEMS_PER_PAGE, len(vedomosti))

        # Создаем клавиатуру
        keyboard_builder = InlineKeyboardBuilder()

        # Добавляем кнопки для ведомостей на текущей странице
        for ved in vedomosti[start_idx:end_idx]:
            # Добавляем статус ведомости к тексту кнопки
            status_emoji = "🔒" if ved.closed == "Да" else "🔓"
            button_text = f"{ved.discipline} ({ved.type}) {status_emoji}"

            keyboard_builder.add(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"vedomost_{ved.id}"
                )
            )

        # Добавляем кнопки навигации
        navigation_buttons = []

        # Кнопка "Назад" (к списку групп)
        navigation_buttons.append(
            InlineKeyboardButton(
                text=BUTTON_LABELS["back"],
                callback_data="vedomost_back"
            )
        )

        # Кнопки пагинации
        if total_pages > 1:
            if page > 1:
                navigation_buttons.append(
                    InlineKeyboardButton(
                        text=BUTTON_LABELS["prev_page"],
                        callback_data="vedomost_prev_page"
                    )
                )

            if page < total_pages:
                navigation_buttons.append(
                    InlineKeyboardButton(
                        text=BUTTON_LABELS["next_page"],
                        callback_data="vedomost_next_page"
                    )
                )

        # Кнопка возврата в главное меню
        navigation_buttons.append(
            InlineKeyboardButton(
                text=BUTTON_LABELS["main_menu"],
                callback_data="main_menu"
            )
        )

        # Добавляем кнопки навигации в клавиатуру
        for button in navigation_buttons:
            keyboard_builder.add(button)

        # Размещаем кнопки: ведомости в одну колонку, навигационные в ряд
        keyboard_builder.adjust(1, len(navigation_buttons))

        return keyboard_builder.as_markup()

    except Exception as e:
        logger.error(f"Ошибка при создании клавиатуры ведомостей: {e}")
        return None


def get_vedomost_details_keyboard() -> InlineKeyboardMarkup:
    """
    Создание инлайн-клавиатуры для работы с детальной информацией о ведомости.

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками действий
    """
    try:
        # Создаем клавиатуру
        keyboard_builder = InlineKeyboardBuilder()

        # Добавляем кнопки действий
        keyboard_builder.add(
            InlineKeyboardButton(
                text=BUTTON_LABELS["show_details"],
                callback_data="show_details"
            )
        )

        # Добавляем кнопки экспорта
        keyboard_builder.add(
            InlineKeyboardButton(
                text=BUTTON_LABELS["export_json"],
                callback_data="export_json"
            )
        )

        keyboard_builder.add(
            InlineKeyboardButton(
                text=BUTTON_LABELS["export_csv"],
                callback_data="export_csv"
            )
        )

        keyboard_builder.add(
            InlineKeyboardButton(
                text=BUTTON_LABELS["export_excel"],
                callback_data="export_excel"
            )
        )

        # Добавляем кнопку "Назад"
        keyboard_builder.add(
            InlineKeyboardButton(
                text=BUTTON_LABELS["back"],
                callback_data="vedomost_detail_back"
            )
        )

        # Добавляем кнопку "Главное меню"
        keyboard_builder.add(
            InlineKeyboardButton(
                text=BUTTON_LABELS["main_menu"],
                callback_data="main_menu"
            )
        )

        # Размещаем кнопки: действия в одну колонку, экспорт в один ряд, навигация отдельно
        keyboard_builder.adjust(1, 3, 1, 1)

        return keyboard_builder.as_markup()

    except Exception as e:
        logger.error(f"Ошибка при создании клавиатуры действий с ведомостью: {e}")
        return None


def get_search_keyboard() -> InlineKeyboardMarkup:
    """
    Создание инлайн-клавиатуры главного меню поиска.

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками поиска
    """
    try:
        keyboard_builder = InlineKeyboardBuilder()

        # Добавляем кнопки
        keyboard_builder.add(
            InlineKeyboardButton(
                text="🔍 Поиск по зачетной книжке",
                callback_data="search_by_record_book"
            )
        )

        keyboard_builder.add(
            InlineKeyboardButton(
                text="📋 Просмотр по факультетам и группам",
                callback_data="browse_faculties"
            )
        )

        # Размещаем кнопки в колонку
        keyboard_builder.adjust(1)

        return keyboard_builder.as_markup()

    except Exception as e:
        logger.error(f"Ошибка при создании клавиатуры поиска: {e}")
        # Возвращаем пустую клавиатуру в случае ошибки
        return InlineKeyboardBuilder().as_markup()


def get_student_details_keyboard(record_book: str) -> InlineKeyboardMarkup:
    """
    Создание инлайн-клавиатуры для действий с результатами студента.

    Args:
        record_book: Номер зачетной книжки студента

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками действий
    """
    try:
        keyboard_builder = InlineKeyboardBuilder()

        # Добавляем кнопки действий
        keyboard_builder.add(
            InlineKeyboardButton(
                text="📊 Экспорт результатов",
                callback_data=f"export_student_{record_book}"
            )
        )

        # Добавляем кнопку "Назад в меню"
        keyboard_builder.add(
            InlineKeyboardButton(
                text="🔍 Новый поиск",
                callback_data="search_by_record_book"
            )
        )

        # Добавляем кнопку "Главное меню"
        keyboard_builder.add(
            InlineKeyboardButton(
                text="🏠 Главное меню",
                callback_data="main_menu"
            )
        )

        # Размещаем кнопки
        keyboard_builder.adjust(1)

        return keyboard_builder.as_markup()

    except Exception as e:
        logger.error(f"Ошибка при создании клавиатуры результатов студента: {e}")
        # Возвращаем пустую клавиатуру в случае ошибки
        return InlineKeyboardBuilder().as_markup()