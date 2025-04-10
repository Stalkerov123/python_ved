#!/usr/bin/env python
"""
Главный файл для запуска Telegram бота для получения данных о ведомостях ВГУИТ.
"""

import asyncio
import logging
import os
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN, WEBHOOK_URL, WEBHOOK_PATH, WEBAPP_HOST, WEBAPP_PORT, USE_WEBHOOK
from bot.handlers import register_all_handlers
from bot.utils.message_utils import set_commands
from bot.notification_service import check_and_send_notifications
from database_manager import DatabaseManager
from data_updater import DataUpdater

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Создаем экземпляр базы данных
db_manager = DatabaseManager()

# Создаем экземпляр обновителя данных
data_updater = DataUpdater()


async def on_startup(bot: Bot) -> None:
    """
    Действия при запуске бота.
    """
    await set_commands(bot)

    # Инициализация базы данных, если она еще не инициализирована
    # Проверяем наличие факультетов в базе
    faculties = db_manager.get_faculties()
    if not faculties:
        logger.info("База данных не инициализирована, запускаем инициализацию...")
        await data_updater.initialize_database()

    logger.info("Бот успешно запущен")


async def on_shutdown(bot: Bot) -> None:
    """
    Действия при остановке бота.
    """
    # Закрываем соединения с базой данных
    db_manager.close()
    data_updater.close()
    logger.info("Соединения с базой данных закрыты")

    # Отключаем вебхук, если он был включен
    if USE_WEBHOOK:
        await bot.delete_webhook()

    logger.info("Бот успешно остановлен")


async def scheduled_jobs(bot: Bot) -> None:
    """
    Запланированные задачи.
    """
    # Обновление устаревших ведомостей
    await data_updater.update_outdated_vedomosti()

    # Отправка уведомлений пользователям
    await check_and_send_notifications(bot, db_manager)


async def main():
    """Основная функция для запуска бота"""
    logger.info("Запуск бота")

    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрация всех хендлеров
    register_all_handlers(dp, db_manager)

    # Установка действий при запуске и остановке
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Настройка планировщика задач
    scheduler = AsyncIOScheduler()
    # Обновление каждые 10 минут
    scheduler.add_job(scheduled_jobs, 'interval', minutes=10, args=(bot,))
    scheduler.start()

    # Режим запуска - вебхук или лонг поллинг
    if USE_WEBHOOK:
        # Удаляем старые вебхуки
        await bot.delete_webhook()
        # Устанавливаем новый вебхук
        await bot.set_webhook(url=WEBHOOK_URL + WEBHOOK_PATH)
        logger.info(f"Бот запущен с вебхуком на {WEBHOOK_URL + WEBHOOK_PATH}")

        # Настройка aiohttp сервера
        from aiohttp import web
        app = web.Application()

        # Обработчик для вебхуков
        async def webhook_handler(request):
            """Обработчик вебхуков Telegram"""
            req = await request.json()
            await bot.process_update(req)
            return web.Response()

        # Регистрация обработчика вебхуков
        app.router.add_post(WEBHOOK_PATH, webhook_handler)

        # Запуск веб-сервера
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, WEBAPP_HOST, WEBAPP_PORT)
        await site.start()

        # Вызываем обработчик запуска вручную
        await on_startup(bot)

        # Держим приложение запущенным
        while True:
            await asyncio.sleep(3600)
    else:
        # Запуск бота в режиме long polling
        logger.info("Бот запущен с long polling")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)