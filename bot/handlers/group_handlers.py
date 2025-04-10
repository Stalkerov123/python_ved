"""
Обработчики сообщений для работы с группами.
"""

import logging
from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.states.dialog_states import BotStates
from bot.keyboards.group_keyboards import get_groups_keyboard
from bot.keyboards.vedomost_keyboards import get_vedomosti_keyboard
from bot.keyboards.faculty_keyboards import get_faculties_keyboard
from database_manager import DatabaseManager
from parsers.vsuet_parser import VsuetParser

# Инициализация логирования
logger = logging.getLogger(__name__)


async def cmd_groups(message: Message, state: FSMContext, db_manager: DatabaseManager):
    """
    Обработчик команды /groups.

    Args:
        message: Объект сообщения
        state: Контекст состояния FSM
        db_manager: Менеджер базы данных
    """
    # Проверяем, был ли выбран факультет
    data = await state.get_data()
    faculty_id = data.get('selected_faculty_id')

    if not faculty_id:
        # Если факультет не выбран, предлагаем его выбрать
        await message.answer("Сначала выберите факультет:")
        keyboard = await get_faculties_keyboard(db_manager)
        if keyboard:
            await state.set_state(BotStates.select_faculty)
            await message.answer("Выберите факультет:", reply_markup=keyboard)
        else:
            await message.answer("Не удалось получить список факультетов. Пожалуйста, попробуйте позже.")
        return

    # Если факультет уже выбран, показываем группы
    keyboard = await get_groups_keyboard(faculty_id, db_manager)
    if keyboard:
        faculty_name = data.get('selected_faculty_name', 'Выбранный факультет')
        await state.set_state(BotStates.select_group)
        await message.answer(f"Факультет: {faculty_name}\n\nВыберите группу:", reply_markup=keyboard)
    else:
        await message.answer("Не удалось получить список групп. Пожалуйста, попробуйте позже.")


async def process_group_back(callback: CallbackQuery, state: FSMContext, db_manager: DatabaseManager):
    """
    Обработчик возврата к выбору факультета.

    Args:
        callback: Объект callback-запроса
        state: Контекст состояния FSM
        db_manager: Менеджер базы данных
    """
    await callback.answer("Возврат к выбору факультета")

    # Устанавливаем состояние выбора факультета
    await state.set_state(BotStates.select_faculty)

    # Получаем клавиатуру выбора факультета
    keyboard = await get_faculties_keyboard(db_manager)

    if keyboard:
        await callback.message.edit_text("Выберите факультет:", reply_markup=keyboard)
    else:
        await callback.message.edit_text(
            "Не удалось получить список факультетов. Пожалуйста, попробуйте позже."
        )


async def process_group_selection(callback: CallbackQuery, state: FSMContext, db_manager: DatabaseManager):
    """
    Обработчик выбора группы.

    Args:
        callback: Объект callback-запроса
        state: Контекст состояния FSM
        db_manager: Менеджер базы данных
    """
    # Извлекаем ID группы из callback данных
    group_id = callback.data.replace("group_", "")

    try:
        # Получаем данные о факультете
        data = await state.get_data()
        faculty_id = data.get('selected_faculty_id')

        if not faculty_id:
            await callback.answer("Произошла ошибка: факультет не выбран")
            await callback.message.edit_text(
                "Произошла ошибка при выборе группы. Попробуйте начать сначала с команды /start"
            )
            return

        # Получаем информацию о группе
        groups = db_manager.get_groups(faculty_id)

        # Находим название выбранной группы
        group_name = "Неизвестная группа"
        for group in groups:
            if group['id'] == group_id:
                group_name = group['name']
                break

        # Сохраняем ID и название группы в состоянии
        await state.update_data(selected_group_id=group_id)
        await state.update_data(selected_group_name=group_name)

        # Оповещаем пользователя о выборе
        await callback.answer(f"Выбрана группа: {group_name}")

        # Получаем ведомости для выбранной группы
        # По умолчанию используем текущий учебный год и весенний семестр (0)
        parser = VsuetParser()
        vedomosti = parser.get_ved_list(group_id, year="2024-2025", semester="0")

        if vedomosti:
            # Устанавливаем состояние выбора ведомости
            await state.set_state(BotStates.select_vedomost)

            # Сохраняем список ведомостей в состоянии
            await state.update_data(vedomosti=vedomosti)

            # Получаем клавиатуру для выбора ведомости
            keyboard = await get_vedomosti_keyboard(vedomosti, page=1)

            await callback.message.edit_text(
                f"Группа: {group_name}\n\n"
                f"Найдено ведомостей: {len(vedomosti)}\n\n"
                "Выберите ведомость для просмотра:",
                reply_markup=keyboard
            )
        else:
            await callback.message.edit_text(
                f"Для группы {group_name} не найдено ведомостей.\n"
                "Возможно, в текущем семестре еще нет ведомостей для этой группы."
            )

    except Exception as e:
        logger.error(f"Ошибка при обработке выбора группы: {e}")
        await callback.answer("Произошла ошибка при обработке запроса")
        await callback.message.edit_text(
            "Извините, произошла ошибка при выборе группы.\n"
            "Пожалуйста, попробуйте позже или используйте команду /start чтобы начать сначала."
        )


def register_group_handlers(dp: Dispatcher, db_manager: DatabaseManager):
    """
    Регистрация обработчиков сообщений для работы с группами.

    Args:
        dp: Диспетчер Telegram бота
        db_manager: Менеджер базы данных
    """
    # Регистрация обработчика команды groups
    dp.message.register(lambda msg, state: cmd_groups(msg, state, db_manager), Command("groups"))

    # Регистрация обработчика кнопки "Назад"
    dp.callback_query.register(
        lambda callback, state: process_group_back(callback, state, db_manager),
        F.data == "group_back",
        BotStates.select_group
    )

    # Регистрация обработчика выбора группы
    dp.callback_query.register(
        lambda callback, state: process_group_selection(callback, state, db_manager),
        F.data.startswith("group_"),
        ~F.data.in_({"group_back"}),
        BotStates.select_group
    )