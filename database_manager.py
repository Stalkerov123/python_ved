"""
Модуль для работы с базой данных SQLite.
Обеспечивает хранение и обновление данных о ведомостях, студентах и их оценках.
"""

import sqlite3
import logging
import json
import os
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DatabaseManager')


class DatabaseManager:
    """Класс для управления SQLite базой данных."""

    def __init__(self, db_path: str = "vedomosti.db"):
        """
        Инициализация менеджера базы данных.

        Args:
            db_path: Путь к файлу базы данных SQLite
        """
        self.db_path = db_path
        self.connection = None
        self.cursor = None

        # Подключение к базе данных
        self._connect()

        # Инициализация структуры базы данных
        self._init_db()

    def _connect(self) -> None:
        """Подключение к базе данных."""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row  # Для доступа к колонкам по имени
            self.cursor = self.connection.cursor()
            logger.debug(f"Подключение к базе данных {self.db_path} установлено")
        except sqlite3.Error as e:
            logger.error(f"Ошибка при подключении к базе данных: {e}")
            raise

    def _disconnect(self) -> None:
        """Отключение от базы данных."""
        if self.connection:
            self.connection.close()
            logger.debug("Соединение с базой данных закрыто")

    def _init_db(self) -> None:
        """Инициализация структуры базы данных, если она еще не создана."""
        try:
            # Таблица факультетов
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS faculties (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                last_updated TIMESTAMP
            )
            ''')

            # Таблица групп
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                faculty_id TEXT NOT NULL,
                last_updated TIMESTAMP,
                FOREIGN KEY (faculty_id) REFERENCES faculties(id)
            )
            ''')

            # Таблица ведомостей
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS vedomosti (
                id TEXT PRIMARY KEY,
                discipline TEXT NOT NULL,
                type TEXT NOT NULL,
                group_id TEXT NOT NULL,
                teacher TEXT,
                semester TEXT,
                year TEXT,
                status TEXT,
                hours TEXT,
                block TEXT,
                kurs TEXT,
                department TEXT,
                plan TEXT,
                date_update TEXT,
                last_checked TIMESTAMP,
                details_json TEXT,
                FOREIGN KEY (group_id) REFERENCES groups(id)
            )
            ''')

            # Таблица студентов
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT UNIQUE,
                record_book TEXT NOT NULL,
                name TEXT NOT NULL,
                group_id TEXT,
                FOREIGN KEY (group_id) REFERENCES groups(id)
            )
            ''')

            # Таблица результатов студентов
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS student_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                vedomost_id TEXT NOT NULL,
                final_rating TEXT,
                rating_grade TEXT,
                exam_grade TEXT,
                final_grade TEXT,
                kt_results_json TEXT,
                last_updated TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(student_id),
                FOREIGN KEY (vedomost_id) REFERENCES vedomosti(id),
                UNIQUE(student_id, vedomost_id)
            )
            ''')

            # Таблица уведомлений
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                student_id TEXT NOT NULL,
                vedomost_id TEXT NOT NULL,
                old_grade TEXT,
                new_grade TEXT,
                old_rating TEXT,
                new_rating TEXT,
                created_at TIMESTAMP,
                sent BOOLEAN DEFAULT 0,
                FOREIGN KEY (student_id) REFERENCES students(student_id),
                FOREIGN KEY (vedomost_id) REFERENCES vedomosti(id)
            )
            ''')

            # Таблица настроек пользователей
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                telegram_user_id INTEGER PRIMARY KEY,
                faculty_id TEXT,
                group_id TEXT,
                record_book TEXT,
                notify_enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP,
                last_updated TIMESTAMP,
                FOREIGN KEY (faculty_id) REFERENCES faculties(id),
                FOREIGN KEY (group_id) REFERENCES groups(id)
            )
            ''')

            # Создаем индексы для повышения производительности
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_student_results_student ON student_results(student_id)')
            self.cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_student_results_vedomost ON student_results(vedomost_id)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(telegram_user_id)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_students_record_book ON students(record_book)')

            self.connection.commit()
            logger.info("Структура базы данных инициализирована")
        except sqlite3.Error as e:
            logger.error(f"Ошибка при инициализации структуры базы данных: {e}")
            raise

    # Методы для работы с факультетами
    def save_faculties(self, faculties: List[Dict[str, Any]]) -> None:
        """
        Сохранение списка факультетов в базу данных.

        Args:
            faculties: Список словарей с данными о факультетах
        """
        try:
            now = datetime.now().isoformat()

            for faculty in faculties:
                self.cursor.execute(
                    "INSERT OR REPLACE INTO faculties (id, name, last_updated) VALUES (?, ?, ?)",
                    (faculty['id'], faculty['name'], now)
                )

            self.connection.commit()
            logger.info(f"Сохранено {len(faculties)} факультетов")
        except sqlite3.Error as e:
            logger.error(f"Ошибка при сохранении факультетов: {e}")
            self.connection.rollback()

    def get_faculties(self) -> List[Dict[str, Any]]:
        """
        Получение списка всех факультетов из базы данных.

        Returns:
            List[Dict[str, Any]]: Список словарей с данными о факультетах
        """
        try:
            self.cursor.execute("SELECT id, name FROM faculties ORDER BY name")
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении списка факультетов: {e}")
            return []

    # Методы для работы с группами
    def save_groups(self, groups: List[Dict[str, Any]], faculty_id: str) -> None:
        """
        Сохранение списка групп для факультета в базу данных.

        Args:
            groups: Список словарей с данными о группах
            faculty_id: ID факультета
        """
        try:
            now = datetime.now().isoformat()

            for group in groups:
                self.cursor.execute(
                    "INSERT OR REPLACE INTO groups (id, name, faculty_id, last_updated) VALUES (?, ?, ?, ?)",
                    (group['id'], group['name'], faculty_id, now)
                )

            self.connection.commit()
            logger.info(f"Сохранено {len(groups)} групп для факультета {faculty_id}")
        except sqlite3.Error as e:
            logger.error(f"Ошибка при сохранении групп: {e}")
            self.connection.rollback()

    def get_groups(self, faculty_id: str = None) -> List[Dict[str, Any]]:
        """
        Получение списка групп из базы данных.

        Args:
            faculty_id: ID факультета (если None, вернуть все группы)

        Returns:
            List[Dict[str, Any]]: Список словарей с данными о группах
        """
        try:
            if faculty_id:
                self.cursor.execute("SELECT id, name, faculty_id FROM groups WHERE faculty_id = ? ORDER BY name",
                                    (faculty_id,))
            else:
                self.cursor.execute("SELECT id, name, faculty_id FROM groups ORDER BY name")

            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении списка групп: {e}")
            return []

    # Методы для работы с ведомостями
    def save_vedomosti(self, vedomosti: List[Dict[str, Any]], group_id: str) -> None:
        """
        Сохранение списка ведомостей для группы в базу данных.

        Args:
            vedomosti: Список словарей с данными о ведомостях
            group_id: ID группы
        """
        try:
            now = datetime.now().isoformat()

            for ved in vedomosti:
                self.cursor.execute(
                    """
                    INSERT OR REPLACE INTO vedomosti 
                    (id, discipline, type, group_id, status, last_checked) 
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (ved['id'], ved['discipline'], ved['type'], group_id, ved.get('closed', ''), now)
                )

            self.connection.commit()
            logger.info(f"Сохранено {len(vedomosti)} ведомостей для группы {group_id}")
        except sqlite3.Error as e:
            logger.error(f"Ошибка при сохранении ведомостей: {e}")
            self.connection.rollback()

    def get_vedomosti(self, group_id: str = None) -> List[Dict[str, Any]]:
        """
        Получение списка ведомостей из базы данных.

        Args:
            group_id: ID группы (если None, вернуть все ведомости)

        Returns:
            List[Dict[str, Any]]: Список словарей с данными о ведомостях
        """
        try:
            if group_id:
                self.cursor.execute(
                    """
                    SELECT v.id, v.discipline, v.type, v.status, v.group_id, g.name as group_name 
                    FROM vedomosti v 
                    JOIN groups g ON v.group_id = g.id 
                    WHERE v.group_id = ? 
                    ORDER BY v.discipline
                    """,
                    (group_id,)
                )
            else:
                self.cursor.execute(
                    """
                    SELECT v.id, v.discipline, v.type, v.status, v.group_id, g.name as group_name 
                    FROM vedomosti v 
                    JOIN groups g ON v.group_id = g.id 
                    ORDER BY g.name, v.discipline
                    """
                )

            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении списка ведомостей: {e}")
            return []

    def save_vedomost_details(self, vedomost_id: str, details: Dict[str, Any]) -> None:
        """
        Сохранение детальной информации о ведомости.

        Args:
            vedomost_id: ID ведомости
            details: Словарь с детальной информацией о ведомости
        """
        try:
            now = datetime.now().isoformat()
            details_json = json.dumps(details, ensure_ascii=False)

            self.cursor.execute(
                """
                UPDATE vedomosti SET 
                teacher = ?, semester = ?, year = ?, status = ?, 
                hours = ?, block = ?, kurs = ?, department = ?,
                plan = ?, date_update = ?, last_checked = ?, details_json = ? 
                WHERE id = ?
                """,
                (
                    details.get('teacher', ''),
                    details.get('semester', ''),
                    details.get('year', ''),
                    details.get('status', ''),
                    details.get('hours', ''),
                    details.get('block', ''),
                    details.get('kurs', ''),
                    details.get('department', ''),
                    details.get('plan', ''),
                    details.get('date_update', ''),
                    now,
                    details_json,
                    vedomost_id
                )
            )

            # Сохраняем данные о студентах
            students = details.get('students', [])
            for student in students:
                student_id = student.get('id')
                if not student_id:
                    continue

                # Проверяем и сохраняем информацию о студенте
                self._save_or_update_student(
                    student_id=student_id,
                    record_book=student.get('record_book', ''),
                    name=student.get('name', ''),
                    group_id=details.get('group_id', '')
                )

                # Получаем предыдущий результат студента, если есть
                old_result = self._get_student_result(student_id, vedomost_id)

                # Сохраняем результат студента
                kt_results_json = json.dumps(student.get('kt_results', []), ensure_ascii=False)

                self.cursor.execute(
                    """
                    INSERT OR REPLACE INTO student_results
                    (student_id, vedomost_id, final_rating, rating_grade, exam_grade, final_grade, kt_results_json, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        student_id,
                        vedomost_id,
                        student.get('final_rating', ''),
                        student.get('rating_grade', ''),
                        student.get('exam_grade', ''),
                        student.get('final_grade', ''),
                        kt_results_json,
                        now
                    )
                )

                # Проверяем изменения и создаем уведомления
                self._check_for_changes(
                    student_id,
                    vedomost_id,
                    old_result,
                    {
                        'final_rating': student.get('final_rating', ''),
                        'final_grade': student.get('final_grade', '')
                    }
                )

            self.connection.commit()
            logger.info(f"Сохранены детали ведомости {vedomost_id} и данные {len(students)} студентов")
        except sqlite3.Error as e:
            logger.error(f"Ошибка при сохранении деталей ведомости: {e}")
            self.connection.rollback()

    def get_vedomost_details(self, vedomost_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение детальной информации о ведомости.

        Args:
            vedomost_id: ID ведомости

        Returns:
            Optional[Dict[str, Any]]: Словарь с детальной информацией о ведомости или None
        """
        try:
            self.cursor.execute(
                """
                SELECT v.*, g.name as group_name 
                FROM vedomosti v 
                JOIN groups g ON v.group_id = g.id 
                WHERE v.id = ?
                """,
                (vedomost_id,)
            )
            row = self.cursor.fetchone()

            if not row:
                return None

            result = dict(row)

            # Преобразуем JSON обратно в словарь, если есть данные
            if result.get('details_json'):
                details = json.loads(result['details_json'])
                result.update(details)

            # Получаем результаты студентов
            self.cursor.execute(
                """
                SELECT sr.*, s.name, s.record_book 
                FROM student_results sr 
                JOIN students s ON sr.student_id = s.student_id 
                WHERE sr.vedomost_id = ?
                """,
                (vedomost_id,)
            )
            students = []
            for student_row in self.cursor.fetchall():
                student_data = dict(student_row)

                # Преобразуем JSON результатов КТ обратно в список
                if student_data.get('kt_results_json'):
                    student_data['kt_results'] = json.loads(student_data['kt_results_json'])
                    del student_data['kt_results_json']

                students.append(student_data)

            result['students'] = students

            return result
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении деталей ведомости: {e}")
            return None

    def _save_or_update_student(self, student_id: str, record_book: str, name: str, group_id: str = None) -> None:
        """
        Сохранение или обновление информации о студенте.

        Args:
            student_id: ID студента
            record_book: Номер зачетной книжки
            name: ФИО студента
            group_id: ID группы (опционально)
        """
        try:
            # Проверяем, существует ли уже запись о данном студенте
            self.cursor.execute("SELECT student_id FROM students WHERE student_id = ?", (student_id,))
            if self.cursor.fetchone():
                # Обновляем существующую запись
                self.cursor.execute(
                    "UPDATE students SET name = ?, record_book = ?, group_id = COALESCE(?, group_id) WHERE student_id = ?",
                    (name, record_book, group_id, student_id)
                )
            else:
                # Создаем новую запись
                self.cursor.execute(
                    "INSERT INTO students (student_id, record_book, name, group_id) VALUES (?, ?, ?, ?)",
                    (student_id, record_book, name, group_id)
                )
        except sqlite3.Error as e:
            logger.error(f"Ошибка при сохранении информации о студенте: {e}")
            raise

    def get_student_by_record_book(self, record_book: str) -> Optional[Dict[str, Any]]:
        """
        Поиск студента по номеру зачетной книжки.

        Args:
            record_book: Номер зачетной книжки

        Returns:
            Optional[Dict[str, Any]]: Словарь с информацией о студенте или None
        """
        try:
            self.cursor.execute(
                """
                SELECT s.*, g.name as group_name, g.faculty_id 
                FROM students s 
                LEFT JOIN groups g ON s.group_id = g.id 
                WHERE s.record_book = ?
                """,
                (record_book,)
            )
            row = self.cursor.fetchone()

            if not row:
                return None

            return dict(row)
        except sqlite3.Error as e:
            logger.error(f"Ошибка при поиске студента по зачетной книжке: {e}")
            return None

    def get_student_results(self, student_id: str) -> List[Dict[str, Any]]:
        """
        Получение всех результатов студента.

        Args:
            student_id: ID студента

        Returns:
            List[Dict[str, Any]]: Список словарей с результатами студента
        """
        try:
            self.cursor.execute(
                """
                SELECT sr.*, v.discipline, v.type, v.group_id, g.name as group_name
                FROM student_results sr 
                JOIN vedomosti v ON sr.vedomost_id = v.id 
                JOIN groups g ON v.group_id = g.id 
                WHERE sr.student_id = ?
                ORDER BY v.year DESC, v.semester DESC, v.discipline
                """,
                (student_id,)
            )
            results = []
            for row in self.cursor.fetchall():
                result = dict(row)

                # Преобразуем JSON результатов КТ обратно в список
                if result.get('kt_results_json'):
                    result['kt_results'] = json.loads(result['kt_results_json'])
                    del result['kt_results_json']

                results.append(result)

            return results
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении результатов студента: {e}")
            return []

    def _get_student_result(self, student_id: str, vedomost_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение результата студента по конкретной ведомости.

        Args:
            student_id: ID студента
            vedomost_id: ID ведомости

        Returns:
            Optional[Dict[str, Any]]: Словарь с результатом или None
        """
        try:
            self.cursor.execute(
                "SELECT * FROM student_results WHERE student_id = ? AND vedomost_id = ?",
                (student_id, vedomost_id)
            )
            row = self.cursor.fetchone()

            if not row:
                return None

            result = dict(row)

            # Преобразуем JSON результатов КТ обратно в список
            if result.get('kt_results_json'):
                result['kt_results'] = json.loads(result['kt_results_json'])
                del result['kt_results_json']

            return result
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении результата студента: {e}")
            return None

    def _check_for_changes(self, student_id: str, vedomost_id: str, old_result: Optional[Dict[str, Any]],
                           new_result: Dict[str, Any]) -> None:
        """
        Проверка изменений в результатах студента и создание уведомлений.

        Args:
            student_id: ID студента
            vedomost_id: ID ведомости
            old_result: Старый результат (словарь или None)
            new_result: Новый результат (словарь)
        """
        try:
            # Если нет старого результата, значит это первая запись, не создаем уведомления
            if not old_result:
                return

            has_changes = False
            old_grade = old_result.get('final_grade', '')
            new_grade = new_result.get('final_grade', '')
            old_rating = old_result.get('final_rating', '')
            new_rating = new_result.get('final_rating', '')

            # Проверяем изменения в оценке
            if old_grade != new_grade and new_grade and old_grade:
                has_changes = True

            # Проверяем изменения в рейтинге
            if old_rating != new_rating and new_rating and old_rating:
                has_changes = True

            if has_changes:
                # Находим всех пользователей, подписанных на уведомления по данному студенту
                self.cursor.execute(
                    "SELECT telegram_user_id FROM user_settings WHERE record_book = (SELECT record_book FROM students WHERE student_id = ?) AND notify_enabled = 1",
                    (student_id,)
                )
                users = self.cursor.fetchall()

                now = datetime.now().isoformat()

                for user in users:
                    telegram_user_id = user[0]

                    self.cursor.execute(
                        """
                        INSERT INTO notifications 
                        (telegram_user_id, student_id, vedomost_id, old_grade, new_grade, old_rating, new_rating, created_at) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (telegram_user_id, student_id, vedomost_id, old_grade, new_grade, old_rating, new_rating, now)
                    )
        except sqlite3.Error as e:
            logger.error(f"Ошибка при проверке изменений: {e}")
            raise

    # Методы для работы с пользователями
    def save_user_settings(self, telegram_user_id: int, settings: Dict[str, Any]) -> None:
        """
        Сохранение настроек пользователя.

        Args:
            telegram_user_id: ID пользователя в Telegram
            settings: Словарь с настройками
        """
        try:
            now = datetime.now().isoformat()

            # Проверяем, существует ли уже запись о данном пользователе
            self.cursor.execute("SELECT telegram_user_id FROM user_settings WHERE telegram_user_id = ?",
                                (telegram_user_id,))
            if self.cursor.fetchone():
                # Обновляем существующую запись
                self.cursor.execute(
                    """
                    UPDATE user_settings SET 
                    faculty_id = COALESCE(?, faculty_id),
                    group_id = COALESCE(?, group_id),
                    record_book = COALESCE(?, record_book),
                    notify_enabled = COALESCE(?, notify_enabled),
                    last_updated = ?
                    WHERE telegram_user_id = ?
                    """,
                    (
                        settings.get('faculty_id'),
                        settings.get('group_id'),
                        settings.get('record_book'),
                        settings.get('notify_enabled'),
                        now,
                        telegram_user_id
                    )
                )
            else:
                # Создаем новую запись
                self.cursor.execute(
                    """
                    INSERT INTO user_settings 
                    (telegram_user_id, faculty_id, group_id, record_book, notify_enabled, created_at, last_updated) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        telegram_user_id,
                        settings.get('faculty_id'),
                        settings.get('group_id'),
                        settings.get('record_book'),
                        settings.get('notify_enabled', 1),
                        now,
                        now
                    )
                )

            self.connection.commit()
            logger.info(f"Сохранены настройки пользователя {telegram_user_id}")
        except sqlite3.Error as e:
            logger.error(f"Ошибка при сохранении настроек пользователя: {e}")
            self.connection.rollback()

    def get_user_settings(self, telegram_user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение настроек пользователя.

        Args:
            telegram_user_id: ID пользователя в Telegram

        Returns:
            Optional[Dict[str, Any]]: Словарь с настройками пользователя или None
        """
        try:
            self.cursor.execute(
                """
                SELECT us.*, f.name as faculty_name, g.name as group_name 
                FROM user_settings us 
                LEFT JOIN faculties f ON us.faculty_id = f.id 
                LEFT JOIN groups g ON us.group_id = g.id 
                WHERE us.telegram_user_id = ?
                """,
                (telegram_user_id,)
            )
            row = self.cursor.fetchone()

            if not row:
                return None

            return dict(row)
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении настроек пользователя: {e}")
            return None

    # Методы для работы с уведомлениями
    def get_pending_notifications(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Получение списка непрочитанных уведомлений.

        Args:
            limit: Максимальное количество уведомлений

        Returns:
            List[Dict[str, Any]]: Список словарей с данными уведомлений
        """
        try:
            self.cursor.execute(
                """
                SELECT n.*, v.discipline, v.group_id, g.name as group_name, s.name as student_name 
                FROM notifications n 
                JOIN vedomosti v ON n.vedomost_id = v.id 
                JOIN groups g ON v.group_id = g.id 
                JOIN students s ON n.student_id = s.student_id 
                WHERE n.sent = 0 
                ORDER BY n.created_at 
                LIMIT ?
                """,
                (limit,)
            )

            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении непрочитанных уведомлений: {e}")
            return []

    def mark_notification_as_sent(self, notification_id: int) -> None:
        """
        Отметка уведомления как отправленного.

        Args:
            notification_id: ID уведомления
        """
        try:
            self.cursor.execute(
                "UPDATE notifications SET sent = 1 WHERE id = ?",
                (notification_id,)
            )
            self.connection.commit()
            logger.debug(f"Уведомление {notification_id} отмечено как отправленное")
        except sqlite3.Error as e:
            logger.error(f"Ошибка при отметке уведомления как отправленного: {e}")
            self.connection.rollback()

    def get_vedomosti_to_update(self, age_hours: int = 6) -> List[Dict[str, Any]]:
        """
        Получение списка ведомостей, которые нужно обновить.

        Args:
            age_hours: Минимальный возраст ведомости в часах для обновления

        Returns:
            List[Dict[str, Any]]: Список словарей с данными о ведомостях
        """
        try:
            # Вычисляем время, после которого ведомости требуют обновления
            cutoff_time = datetime.now().timestamp() - (age_hours * 3600)
            cutoff_iso = datetime.fromtimestamp(cutoff_time).isoformat()

            self.cursor.execute(
                """
                SELECT v.id, v.discipline, v.group_id, g.name as group_name 
                FROM vedomosti v 
                JOIN groups g ON v.group_id = g.id 
                WHERE v.last_checked IS NULL OR v.last_checked < ? 
                ORDER BY v.last_checked ASC 
                LIMIT 100
                """,
                (cutoff_iso,)
            )

            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении списка ведомостей для обновления: {e}")
            return []

    def get_vedomosti_for_student(self, record_book: str) -> List[Dict[str, Any]]:
        """
        Получение списка ведомостей, в которых есть результаты для студента.

        Args:
            record_book: Номер зачетной книжки

        Returns:
            List[Dict[str, Any]]: Список словарей с данными о ведомостях
        """
        try:
            self.cursor.execute(
                """
                SELECT v.id, v.discipline, v.type, v.group_id, g.name as group_name, 
                       sr.final_rating, sr.rating_grade, sr.exam_grade, sr.final_grade 
                FROM student_results sr 
                JOIN students s ON sr.student_id = s.student_id 
                JOIN vedomosti v ON sr.vedomost_id = v.id 
                JOIN groups g ON v.group_id = g.id 
                WHERE s.record_book = ? 
                ORDER BY v.year DESC, v.semester DESC, v.discipline
                """,
                (record_book,)
            )

            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении ведомостей для студента: {e}")
            return []

    def close(self) -> None:
        """Закрытие соединения с базой данных."""
        self._disconnect()