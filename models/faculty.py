"""
Модель для представления факультета.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class Faculty:
    """
    Класс для представления информации о факультете.
    
    Attributes:
        id: Идентификатор факультета
        name: Название факультета
    """
    id: str
    name: str
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразование объекта в словарь.
        
        Returns:
            Dict[str, Any]: Словарь с атрибутами объекта
        """
        return asdict(self)