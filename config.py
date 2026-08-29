import os
import json
import sys


class ConfigManager:
    def __init__(self, app_dir):
        self.app_dir = app_dir
        self.config_file = 'config.json'
        self.config_path = os.path.join(app_dir, self.config_file)
        self.config_data = {}

    def get_config_path(self):
        """Получение пути к файлу конфигурации"""
        return self.config_path

    def load(self):
        """Загрузка конфигурации"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
                return self.config_data
            return {}
        except Exception as e:
            print(f"Ошибка загрузки конфигурации: {str(e)}")
            return {}

    def save(self, config_data):
        """Сохранение конфигурации"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Ошибка сохранения конфигурации: {str(e)}")
            return False

    def get(self, key, default=None):
        """Получение значения из конфигурации"""
        return self.config_data.get(key, default)

    def set(self, key, value):
        """Установка значения в конфигурации"""
        self.config_data[key] = value