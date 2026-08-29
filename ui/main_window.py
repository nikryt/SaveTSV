import tkinter as tk
from tkinter import ttk, scrolledtext
from ui.sheet_settings import SheetSettingsFrame


class MainWindow:
    def __init__(self, root, app):
        self.root = root
        self.app = app
        self.context_menu = app.context_menu_manager

        self.create_widgets()

    def create_widgets(self):
        """Создание виджетов главного окна"""
        # Main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Верхняя панель
        self.create_top_panel()

        # Настройки подключения
        self.create_connection_settings()

        # Настройки листов
        self.sheet1_settings = SheetSettingsFrame(self.main_frame, 1, self.context_menu)
        self.sheet1_settings.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        self.sheet2_settings = SheetSettingsFrame(self.main_frame, 2, self.context_menu)
        self.sheet2_settings.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        # Настройки сохранения
        self.create_output_settings()

        # Настройки уведомлений
        self.create_notification_settings()

        # Кнопки
        self.create_buttons()

        # Статус
        self.create_status()

        # Журнал
        self.create_log()

    def create_top_panel(self):
        """Создание верхней панели"""
        top_frame = ttk.Frame(self.main_frame)
        top_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)

        self.theme_button = ttk.Button(top_frame, text="🌙 Темная тема",
                                       command=self.app.toggle_theme)
        self.theme_button.pack(side=tk.RIGHT, padx=5)

    def create_connection_settings(self):
        """Создание настроек подключения"""
        config_frame = ttk.LabelFrame(self.main_frame, text="Настройки подключения", padding="10")
        config_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)

        # Spreadsheet ID
        ttk.Label(config_frame, text="Spreadsheet ID:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.spreadsheet_id_var = tk.StringVar()
        spreadsheet_entry = ttk.Entry(config_frame, textvariable=self.spreadsheet_id_var, width=50)
        spreadsheet_entry.grid(row=0, column=1, pady=2)
        ttk.Button(config_frame, text="Получить листы",
                   command=self.app.get_sheet_list).grid(row=0, column=2, padx=5)
        self.context_menu.add_to_entry(spreadsheet_entry)

        # Метод выбора
        ttk.Label(config_frame, text="Метод выбора:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.selection_method = tk.StringVar(value="by_name")
        method_frame = ttk.Frame(config_frame)
        method_frame.grid(row=1, column=1, sticky=tk.W, pady=2)

        ttk.Radiobutton(method_frame, text="По имени", variable=self.selection_method,
                        value="by_name", command=self.app.toggle_selection_method).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(method_frame, text="По индексу", variable=self.selection_method,
                        value="by_index", command=self.app.toggle_selection_method).pack(side=tk.LEFT, padx=5)

        # Автоопределение имени файла
        self.auto_filename = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame,
                        text="Автоматически использовать имя листа как имя файла",
                        variable=self.auto_filename,
                        command=self.app.toggle_auto_filename).grid(row=2, column=1, sticky=tk.W, pady=5)

        # Кодировка
        ttk.Label(config_frame, text="Кодировка:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.encoding_var = tk.StringVar(value='utf-8')
        encoding_combo = ttk.Combobox(config_frame, textvariable=self.encoding_var,
                                      values=['utf-8', 'utf-8-sig', 'cp1251', 'cp866', 'koi8-r'],
                                      width=20)
        encoding_combo.grid(row=3, column=1, sticky=tk.W, pady=2)
        self.context_menu.add_to_entry(encoding_combo)

        # Переносы строк
        ttk.Label(config_frame, text="Переносы строк:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.newline_var = tk.StringVar(value='unix')
        newline_frame = ttk.Frame(config_frame)
        newline_frame.grid(row=4, column=1, sticky=tk.W, pady=2)

        ttk.Radiobutton(newline_frame, text="Windows (CRLF)", variable=self.newline_var,
                        value="windows").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(newline_frame, text="Unix (LF)", variable=self.newline_var,
                        value="unix").pack(side=tk.LEFT, padx=5)

    def create_output_settings(self):
        """Создание настроек сохранения"""
        output_frame = ttk.LabelFrame(self.main_frame, text="Настройки сохранения", padding="10")
        output_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(output_frame, text="Папка:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.folder_path_var = tk.StringVar()
        folder_entry = ttk.Entry(output_frame, textvariable=self.folder_path_var, width=40)
        folder_entry.grid(row=0, column=1, pady=2)
        self.context_menu.add_to_entry(folder_entry)

        ttk.Button(output_frame, text="Обзор", command=self.app.browse_folder).grid(row=0, column=2, padx=5)
        ttk.Button(output_frame, text="По умолчанию",
                   command=self.app.set_default_folder).grid(row=0, column=3, padx=5)

    def create_notification_settings(self):
        """Создание настроек уведомлений"""
        notification_frame = ttk.LabelFrame(self.main_frame, text="Настройки уведомлений", padding="10")
        notification_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=5)

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

    def create_buttons(self):
        """Создание кнопок"""
        button_frame = ttk.Frame(self.main_frame)
        button_frame.grid(row=6, column=0, pady=10)

        self.auth_btn = ttk.Button(button_frame, text="1. Авторизация",
                                   command=self.app.authenticate_google)
        self.auth_btn.pack(side=tk.LEFT, padx=5)

        self.save_btn = ttk.Button(button_frame, text="2. Сохранить сейчас",
                                   command=self.app.save_now, state=tk.DISABLED)
        self.save_btn.pack(side=tk.LEFT, padx=5)

        self.start_btn = ttk.Button(button_frame, text="3. Запустить авто-сохранение",
                                    command=self.app.toggle_auto_save, state=tk.DISABLED)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="Сохранить конфигурацию",
                   command=self.app.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Свернуть в трей",
                   command=self.app.hide_window).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Сохранить журнал",
                   command=self.app.save_log).pack(side=tk.LEFT, padx=5)

    def create_status(self):
        """Создание статуса"""
        self.status_var = tk.StringVar(value="Статус: Не авторизован")
        ttk.Label(self.main_frame, textvariable=self.status_var,
                  foreground="red", font=("Arial", 10, "bold")).grid(row=7, column=0, pady=5)

    def create_log(self):
        """Создание журнала"""
        ttk.Label(self.main_frame, text="Журнал:").grid(row=8, column=0, sticky=tk.W)
        self.log_text = scrolledtext.ScrolledText(self.main_frame, height=12, width=90)
        self.log_text.grid(row=9, column=0, pady=5)