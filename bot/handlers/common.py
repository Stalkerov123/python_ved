"""
Общие обработчики сообщений для Telegram бота.
"""

from aiogram import Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.states.dialog_states import BotStates
from bot.config import START_MESSAGE, HELP_MESSAGE
from bot.keyboards.faculty_keyboards import get_faculties_keyboard
from bot.keyboards.vedomost_keyboards import get_search_keyboard
from database_manager import DatabaseManager


async def cmd_start(message: Message, state: FSMContext, db_manager: DatabaseManager):
    """
    Обработчик команды /start.

    Args:
        message: Объект сообщения
        state: Контекст состояния FSM
        db_manager: Менеджер базы данных
    """
    # Сбрасываем состояние диалога
    await state.clear()

    # Проверяем, есть ли у пользователя настройки
    user_settings = db_manager.get_user_settings(message.from_user.id)

    # Если настроек нет, предлагаем настроить профиль
    if not user_settings:
        welcome_text = (
            f"{START_MESSAGE}\n\n"
            f"🔧 Похоже, вы впервые используете бота. "
            f"Рекомендуется настроить профиль для отслеживания изменений в ведомостях.\n"
            f"Используйте команду /settings для настройки."
        )
    else:
        welcome_text = START_MESSAGE

    # Отправляем приветственное сообщение с главным меню
    keyboard = get_search_keyboard()
    await message.answer(welcome_text, reply_markup=keyboard)


async def cmd_help(message: Message):
    """
    Обработчик команды /help.

    Args:
        message: Объект сообщения
    """
    await message.answer(HELP_MESSAGE, parse_mode="Markdown")


async def process_main_menu(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик нажатия на кнопку главного меню.

    Args:
        callback: Объект callback-запроса
        state: Контекст состояния FSM
    """
    await callback.answer()
    await state.clear()
    keyboard = get_search_keyboard()
    await callback.message.edit_text(START_MESSAGE, reply_markup=keyboard)


async def process_browse_faculties(callback: CallbackQuery, state: FSMContext, db_manager: DatabaseManager):
    """
    Обработчик перехода к просмотру факультетов.

    Args:
        callback: Объект callback-запроса
        state: Контекст состояния FSM
        db_manager: Менеджер базы данных
    """
    await callback.answer("Загрузка списка факультетов...")
    await state.set_state(BotStates.select_faculty)

    # Получаем клавиатуру выбора факультета
    keyboard = await get_faculties_keyboard(db_manager)

    if keyboard:
        await callback.message.edit_text("Выберите факультет:", reply_markup=keyboard)
    else:
        await callback.message.edit_text(
            "Не удалось получить список факультетов. Пожалуйста, попробуйте позже.",
            reply_markup=get_search_keyboard()
        )


async def process_search_by_record_book(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик перехода к поиску по номеру зачетной книжки.

    Args:
        callback: Объект callback-запроса
        state: Контекст состояния FSM
    """
    await callback.answer()
    # Устанавливаем состояние ожидания ввода номера зачетки
    await state.set_state(BotStates.enter_record_book)

    await callback.message.edit_text(
        "Введите номер зачетной книжки студента для поиска ведомостей:"
    )


async def process_input_record_book(message: Message, state: FSMContext, db_manager: DatabaseManager):
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
            "Пожалуйста, введите корректный номер зачетной книжки (только цифры).",
            reply_markup=get_search_keyboard()
        )
        return

    # Сохраняем номер зачетки в состоянии
    await state.update_data(record_book=record_book)
    await state.set_state(BotStates.search_record_book)

    # Ищем результаты по номеру зачетки в базе данных
    from bot.handlers.vedomost_handlers import search_by_record_book_db
    await search_by_record_book_db(message, state, db_manager)


async def handle_unknown_callback(callback: CallbackQuery):
    """
    Обработчик неизвестных callback-запросов.

    Args:
        callback: Объект callback-запроса
    """
    await callback.answer("Действие устарело или недоступно", show_alert=True)
    # Предлагаем начать заново
    keyboard = get_search_keyboard()
    await callback.message.edit_text(
        "Произошла ошибка. Пожалуйста, выберите действие:",
        reply_markup=keyboard
    )


def register_common_handlers(dp: Dispatcher, db_manager: DatabaseManager):
    """
    Регистрация общих обработчиков сообщений.

    Args:
        dp: Диспетчер Telegram бота
        db_manager: Менеджер базы данных
    """
    # Регистрация обработчиков команд
    dp.message.register(lambda msg, state: cmd_start(msg, state, db_manager), Command("start"))
    dp.message.register(cmd_help, Command("help"))

    # Обработчики главного меню
    dp.callback_query.register(process_main_menu, F.data == "main_menu")
    dp.callback_query.register(
        lambda callback, state: process_browse_faculties(callback, state, db_manager),
        F.data == "browse_faculties"
    )
    dp.callback_query.register(process_search_by_record_book, F.data == "search_by_record_book")

    # Обработчик ввода номера зачетки
    dp.message.register(
        lambda message, state: process_input_record_book(message, state, db_manager),
        BotStates.enter_record_book
    )

    # Регистрация обработчика неизвестных callback-запросов (в последнюю очередь)
    dp.callback_query.register(handle_unknown_callback)