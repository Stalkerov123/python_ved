"""
Клавиатуры для работы с факультетами.
"""

import logging
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database_manager import DatabaseManager
from parsers.vsuet_parser import VsuetParser

# Инициализация логирования
logger = logging.getLogger(__name__)


async def get_faculties_keyboard(db_manager: DatabaseManager) -> InlineKeyboardMarkup:
    """
    Создание инлайн-клавиатуры для выбора факультета.

    Args:
        db_manager: Менеджер базы данных

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками факультетов
    """
    try:
        # Получаем список факультетов из базы данных
        faculties = db_manager.get_faculties()

        if not faculties:
            logger.warning("Не удалось получить список факультетов из базы данных")
            # Пробуем получить через парсер
            parser = VsuetParser()
            parser_faculties = parser.get_faculties()

            if not parser_faculties:
                logger.warning("Не удалось получить список факультетов через парсер")
                return None

            faculties = [faculty.to_dict() for faculty in parser_faculties]

            # Сохраняем факультеты в базу данных
            db_manager.save_faculties(faculties)

        # Создаем клавиатуру
        keyboard_builder = InlineKeyboardBuilder()

        # Добавляем кнопки для каждого факультета
        for faculty in faculties:
            keyboard_builder.add(
                InlineKeyboardButton(
                    text=faculty['name'],
                    callback_data=f"faculty_{faculty['id']}"
                )
            )

        # Добавляем кнопку возврата в главное меню
        keyboard_builder.add(
            InlineKeyboardButton(
                text="🏠 Главное меню",
                callback_data="main_menu"
            )
        )

        # Размещаем кнопки в одну колонку
        keyboard_builder.adjust(1)

        return keyboard_builder.as_markup()

    except Exception as e:
        logger.error(f"Ошибка при создании клавиатуры факультетов: {e}")
        return None