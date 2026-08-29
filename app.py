import os
import json
import time
import threading
import platform
import tkinter as tk
from tkinter import messagebox, filedialog

from config import ConfigManager
from logger import Logger
from theme_manager import ThemeManager
from tray_manager import TrayManager
from google_sheets import GoogleSheetsManager
from file_manager import FileManager
from ui.context_menu import ContextMenuManager
from ui.hotkeys import HotkeyManager
from ui.main_window import MainWindow


class GoogleSheetsSyncApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Google Sheets Sync")
        self.root.geometry("860x1120")

        # Инициализация менеджеров
        self.file_manager = FileManager()
        self.app_dir = self.file_manager.get_app_directory()
        self.logger = Logger()
        self.config_manager = ConfigManager(self.app_dir)
        self.theme_manager = ThemeManager(self.root)
        self.tray_manager = TrayManager(self)
        self.sheets_manager = None
        self.context_menu_manager = ContextMenuManager(self.root)
        self.hotkey_manager = None

        # Переменные состояния
        self.is_running = False
        self.monitoring_thread = None
        self.available_sheets = []
        self.sheet_names_cache = {}

        # Инициализация UI
        self.ui = MainWindow(self.root, self)

        # Подключаем логгер
        self.logger.set_log_widget(self.ui.log_text)

        # Настройка горячих клавиш
        self.hotkey_manager = HotkeyManager(self.root)

        # Загрузка конфигурации
        self.load_config()

        # Применение темы
        self.apply_theme()

        # Настройка трея
        self.setup_tray()

        # Настройка контекстных меню
        self.setup_context_menus()

        # Определение ОС
        self.detect_os()

        # Инициализация UI
        self.toggle_selection_method()
        self.toggle_auto_filename()

    def detect_os(self):
        """Определение операционной системы"""
        self.os_type = platform.system()
        self.is_windows = self.os_type == 'Windows'
        self.is_macos = self.os_type == 'Darwin'
        self.default_encoding = 'utf-8'
        self.logger.log(f"Операционная система: {self.os_type}")

    def setup_context_menus(self):
        """Настройка контекстных меню"""
        callbacks = {
            'clear': self.clear_log,
            'save': self.save_log
        }
        self.context_menu_manager.add_to_text(self.ui.log_text, callbacks)

    def apply_theme(self):
        """Применение темы"""
        self.theme_manager.apply_theme(self.ui.log_text)

    def toggle_theme(self):
        """Переключение темы"""
        self.theme_manager.toggle_theme(self.ui.log_text)
        theme_name = self.theme_manager.theme_var.get()
        self.ui.theme_button.config(text="☀️ Светлая тема" if theme_name == "dark" else "🌙 Темная тема")
        self.logger.log(f"Применена {'темная' if theme_name == 'dark' else 'светлая'} тема")

    def setup_tray(self):
        """Настройка трея"""
        callbacks = {
            'show': self.show_window,
            'start': self.start_autosave,
            'stop': self.stop_autosave,
            'save': self.save_now,
            'quit': self.quit_app
        }
        if self.tray_manager.setup(callbacks):
            self.logger.log("Иконка в трее создана")

    def toggle_selection_method(self):
        """Переключение метода выбора"""
        method = self.ui.selection_method.get()

        if method == "by_name":
            self.ui.sheet1_settings.show_name_selection()
            self.ui.sheet2_settings.show_name_selection()
        else:
            self.ui.sheet1_settings.show_index_selection()
            self.ui.sheet2_settings.show_index_selection()
            self.update_index_labels()

    def toggle_auto_filename(self):
        """Переключение автоопределения имени файла"""
        if self.ui.auto_filename.get():
            self.ui.sheet1_settings.filename_entry.config(state=tk.DISABLED)
            self.ui.sheet2_settings.filename_entry.config(state=tk.DISABLED)
        else:
            self.ui.sheet1_settings.filename_entry.config(state=tk.NORMAL)
            self.ui.sheet2_settings.filename_entry.config(state=tk.NORMAL)

    def get_current_sheet_name(self, sheet_number):
        """Получение имени текущего листа"""
        if self.ui.selection_method.get() == "by_name":
            if sheet_number == 1:
                return self.ui.sheet1_settings.name_var.get().strip()
            else:
                return self.ui.sheet2_settings.name_var.get().strip()
        else:
            if sheet_number == 1:
                index = self.ui.sheet1_settings.index_var.get()
            else:
                index = self.ui.sheet2_settings.index_var.get()

            if index in self.sheet_names_cache:
                return self.sheet_names_cache[index]
            elif index < len(self.available_sheets):
                return self.available_sheets[index]
        return None

    def update_filename_from_sheet(self):
        """Обновление имени файла из имени листа"""
        if not self.ui.auto_filename.get():
            return

        for sheet_num in [1, 2]:
            sheet_name = self.get_current_sheet_name(sheet_num)
            if sheet_name:
                safe_name = self.file_manager.sanitize_filename(sheet_name)
                if sheet_num == 1:
                    self.ui.sheet1_settings.filename_var.set(f"{safe_name}.tsv")
                else:
                    self.ui.sheet2_settings.filename_var.set(f"{safe_name}.tsv")

    def update_index_labels(self):
        """Обновление меток индексов"""
        if self.available_sheets:
            for sheet_num in [1, 2]:
                if sheet_num == 1:
                    index = self.ui.sheet1_settings.index_var.get()
                    label = self.ui.sheet1_settings.index_label
                else:
                    index = self.ui.sheet2_settings.index_var.get()
                    label = self.ui.sheet2_settings.index_label

                if index < len(self.available_sheets):
                    label.config(text=f"→ {self.available_sheets[index]}")
                else:
                    label.config(text="→ Индекс вне диапазона")

    def authenticate_google(self):
        """Авторизация в Google"""
        if not self.sheets_manager:
            self.sheets_manager = GoogleSheetsManager(self.app_dir, self.logger)

        if self.sheets_manager.authenticate():
            self.ui.status_var.set("Статус: Авторизован")
            self.ui.save_btn.config(state=tk.NORMAL)
            self.ui.start_btn.config(state=tk.NORMAL)

            if self.ui.spreadsheet_id_var.get():
                self.get_sheet_list()

    def get_sheet_list(self):
        """Получение списка листов"""
        if not self.sheets_manager:
            messagebox.showwarning("Предупреждение", "Сначала авторизуйтесь")
            return

        spreadsheet_id = self.ui.spreadsheet_id_var.get().strip()

        if 'docs.google.com' in spreadsheet_id:
            import re
            match = re.search(r'/d/([a-zA-Z0-9-_]+)', spreadsheet_id)
            if match:
                spreadsheet_id = match.group(1)
                self.ui.spreadsheet_id_var.set(spreadsheet_id)

        sheets = self.sheets_manager.get_sheet_list(spreadsheet_id)

        if sheets:
            self.available_sheets = [sheet['name'] for sheet in sheets]
            self.sheet_names_cache = {sheet['index']: sheet['name'] for sheet in sheets}

            self.ui.sheet1_settings.name_combo['values'] = self.available_sheets
            self.ui.sheet2_settings.name_combo['values'] = self.available_sheets

            max_index = len(self.available_sheets) - 1
            self.ui.sheet1_settings.index_spinbox.config(to=max_index)
            self.ui.sheet2_settings.index_spinbox.config(to=max_index)

            self.update_index_labels()
            self.update_filename_from_sheet()

            self.logger.log(f"Загружено листов: {len(self.available_sheets)}")

    def save_now(self):
        """Немедленное сохранение"""
        if not self.sheets_manager or not self.sheets_manager.service:
            messagebox.showwarning("Предупреждение", "Сначала авторизуйтесь")
            return

        spreadsheet_id = self.ui.spreadsheet_id_var.get().strip()
        output_folder = self.ui.folder_path_var.get().strip() or self.file_manager.get_default_save_folder()
        self.file_manager.ensure_folder_exists(output_folder)

        newline = '\r\n' if self.ui.newline_var.get() == 'windows' else '\n'
        encoding = self.ui.encoding_var.get()

        for sheet_num in [1, 2]:
            if sheet_num == 1:
                save_enabled = self.ui.sheet1_settings.save_enabled_var.get()
            else:
                save_enabled = self.ui.sheet2_settings.save_enabled_var.get()

            if not save_enabled:
                continue

            sheet_identifier = self.get_current_sheet_name(sheet_num)
            if sheet_num == 1:
                filename = self.ui.sheet1_settings.filename_var.get()
            else:
                filename = self.ui.sheet2_settings.filename_var.get()

            if sheet_identifier and filename:
                data = self.sheets_manager.get_sheet_data(spreadsheet_id, sheet_identifier)
                if data:
                    filepath = os.path.join(output_folder, filename)
                    if self.file_manager.save_tsv(data, filepath, encoding, newline):
                        self.logger.log(f"Сохранено: {filename}")

    def start_autosave(self):
        """Запуск автосохранения"""
        if not self.sheets_manager or not self.sheets_manager.service:
            messagebox.showwarning("Предупреждение", "Сначала авторизуйтесь")
            return

        self.is_running = True
        self.ui.start_btn.config(text="Остановить авто-сохранение")
        self.start_monitoring()
        self.tray_manager.update_icon(True, self.theme_manager.theme_var.get())
        self.logger.log("Авто-сохранение запущено")

    def stop_autosave(self):
        """Остановка автосохранения"""
        self.is_running = False
        self.ui.start_btn.config(text="Запустить авто-сохранение")
        self.stop_monitoring()
        self.tray_manager.update_icon(False, self.theme_manager.theme_var.get())
        self.logger.log("Авто-сохранение остановлено")

    def toggle_auto_save(self):
        """Переключение автосохранения"""
        if self.is_running:
            self.stop_autosave()
        else:
            self.start_autosave()

    def start_monitoring(self):
        """Запуск мониторинга"""
        self.monitoring_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitoring_thread.start()
        self.last_check_time = {1: time.time(), 2: time.time()}
        self.last_data_hash = {}

    def monitor_loop(self):
        """Цикл мониторинга"""
        while self.is_running:
            try:
                current_time = time.time()

                for sheet_num in [1, 2]:
                    if sheet_num == 1:
                        save_enabled = self.ui.sheet1_settings.save_enabled_var.get()
                        check_interval = self.ui.sheet1_settings.check_interval_var.get()
                    else:
                        save_enabled = self.ui.sheet2_settings.save_enabled_var.get()
                        check_interval = self.ui.sheet2_settings.check_interval_var.get()

                    if (save_enabled and
                            current_time - self.last_check_time.get(sheet_num, 0) >= check_interval):
                        self.check_and_save_sheet(sheet_num)
                        self.last_check_time[sheet_num] = current_time

                time.sleep(5)
            except Exception as e:
                self.logger.log(f"Ошибка в цикле мониторинга: {str(e)}")
                time.sleep(10)

    def check_and_save_sheet(self, sheet_number):
        """Проверка и сохранение листа"""
        try:
            spreadsheet_id = self.ui.spreadsheet_id_var.get().strip()
            sheet_identifier = self.get_current_sheet_name(sheet_number)

            if not spreadsheet_id or not sheet_identifier:
                return

            data = self.sheets_manager.get_sheet_data(spreadsheet_id, sheet_identifier)
            if not data:
                return

            current_hash = hash(str(data))

            if sheet_number not in self.last_data_hash or self.last_data_hash[sheet_number] != current_hash:
                self.logger.log(f"Обнаружены изменения в листе {sheet_number}")

                if self.ui.notify_changes_var.get():
                    self.root.after(0, lambda: messagebox.showinfo("Изменения",
                                                                   "Обнаружены изменения в таблице. Обнови в PhotoMechanic, Reload All. Выполняется сохранение файлов..."))

                self.save_now()
                self.last_data_hash[sheet_number] = current_hash

        except Exception as e:
            self.logger.log(f"Ошибка проверки листа {sheet_number}: {str(e)}")

    def stop_monitoring(self):
        """Остановка мониторинга"""
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=1)

    def show_window(self):
        """Показать окно"""
        self.root.after(0, self._show_window)

    def _show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide_window(self):
        """Скрыть окно"""
        self.root.withdraw()
        self.tray_manager.notify("Приложение свернуто в трей", "Google Sheets Sync продолжает работать")

    def quit_app(self):
        """Закрытие приложения"""
        self.root.after(0, self.on_closing)

    def set_default_folder(self):
        """Установка папки по умолчанию"""
        default_folder = self.file_manager.get_default_save_folder()
        self.ui.folder_path_var.set(default_folder)
        self.logger.log(f"Установлена папка по умолчанию: {default_folder}")

    def browse_folder(self):
        """Выбор папки"""
        folder = filedialog.askdirectory()
        if folder:
            self.ui.folder_path_var.set(folder)

    def save_log(self):
        """Сохранение журнала"""
        if self.logger.save_to_file(self.root):
            messagebox.showinfo("Успех", "Журнал сохранен")

    def clear_log(self):
        """Очистка журнала"""
        if messagebox.askyesno("Подтверждение", "Очистить журнал?"):
            self.logger.clear()

    def load_config(self):
        """Загрузка конфигурации"""
        config = self.config_manager.load()

        if config:
            self.ui.spreadsheet_id_var.set(config.get('spreadsheet_id', ''))
            self.ui.selection_method.set(config.get('selection_method', 'by_name'))
            self.ui.auto_filename.set(config.get('auto_filename', True))
            self.ui.encoding_var.set(config.get('encoding', 'utf-8'))
            self.ui.newline_var.set(config.get('newline_mode', 'unix'))
            self.theme_manager.theme_var.set(config.get('theme', 'light'))

            sheets = config.get('sheets', [])

            if len(sheets) > 0:
                self.ui.sheet1_settings.name_var.set(sheets[0].get('name', ''))
                self.ui.sheet1_settings.filename_var.set(sheets[0].get('output_filename', 'sheet1.tsv'))
                self.ui.sheet1_settings.check_interval_var.set(sheets[0].get('check_interval', 30))
                self.ui.sheet1_settings.save_enabled_var.set(sheets[0].get('save_enabled', True))

            if len(sheets) > 1:
                self.ui.sheet2_settings.name_var.set(sheets[1].get('name', ''))
                self.ui.sheet2_settings.filename_var.set(sheets[1].get('output_filename', 'sheet2.tsv'))
                self.ui.sheet2_settings.check_interval_var.set(sheets[1].get('check_interval', 300))
                self.ui.sheet2_settings.save_enabled_var.set(sheets[1].get('save_enabled', True))

            folder_path = config.get('output_folder', '')
            self.ui.folder_path_var.set(folder_path or self.file_manager.get_default_save_folder())

            notifications = config.get('notifications', {})
            self.ui.notify_success_var.set(notifications.get('success', True))
            self.ui.notify_error_var.set(notifications.get('error', True))
            self.ui.notify_autosave_var.set(notifications.get('autosave', False))
            self.ui.notify_changes_var.set(notifications.get('changes', True))

    def save_config(self):
        """Сохранение конфигурации"""
        sheets = []

        for i in range(2):
            sheet_num = i + 1
            if sheet_num == 1:
                name = self.ui.sheet1_settings.name_var.get()
                filename = self.ui.sheet1_settings.filename_var.get()
                check_interval = self.ui.sheet1_settings.check_interval_var.get()
                save_enabled = self.ui.sheet1_settings.save_enabled_var.get()
                index = self.ui.sheet1_settings.index_var.get()
            else:
                name = self.ui.sheet2_settings.name_var.get()
                filename = self.ui.sheet2_settings.filename_var.get()
                check_interval = self.ui.sheet2_settings.check_interval_var.get()
                save_enabled = self.ui.sheet2_settings.save_enabled_var.get()
                index = self.ui.sheet2_settings.index_var.get()

            if self.ui.selection_method.get() == "by_name":
                sheet_config = {
                    'name': name,
                    'output_filename': filename,
                    'check_interval': check_interval,
                    'save_enabled': save_enabled
                }
            else:
                sheet_config = {
                    'index': index,
                    'output_filename': filename,
                    'check_interval': check_interval,
                    'save_enabled': save_enabled
                }
            sheets.append(sheet_config)

        config = {
            'spreadsheet_id': self.ui.spreadsheet_id_var.get(),
            'selection_method': self.ui.selection_method.get(),
            'auto_filename': self.ui.auto_filename.get(),
            'encoding': self.ui.encoding_var.get(),
            'newline_mode': self.ui.newline_var.get(),
            'theme': self.theme_manager.theme_var.get(),
            'sheets': sheets,
            'output_folder': self.ui.folder_path_var.get(),
            'notifications': {
                'success': self.ui.notify_success_var.get(),
                'error': self.ui.notify_error_var.get(),
                'autosave': self.ui.notify_autosave_var.get(),
                'changes': self.ui.notify_changes_var.get()
            }
        }

        if self.config_manager.save(config):
            self.logger.log("Конфигурация сохранена")

    def run(self):
        """Запуск приложения"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def on_closing(self):
        """Обработка закрытия"""
        self.save_config()
        self.is_running = False
        self.stop_monitoring()
        self.tray_manager.stop()
        self.root.destroy()


def create_app():
    """Создание приложения"""
    root = tk.Tk()
    app = GoogleSheetsSyncApp(root)
    return app, root