"""
Утилиты для работы с сообщениями в Telegram боте.
"""

from aiogram import Bot
from aiogram.types import BotCommand


async def set_commands(bot: Bot) -> None:
    """
    Установка команд бота в меню.

    Args:
        bot: Экземпляр бота
    """
    commands = [
        BotCommand(command="start", description="Начать работу с ботом"),
        BotCommand(command="faculties", description="Список факультетов"),
        BotCommand(command="groups", description="Выбор группы"),
        BotCommand(command="cancel", description="Отменить текущее действие"),
        BotCommand(command="help", description="Справка по боту")
    ]

    await bot.set_my_commands(commands)