"""
Клавиатуры для работы с группами.
"""

import logging
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database_manager import DatabaseManager
from parsers.vsuet_parser import VsuetParser
from bot.config import BUTTON_LABELS

# Инициализация логирования
logger = logging.getLogger(__name__)


async def get_groups_keyboard(faculty_id: str, db_manager: DatabaseManager) -> InlineKeyboardMarkup:
    """
    Создание инлайн-клавиатуры для выбора группы.

    Args:
        faculty_id: ID факультета
        db_manager: Менеджер базы данных

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками групп
    """
    try:
        # Получаем список групп для факультета из базы данных
        groups = db_manager.get_groups(faculty_id)

        if not groups:
            logger.warning(f"Не удалось получить список групп для факультета {faculty_id} из базы данных")
            # Пробуем получить через парсер
            parser = VsuetParser()
            parser_groups = parser.get_groups_by_faculty(faculty_id)

            if not parser_groups:
                logger.warning(f"Не удалось получить список групп для факультета {faculty_id} через парсер")
                return None

            groups = [group.to_dict() for group in parser_groups]

            # Сохраняем группы в базу данных
            db_manager.save_groups(groups, faculty_id)

        # Создаем клавиатуру
        keyboard_builder = InlineKeyboardBuilder()

        # Добавляем кнопки для каждой группы
        for group in groups:
            keyboard_builder.add(
                InlineKeyboardButton(
                    text=group['name'],
                    callback_data=f"group_{group['id']}"
                )
            )

        # Добавляем кнопки навигации
        keyboard_builder.add(
            InlineKeyboardButton(
                text=BUTTON_LABELS["back"],
                callback_data="group_back"
            )
        )

        keyboard_builder.add(
            InlineKeyboardButton(
                text=BUTTON_LABELS["main_menu"],
                callback_data="main_menu"
            )
        )

        # Размещаем кнопки в две колонки, кроме кнопок навигации
        keyboard_builder.adjust(2, 2, 2)

        return keyboard_builder.as_markup()

    except Exception as e:
        logger.error(f"Ошибка при создании клавиатуры групп: {e}")
        return None