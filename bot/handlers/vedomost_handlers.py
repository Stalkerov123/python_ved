"""
Обработчики сообщений для работы с ведомостями.
"""

import os
import logging
import json
import tempfile
from datetime import datetime
from aiogram import Dispatcher, F, Bot
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.fsm.context import FSMContext

from bot.states.dialog_states import BotStates
from bot.keyboards.vedomost_keyboards import (
    get_vedomosti_keyboard,
    get_vedomost_details_keyboard,
    get_search_keyboard,
    get_student_details_keyboard
)
from bot.keyboards.group_keyboards import get_groups_keyboard
from parsers.vsuet_parser import VsuetParser
from utils.data_exporter import DataExporter
from database_manager import DatabaseManager
from config import EXPORT_DIR

# Инициализация логирования
logger = logging.getLogger(__name__)


async def process_vedomost_pagination(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик пагинации списка ведомостей.

    Args:
        callback: Объект callback-запроса
        state: Контекст состояния FSM
    """
    # Получаем направление пагинации и текущую страницу
    action = callback.data
    data = await state.get_data()
    current_page = data.get('current_vedomost_page', 1)
    vedomosti = data.get('vedomosti', [])
    group_name = data.get('selected_group_name', "Выбранная группа")

    # Определяем новую страницу
    if action == "vedomost_next_page":
        new_page = current_page + 1
    else:  # vedomost_prev_page
        new_page = max(1, current_page - 1)

    # Сохраняем новую страницу
    await state.update_data(current_vedomost_page=new_page)

    # Получаем клавиатуру для новой страницы
    keyboard = await get_vedomosti_keyboard(vedomosti, page=new_page)

    await callback.answer(f"Страница {new_page}")
    await callback.message.edit_text(
        f"Группа: {group_name}\n\n"
        f"Найдено ведомостей: {len(vedomosti)}\n\n"
        "Выберите ведомость для просмотра:",
        reply_markup=keyboard
    )


async def process_vedomost_back(callback: CallbackQuery, state: FSMContext, db_manager: DatabaseManager):
    """
    Обработчик возврата к выбору группы.

    Args:
        callback: Объект callback-запроса
        state: Контекст состояния FSM
        db_manager: Менеджер базы данных
    """
    await callback.answer("Возврат к выбору группы")

    # Получаем данные о факультете
    data = await state.get_data()
    faculty_id = data.get('selected_faculty_id')
    faculty_name = data.get('selected_faculty_name', 'Выбранный факультет')

    # Устанавливаем состояние выбора группы
    await state.set_state(BotStates.select_group)

    # Получаем клавиатуру выбора группы
    keyboard = await get_groups_keyboard(faculty_id, db_manager)

    if keyboard:
        await callback.message.edit_text(
            f"Факультет: {faculty_name}\n\nВыберите группу:",
            reply_markup=keyboard
        )
    else:
        await callback.message.edit_text(
            "Не удалось получить список групп. Пожалуйста, попробуйте позже.",
            reply_markup=get_search_keyboard()
        )


async def process_vedomost_selection(callback: CallbackQuery, state: FSMContext, db_manager: DatabaseManager):
    """
    Обработчик выбора ведомости.

    Args:
        callback: Объект callback-запроса
        state: Контекст состояния FSM
        db_manager: Менеджер базы данных
    """
    # Извлекаем ID ведомости из callback данных
    vedomost_id = callback.data.replace("vedomost_", "")

    try:
        # Сохраняем ID ведомости в состоянии
        await state.update_data(selected_vedomost_id=vedomost_id)

        # Получаем данные о группе и список ведомостей
        data = await state.get_data()
        group_name = data.get('selected_group_name', "Группа")
        vedomosti = data.get('vedomosti', [])

        # Находим выбранную ведомость
        selected_vedomost = None
        for ved in vedomosti:
            if ved.id == vedomost_id:
                selected_vedomost = ved
                break

        if not selected_vedomost:
            await callback.answer("Ведомость не найдена")
            await callback.message.edit_text(
                "Произошла ошибка при выборе ведомости. Пожалуйста, попробуйте еще раз.",
                reply_markup=get_search_keyboard()
            )
            return

        # Сообщаем пользователю, что идет загрузка
        await callback.answer("Загрузка информации о ведомости...")

        # Сохраняем информацию о выбранной ведомости
        await state.update_data(selected_vedomost=selected_vedomost)

        # Проверяем, есть ли детальная информация в базе данных
        vedomost_details = db_manager.get_vedomost_details(vedomost_id)

        if not vedomost_details:
            # Если нет в базе, получаем через парсер
            parser = VsuetParser()
            vedomost_details = parser.get_detailed_ved(vedomost_id)

            # Сохраняем в базу данных
            if vedomost_details:
                db_manager.save_vedomost_details(vedomost_id, vedomost_details)

        if vedomost_details:
            # Сохраняем детальную информацию в состоянии
            await state.update_data(vedomost_details=vedomost_details)

            # Устанавливаем состояние просмотра ведомости
            await state.set_state(BotStates.view_vedomost)

            # Формируем сообщение с основной информацией
            message_text = (
                f"📋 *Информация о ведомости*\n\n"
                f"*Группа:* {vedomost_details['group']}\n"
                f"*Дисциплина:* {vedomost_details['discipline']}\n"
                f"*Тип:* {vedomost_details['type']}\n"
                f"*Преподаватель:* {vedomost_details['teacher']}\n"
                f"*Семестр:* {vedomost_details['semester']}\n"
                f"*Учебный год:* {vedomost_details['year']}\n"
                f"*Статус:* {vedomost_details['status']}\n"
                f"*Обновлено:* {vedomost_details['date_update']}\n\n"
                f"*Количество студентов:* {len(vedomost_details['students'])}\n"
            )

            # Получаем клавиатуру для действий с ведомостью
            keyboard = get_vedomost_details_keyboard()

            await callback.message.edit_text(
                message_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            await callback.message.edit_text(
                f"Не удалось получить детальную информацию о ведомости {selected_vedomost.discipline}.\n"
                "Пожалуйста, попробуйте позже.",
                reply_markup=get_search_keyboard()
            )

    except Exception as e:
        logger.error(f"Ошибка при обработке выбора ведомости: {e}")
        await callback.answer("Произошла ошибка при обработке запроса")
        await callback.message.edit_text(
            "Извините, произошла ошибка при выборе ведомости.\n"
            "Пожалуйста, попробуйте позже или используйте меню для повторного выбора.",
            reply_markup=get_search_keyboard()
        )


async def process_vedomost_detail_back(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик возврата к списку ведомостей.

    Args:
        callback: Объект callback-запроса
        state: Контекст состояния FSM
    """
    await callback.answer("Возврат к списку ведомостей")

    # Получаем данные из состояния
    data = await state.get_data()
    vedomosti = data.get('vedomosti', [])
    group_name = data.get('selected_group_name', "Выбранная группа")
    current_page = data.get('current_vedomost_page', 1)

    # Устанавливаем состояние выбора ведомости
    await state.set_state(BotStates.select_vedomost)

    # Получаем клавиатуру для выбора ведомости
    keyboard = await get_vedomosti_keyboard(vedomosti, page=current_page)

    await callback.message.edit_text(
        f"Группа: {group_name}\n\n"
        f"Найдено ведомостей: {len(vedomosti)}\n\n"
        "Выберите ведомость для просмотра:",
        reply_markup=keyboard
    )


async def process_export_vedomost(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Обработчик экспорта ведомости.

    Args:
        callback: Объект callback-запроса
        state: Контекст состояния FSM
        bot: Экземпляр бота
    """
    # Извлекаем формат экспорта
    export_format = callback.data.replace("export_", "")

    # Получаем данные из состояния
    data = await state.get_data()
    vedomost_details = data.get('vedomost_details')

    if not vedomost_details:
        await callback.answer("Нет данных для экспорта")
        return

    try:
        # Сообщаем пользователю, что идет подготовка экспорта
        await callback.answer("Подготовка файла для экспорта...")

        # Создаем временный файл для экспорта
        group_name = vedomost_details['group']
        discipline = vedomost_details['discipline'].replace("/", "_").replace("\\", "_")
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{group_name}_{discipline}_{timestamp}"

        # Экспортируем данные
        exporter = DataExporter(output_dir=EXPORT_DIR)

        if export_format == "json":
            filepath = exporter.export_to_json(vedomost_details, filename)
            file_description = "JSON"
        elif export_format == "csv":
            # Преобразование для CSV
            students_data = []
            for student in vedomost_details.get('students', []):
                student_data = {
                    'id': student.get('id', ''),
                    'name': student.get('name', ''),
                    'record_book': student.get('record_book', '')
                }

                # Добавление результатов по КТ
                for i, kt_result in enumerate(student.get('kt_results', []), 1):
                    student_data[f'kt_{i}'] = kt_result

                # Добавление итоговых результатов
                student_data['final_rating'] = student.get('final_rating', '')
                student_data['rating_grade'] = student.get('rating_grade', '')
                student_data['exam_grade'] = student.get('exam_grade', '')
                student_data['final_grade'] = student.get('final_grade', '')

                students_data.append(student_data)

            filepath = exporter.export_to_csv(students_data, filename)
            file_description = "CSV"
        elif export_format == "excel":
            # Преобразование для Excel аналогично CSV
            students_data = []
            for student in vedomost_details.get('students', []):
                student_data = {
                    'id': student.get('id', ''),
                    'name': student.get('name', ''),
                    'record_book': student.get('record_book', '')
                }

                # Добавление результатов по КТ
                for i, kt_result in enumerate(student.get('kt_results', []), 1):
                    student_data[f'kt_{i}'] = kt_result

                # Добавление итоговых результатов
                student_data['final_rating'] = student.get('final_rating', '')
                student_data['rating_grade'] = student.get('rating_grade', '')
                student_data['exam_grade'] = student.get('exam_grade', '')
                student_data['final_grade'] = student.get('final_grade', '')

                students_data.append(student_data)

            filepath = exporter.export_to_excel(students_data, filename)
            file_description = "Excel"
        else:
            await callback.answer(f"Неподдерживаемый формат: {export_format}")
            return

        # Проверяем, что файл создан
        if not filepath or not os.path.exists(filepath):
            await callback.answer("Не удалось создать файл для экспорта")
            return

        # Отправляем файл пользователю
        await callback.answer(f"Экспорт в {file_description} выполнен успешно")
        await bot.send_document(
            callback.from_user.id,
            FSInputFile(filepath),
            caption=f"Экспорт ведомости '{discipline}' для группы {group_name}"
        )

        # Уведомляем пользователя об успешном выполнении
        await callback.message.reply(
            f"✅ Экспорт ведомости в формате {file_description} выполнен успешно."
        )

    except Exception as e:
        logger.error(f"Ошибка при экспорте ведомости: {e}")
        await callback.answer("Произошла ошибка при экспорте")
        await callback.message.reply(
            "Извините, произошла ошибка при экспорте")

async def process_show_detailed_vedomost(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик показа подробной информации о ведомости.

    Args:
        callback: Объект callback-запроса
        state: Контекст состояния FSM
    """
    # Получаем данные из состояния
    data = await state.get_data()
    vedomost_details = data.get('vedomost_details')

    if not vedomost_details:
        await callback.answer("Нет данных для отображения")
        return

    try:
        await callback.answer("Загрузка детальной информации...")

        # Формируем сообщение с подробной информацией
        message_text = (
            f"📋 *Детальная информация о ведомости*\n\n"
            f"*Группа:* {vedomost_details['group']}\n"
            f"*Дисциплина:* {vedomost_details['discipline']}\n"
            f"*Тип:* {vedomost_details['type']}\n"
            f"*Преподаватель:* {vedomost_details['teacher']}\n"
            f"*Блок:* {vedomost_details['block']}\n"
            f"*Семестр:* {vedomost_details['semester']}\n"
            f"*Курс:* {vedomost_details['kurs']}\n"
            f"*Часов:* {vedomost_details['hours']}\n"
            f"*Учебный год:* {vedomost_details['year']}\n"
            f"*Статус:* {vedomost_details['status']}\n"
            f"*Обновлено:* {vedomost_details['date_update']}\n"
            f"*Кафедра:* {vedomost_details['department']}\n"
            f"*План:* {vedomost_details['plan']}\n\n"
        )

        # Добавляем информацию о контрольных точках
        if vedomost_details.get('kt_dates'):
            message_text += "*Контрольные точки:*\n"
            for i, (date, weight) in enumerate(zip(
                    vedomost_details.get('kt_dates', []),
                    vedomost_details.get('kt_weights', [])
            ), 1):
                message_text += f"КТ {i}: {date} (вес: {weight})\n"
            message_text += "\n"

        # Добавляем информацию о студентах (первые 5)
        students = vedomost_details.get('students', [])
        if students:
            message_text += f"*Студенты ({len(students)} человек):*\n"
            for i, student in enumerate(students[:5], 1):
                message_text += f"{i}. {student['name']} - {student.get('final_grade', '')}\n"

            if len(students) > 5:
                message_text += f"... и еще {len(students) - 5} студентов\n"

        # Получаем клавиатуру для действий с ведомостью
        keyboard = get_vedomost_details_keyboard()

        await callback.message.edit_text(
            message_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Ошибка при показе детальной информации: {e}")
        await callback.answer("Произошла ошибка при отображении информации")


async def search_by_record_book(message: Message, state: FSMContext):
    """
    Поиск ведомостей по номеру зачетной книжки.

    Args:
        message: Объект сообщения
        state: Контекст состояния FSM
    """
    # Получаем данные из состояния
    data = await state.get_data()
    record_book = data.get('record_book')

    if not record_book:
        await message.answer(
            "Номер зачетной книжки не указан. Пожалуйста, попробуйте снова.",
            reply_markup=get_search_keyboard()
        )
        return

    await message.answer(f"🔍 Ищем информацию по зачетной книжке: {record_book}...")

    try:
        # Создаем парсер
        parser = VsuetParser()

        # В этой реализации мы будем перебирать доступные ведомости и искать студента
        # В реальном приложении лучше сделать отдельный метод в парсере для прямого поиска

        # Получаем список факультетов
        faculties = parser.get_faculties()

        found_results = []
        student_name = None

        # Поиск по всем факультетам и группам (это может занять много времени)
        # В реальном приложении лучше ограничить поиск или кешировать результаты
        for faculty in faculties[:3]:  # Ограничиваем для демонстрации
            groups = parser.get_groups_by_faculty(faculty.id)

            for group in groups[:5]:  # Ограничиваем для демонстрации
                vedomosti = parser.get_ved_list(group.id)

                for ved in vedomosti:
                    # Получаем детальную информацию о ведомости
                    ved_details = parser.get_detailed_ved(ved.id)

                    if ved_details and 'students' in ved_details:
                        # Ищем студента по номеру зачетки
                        for student in ved_details['students']:
                            if student.get('record_book') == record_book:
                                student_name = student.get('name')

                                # Добавляем результат
                                found_results.append({
                                    'vedomost_id': ved.id,
                                    'discipline': ved_details['discipline'],
                                    'group': ved_details['group'],
                                    'semester': ved_details['semester'],
                                    'year': ved_details['year'],
                                    'final_grade': student.get('final_grade', 'Нет оценки'),
                                    'kt_results': student.get('kt_results', []),
                                    'final_rating': student.get('final_rating', '')
                                })

                                # Если нашли хотя бы одну ведомость, прерываем поиск для демонстрации
                                if len(found_results) >= 1:
                                    break

                        # Прерываем поиск если нашли результаты
                        if student_name and len(found_results) >= 1:
                            break

                # Прерываем поиск если нашли результаты
                if student_name and len(found_results) >= 1:
                    break

            # Прерываем поиск если нашли результаты
            if student_name and len(found_results) >= 1:
                break

        # Обрабатываем результаты
        if student_name and found_results:
            # Сохраняем найденные результаты в состоянии
            await state.update_data(
                student_name=student_name,
                found_results=found_results
            )

            # Формируем сообщение
            message_text = (
                f"📋 *Информация о студенте*\n\n"
                f"*Студент:* {student_name}\n"
                f"*Номер зачетной книжки:* {record_book}\n\n"
                f"*Найдено ведомостей:* {len(found_results)}\n\n"
            )

            # Добавляем информацию о найденных ведомостях
            for i, result in enumerate(found_results, 1):
                message_text += (
                    f"{i}. *{result['discipline']}*\n"
                    f"   Группа: {result['group']}\n"
                    f"   Семестр: {result['semester']}\n"
                    f"   Учебный год: {result['year']}\n"
                    f"   Итоговая оценка: {result['final_grade']}\n"
                    f"   Рейтинг: {result['final_rating']}\n\n"
                )

            # Создаем клавиатуру с действиями
            keyboard = get_student_details_keyboard(record_book)

            await message.answer(
                message_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                f"❌ Информация по зачетной книжке {record_book} не найдена.\n"
                "Проверьте правильность ввода номера и попробуйте снова.",
                reply_markup=get_search_keyboard()
            )

    except Exception as e:
        logger.error(f"Ошибка при поиске по зачетной книжке: {e}")
        await message.answer(
            "Произошла ошибка при поиске информации. Пожалуйста, попробуйте позже.",
            reply_markup=get_search_keyboard()
        )


async def search_by_record_book_db(message: Message, state: FSMContext, db_manager: DatabaseManager):
    """
    Поиск ведомостей по номеру зачетной книжки в базе данных.

    Args:
        message: Объект сообщения
        state: Контекст состояния FSM
        db_manager: Менеджер базы данных
    """
    # Получаем данные из состояния
    data = await state.get_data()
    record_book = data.get('record_book')

    if not record_book:
        await message.answer(
            "Номер зачетной книжки не указан. Пожалуйста, попробуйте снова.",
            reply_markup=get_search_keyboard()
        )
        return

    await message.answer(f"🔍 Ищем информацию по зачетной книжке: {record_book}...")

    try:
        # Ищем студента в базе данных
        student = db_manager.get_student_by_record_book(record_book)

        if not student:
            # Если студент не найден в базе, пробуем поискать через парсер
            await search_by_record_book(message, state)
            return

        # Получаем все ведомости с результатами для этого студента
        vedomosti = db_manager.get_vedomosti_for_student(record_book)

        if not vedomosti:
            await message.answer(
                f"❌ В базе данных нет информации о результатах студента с зачетной книжкой {record_book}.\n"
                "Попробуем выполнить поиск через сайт...",
                reply_markup=get_search_keyboard()
            )
            # Если результатов нет в базе, пробуем поискать через парсер
            await search_by_record_book(message, state)
            return

        # Формируем сообщение с результатами
        message_text = (
            f"📋 *Информация о студенте*\n\n"
            f"*Студент:* {student['name']}\n"
            f"*Номер зачетной книжки:* {record_book}\n\n"
            f"*Найдено ведомостей:* {len(vedomosti)}\n\n"
        )

        # Добавляем информацию о найденных ведомостях
        for i, ved in enumerate(vedomosti[:10], 1):  # Ограничиваем вывод 10 ведомостями
            message_text += (
                f"{i}. *{ved['discipline']}*\n"
                f"   Группа: {ved['group_name']}\n"
                f"   Итоговая оценка: {ved.get('final_grade', 'Не указана')}\n"
                f"   Рейтинг: {ved.get('final_rating', 'Не указан')}\n\n"
            )

        if len(vedomosti) > 10:
            message_text += f"... и еще {len(vedomosti) - 10} ведомостей\n\n"

        # Создаем клавиатуру с действиями
        keyboard = get_student_details_keyboard(record_book)

        await message.answer(
            message_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Ошибка при поиске по зачетной книжке в базе данных: {e}")
        await message.answer(
            "Произошла ошибка при поиске информации в базе данных. Попробуем выполнить поиск через сайт...",
            reply_markup=get_search_keyboard()
        )
        # В случае ошибки пробуем поискать через парсер
        await search_by_record_book(message, state)


async def process_export_student_results(callback: CallbackQuery, state: FSMContext, bot: Bot,
                                         db_manager: DatabaseManager):
    """
    Обработчик экспорта результатов студента.

    Args:
        callback: Объект callback-запроса
        state: Контекст состояния FSM
        bot: Экземпляр бота
        db_manager: Менеджер базы данных
    """
    # Извлекаем номер зачетной книжки из callback данных
    record_book = callback.data.replace("export_student_", "")

    # Получаем данные из состояния
    data = await state.get_data()
    student_name = data.get('student_name', 'Студент

    found_results = data.get('found_results', [])

    if not found_results:
        await callback.answer("Нет данных для экспорта")
    return

    try:
        # Сообщаем пользователю, что идет подготовка экспорта
        await callback.answer("Подготовка файла для экспорта...")

        # Создаем имя файла
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        clean_name = student_name.replace(" ", "_").replace(",", "")
        filename = f"student_{clean_name}_{record_book}_{timestamp}"

        # Экспортируем данные
        exporter = DataExporter(output_dir=EXPORT_DIR)

        # Создаем JSON с результатами студента
        student_data = {
            'name': student_name,
            'record_book': record_book,
            'results': found_results
        }

        filepath = exporter.export_to_json(student_data, filename)

        # Проверяем, что файл создан
        if not filepath or not os.path.exists(filepath):
            await callback.answer("Не удалось создать файл для экспорта")
            return

        # Отправляем файл пользователю
        await callback.answer("Экспорт выполнен успешно")
        await bot.send_document(
            callback.from_user.id,
            FSInputFile(filepath),
            caption=f"Результаты студента {student_name} (зачетная книжка {record_book})"
        )

        # Уведомляем пользователя об успешном выполнении
        await callback.message.reply(
            "✅ Экспорт результатов студента выполнен успешно."
        )

    except Exception as e:
        logger.error(f"Ошибка при экспорте результатов студента: {e}")
        await callback.answer("Произошла ошибка при экспорте")
        await callback.message.reply(
            "Извините, произошла ошибка при экспорте результатов.\n"
            "Пожалуйста, попробуйте позже."
        )


def register_vedomost_handlers(dp: Dispatcher, db_manager: DatabaseManager):
    """
    Регистрация обработчиков сообщений для работы с ведомостями.

    Args:
        dp: Диспетчер Telegram бота
        db_manager: Менеджер базы данных
    """
    # Регистрация обработчиков пагинации списка ведомостей
    dp.callback_query.register(
        process_vedomost_pagination,
        F.data.in_({"vedomost_next_page", "vedomost_prev_page"}),
        BotStates.select_vedomost
    )

    # Регистрация обработчика возврата к выбору группы
    dp.callback_query.register(
        lambda callback, state: process_vedomost_back(callback, state, db_manager),
        F.data == "vedomost_back",
        BotStates.select_vedomost
    )

    # Регистрация обработчика выбора ведомости
    dp.callback_query.register(
        lambda callback, state: process_vedomost_selection(callback, state, db_manager),
        F.data.startswith("vedomost_"),
        ~F.data.in_({"vedomost_next_page", "vedomost_prev_page", "vedomost_back", "vedomost_detail_back"}),
        BotStates.select_vedomost
    )

    # Регистрация обработчика возврата к списку ведомостей
    dp.callback_query.register(
        process_vedomost_detail_back,
        F.data == "vedomost_detail_back",
        BotStates.view_vedomost
    )

    # Регистрация обработчиков экспорта ведомости
    dp.callback_query.register(
        process_export_vedomost,
        F.data.in_({"export_json", "export_csv", "export_excel"}),
        BotStates.view_vedomost
    )

    # Регистрация обработчика показа подробной информации
    dp.callback_query.register(
        process_show_detailed_vedomost,
        F.data == "show_details",
        BotStates.view_vedomost
    )

    # Регистрация обработчика экспорта результатов студента
    dp.callback_query.register(
        lambda callback, state, bot: process_export_student_results(callback, state, bot, db_manager),
        F.data.startswith("export_student_"),
        BotStates.search_record_book
    )