import sys
import os
import json
import time
import threading
import platform
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle


class GoogleSheetsSyncApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Google Sheets Sync")
        self.root.geometry("800x850")

        self.sheets_service = None
        self.is_running = False
        self.last_data_hash = None
        self.monitoring_thread = None
        self.scheduler_thread = None
        self.config_file = 'config.json'
        self.available_sheets = []
        self.sheet_names_cache = {}
        self.auto_filename = tk.BooleanVar(value=True)

        # Инициализируем log_text как None
        self.log_text = None

        # Определяем ОС и настройки
        self.detect_os_settings()

        # Определяем правильный путь к исполняемому файлу
        self.app_dir = self.get_app_directory()

        self.init_ui()
        self.load_config()

    def detect_os_settings(self):
        """Определение операционной системы и настроек"""
        self.os_type = platform.system()
        self.os_release = platform.release()

        if self.os_type == 'Windows':
            self.default_encoding = 'utf-8-sig'  # Для Excel на Windows
            self.newline_mode = '\r\n'  # Windows line endings
            self.path_separator = '\\'
            self.is_windows = True
            self.is_macos = False
        elif self.os_type == 'Darwin':
            self.default_encoding = 'utf-8'  # Стандарт для macOS
            self.newline_mode = '\n'  # Unix line endings
            self.path_separator = '/'
            self.is_windows = False
            self.is_macos = True
        else:  # Linux и другие Unix-подобные
            self.default_encoding = 'utf-8'
            self.newline_mode = '\n'
            self.path_separator = '/'
            self.is_windows = False
            self.is_macos = False

        # Не вызываем log здесь, так как log_text еще не создан
        print(f"Операционная система: {self.os_type} {self.os_release}")

    def get_app_directory(self):
        """Получение правильной директории приложения"""
        if getattr(sys, 'frozen', False):
            # Если приложение запущено как exe/app (PyInstaller)
            if hasattr(self, 'is_macos') and self.is_macos:
                # Для macOS .app bundle
                if '.app' in sys.executable:
                    # Находим папку Contents/MacOS
                    app_path = os.path.dirname(sys.executable)
                    # Поднимаемся на 2 уровня: MacOS -> Contents -> .app
                    bundle_path = os.path.dirname(os.path.dirname(app_path))
                    return bundle_path
                else:
                    return os.path.dirname(os.path.abspath(sys.executable))
            else:
                return os.path.dirname(os.path.abspath(sys.executable))
        else:
            # Если запущено как скрипт Python
            return os.path.dirname(os.path.abspath(__file__))

    def get_default_save_folder(self):
        """Получение папки сохранения по умолчанию"""
        return os.path.join(self.app_dir, "SaveSheets")

    def get_config_path(self):
        """Получение пути к файлу конфигурации"""
        return os.path.join(self.app_dir, self.config_file)

    def get_credentials_path(self):
        """Получение пути к файлу credentials.json"""
        return os.path.join(self.app_dir, 'credentials.json')

    def get_token_path(self):
        """Получение пути к файлу токена"""
        return os.path.join(self.app_dir, 'token.pickle')

    def init_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # OS Info
        os_frame = ttk.LabelFrame(main_frame, text="Информация о системе", padding="5")
        os_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)

        os_info = f"ОС: {self.os_type} | Кодировка: {self.default_encoding} | Переносы строк: {repr(self.newline_mode)}"
        ttk.Label(os_frame, text=os_info, foreground="blue").pack(anchor=tk.W)

        # Configuration section
        config_frame = ttk.LabelFrame(main_frame, text="Настройки подключения", padding="10")
        config_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)

        # Spreadsheet ID
        ttk.Label(config_frame, text="Spreadsheet ID:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.spreadsheet_id_var = tk.StringVar()
        spreadsheet_entry = ttk.Entry(config_frame, textvariable=self.spreadsheet_id_var, width=50)
        spreadsheet_entry.grid(row=0, column=1, pady=2)
        ttk.Button(config_frame, text="Получить листы", command=self.get_sheet_list).grid(row=0, column=2, padx=5)

        # Sheet selection method
        ttk.Label(config_frame, text="Метод выбора:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.selection_method = tk.StringVar(value="by_name")
        method_frame = ttk.Frame(config_frame)
        method_frame.grid(row=1, column=1, sticky=tk.W, pady=2)

        ttk.Radiobutton(method_frame, text="По имени", variable=self.selection_method,
                        value="by_name", command=self.toggle_selection_method).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(method_frame, text="По индексу", variable=self.selection_method,
                        value="by_index", command=self.toggle_selection_method).pack(side=tk.LEFT, padx=5)

        # Auto filename checkbox
        self.auto_filename_check = ttk.Checkbutton(config_frame,
                                                   text="Автоматически использовать имя листа как имя файла",
                                                   variable=self.auto_filename, command=self.toggle_auto_filename)
        self.auto_filename_check.grid(row=2, column=1, sticky=tk.W, pady=5)

        # Encoding selection
        ttk.Label(config_frame, text="Кодировка:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.encoding_var = tk.StringVar(value=self.default_encoding)
        encoding_frame = ttk.Frame(config_frame)
        encoding_frame.grid(row=3, column=1, sticky=tk.W, pady=2)

        encodings = ['utf-8', 'utf-8-sig', 'cp1251', 'cp866', 'koi8-r']
        self.encoding_combo = ttk.Combobox(encoding_frame, textvariable=self.encoding_var,
                                           values=encodings, width=20)
        self.encoding_combo.pack(side=tk.LEFT)
        ttk.Label(encoding_frame, text="(рекомендуется для этой ОС: {})".format(
            self.default_encoding)).pack(side=tk.LEFT, padx=5)

        # Line endings selection
        ttk.Label(config_frame, text="Переносы строк:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.newline_var = tk.StringVar(value='windows' if self.is_windows else 'unix')
        newline_frame = ttk.Frame(config_frame)
        newline_frame.grid(row=4, column=1, sticky=tk.W, pady=2)

        ttk.Radiobutton(newline_frame, text="Windows (CRLF)", variable=self.newline_var,
                        value="windows").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(newline_frame, text="Unix (LF)", variable=self.newline_var,
                        value="unix").pack(side=tk.LEFT, padx=5)

        # Sheet 1
        ttk.Label(config_frame, text="Лист 1:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.sheet1_frame = ttk.Frame(config_frame)
        self.sheet1_frame.grid(row=5, column=1, sticky=tk.W, pady=2)

        self.sheet1_name_var = tk.StringVar()
        self.sheet1_name_combo = ttk.Combobox(self.sheet1_frame, textvariable=self.sheet1_name_var, width=40)
        self.sheet1_name_combo.pack(side=tk.LEFT)
        self.sheet1_name_combo.bind('<<ComboboxSelected>>', self.on_sheet1_selected)

        self.sheet1_index_var = tk.IntVar(value=0)
        self.sheet1_index_spinbox = ttk.Spinbox(self.sheet1_frame, from_=0, to=100,
                                                textvariable=self.sheet1_index_var, width=10)
        self.sheet1_index_spinbox.bind('<KeyRelease>', self.on_sheet1_index_changed)
        self.sheet1_index_spinbox.bind('<ButtonRelease>', self.on_sheet1_index_changed)

        self.sheet1_index_label = ttk.Label(self.sheet1_frame, text="", foreground="blue")

        ttk.Label(config_frame, text="Файл 1:").grid(row=6, column=0, sticky=tk.W, pady=2)
        self.sheet1_filename_var = tk.StringVar(value="sheet1.tsv")
        self.sheet1_filename_entry = ttk.Entry(config_frame, textvariable=self.sheet1_filename_var, width=50)
        self.sheet1_filename_entry.grid(row=6, column=1, pady=2)

        # Sheet 2
        ttk.Label(config_frame, text="Лист 2:").grid(row=7, column=0, sticky=tk.W, pady=2)
        self.sheet2_frame = ttk.Frame(config_frame)
        self.sheet2_frame.grid(row=7, column=1, sticky=tk.W, pady=2)

        self.sheet2_name_var = tk.StringVar()
        self.sheet2_name_combo = ttk.Combobox(self.sheet2_frame, textvariable=self.sheet2_name_var, width=40)
        self.sheet2_name_combo.pack(side=tk.LEFT)
        self.sheet2_name_combo.bind('<<ComboboxSelected>>', self.on_sheet2_selected)

        self.sheet2_index_var = tk.IntVar(value=1)
        self.sheet2_index_spinbox = ttk.Spinbox(self.sheet2_frame, from_=0, to=100,
                                                textvariable=self.sheet2_index_var, width=10)
        self.sheet2_index_spinbox.bind('<KeyRelease>', self.on_sheet2_index_changed)
        self.sheet2_index_spinbox.bind('<ButtonRelease>', self.on_sheet2_index_changed)

        self.sheet2_index_label = ttk.Label(self.sheet2_frame, text="", foreground="blue")

        ttk.Label(config_frame, text="Файл 2:").grid(row=8, column=0, sticky=tk.W, pady=2)
        self.sheet2_filename_var = tk.StringVar(value="sheet2.tsv")
        self.sheet2_filename_entry = ttk.Entry(config_frame, textvariable=self.sheet2_filename_var, width=50)
        self.sheet2_filename_entry.grid(row=8, column=1, pady=2)

        # Output settings
        output_frame = ttk.LabelFrame(main_frame, text="Настройки сохранения", padding="10")
        output_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(output_frame, text="Папка:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.folder_path_var = tk.StringVar()
        ttk.Entry(output_frame, textvariable=self.folder_path_var, width=40).grid(row=0, column=1, pady=2)
        ttk.Button(output_frame, text="Обзор", command=self.browse_folder).grid(row=0, column=2, padx=5)
        ttk.Button(output_frame, text="По умолчанию", command=self.set_default_folder).grid(row=0, column=3, padx=5)

        default_folder = self.get_default_save_folder()
        ttk.Label(output_frame, text=f"По умолчанию: {default_folder}",
                  foreground="gray").grid(row=1, column=1, sticky=tk.W, pady=2)

        ttk.Label(output_frame, text="Интервал (мин):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.interval_var = tk.IntVar(value=5)
        ttk.Spinbox(output_frame, from_=1, to=1440, textvariable=self.interval_var, width=10).grid(row=2, column=1,
                                                                                                   sticky=tk.W, pady=2)

        self.auto_monitor_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(output_frame, text="Автоопределение изменений", variable=self.auto_monitor_var).grid(row=3,
                                                                                                             column=1,
                                                                                                             sticky=tk.W,
                                                                                                             pady=2)

        # Notification settings
        notification_frame = ttk.LabelFrame(main_frame, text="Настройки уведомлений", padding="10")
        notification_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)

        self.notify_success_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(notification_frame, text="Уведомлять об успешном сохранении",
                        variable=self.notify_success_var).grid(row=0, column=0, sticky=tk.W, pady=2)

        self.notify_error_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(notification_frame, text="Уведомлять об ошибках",
                        variable=self.notify_error_var).grid(row=1, column=0, sticky=tk.W, pady=2)

        self.notify_autosave_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(notification_frame, text="Уведомлять при автосохранении",
                        variable=self.notify_autosave_var).grid(row=2, column=0, sticky=tk.W, pady=2)

        self.notify_changes_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(notification_frame, text="Уведомлять об обнаружении изменений",
                        variable=self.notify_changes_var).grid(row=3, column=0, sticky=tk.W, pady=2)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, pady=10)

        self.auth_btn = ttk.Button(button_frame, text="1. Авторизация", command=self.authenticate_google)
        self.auth_btn.pack(side=tk.LEFT, padx=5)

        self.save_btn = ttk.Button(button_frame, text="2. Сохранить сейчас", command=self.save_now, state=tk.DISABLED)
        self.save_btn.pack(side=tk.LEFT, padx=5)

        self.start_btn = ttk.Button(button_frame, text="3. Запустить авто-сохранение", command=self.toggle_auto_save,
                                    state=tk.DISABLED)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="Сохранить конфигурацию", command=self.save_config).pack(side=tk.LEFT, padx=5)

        # Status
        self.status_var = tk.StringVar(value="Статус: Не авторизован")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, foreground="red", font=("Arial", 10, "bold"))
        status_label.grid(row=5, column=0, pady=5)

        # Log
        ttk.Label(main_frame, text="Журнал:").grid(row=6, column=0, sticky=tk.W)
        self.log_text = scrolledtext.ScrolledText(main_frame, height=12, width=90)
        self.log_text.grid(row=7, column=0, pady=5)

        # Теперь, когда log_text создан, выводим информацию об ОС
        self.log(f"Операционная система: {self.os_type} {self.os_release}")
        self.log(f"Кодировка по умолчанию: {self.default_encoding}")
        self.log(f"Папка приложения: {self.app_dir}")

        # Initialize UI state
        self.toggle_selection_method()
        self.toggle_auto_filename()

    def get_newline_chars(self):
        """Получение символов переноса строки в зависимости от настроек"""
        if self.newline_var.get() == 'windows':
            return '\r\n'
        else:
            return '\n'

    def toggle_auto_filename(self):
        """Включение/выключение автоматического определения имени файла"""
        if self.auto_filename.get():
            self.sheet1_filename_entry.config(state=tk.DISABLED)
            self.sheet2_filename_entry.config(state=tk.DISABLED)
            self.update_filename_from_sheet()
        else:
            self.sheet1_filename_entry.config(state=tk.NORMAL)
            self.sheet2_filename_entry.config(state=tk.NORMAL)

    def update_filename_from_sheet(self):
        """Обновление имени файла из имени листа"""
        if not self.auto_filename.get():
            return

        sheet1_name = self.get_current_sheet_name(1)
        if sheet1_name:
            safe_filename = self.sanitize_filename(sheet1_name)
            self.sheet1_filename_var.set(f"{safe_filename}.tsv")

        sheet2_name = self.get_current_sheet_name(2)
        if sheet2_name:
            safe_filename = self.sanitize_filename(sheet2_name)
            self.sheet2_filename_var.set(f"{safe_filename}.tsv")

    def sanitize_filename(self, filename):
        """Очистка имени файла от недопустимых символов для разных ОС"""
        # Общие недопустимые символы для Windows и macOS
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')

        # Дополнительные проверки для Windows
        if self.is_windows:
            # Зарезервированные имена в Windows
            reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3',
                              'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
                              'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6',
                              'LPT7', 'LPT8', 'LPT9']

            base_name = filename.split('.')[0].upper()
            if base_name in reserved_names:
                filename = f"_{filename}"

        # Убираем пробелы в начале и конце
        filename = filename.strip()

        # Убираем точки в конце (проблема для Windows)
        if self.is_windows:
            filename = filename.rstrip('.')

        return filename

    def get_current_sheet_name(self, sheet_number):
        """Получение текущего имени листа"""
        if self.selection_method.get() == "by_name":
            if sheet_number == 1:
                return self.sheet1_name_var.get().strip()
            else:
                return self.sheet2_name_var.get().strip()
        else:
            if sheet_number == 1:
                index = self.sheet1_index_var.get()
            else:
                index = self.sheet2_index_var.get()

            if index in self.sheet_names_cache:
                return self.sheet_names_cache[index]
            elif index < len(self.available_sheets):
                return self.available_sheets[index]

        return None

    def on_sheet1_selected(self, event=None):
        self.update_filename_from_sheet()

    def on_sheet2_selected(self, event=None):
        self.update_filename_from_sheet()

    def on_sheet1_index_changed(self, event=None):
        self.update_index_labels()
        self.update_filename_from_sheet()

    def on_sheet2_index_changed(self, event=None):
        self.update_index_labels()
        self.update_filename_from_sheet()

    def toggle_selection_method(self):
        """Переключение между выбором по имени и по индексу"""
        method = self.selection_method.get()

        for widget in self.sheet1_frame.winfo_children():
            widget.pack_forget()
        for widget in self.sheet2_frame.winfo_children():
            widget.pack_forget()

        if method == "by_name":
            self.sheet1_name_combo.pack(side=tk.LEFT)
            self.sheet2_name_combo.pack(side=tk.LEFT)
            self.log("Режим выбора: по имени листа")
        else:
            self.sheet1_index_spinbox.pack(side=tk.LEFT)
            self.sheet1_index_label.pack(side=tk.LEFT, padx=(10, 0))
            self.sheet2_index_spinbox.pack(side=tk.LEFT)
            self.sheet2_index_label.pack(side=tk.LEFT, padx=(10, 0))
            self.log("Режим выбора: по индексу листа")
            self.update_index_labels()

        self.update_filename_from_sheet()

    def update_index_labels(self):
        """Обновление меток с именами листов при выборе по индексу"""
        if self.available_sheets:
            try:
                index1 = self.sheet1_index_var.get()
                if index1 < len(self.available_sheets):
                    self.sheet1_index_label.config(text=f"→ {self.available_sheets[index1]}")
                else:
                    self.sheet1_index_label.config(text="→ Индекс вне диапазона")
            except:
                pass

            try:
                index2 = self.sheet2_index_var.get()
                if index2 < len(self.available_sheets):
                    self.sheet2_index_label.config(text=f"→ {self.available_sheets[index2]}")
                else:
                    self.sheet2_index_label.config(text="→ Индекс вне диапазона")
            except:
                pass

    def set_default_folder(self):
        """Установка папки по умолчанию"""
        default_folder = self.get_default_save_folder()
        self.folder_path_var.set(default_folder)
        self.log(f"Установлена папка по умолчанию: {default_folder}")

        if self.notify_success_var.get():
            messagebox.showinfo("Папка", f"Установлена папка:\n{default_folder}")

    def get_sheet_list(self):
        """Получение списка листов из Google Sheets"""
        if not self.sheets_service:
            messagebox.showwarning("Предупреждение", "Сначала авторизуйтесь")
            return

        spreadsheet_id = self.spreadsheet_id_var.get().strip()
        if not spreadsheet_id:
            messagebox.showwarning("Предупреждение", "Введите Spreadsheet ID")
            return

        try:
            spreadsheet = self.sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()

            self.available_sheets = []
            self.sheet_names_cache = {}

            for i, sheet in enumerate(spreadsheet.get('sheets', [])):
                sheet_name = sheet['properties']['title']
                self.available_sheets.append(sheet_name)
                self.sheet_names_cache[i] = sheet_name

            self.sheet1_name_combo['values'] = self.available_sheets
            self.sheet2_name_combo['values'] = self.available_sheets

            max_index = len(self.available_sheets) - 1
            self.sheet1_index_spinbox.config(to=max_index if max_index > 0 else 1)
            self.sheet2_index_spinbox.config(to=max_index if max_index > 0 else 1)

            self.log(f"Найдено листов: {len(self.available_sheets)}")
            self.log(f"Доступные листы: {', '.join(self.available_sheets)}")

            self.update_index_labels()
            self.update_filename_from_sheet()

            if self.notify_success_var.get():
                messagebox.showinfo("Успех", f"Найдено листов: {len(self.available_sheets)}\n\n" +
                                    "\n".join(f"{i}. {name}" for i, name in enumerate(self.available_sheets)))

        except Exception as e:
            self.log(f"Ошибка получения списка листов: {str(e)}")
            if self.notify_error_var.get():
                messagebox.showerror("Ошибка", f"Ошибка получения списка листов: {str(e)}")

    def log(self, message):
        """Логирование с проверкой наличия log_text"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"

        # Выводим в консоль для отладки
        print(log_message)

        # Выводим в GUI если log_text создан
        if self.log_text is not None:
            self.log_text.insert(tk.END, log_message + "\n")
            self.log_text.see(tk.END)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path_var.set(folder)
            self.log(f"Выбрана папка: {folder}")

    def load_config(self):
        """Загрузка конфигурации из файла"""
        try:
            config_path = self.get_config_path()

            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                self.spreadsheet_id_var.set(config.get('spreadsheet_id', ''))

                selection_method = config.get('selection_method', 'by_name')
                self.selection_method.set(selection_method)

                self.auto_filename.set(config.get('auto_filename', True))

                encoding = config.get('encoding', self.default_encoding)
                self.encoding_var.set(encoding)

                newline_setting = config.get('newline_mode', 'windows' if self.is_windows else 'unix')
                self.newline_var.set(newline_setting)

                sheets = config.get('sheets', [])

                if selection_method == "by_name":
                    if len(sheets) > 0:
                        self.sheet1_name_var.set(sheets[0].get('name', ''))
                        self.sheet1_filename_var.set(sheets[0].get('output_filename', 'sheet1.tsv'))
                    if len(sheets) > 1:
                        self.sheet2_name_var.set(sheets[1].get('name', ''))
                        self.sheet2_filename_var.set(sheets[1].get('output_filename', 'sheet2.tsv'))
                else:
                    if len(sheets) > 0:
                        self.sheet1_index_var.set(sheets[0].get('index', 0))
                        self.sheet1_filename_var.set(sheets[0].get('output_filename', 'sheet1.tsv'))
                    if len(sheets) > 1:
                        self.sheet2_index_var.set(sheets[1].get('index', 1))
                        self.sheet2_filename_var.set(sheets[1].get('output_filename', 'sheet2.tsv'))

                folder_path = config.get('output_folder', '')
                if not folder_path:
                    folder_path = self.get_default_save_folder()
                self.folder_path_var.set(folder_path)

                self.interval_var.set(config.get('update_interval_minutes', 5))
                self.auto_monitor_var.set(config.get('auto_monitor_changes', True))

                notifications = config.get('notifications', {})
                self.notify_success_var.set(notifications.get('success', True))
                self.notify_error_var.set(notifications.get('error', True))
                self.notify_autosave_var.set(notifications.get('autosave', False))
                self.notify_changes_var.set(notifications.get('changes', True))

                self.toggle_selection_method()
                self.toggle_auto_filename()
                self.log("Конфигурация загружена")
            else:
                self.set_default_folder()
                self.log("Конфигурация не найдена, установлены значения по умолчанию")

        except Exception as e:
            self.log(f"Ошибка загрузки конфигурации: {str(e)}")
            self.set_default_folder()

    def save_config(self):
        """Сохранение конфигурации в файл"""
        try:
            selection_method = self.selection_method.get()

            if selection_method == "by_name":
                sheets = [
                    {
                        'name': self.sheet1_name_var.get(),
                        'output_filename': self.sheet1_filename_var.get()
                    },
                    {
                        'name': self.sheet2_name_var.get(),
                        'output_filename': self.sheet2_filename_var.get()
                    }
                ]
            else:
                sheets = [
                    {
                        'index': self.sheet1_index_var.get(),
                        'output_filename': self.sheet1_filename_var.get()
                    },
                    {
                        'index': self.sheet2_index_var.get(),
                        'output_filename': self.sheet2_filename_var.get()
                    }
                ]

            config = {
                'spreadsheet_id': self.spreadsheet_id_var.get(),
                'selection_method': selection_method,
                'auto_filename': self.auto_filename.get(),
                'encoding': self.encoding_var.get(),
                'newline_mode': self.newline_var.get(),
                'sheets': sheets,
                'output_folder': self.folder_path_var.get(),
                'update_interval_minutes': self.interval_var.get(),
                'auto_monitor_changes': self.auto_monitor_var.get(),
                'notifications': {
                    'success': self.notify_success_var.get(),
                    'error': self.notify_error_var.get(),
                    'autosave': self.notify_autosave_var.get(),
                    'changes': self.notify_changes_var.get()
                }
            }

            config_path = self.get_config_path()

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            self.log(f"Конфигурация сохранена в: {config_path}")
            if self.notify_success_var.get():
                messagebox.showinfo("Успех", "Конфигурация сохранена")
        except Exception as e:
            if self.notify_error_var.get():
                messagebox.showerror("Ошибка", f"Ошибка сохранения: {str(e)}")

    def authenticate_google(self):
        """Авторизация в Google"""
        try:
            SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
            creds = None

            token_file = self.get_token_path()
            if os.path.exists(token_file):
                with open(token_file, 'rb') as token:
                    creds = pickle.load(token)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    credentials_file = self.get_credentials_path()
                    if not os.path.exists(credentials_file):
                        if self.notify_error_var.get():
                            messagebox.showerror("Ошибка",
                                                 f"Файл credentials.json не найден.\n"
                                                 f"Поместите его в папку:\n{self.app_dir}")
                        return

                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_file, SCOPES)
                    creds = flow.run_local_server(port=0)

                with open(token_file, 'wb') as token:
                    pickle.dump(creds, token)

            self.sheets_service = build('sheets', 'v4', credentials=creds)
            self.status_var.set("Статус: Авторизован")
            self.save_btn.config(state=tk.NORMAL)
            self.start_btn.config(state=tk.NORMAL)
            self.log("Авторизация успешна")

            if self.spreadsheet_id_var.get():
                self.get_sheet_list()

            if self.notify_success_var.get():
                messagebox.showinfo("Успех", "Авторизация успешна!")

        except Exception as e:
            self.log(f"Ошибка авторизации: {str(e)}")
            if self.notify_error_var.get():
                messagebox.showerror("Ошибка", f"Ошибка авторизации: {str(e)}")

    def get_sheet_name_by_index(self, index):
        """Получение актуального имени листа по индексу"""
        self.refresh_sheet_names()

        if index in self.sheet_names_cache:
            return self.sheet_names_cache[index]

        return None

    def refresh_sheet_names(self):
        """Обновление списка имен листов"""
        if not self.sheets_service:
            return

        spreadsheet_id = self.spreadsheet_id_var.get().strip()
        if not spreadsheet_id:
            return

        try:
            spreadsheet = self.sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()

            self.available_sheets = []
            self.sheet_names_cache = {}

            for i, sheet in enumerate(spreadsheet.get('sheets', [])):
                sheet_name = sheet['properties']['title']
                self.available_sheets.append(sheet_name)
                self.sheet_names_cache[i] = sheet_name

            self.sheet1_name_combo['values'] = self.available_sheets
            self.sheet2_name_combo['values'] = self.available_sheets
            self.update_index_labels()
            self.update_filename_from_sheet()

        except Exception as e:
            self.log(f"Ошибка обновления списка листов: {str(e)}")

    def get_sheet_identifier(self, sheet_number):
        """Получение идентификатора листа"""
        if self.selection_method.get() == "by_name":
            if sheet_number == 1:
                return self.sheet1_name_var.get().strip()
            else:
                return self.sheet2_name_var.get().strip()
        else:
            if sheet_number == 1:
                index = self.sheet1_index_var.get()
            else:
                index = self.sheet2_index_var.get()

            sheet_name = self.get_sheet_name_by_index(index)
            if sheet_name:
                self.log(f"Лист {sheet_number} (индекс {index}): {sheet_name}")
                return sheet_name
            else:
                return str(index)

    def get_output_folder(self):
        """Получение папки для сохранения"""
        folder = self.folder_path_var.get().strip()
        if not folder:
            folder = self.get_default_save_folder()

        os.makedirs(folder, exist_ok=True)
        return folder

    def save_now(self, is_auto_save=False):
        """Немедленное сохранение"""
        if not self.sheets_service:
            if self.notify_error_var.get():
                messagebox.showwarning("Предупреждение", "Сначала авторизуйтесь")
            return

        spreadsheet_id = self.spreadsheet_id_var.get().strip()

        if not spreadsheet_id:
            if self.notify_error_var.get():
                messagebox.showwarning("Предупреждение", "Введите Spreadsheet ID")
            return

        try:
            self.refresh_sheet_names()

            if self.auto_filename.get():
                self.update_filename_from_sheet()

            output_folder = self.get_output_folder()

            sheet1_identifier = self.get_sheet_identifier(1)
            filename1 = self.sheet1_filename_var.get().strip()
            if sheet1_identifier and filename1:
                self.save_sheet_to_tsv(spreadsheet_id, sheet1_identifier, output_folder, filename1)

            sheet2_identifier = self.get_sheet_identifier(2)
            filename2 = self.sheet2_filename_var.get().strip()
            if sheet2_identifier and filename2:
                self.save_sheet_to_tsv(spreadsheet_id, sheet2_identifier, output_folder, filename2)

            self.log(f"Данные успешно сохранены в: {output_folder}")

            if not is_auto_save or self.notify_autosave_var.get():
                if self.notify_success_var.get():
                    messagebox.showinfo("Успех", f"Данные сохранены в:\n{output_folder}")

        except Exception as e:
            self.log(f"Ошибка сохранения: {str(e)}")
            if self.notify_error_var.get():
                messagebox.showerror("Ошибка", f"Ошибка сохранения: {str(e)}")

    def save_sheet_to_tsv(self, spreadsheet_id, sheet_identifier, output_folder, filename):
        """Сохранение листа в TSV с учетом настроек ОС"""
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=sheet_identifier
            ).execute()

            values = result.get('values', [])

            if not values:
                self.log(f"Лист '{sheet_identifier}' пуст")
                return

            filepath = os.path.join(output_folder, filename)

            encoding = self.encoding_var.get()
            newline = self.get_newline_chars()

            with open(filepath, 'w', encoding=encoding, newline='') as f:
                for row in values:
                    processed_row = []
                    for cell in row:
                        cell_str = str(cell)
                        cell_str = cell_str.replace('\t', ' ')
                        cell_str = cell_str.replace('\r\n', ' ')
                        cell_str = cell_str.replace('\n', ' ')
                        cell_str = cell_str.replace('\r', ' ')
                        processed_row.append(cell_str)

                    f.write('\t'.join(processed_row) + newline)

            self.log(f"Сохранено: {filename} (лист: {sheet_identifier}, кодировка: {encoding})")

        except Exception as e:
            raise Exception(f"Ошибка сохранения листа '{sheet_identifier}': {str(e)}")

    def toggle_auto_save(self):
        """Включение/выключение автосохранения"""
        if not self.is_running:
            if not self.sheets_service:
                if self.notify_error_var.get():
                    messagebox.showwarning("Предупреждение", "Сначала авторизуйтесь")
                return

            self.is_running = True
            self.start_btn.config(text="Остановить авто-сохранение")
            self.start_scheduler()

            if self.auto_monitor_var.get():
                self.start_monitoring()

            self.log("Авто-сохранение запущено")

        else:
            self.is_running = False
            self.start_btn.config(text="Запустить авто-сохранение")
            self.stop_scheduler()
            self.stop_monitoring()
            self.log("Авто-сохранение остановлено")

    def start_scheduler(self):
        """Запуск планировщика"""
        self.scheduler_thread = threading.Thread(target=self.scheduler_loop, daemon=True)
        self.scheduler_thread.start()

    def scheduler_loop(self):
        """Цикл планировщика"""
        interval = self.interval_var.get() * 60
        while self.is_running:
            time.sleep(interval)
            if self.is_running:
                self.root.after(0, lambda: self.save_now(is_auto_save=True))

    def stop_scheduler(self):
        """Остановка планировщика"""
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=1)

    def start_monitoring(self):
        """Запуск мониторинга изменений"""
        self.monitoring_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitoring_thread.start()

    def monitor_loop(self):
        """Цикл мониторинга изменений"""
        while self.is_running:
            try:
                spreadsheet_id = self.spreadsheet_id_var.get().strip()

                if spreadsheet_id:
                    self.refresh_sheet_names()

                    sheet1_identifier = self.get_sheet_identifier(1)
                    sheet2_identifier = self.get_sheet_identifier(2)

                    data_hash = ""

                    for sheet_identifier in [sheet1_identifier, sheet2_identifier]:
                        if sheet_identifier:
                            try:
                                result = self.sheets_service.spreadsheets().values().get(
                                    spreadsheetId=spreadsheet_id,
                                    range=sheet_identifier
                                ).execute()
                                data_hash += str(result)
                            except:
                                pass

                    current_hash = hash(data_hash)

                    if self.last_data_hash is not None and self.last_data_hash != current_hash:
                        self.log("Обнаружены изменения в таблице")

                        if self.notify_changes_var.get():
                            self.root.after(0, lambda: messagebox.showinfo("Изменения",
                                                                           "Обнаружены изменения в таблице. Обнови в PhotoMechanic, Reload All. Выполняется сохранение файлов..."))

                        self.root.after(0, lambda: self.save_now(is_auto_save=True))

                    self.last_data_hash = current_hash

                time.sleep(90)

            except Exception as e:
                time.sleep(180)

    def stop_monitoring(self):
        """Остановка мониторинга"""
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=1)

    def run(self):
        """Запуск приложения"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def on_closing(self):
        """Обработка закрытия приложения"""
        self.save_config()
        self.is_running = False
        self.stop_scheduler()
        self.stop_monitoring()
        self.root.destroy()


def main():
    app = GoogleSheetsSyncApp()
    app.run()


if __name__ == '__main__':
    main()