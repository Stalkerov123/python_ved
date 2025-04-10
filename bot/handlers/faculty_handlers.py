"""
Обработчики сообщений для работы с факультетами.
"""

import logging
from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.states.dialog_states import BotStates
from bot.keyboards.group_keyboards import get_groups_keyboard
from database_manager import DatabaseManager

# Инициализация логирования
logger = logging.getLogger(__name__)


async def process_faculty_selection(callback: CallbackQuery, state: FSMContext, db_manager: DatabaseManager):
    """
    Обработчик выбора факультета.

    Args:
        callback: Объект callback-запроса
        state: Контекст состояния FSM
        db_manager: Менеджер базы данных
    """
    # Извлекаем ID факультета из callback данных
    faculty_id = callback.data.replace("faculty_", "")

    try:
        # Сохраняем ID факультета в состоянии
        await state.update_data(selected_faculty_id=faculty_id)

        # Получаем данные о факультете
        faculties = db_manager.get_faculties()

        # Находим название выбранного факультета
        faculty_name = "Неизвестный факультет"
        for faculty in faculties:
            if faculty['id'] == faculty_id:
                faculty_name = faculty['name']
                break

        await state.update_data(selected_faculty_name=faculty_name)

        # Оповещаем пользователя о выборе
        await callback.answer(f"Выбран факультет: {faculty_name}")

        # Получаем клавиатуру с группами для выбранного факультета
        keyboard = await get_groups_keyboard(faculty_id, db_manager)

        if keyboard:
            # Устанавливаем состояние выбора группы
            await state.set_state(BotStates.select_group)
            await callback.message.edit_text(
                f"Факультет: {faculty_name}\n\nВыберите группу:",
                reply_markup=keyboard
            )
        else:
            await callback.message.edit_text(
                f"Не удалось получить список групп для факультета {faculty_name}.\n"
                "Пожалуйста, попробуйте позже или выберите другой факультет."
            )
            # Возвращаемся к выбору факультета
            await state.set_state(BotStates.select_faculty)

    except Exception as e:
        logger.error(f"Ошибка при обработке выбора факультета: {e}")
        await callback.answer("Произошла ошибка при обработке запроса")
        await callback.message.edit_text(
            "Извините, произошла ошибка при выборе факультета.\n"
            "Пожалуйста, попробуйте позже или используйте команду /start чтобы начать сначала."
        )


def register_faculty_handlers(dp: Dispatcher, db_manager: DatabaseManager):
    """
    Регистрация обработчиков сообщений для работы с факультетами.

    Args:
        dp: Диспетчер Telegram бота
        db_manager: Менеджер базы данных
    """
    # Регистрация обработчика выбора факультета
    dp.callback_query.register(
        lambda callback, state: process_faculty_selection(callback, state, db_manager),
        F.data.startswith("faculty_"),
        BotStates.select_faculty
    )