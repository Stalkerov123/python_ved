"""
Модуль для обновления данных из системы ведомостей ВГУИТ.
Обеспечивает периодическое обновление данных и отслеживание изменений.
"""

import logging
import time
import os
import sys
import tempfile
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import traceback

from database_manager import DatabaseManager
from parsers.vsuet_parser import VsuetParser
from config import EXPORT_DIR

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("updater.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('DataUpdater')


class DataUpdater:
    """Класс для обновления данных из системы ведомостей ВГУИТ."""

    def __init__(self, db_path: str = "vedomosti.db"):
        """
        Инициализация обновителя данных.

        Args:
            db_path: Путь к файлу базы данных SQLite
        """
        self.db_manager = DatabaseManager(db_path)
        self.parser = VsuetParser()

        # Создаем директорию для экспорта, если она не существует
        if not os.path.exists(EXPORT_DIR):
            os.makedirs(EXPORT_DIR)

    async def update_all_faculties(self) -> None:
        """Обновление информации о всех факультетах."""
        try:
            logger.info("Начало обновления факультетов")

            faculties = self.parser.get_faculties()
            faculties_dicts = [faculty.to_dict() for faculty in faculties]

            self.db_manager.save_faculties(faculties_dicts)

            logger.info(f"Обновлено {len(faculties)} факультетов")
        except Exception as e:
            logger.error(f"Ошибка при обновлении факультетов: {e}\n{traceback.format_exc()}")

    async def update_groups_for_faculty(self, faculty_id: str) -> None:
        """
        Обновление информации о группах для факультета.

        Args:
            faculty_id: ID факультета
        """
        try:
            logger.info(f"Начало обновления групп для факультета {faculty_id}")

            groups = self.parser.get_groups_by_faculty(faculty_id)
            groups_dicts = [group.to_dict() for group in groups]

            self.db_manager.save_groups(groups_dicts, faculty_id)

            logger.info(f"Обновлено {len(groups)} групп для факультета {faculty_id}")
        except Exception as e:
            logger.error(f"Ошибка при обновлении групп для факультета {faculty_id}: {e}\n{traceback.format_exc()}")

    async def update_all_groups(self) -> None:
        """Обновление информации о группах для всех факультетов."""
        try:
            logger.info("Начало обновления всех групп")

            faculties = self.db_manager.get_faculties()

            for faculty in faculties:
                await self.update_groups_for_faculty(faculty['id'])
                # Небольшая пауза между запросами
                await asyncio.sleep(1)

            logger.info("Завершено обновление всех групп")
        except Exception as e:
            logger.error(f"Ошибка при обновлении всех групп: {e}\n{traceback.format_exc()}")

    async def update_vedomosti_for_group(self, group_id: str, year: str = "2024-2025", semester: str = "0") -> None:
        """
        Обновление информации о ведомостях для группы.

        Args:
            group_id: ID группы
            year: Учебный год
            semester: Семестр (0 - весна, 1 - осень)
        """
        try:
            logger.info(f"Начало обновления ведомостей для группы {group_id}")

            vedomosti = self.parser.get_ved_list(group_id, year, semester)
            vedomosti_dicts = [ved.to_dict() for ved in vedomosti]

            self.db_manager.save_vedomosti(vedomosti_dicts, group_id)

            logger.info(f"Обновлено {len(vedomosti)} ведомостей для группы {group_id}")
        except Exception as e:
            logger.error(f"Ошибка при обновлении ведомостей для группы {group_id}: {e}\n{traceback.format_exc()}")

    async def update_vedomost_details(self, vedomost_id: str) -> None:
        """
        Обновление детальной информации о ведомости.

        Args:
            vedomost_id: ID ведомости
        """
        try:
            logger.info(f"Начало обновления деталей ведомости {vedomost_id}")

            vedomost_details = self.parser.get_detailed_ved(vedomost_id)

            if vedomost_details:
                self.db_manager.save_vedomost_details(vedomost_id, vedomost_details)
                logger.info(f"Обновлены детали ведомости {vedomost_id}")
            else:
                logger.warning(f"Не удалось получить детали ведомости {vedomost_id}")
        except Exception as e:
            logger.error(f"Ошибка при обновлении деталей ведомости {vedomost_id}: {e}\n{traceback.format_exc()}")

    async def update_all_groups_vedomosti(self, year: str = "2024-2025", semester: str = "0") -> None:
        """
        Обновление информации о ведомостях для всех групп.

        Args:
            year: Учебный год
            semester: Семестр (0 - весна, 1 - осень)
        """
        try:
            logger.info(f"Начало обновления ведомостей для всех групп (год: {year}, семестр: {semester})")

            groups = self.db_manager.get_groups()

            for group in groups:
                await self.update_vedomosti_for_group(group['id'], year, semester)
                # Небольшая пауза между запросами
                await asyncio.sleep(1)

            logger.info("Завершено обновление ведомостей для всех групп")
        except Exception as e:
            logger.error(f"Ошибка при обновлении ведомостей для всех групп: {e}\n{traceback.format_exc()}")

    async def update_outdated_vedomosti(self) -> None:
        """Обновление устаревших ведомостей."""
        try:
            logger.info("Начало обновления устаревших ведомостей")

            vedomosti = self.db_manager.get_vedomosti_to_update()

            for ved in vedomosti:
                await self.update_vedomost_details(ved['id'])
                # Небольшая пауза между запросами
                await asyncio.sleep(2)

            logger.info(f"Завершено обновление {len(vedomosti)} устаревших ведомостей")
        except Exception as e:
            logger.error(f"Ошибка при обновлении устаревших ведомостей: {e}\n{traceback.format_exc()}")

    async def export_vedomost_to_pdf(self, vedomost_id: str) -> Optional[str]:
        """
        Экспорт ведомости в PDF формат.

        Args:
            vedomost_id: ID ведомости

        Returns:
            Optional[str]: Путь к сохраненному файлу или None
        """
        try:
            # Получаем информацию о ведомости
            vedomost = self.db_manager.get_vedomost_details(vedomost_id)

            if not vedomost:
                logger.warning(f"Не найдена ведомость {vedomost_id} для экспорта в PDF")
                return None

            # Имя файла для PDF
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            clean_name = vedomost['discipline'].replace(" ", "_").replace("/", "_")
            filename = f"{vedomost['group_name']}_{clean_name}_{timestamp}.pdf"
            filepath = os.path.join(EXPORT_DIR, filename)

            # Для простоты демонстрации используем библиотеку ReportLab для создания PDF
            try:
                from reportlab.lib.pagesizes import A4
                from reportlab.lib import colors
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

                # Создаем PDF документ
                doc = SimpleDocTemplate(filepath, pagesize=A4)
                elements = []

                # Добавляем стили
                styles = getSampleStyleSheet()
                title_style = styles['Heading1']
                subtitle_style = styles['Heading2']
                normal_style = styles['Normal']

                # Добавляем заголовок
                elements.append(Paragraph(f"Ведомость: {vedomost['discipline']}", title_style))
                elements.append(Spacer(1, 12))

                # Добавляем информацию о ведомости
                elements.append(Paragraph(f"Группа: {vedomost['group_name']}", subtitle_style))
                elements.append(Paragraph(f"Преподаватель: {vedomost['teacher']}", normal_style))
                elements.append(Paragraph(f"Тип: {vedomost['type']}", normal_style))
                elements.append(Paragraph(f"Семестр: {vedomost['semester']} ({vedomost['year']})", normal_style))
                elements.append(Paragraph(f"Статус: {vedomost['status']}", normal_style))
                elements.append(Spacer(1, 12))

                # Создаем таблицу студентов
                if 'students' in vedomost and vedomost['students']:
                    # Заголовки таблицы
                    table_data = [['№', 'ФИО', 'Зачетная книжка', 'Рейтинг', 'Оценка']]

                    # Данные студентов
                    for i, student in enumerate(vedomost['students'], 1):
                        table_data.append([
                            str(i),
                            student.get('name', ''),
                            student.get('record_book', ''),
                            student.get('final_rating', ''),
                            student.get('final_grade', '')
                        ])

                    # Создаем таблицу
                    table = Table(table_data, repeatRows=1)

                    # Стиль таблицы
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))

                    elements.append(table)

                # Генерируем PDF
                doc.build(elements)

                logger.info(f"Ведомость {vedomost_id} экспортирована в PDF: {filepath}")
                return filepath

            except ImportError:
                logger.warning("Библиотека ReportLab не установлена, создаем простой текстовый файл вместо PDF")

                # Если ReportLab не установлен, создаем текстовый файл с расширением .pdf
                with open(filepath, 'w', encoding='utf-8') as file:
                    file.write(f"Ведомость: {vedomost['discipline']}\n")
                    file.write(f"Группа: {vedomost['group_name']}\n")
                    file.write(f"Преподаватель: {vedomost['teacher']}\n")
                    file.write(f"Тип: {vedomost['type']}\n")
                    file.write(f"Семестр: {vedomost['semester']} ({vedomost['year']})\n")
                    file.write(f"Статус: {vedomost['status']}\n\n")

                    file.write("Студенты:\n")
                    if 'students' in vedomost and vedomost['students']:
                        for i, student in enumerate(vedomost['students'], 1):
                            file.write(f"{i}. {student.get('name', '')}, "
                                       f"Зачетка: {student.get('record_book', '')}, "
                                       f"Рейтинг: {student.get('final_rating', '')}, "
                                       f"Оценка: {student.get('final_grade', '')}\n")

                logger.info(f"Ведомость {vedomost_id} экспортирована в текстовый файл: {filepath}")
                return filepath

        except Exception as e:
            logger.error(f"Ошибка при экспорте ведомости в PDF: {e}\n{traceback.format_exc()}")
            return None

    async def initialize_database(self) -> None:
        """Инициализация базы данных начальными данными."""
        try:
            logger.info("Начало инициализации базы данных")

            # Обновляем факультеты
            await self.update_all_faculties()

            # Обновляем группы для всех факультетов
            await self.update_all_groups()

            # Обновляем ведомости для текущего учебного года и семестра
            await self.update_all_groups_vedomosti()

            logger.info("База данных успешно инициализирована")
        except Exception as e:
            logger.error(f"Ошибка при инициализации базы данных: {e}\n{traceback.format_exc()}")

    async def run_periodic_update(self, update_interval: int = 600) -> None:
        """
        Запуск периодического обновления данных.

        Args:
            update_interval: Интервал обновления в секундах (по умолчанию 10 минут)
        """
        try:
            logger.info(f"Запуск периодического обновления с интервалом {update_interval} секунд")

            while True:
                try:
                    # Обновляем устаревшие ведомости
                    await self.update_outdated_vedomosti()

                    # Ждем до следующего обновления
                    logger.info(f"Следующее обновление через {update_interval} секунд")
                    await asyncio.sleep(update_interval)
                except Exception as e:
                    logger.error(f"Ошибка в цикле обновления: {e}\n{traceback.format_exc()}")
                    # В случае ошибки делаем паузу перед повторной попыткой
                    await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Критическая ошибка в периодическом обновлении: {e}\n{traceback.format_exc()}")
            # Завершаем работу в случае критической ошибки
            sys.exit(1)

    def close(self) -> None:
        """Закрытие соединений и освобождение ресурсов."""
        self.db_manager.close()
        logger.info("Обновление данных завершено, соединения закрыты")


async def main():
    """Основная функция для запуска обновления данных."""
    # Устанавливаем обработчик сигналов для корректного завершения
    import signal

    updater = DataUpdater()

    def signal_handler(sig, frame):
        logger.info("Получен сигнал завершения, закрываем соединения")
        updater.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Проверяем наличие аргументов командной строки
        if len(sys.argv) > 1:
            command = sys.argv[1]

            if command == "init":
                # Инициализация базы данных
                await updater.initialize_database()
            elif command == "update_faculties":
                # Обновление только факультетов
                await updater.update_all_faculties()
            elif command == "update_groups":
                # Обновление только групп
                await updater.update_all_groups()
            elif command == "update_vedomosti":
                # Обновление только ведомостей
                await updater.update_all_groups_vedomosti()
            else:
                logger.error(f"Неизвестная команда: {command}")
                print(f"Использование: {sys.argv[0]} [init|update_faculties|update_groups|update_vedomosti]")
        else:
            # Запуск периодического обновления
            await updater.run_periodic_update()
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}\n{traceback.format_exc()}")
    finally:
        updater.close()


if __name__ == "__main__":
    asyncio.run(main())