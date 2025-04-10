"""
Обработчики сообщений для Telegram бота.
"""

from aiogram import Dispatcher
from database_manager import DatabaseManager

from bot.handlers.common import register_common_handlers
from bot.handlers.faculty_handlers import register_faculty_handlers
from bot.handlers.group_handlers import register_group_handlers
from bot.handlers.vedomost_handlers import register_vedomost_handlers
from bot.handlers.settings_handlers import register_settings_handlers


def register_all_handlers(dp: Dispatcher, db_manager: DatabaseManager):
    """
    Регистрация всех обработчиков сообщений.

    Args:
        dp: Диспетчер Telegram бота
        db_manager: Менеджер базы данных
    """
    # Порядок регистрации важен для правильной обработки запросов
    register_common_handlers(dp, db_manager)
    register_settings_handlers(dp, db_manager)
    register_faculty_handlers(dp, db_manager)
    register_group_handlers(dp, db_manager)
    register_vedomost_handlers(dp, db_manager)