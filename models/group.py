"""
Модель для представления учебной группы.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional


@dataclass
class Group:
    """
    Класс для представления информации о группе.
    
    Attributes:
        id: Идентификатор группы
        name: Название группы
        faculty_id: Идентификатор факультета, к которому относится группа
    """
    id: str
    name: str
    faculty_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразование объекта в словарь.
        
        Returns:
            Dict[str, Any]: Словарь с атрибутами объекта
        """
        return asdict(self)