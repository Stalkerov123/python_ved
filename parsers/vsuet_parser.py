"""
Класс для парсинга данных с сайта ВГУИТ.
"""

import requests
from bs4 import BeautifulSoup
import re
import logging
from typing import List, Optional

from models.faculty import Faculty
from models.group import Group
from models.vedomosti import VedomostInfo

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('VsuetParser')


class VsuetParser:
    """
    Класс для работы с API сайта ВГУИТ и парсинга данных о ведомостях.
    """
    
    def __init__(self, base_url="https://rating.vsuet.ru/web/Ved/"):
        """
        Инициализация парсера.
        
        Args:
            base_url: Базовый URL для API ведомостей
        """
        self.base_url = base_url
        self.session = requests.Session()
        # Инициализация сессии для сохранения cookies
        self._init_session()
    
    def _init_session(self) -> None:
        """Инициализация сессии для получения необходимых cookies."""
        try:
            response = self.session.get(self.base_url + "Default.aspx")
            response.raise_for_status()
            logger.debug("Сессия успешно инициализирована")
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при инициализации сессии: {e}")
            raise Exception(f"Не удалось подключиться к серверу ВГУИТ: {e}")
    
    def _get_view_state(self, html_content: str) -> tuple:
        """
        Извлечение значений __VIEWSTATE и __EVENTVALIDATION из HTML.
        
        Args:
            html_content: HTML-контент страницы
            
        Returns:
            tuple: (viewstate, eventvalidation)
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        viewstate = soup.find('input', {'id': '__VIEWSTATE'}).get('value', '')
        eventvalidation = soup.find('input', {'id': '__EVENTVALIDATION'}).get('value', '')
        return viewstate, eventvalidation
    
    def get_faculties(self) -> List[Faculty]:
        """
        Получение списка всех факультетов.
        
        Returns:
            List[Faculty]: Список объектов Faculty
        """
        try:
            response = self.session.get(self.base_url + "Default.aspx")
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            faculties = []
            
            faculty_select = soup.find('select', {'id': 'ctl00_ContentPage_cmbFacultets'})
            if faculty_select:
                for option in faculty_select.find_all('option'):
                    faculties.append(Faculty(
                        id=option['value'],
                        name=option.text
                    ))
                
                logger.info(f"Получено {len(faculties)} факультетов")
                return faculties
            else:
                logger.warning("Не найден элемент выбора факультета")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении списка факультетов: {e}")
            return []
    
    def get_groups_by_faculty(self, faculty_id: str) -> List[Group]:
        """
        Получение списка групп для конкретного факультета.
        
        Args:
            faculty_id: ID факультета
            
        Returns:
            List[Group]: Список объектов Group
        """
        try:
            response = self.session.get(self.base_url + "Default.aspx")
            response.raise_for_status()
            
            viewstate, eventvalidation = self._get_view_state(response.text)
            
            # Формирование POST-запроса для выбора факультета
            form_data = {
                '__EVENTTARGET': 'ctl00$ContentPage$cmbFacultets',
                '__EVENTARGUMENT': '',
                '__VIEWSTATE': viewstate,
                '__EVENTVALIDATION': eventvalidation,
                'ctl00$ContentPage$cmbFacultets': faculty_id
            }
            
            response = self.session.post(self.base_url + "Default.aspx", data=form_data)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            groups = []
            
            group_select = soup.find('select', {'id': 'ctl00_ContentPage_cmbGroups'})
            if group_select:
                for option in group_select.find_all('option'):
                    groups.append(Group(
                        id=option['value'],
                        name=option.text,
                        faculty_id=faculty_id
                    ))
                
                logger.info(f"Получено {len(groups)} групп для факультета {faculty_id}")
                return groups
            else:
                logger.warning(f"Не найден элемент выбора групп для факультета {faculty_id}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении списка групп: {e}")
            return []
    
    def get_ved_list(self, group_id: str, year: str = "2024-2025", semester: str = "0") -> List[VedomostInfo]:
        """
        Получение списка ведомостей для конкретной группы.
        
        Args:
            group_id: ID группы
            year: Учебный год (формат: "2024-2025")
            semester: Семестр (0 - весна, 1 - осень)
            
        Returns:
            List[VedomostInfo]: Список объектов VedomostInfo
        """
        try:
            response = self.session.get(self.base_url + "Default.aspx")
            response.raise_for_status()
            
            viewstate, eventvalidation = self._get_view_state(response.text)
            
            # Формирование POST-запроса для выбора группы и семестра
            form_data = {
                '__EVENTTARGET': 'ctl00$ContentPage$cmbGroups',
                '__EVENTARGUMENT': '',
                '__VIEWSTATE': viewstate,
                '__EVENTVALIDATION': eventvalidation,
                'ctl00$ContentPage$cmbGroups': group_id,
                'ctl00$ContentPage$cmbYears': year,
                'ctl00$ContentPage$cmbSem': semester
            }
            
            response = self.session.post(self.base_url + "Default.aspx", data=form_data)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            ved_list = []
            
            # Получаем название группы для добавления в объект ведомости
            group_name = ""
            group_info = soup.find('span', {'id': 'ctl00_ContentPage_lblName'})
            if group_info:
                match = re.search(r'>([^<]+)<a>', group_info.decode_contents())
                if match:
                    group_name = match.group(1).strip()
            
            ved_table = soup.find('table', {'id': 'ctl00_ContentPage_ucListVedBox_Grid'})
            if ved_table:
                rows = ved_table.find_all('tr')[1:]  # Пропускаем заголовок таблицы
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        discipline_cell = cells[0]
                        discipline_link = discipline_cell.find('a')
                        
                        discipline_name = discipline_cell.text.strip()
                        ved_type = cells[1].text.strip()
                        closed = cells[2].text.strip()
                        
                        ved_url = None
                        ved_id = None
                        if discipline_link and 'href' in discipline_link.attrs:
                            href = discipline_link['href']
                            ved_url = self.base_url + href
                            match = re.search(r'id=(\d+)', href)
                            if match:
                                ved_id = match.group(1)
                        
                        ved_list.append(VedomostInfo(
                            id=ved_id,
                            discipline=discipline_name,
                            type=ved_type,
                            closed=closed,
                            url=ved_url,
                            group_id=group_id,
                            group_name=group_name,
                            year=year,
                            semester="Весна" if semester == "0" else "Осень"
                        ))
                
                logger.info(f"Получено {len(ved_list)} ведомостей для группы {group_id}")
                return ved_list
            else:
                logger.warning(f"Не найдена таблица ведомостей для группы {group_id}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении списка ведомостей: {e}")
            return []
    
    def get_detailed_ved(self, ved_id: str) -> Optional[dict]:
        """
        Получение детальной информации о ведомости.
        
        Args:
            ved_id: ID ведомости
            
        Returns:
            Optional[dict]: Словарь с информацией о ведомости или None в случае ошибки
        """
        try:
            response = self.session.get(f"{self.base_url}Ved.aspx?id={ved_id}")
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Извлечение основной информации о ведомости
            ved_info = {
                'id': ved_id,
                'group': self._get_text_by_id(soup, 'ucVedBox_lblGroup'),
                'discipline': self._get_text_by_id(soup, 'ucVedBox_lblDis'),
                'teacher': self._get_text_by_id(soup, 'ucVedBox_lblPrep'),
                'hours': self._get_text_by_id(soup, 'ucVedBox_lblHours'),
                'type': self._get_text_by_id(soup, 'ucVedBox_lblTypeVed'),
                'block': self._get_text_by_id(soup, 'ucVedBox_lblBlock'),
                'kurs': self._get_text_by_id(soup, 'ucVedBox_lblKurs'),
                'semester': self._get_text_by_id(soup, 'ucVedBox_lblSem'),
                'year': self._get_text_by_id(soup, 'ucVedBox_lblYear'),
                'status': self._get_text_by_id(soup, 'ucVedBox_lblStatus'),
                'date_update': self._get_text_by_id(soup, 'ucVedBox_lblDateUpdate'),
                'department': self._get_text_by_id(soup, 'ucVedBox_lblKafName'),
                'plan': self._get_text_by_id(soup, 'ucVedBox_lblPlan'),
                'students': []
            }
            
            # Парсинг таблицы студентов
            table = soup.find('table', {'id': 'ucVedBox_tblVed'})
            if table:
                # Получаем информацию о контрольных точках (КТ)
                kt_dates = []
                kt_weights = []
                kt_row = table.find('tr', {'id': 'ucVedBox_Row1'})
                
                if kt_row:
                    # Извлечение дат КТ
                    date_cells = kt_row.find_all('td', {'class': 'VedRow1'})
                    for cell in date_cells:
                        if cell.text.strip() and len(cell.text.strip()) <= 10:  # Фильтрация ячеек с датами
                            kt_dates.append(cell.text.strip())
                
                # Извлечение весов КТ
                weight_rows = table.find_all('tr')
                if len(weight_rows) > 1:
                    weight_cells = weight_rows[1].find_all('td')
                    for i, cell in enumerate(weight_cells):
                        if "Вес Точки" in cell.text:
                            # Следующая ячейка содержит значение веса
                            weight_value = weight_cells[i+1].text.strip()
                            kt_weights.append(weight_value)
                
                ved_info['kt_dates'] = kt_dates
                ved_info['kt_weights'] = kt_weights
                
                # Извлечение информации о студентах
                student_rows = table.find_all('tr', {'class': re.compile(r'VedRow\d+')})
                
                for row in student_rows:
                    cells = row.find_all('td')
                    if len(cells) >= 5:
                        student_link = cells[1].find('a')
                        student_id = None
                        student_name = ''
                        
                        if student_link:
                            student_href = student_link.get('href', '')
                            student_name = student_link.text.strip()
                            match = re.search(r'id=(\d+)', student_href)
                            if match:
                                student_id = match.group(1)
                        
                        # Извлечение номера зачетной книжки
                        record_book = cells[2].text.strip() if len(cells) > 2 else ''
                        
                        # Извлечение оценок по КТ
                        kt_results = []
                        for i in range(7, len(cells), 5):  # Шаг 5 для извлечения итогов по КТ
                            if i < len(cells):
                                kt_results.append(cells[i].text.strip())
                        
                        # Извлечение итогового рейтинга
                        rating_index = -5  # Обычно это 5-й с конца
                        final_rating = cells[rating_index].text.strip() if len(cells) > abs(rating_index) else ''
                        
                        # Извлечение оценки по рейтингу
                        rating_grade_index = -4  # Обычно это 4-й с конца
                        rating_grade = cells[rating_grade_index].text.strip() if len(cells) > abs(rating_grade_index) else ''
                        
                        # Извлечение экзаменационной/зачетной оценки
                        exam_index = -3  # Обычно это 3-й с конца
                        exam_grade = cells[exam_index].text.strip() if len(cells) > abs(exam_index) else ''
                        
                        # Извлечение итоговой оценки
                        final_index = -2  # Обычно это 2-й с конца
                        final_grade = cells[final_index].text.strip() if len(cells) > abs(final_index) else ''
                        
                        student_info = {
                            'id': student_id,
                            'name': student_name,
                            'record_book': record_book,
                            'kt_results': kt_results,
                            'final_rating': final_rating,
                            'rating_grade': rating_grade,
                            'exam_grade': exam_grade,
                            'final_grade': final_grade
                        }
                        
                        ved_info['students'].append(student_info)
            
            logger.info(f"Получена детальная информация о ведомости {ved_id}")
            return ved_info
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении детальной информации о ведомости {ved_id}: {e}")
            return None
    
    def _get_text_by_id(self, soup: BeautifulSoup, element_id: str) -> str:
        """
        Вспомогательный метод для извлечения текста элемента по ID.
        
        Args:
            soup: объект BeautifulSoup
            element_id: ID элемента
            
        Returns:
            str: Текст элемента или пустая строка
        """
        element = soup.find(id=element_id)
        if element:
            return element.text.strip()
        return ""