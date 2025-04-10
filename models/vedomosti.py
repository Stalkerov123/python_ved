"""
Модели для представления информации о ведомости и связанных данных.
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, Any, Optional, List


@dataclass
class VedomostInfo:
    """
    Класс для представления базовой информации о ведомости в списке.
    
    Attributes:
        id: Идентификатор ведомости
        discipline: Название дисциплины
        type: Тип ведомости
        closed: Статус ведомости (Да/Нет)
        url: URL для доступа к ведомости
        group_id: Идентификатор группы
        group_name: Название группы
        year: Учебный год
        semester: Семестр (Весна/Осень)
    """
    id: Optional[str]
    discipline: str
    type: str
    closed: str
    url: Optional[str]
    group_id: str
    group_name: Optional[str] = None
    year: Optional[str] = None
    semester: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразование объекта в словарь.
        
        Returns:
            Dict[str, Any]: Словарь с атрибутами объекта
        """
        return asdict(self)


@dataclass
class StudentResult:
    """
    Класс для представления результатов студента по ведомости.
    
    Attributes:
        id: Идентификатор студента
        name: ФИО студента
        record_book: Номер зачетной книжки
        kt_results: Результаты по контрольным точкам
        final_rating: Итоговый рейтинг
        rating_grade: Оценка по рейтингу
        exam_grade: Оценка за экзамен/зачет
        final_grade: Итоговая оценка
    """
    id: Optional[str]
    name: str
    record_book: str
    kt_results: List[str] = field(default_factory=list)
    final_rating: str = ""
    rating_grade: str = ""
    exam_grade: str = ""
    final_grade: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразование объекта в словарь.
        
        Returns:
            Dict[str, Any]: Словарь с атрибутами объекта
        """
        return asdict(self)


@dataclass
class DetailedVedomost:
    """
    Класс для представления детальной информации о ведомости.
    
    Attributes:
        id: Идентификатор ведомости
        group: Название группы
        discipline: Название дисциплины
        teacher: ФИО преподавателя
        hours: Количество часов
        type: Тип ведомости
        block: Блок дисциплины
        kurs: Курс
        semester: Семестр
        year: Учебный год
        status: Статус ведомости
        date_update: Дата обновления
        department: Кафедра
        plan: Учебный план
        kt_dates: Даты контрольных точек
        kt_weights: Веса контрольных точек
        students: Список результатов студентов
    """
    id: str
    group: str
    discipline: str
    teacher: str
    hours: str
    type: str
    block: str
    kurs: str
    semester: str
    year: str
    status: str
    date_update: str
    department: str
    plan: str
    kt_dates: List[str] = field(default_factory=list)
    kt_weights: List[str] = field(default_factory=list)
    students: List[StudentResult] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразование объекта в словарь.
        
        Returns:
            Dict[str, Any]: Словарь с атрибутами объекта
        """
        return {
            "id": self.id,
            "group": self.group,
            "discipline": self.discipline,
            "teacher": self.teacher,
            "hours": self.hours,
            "type": self.type,
            "block": self.block,
            "kurs": self.kurs,
            "semester": self.semester,
            "year": self.year,
            "status": self.status,
            "date_update": self.date_update,
            "department": self.department,
            "plan": self.plan,
            "kt_dates": self.kt_dates,
            "kt_weights": self.kt_weights,
            "students": [s.to_dict() for s in self.students]
        }