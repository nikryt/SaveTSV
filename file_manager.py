import os
import sys
import platform


class FileManager:
    def __init__(self, logger=None):
        self.logger = logger
        self.os_type = platform.system()
        self.is_windows = self.os_type == 'Windows'
        self.is_macos = self.os_type == 'Darwin'

    def log(self, message):
        """Логирование"""
        if self.logger:
            self.logger.log(message)
        else:
            print(message)

    def get_app_directory(self):
        """Получение директории приложения"""
        if getattr(sys, 'frozen', False):
            if self.is_macos and '.app' in sys.executable:
                app_path = os.path.dirname(sys.executable)
                return os.path.dirname(os.path.dirname(app_path))
            else:
                return os.path.dirname(os.path.abspath(sys.executable))
        else:
            return os.path.dirname(os.path.abspath(__file__))

    def get_default_save_folder(self):
        """Получение папки сохранения по умолчанию"""
        app_dir = self.get_app_directory()
        return os.path.join(app_dir, "SaveSheets")

    def ensure_folder_exists(self, folder_path):
        """Создание папки, если она не существует"""
        try:
            os.makedirs(folder_path, exist_ok=True)
            return True
        except Exception as e:
            self.log(f"Ошибка создания папки: {str(e)}")
            return False

    def sanitize_filename(self, filename):
        """Очистка имени файла от недопустимых символов"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')

        if self.is_windows:
            reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3',
                              'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
                              'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6',
                              'LPT7', 'LPT8', 'LPT9']

            base_name = filename.split('.')[0].upper()
            if base_name in reserved_names:
                filename = f"_{filename}"

        filename = filename.strip()

        if self.is_windows:
            filename = filename.rstrip('.')

        return filename

    def save_tsv(self, data, filepath, encoding='utf-8', newline='\n'):
        """Сохранение данных в TSV файл"""
        try:
            with open(filepath, 'w', encoding=encoding, newline='') as f:
                for row in data:
                    processed_row = []
                    for cell in row:
                        cell_str = str(cell)
                        cell_str = cell_str.replace('\t', ' ')
                        cell_str = cell_str.replace('\r\n', ' ')
                        cell_str = cell_str.replace('\n', ' ')
                        cell_str = cell_str.replace('\r', ' ')
                        processed_row.append(cell_str)

                    f.write('\t'.join(processed_row) + newline)

            return True
        except Exception as e:
            self.log(f"Ошибка сохранения файла: {str(e)}")
            return False