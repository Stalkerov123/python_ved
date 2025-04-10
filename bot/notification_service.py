"""
Сервис для отправки уведомлений пользователям.
"""

import logging
import os
from typing import List, Dict, Any
from aiogram import Bot
from aiogram.types import FSInputFile
from database_manager import DatabaseManager
from data_updater import DataUpdater

logger = logging.getLogger(__name__)


async def check_and_send_notifications(bot: Bot, db_manager: DatabaseManager) -> None:
    """
    Проверка и отправка уведомлений пользователям.

    Args:
        bot: Объект бота для отправки сообщений
        db_manager: Менеджер базы данных
    """
    try:
        logger.info("Проверка новых уведомлений")

        # Получаем непрочитанные уведомления
        notifications = db_manager.get_pending_notifications(limit=100)

        if not notifications:
            logger.info("Нет новых уведомлений")
            return

        logger.info(f"Найдено {len(notifications)} новых уведомлений")

        # Группируем уведомления по пользователям для отправки в одном сообщении
        user_notifications = {}
        for notification in notifications:
            user_id = notification['telegram_user_id']
            if user_id not in user_notifications:
                user_notifications[user_id] = []
            user_notifications[user_id].append(notification)

        # Создаем экземпляр обновителя данных для экспорта PDF
        data_updater = DataUpdater()

        # Отправляем уведомления пользователям
        for user_id, user_notifs in user_notifications.items():
            try:
                await send_notifications_to_user(bot, db_manager, data_updater, user_id, user_notifs)
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомлений пользователю {user_id}: {e}", exc_info=True)

        # Закрываем соединения
        data_updater.close()

    except Exception as e:
        logger.error(f"Ошибка при проверке и отправке уведомлений: {e}", exc_info=True)


async def send_notifications_to_user(bot: Bot, db_manager: DatabaseManager, data_updater: DataUpdater,
                                     user_id: int, notifications: List[Dict[str, Any]]) -> None:
    """
    Отправка уведомлений конкретному пользователю.

    Args:
        bot: Объект бота для отправки сообщений
        db_manager: Менеджер базы данных
        data_updater: Обновитель данных
        user_id: ID пользователя в Telegram
        notifications: Список уведомлений
    """
    try:
        # Сортируем уведомления по ведомостям
        vedomost_notifications = {}
        for notification in notifications:
            vedomost_id = notification['vedomost_id']
            if vedomost_id not in vedomost_notifications:
                vedomost_notifications[vedomost_id] = []
            vedomost_notifications[vedomost_id].append(notification)

        # Для каждой ведомости отправляем отдельное сообщение с изменениями
        for vedomost_id, ved_notifs in vedomost_notifications.items():
            # Экспортируем ведомость в PDF
            pdf_path = await data_updater.export_vedomost_to_pdf(vedomost_id)

            # Формируем сообщение с изменениями
            message_text = "🔔 *Уведомление об изменениях в ведомости*\n\n"

            # Добавляем информацию о ведомости
            ved_notif = ved_notifs[0]  # Берем первое уведомление для информации о ведомости
            message_text += f"*Дисциплина:* {ved_notif['discipline']}\n"
            message_text += f"*Группа:* {ved_notif['group_name']}\n\n"

            # Добавляем информацию о каждом изменении
            for notif in ved_notifs:
                message_text += f"*Студент:* {notif['student_name']}\n"

                # Изменение оценки
                if notif['old_grade'] != notif['new_grade']:
                    message_text += f"*Оценка:* {notif['old_grade']} → {notif['new_grade']}\n"

                # Изменение рейтинга
                if notif['old_rating'] != notif['new_rating']:
                    message_text += f"*Рейтинг:* {notif['old_rating']} → {notif['new_rating']}\n"

                message_text += "\n"

            # Добавляем ссылку на ведомость
            message_text += f"[Открыть ведомость](https://rating.vsuet.ru/web/Ved/Ved.aspx?id={vedomost_id})"

            # Отправляем сообщение
            await bot.send_message(
                user_id,
                message_text,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )

            # Если PDF-файл создан, отправляем его
            if pdf_path and os.path.exists(pdf_path):
                try:
                    await bot.send_document(
                        user_id,
                        FSInputFile(pdf_path),
                        caption=f"Ведомость: {ved_notif['discipline']}"
                    )
                except Exception as e:
                    logger.error(f"Ошибка при отправке PDF файла: {e}", exc_info=True)

            # Отмечаем уведомления как отправленные
            for notif in ved_notifs:
                db_manager.mark_notification_as_sent(notif['id'])

        logger.info(f"Отправлены уведомления пользователю {user_id}")

    except Exception as e:
        logger.error(f"Ошибка при отправке уведомлений пользователю {user_id}: {e}", exc_info=True)