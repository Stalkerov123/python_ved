#!/usr/bin/env python
"""
Скрипт для создания и настройки файла .env для Telegram бота VSUET.
"""

import os
import re

def create_env_file():
    """Создает файл .env на основе .env.example и предлагает заполнить значения."""
    
    # Проверяем существование файла .env.example
    if not os.path.exists('.env.example'):
        print("Ошибка: Файл .env.example не найден в текущей директории.")
        return False
    
    # Проверяем, существует ли уже файл .env
    if os.path.exists('.env'):
        overwrite = input("Файл .env уже существует. Перезаписать? (y/n): ").lower()
        if overwrite != 'y':
            print("Операция отменена.")
            return False
    
    # Чтение содержимого .env.example
    with open('.env.example', 'r', encoding='utf-8') as example_file:
        example_content = example_file.read()
    
    # Поиск переменных, требующих заполнения
    env_vars = re.findall(r'^([A-Z_]+)=(.*)$', example_content, re.MULTILINE)
    
    # Запрос значений у пользователя
    env_values = {}
    print("\nНеобходимо заполнить следующие переменные:")
    
    for var_name, default_value in env_vars:
        # Предлагаем подсказки для некоторых переменных
        prompt_text = f"{var_name} "
        hint_text = ""
        
        if var_name == "BOT_TOKEN":
            hint_text = "(Получите у @BotFather в Telegram)"
        elif var_name == "WEBHOOK_HOST":
            hint_text = "(Например, yourdomain.com или IP-адрес)"
        elif var_name == "USE_WEBHOOK":
            hint_text = "(True для продакшн, False для локальной разработки)"
        
        if hint_text:
            prompt_text += hint_text + " "
        
        prompt_text += f"[{default_value}]: "
        user_value = input(prompt_text).strip()
        
        # Если пользователь не ввел значение, используем дефолтное
        if not user_value:
            env_values[var_name] = default_value
        else:
            env_values[var_name] = user_value
    
    # Формируем содержимое файла .env
    env_content = ""
    for var_name, default_value in env_vars:
        env_content += f"{var_name}={env_values[var_name]}\n"
    
    # Записываем в файл .env
    with open('.env', 'w', encoding='utf-8') as env_file:
        env_file.write(env_content)
    
    print("\nФайл .env успешно создан и заполнен.")
    
    # Проверка наличия токена бота
    if env_values.get('BOT_TOKEN') == 'YOUR_BOT_TOKEN_HERE':
        print("\nВНИМАНИЕ: Вы не указали токен бота.")
        print("Получите токен у @BotFather в Telegram и обновите файл .env.")
    
    return True

def main():
    """Основная функция."""
    print("=" * 60)
    print("Создание файла .env для Telegram бота VSUET")
    print("=" * 60)
    
    create_env_file()
    
    print("\nДля запуска бота выполните команду: python main.py")
    print("=" * 60)

if __name__ == "__main__":
    main()