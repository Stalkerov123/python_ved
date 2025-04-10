"""
Обработчики сообщений для настройки профиля пользователя.
"""

import logging
from aiogram import Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.states.dialog_states import BotStates
from bot.config import START_MESSAGE
from bot.keyboards.settings_keyboards import (
    get_settings_keyboard,
    get_faculty_settings_keyboard,
    get_group_settings_keyboard,
    get_notification_settings_keyboard
)
from bot.keyboards.vedomost_keyboards import get_search_keyboard
from database_manager import DatabaseManager

# Инициализация логирования
logger = logging.getLogger(__name__)


async def cmd_settings(message: Message, state: FSMContext, db_manager: DatabaseManager):
    """
    Обработчик команды /settings.

    Args:
        message: Объект сообщения
        state: Контекст состояния FSM
        db_manager: Менеджер базы данных
    """
    # Получаем настройки пользователя
    user_settings = db_manager.get_user_settings(message.from_user.id)

    if user_settings:
        # Если настройки уже есть, отображаем их
        text = "⚙️ *Ваши настройки*\n\n"

        if user_settings.get('faculty_name'):
            text += f"*Факультет:* {user_settings['faculty_name']}\n"
        else:
            text += "*Факультет:* Не выбран\n"

        if user_settings.get('group_name'):
            text += f"*Группа:* {user_settings['group_name']}\n"
        else:
            text += "*Группа:* Не выбрана\n"

        if user_settings.get('record_book'):
            text += f"*Номер зачетной книжки:* {user_settings['record_book']}\n"
        else:
            text += "*Номер зачетной книжки:* Не указан\n"

        notify_status = "Включены" if user_settings.get('notify_enabled', 1) else "Отключены"
        text += f"*Уведомления:* {notify_status}\n"
    else:
        # Если настроек еще нет, предлагаем настроить
        text = "⚙️ Вы еще не настроили свой профиль.\n\nДля отслеживания изменений в ведомостях рекомендуется указать свой факультет, группу и номер зачетной книжки."

    # Устанавливаем состояние настроек
    await state.set_state(BotStates.settings_menu)

    # Отправляем сообщение с настройками и клавиатурой
    keyboard = get_settings_keyboard()
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")


async def process_settings_menu(callback: CallbackQuery, state: FSMContext, db_manager: DatabaseManager):
    """
    Обработчик выбора в меню настроек.

    Args:
        callback: Объект callback-запроса
        state: Контекст состояния FSM
        db_manager: Менеджер базы данных
    """
    action = callback.data.replace("settings_", "")

    await callback.answer()

    if action == "faculty":
        # Переходим к выбору факультета
        await state.set_state(BotStates.settings_faculty)

        # Получаем клавиатуру выбора факультета
        keyboard = await get_faculty_settings_keyboard(db_manager)

        if keyboard:
            await callback.message.edit_text(
                "Выберите факультет:",
                reply_markup=keyboard
            )
        else:
            await callback.message.edit_text(
                "Не удалось получить список факультетов. Пожалуйста, попробуйте позже.",
                reply_markup=get_settings_keyboard()
            )

    elif action == "group":
        # Проверяем, выбран ли факультет
        user_settings = db_manager.get_user_settings(callback.from_user.id)

        if not user_settings or not user_settings.get('faculty_id'):
            await callback.message.edit_text(
                "Сначала выберите факультет.",
                reply_markup=get_settings_keyboard()
            )
            return

        # Переходим к выбору группы
        await state.set_state(BotStates.settings_group)

        # Получаем клавиатуру выбора группы
        keyboard = await get_group_settings_keyboard(db_manager, user_settings['faculty_id'])

        if keyboard:
            await callback.message.edit_text(
                f"Факультет: {user_settings.get('faculty_name', 'Выбранный факультет')}\n\nВыберите группу:",
                reply_markup=keyboard
            )
        else:
            await callback.message.edit_text(
                "Не удалось получить список групп. Пожалуйста, попробуйте позже.",
                reply_markup=get_settings_keyboard()
            )

    elif action == "record_book":
        # Переходим к вводу номера зачетной книжки
        await state.set_state(BotStates.settings_record_book)

        await callback.message.edit_text(
            "Введите номер вашей зачетной книжки:",
            reply_markup=None
        )

    elif action == "notifications":
        # Переходим к настройке уведомлений
        await state.set_state(BotStates.settings_notifications)

        # Получаем текущие настройки
        user_settings = db_manager.get_user_settings(callback.from_user.id)
        notify_enabled = user_settings.get('notify_enabled', 1) if user_settings else 1

        # Получаем клавиатуру настройки уведомлений
        keyboard = get_notification_settings_keyboard(notify_enabled)

        await callback.message.edit_text(
            "Настройка уведомлений об изменениях в ведомостях:",
            reply_markup=keyboard
        )

    elif action == "back":
        # Возвращаемся в главное меню
        await state.clear()
        keyboard = get_search_keyboard()
        await callback.message.edit_text(START_MESSAGE, reply_markup=keyboard)


async def process_faculty_selection_settings(callback: CallbackQuery, state: FSMContext, db_manager: DatabaseManager):
    """
    Обработчик выбора факультета в настройках.

    Args:
        callback: Объект callback-запроса
        state: Контекст состояния FSM
        db_manager: Менеджер базы данных
    """
    # Извлекаем ID факультета из callback данных
    faculty_id = callback.data.replace("faculty_settings_", "")

    if faculty_id == "back":
        # Возвращаемся в меню настроек
        await state.set_state(BotStates.settings_menu)
        await cmd_settings(callback.message, state, db_manager)
        return

    try:
        # Получаем информацию о факультете
        faculties = db_manager.get_faculties()
        faculty_name = None

        for faculty in faculties:
            if faculty['id'] == faculty_id:
                faculty_name = faculty['name']
                break

        if not faculty_name:
            await callback.answer("Факультет не найден")
            return

        # Сохраняем выбранный факультет в настройках пользователя
        db_manager.save_user_settings(
            callback.from_user.id,
            {'faculty_id': faculty_id}
        )

        await callback.answer(f"Выбран факультет: {faculty_name}")

        # Возвращаемся в меню настроек
        await state.set_state(BotStates.settings_menu)
        await cmd_settings(callback.message, state, db_manager)

    except Exception as e:
        logger.error(f"Ошибка при обработке выбора факультета: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при обработке запроса")

        # Возвращаемся в меню настроек
        await state.set_state(BotStates.settings_menu)
        await cmd_settings(callback.message, state, db_manager)


async def process_group_selection_settings(callback: CallbackQuery, state: FSMContext, db_manager: DatabaseManager):
    """
    Обработчик выбора группы в настройках.

    Args:
        callback: Объект callback-запроса
        state: Контекст состояния FSM
        db_manager: Менеджер базы данных
    """
    # Извлекаем ID группы из callback данных
    callback_data = callback.data

    if callback_data == "group_settings_back":
        # Возвращаемся в меню настроек
        await state.set_state(BotStates.settings_menu)
        await cmd_settings(callback.message, state, db_manager)
        return

    group_id = callback_data.replace("group_settings_", "")

    try:
        # Получаем информацию о группе
        user_settings = db_manager.get_user_settings(callback.from_user.id)
        if not user_settings or not user_settings.get('faculty_id'):
            await callback.answer("Сначала выберите факультет")
            return

        groups = db_manager.get_groups(user_settings['faculty_id'])
        group_name = None

        for group in groups:
            if group['id'] == group_id:
                group_name = group['name']
                break

        if not group_name:
            await callback.answer("Группа не найдена")
            return

        # Сохраняем выбранную группу в настройках пользователя
        db_manager.save_user_settings(
            callback.from_user.id,
            {'group_id': group_id}
        )

        await callback.answer(f"Выбрана группа: {group_name}")

        # Возвращаемся в меню настроек
        await state.set_state(BotStates.settings_menu)
        await cmd_settings(callback.message, state, db_manager)

    except Exception as e:
        logger.error(f"Ошибка при обработке выбора группы: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при обработке запроса")

        # Возвращаемся в меню настроек
        await state.set_state(BotStates.settings_menu)
        await cmd_settings(callback.message, state, db_manager)


async def process_record_book_input(message: Message, state: FSMContext, db_manager: DatabaseManager):
    """
    Обработчик ввода номера зачетной книжки.

    Args:
        message: Объект сообщения
        state: Контекст состояния FSM
        db_manager: Менеджер базы данных
    """
    record_book = message.text.strip()

    if not record_book.isdigit() or len(record_book) < 4:
        await message.answer(
            "Пожалуйста, введите корректный номер зачетной книжки (только цифры)."
        )
        return

    try:
        # Сохраняем номер зачетной книжки в настройках пользователя
        db_manager.save_user_settings(
            message.from_user.id,
            {'record_book': record_book}
        )

        await message.answer(f"Номер зачетной книжки сохранен: {record_book}")

        # Проверяем, есть ли студент с таким номером в базе
        student = db_manager.get_student_by_record_book(record_book)

        if student:
            # Если студент найден, обновляем группу в настройках
            if student.get('group_id'):
                db_manager.save_user_settings(
                    message.from_user.id,
                    {'group_id': student['group_id']}
                )

            await message.answer(
                f"Найдена информация о студенте с номером зачетной книжки {record_book}.\n"
                f"ФИО: {student.get('name', 'Не указано')}\n"
                f"Группа: {student.get('group_name', 'Не указана')}"
            )

        # Возвращаемся в меню настроек
        await state.set_state(BotStates.settings_menu)
        await cmd_settings(message, state, db_manager)

    except Exception as e:
        logger.error(f"Ошибка при обработке ввода номера зачетной книжки: {e}", exc_info=True)

        await message.answer(
            "Произошла ошибка при сохранении номера зачетной книжки. Пожалуйста, попробуйте позже."
        )

        # Возвращаемся в меню настроек
        await state.set_state(BotStates.settings_menu)
        await cmd_settings(message, state, db_manager)


async def process_notification_settings(callback: CallbackQuery, state: FSMContext, db_manager: DatabaseManager):
    """
    Обработчик настройки уведомлений.

    Args:
        callback: Объект callback-запроса
        state: Контекст состояния FSM
        db_manager: Менеджер базы данных
    """
    action = callback.data.replace("notifications_", "")

    if action == "back":
        # Возвращаемся в меню настроек
        await state.set_state(BotStates.settings_menu)
        await cmd_settings(callback.message, state, db_manager)
        return

    try:
        # Обновляем настройки уведомлений
        if action == "enable":
            db_manager.save_user_settings(
                callback.from_user.id,
                {'notify_enabled': 1}
            )
            await callback.answer("Уведомления включены")

        elif action == "disable":
            db_manager.save_user_settings(
                callback.from_user.id,
                {'notify_enabled': 0}
            )
            await callback.answer("Уведомления отключены")

        # Возвращаемся в меню настроек
        await state.set_state(BotStates.settings_menu)
        await cmd_settings(callback.message, state, db_manager)

    except Exception as e:
        logger.error(f"Ошибка при обработке настройки уведомлений: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при обработке запроса")

        # Возвращаемся в меню настроек
        await state.set_state(BotStates.settings_menu)
        await cmd_settings(callback.message, state, db_manager)


def register_settings_handlers(dp: Dispatcher, db_manager: DatabaseManager):
    """
    Регистрация обработчиков сообщений для настройки профиля.

    Args:
        dp: Диспетчер Telegram бота
        db_manager: Менеджер базы данных
    """
    # Регистрация обработчика команды settings
    dp.message.register(lambda msg, state: cmd_settings(msg, state, db_manager), Command("settings"))

    # Регистрация обработчиков меню настроек
    dp.callback_query.register(
        lambda callback, state: process_settings_menu(callback, state, db_manager),
        F.data.startswith("settings_"),
        BotStates.settings_menu
    )

    # Регистрация обработчиков выбора факультета
    dp.callback_query.register(
        lambda callback, state: process_faculty_selection_settings(callback, state, db_manager),
        F.data.startswith("faculty_settings_") | F.data.in_({"faculty_settings_back"}),
        BotStates.settings_faculty
    )

    # Регистрация обработчиков выбора группы
    dp.callback_query.register(
        lambda callback, state: process_group_selection_settings(callback, state, db_manager),
        F.data.startswith("group_settings_") | F.data.in_({"group_settings_back"}),
        BotStates.settings_group
    )

    # Регистрация обработчика ввода номера зачетной книжки
    dp.message.register(
        lambda message, state: process_record_book_input(message, state, db_manager),
        BotStates.settings_record_book
    )

    # Регистрация обработчиков настройки уведомлений
    dp.callback_query.register(
        lambda callback, state: process_notification_settings(callback, state, db_manager),
        F.data.startswith("notifications_"),
        BotStates.settings_notifications
    )