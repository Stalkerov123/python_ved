"""
Модуль для экспорта данных в различные форматы.
"""
from __future__ import annotations

import csv
import json
import os
from typing import List, Dict, Any, Optional
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DataExporter')

try:
    import pandas as pd

    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logger.warning("Pandas не установлен. Экспорт в Excel недоступен.")


class DataExporter:
    """
    Класс для экспорта данных в различные форматы.
    """

    def __init__(self, output_dir: str = "output"):
        """
        Инициализация экспортера данных.

        Args:
            output_dir: Директория для сохранения файлов
        """
        self.output_dir = output_dir
        # Создаем директорию, если не существует
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.debug(f"Создана директория: {output_dir}")

    def export_to_csv(self, data: List[Dict[str, Any]], filename: str) -> str:
        """
        Экспорт данных в CSV формат.

        Args:
            data: Список словарей с данными
            filename: Имя файла без расширения

        Returns:
            str: Путь к сохраненному файлу
        """
        if not data:
            logger.warning("Нет данных для экспорта в CSV")
            return ""

        filepath = os.path.join(self.output_dir, f"{filename}.csv")

        try:
            # Получаем заголовки из первой записи
            fieldnames = data[0].keys()

            with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)

            logger.info(f"Данные успешно экспортированы в CSV: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Ошибка при экспорте в CSV: {e}")
            return ""

    def export_to_json(self, data: List[Dict[str, Any]] | Dict[str, Any], filename: str) -> str:
        """
        Экспорт данных в JSON формат.

        Args:
            data: Список словарей или словарь с данными
            filename: Имя файла без расширения

        Returns:
            str: Путь к сохраненному файлу
        """
        if not data:
            logger.warning("Нет данных для экспорта в JSON")
            return ""

        filepath = os.path.join(self.output_dir, f"{filename}.json")

        try:
            with open(filepath, 'w', encoding='utf-8') as jsonfile:
                json.dump(data, jsonfile, ensure_ascii=False, indent=4)

            logger.info(f"Данные успешно экспортированы в JSON: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Ошибка при экспорте в JSON: {e}")
            return ""

    def export_to_excel(self, data: List[Dict[str, Any]], filename: str) -> str:
        """
        Экспорт данных в Excel формат.

        Args:
            data: Список словарей с данными
            filename: Имя файла без расширения

        Returns:
            str: Путь к сохраненному файлу
        """
        if not PANDAS_AVAILABLE:
            logger.error("Pandas не установлен. Экспорт в Excel недоступен.")
            return ""

        if not data:
            logger.warning("Нет данных для экспорта в Excel")
            return ""

        filepath = os.path.join(self.output_dir, f"{filename}.xlsx")

        try:
            df = pd.DataFrame(data)
            df.to_excel(filepath, index=False)

            logger.info(f"Данные успешно экспортированы в Excel: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Ошибка при экспорте в Excel: {e}")
            return ""
            return ""

