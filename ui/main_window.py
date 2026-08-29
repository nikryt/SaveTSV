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
        """Создание виджетов главного окна с прокруткой"""

        # Создаем Canvas для прокрутки
        self.canvas = tk.Canvas(self.root, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Создаем вертикальный скроллбар
        self.v_scrollbar = ttk.Scrollbar(self.root, orient=tk.VERTICAL, command=self.canvas.yview)
        self.v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Создаем горизонтальный скроллбар
        self.h_scrollbar = ttk.Scrollbar(self.root, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))

        # Настраиваем Canvas
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)

        # Создаем фрейм внутри Canvas
        self.main_frame = ttk.Frame(self.canvas, padding="10")
        self.canvas_window = self.canvas.create_window((0, 0), window=self.main_frame, anchor=tk.NW)

        # Привязываем события для обновления области прокрутки
        self.main_frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)

        # Настраиваем прокрутку колесиком мыши
        self.setup_mousewheel()

        # Создаем содержимое в правильном порядке
        self.create_content()

    def on_frame_configure(self, event=None):
        """Обновление области прокрутки при изменении размера фрейма"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event):
        """Обновление ширины фрейма при изменении размера Canvas"""
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def setup_mousewheel(self):
        """Настройка прокрутки колесиком мыши"""

        def on_mousewheel_windows(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def on_mousewheel_linux(event):
            if event.num == 4:
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")

        def on_mousewheel_mac(event):
            self.canvas.yview_scroll(int(-1 * event.delta), "units")

        # Привязываем события для разных ОС
        self.canvas.bind("<MouseWheel>", on_mousewheel_windows)
        self.canvas.bind("<Button-4>", on_mousewheel_linux)
        self.canvas.bind("<Button-5>", on_mousewheel_linux)

        # Привязываем к главному окну
        self.root.bind("<MouseWheel>", self.on_root_mousewheel)

    def on_root_mousewheel(self, event):
        """Обработка прокрутки на уровне окна"""
        widget_under_mouse = self.root.winfo_containing(event.x_root, event.y_root)

        if widget_under_mouse and self.is_descendant(widget_under_mouse, self.canvas):
            if event.delta > 0:
                self.canvas.yview_scroll(-1, "units")
            else:
                self.canvas.yview_scroll(1, "units")

    def is_descendant(self, widget, ancestor):
        """Проверка, является ли widget потомком ancestor"""
        while widget is not None:
            if widget == ancestor:
                return True
            widget = widget.master
        return False

    def create_content(self):
        """Создание содержимого окна в правильном порядке"""

        # 1. Верхняя панель с темой
        self.create_top_panel()

        # 2. Настройки подключения
        self.create_connection_settings()

        # 3. Кнопка авторизации
        self.create_auth_button()

        # 4. Статус
        self.create_status()

        # 5. Настройки сохранения
        self.create_output_settings()

        # 6. Настройки листов
        self.sheet1_settings = SheetSettingsFrame(self.main_frame, 1, self.context_menu)
        self.sheet1_settings.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        self.sheet2_settings = SheetSettingsFrame(self.main_frame, 2, self.context_menu)
        self.sheet2_settings.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        # 7. Настройки уведомлений
        self.create_notification_settings()

        # 8. Кнопки управления
        self.create_buttons()

        # 9. Журнал
        self.create_log()

    def create_top_panel(self):
        """Создание верхней панели"""
        top_frame = ttk.Frame(self.main_frame)
        top_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)

        # Заголовок
        title_label = ttk.Label(top_frame, text="Google Sheets Sync",
                                font=("Arial", 14, "bold"))
        title_label.pack(side=tk.LEFT, padx=5)

        # Кнопка темы
        self.theme_button = ttk.Button(top_frame, text="🌙 Темная тема",
                                       command=self.app.toggle_theme)
        self.theme_button.pack(side=tk.RIGHT, padx=5)

    def create_connection_settings(self):
        """Создание настроек подключения"""
        config_frame = ttk.LabelFrame(self.main_frame, text="Настройки подключения", padding="10")
        config_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)

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

    def create_auth_button(self):
        """Создание кнопки авторизации"""
        auth_frame = ttk.Frame(self.main_frame)
        auth_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=10)

        self.auth_btn = ttk.Button(auth_frame, text="1. Авторизоваться",
                                   command=self.app.authenticate_google,
                                   width=20)
        self.auth_btn.pack(side=tk.LEFT, padx=5)

        # Кнопка получения листов (дополнительная)
        ttk.Button(auth_frame, text="Получить листы",
                   command=self.app.get_sheet_list).pack(side=tk.LEFT, padx=5)

    def create_status(self):
        """Создание статуса"""
        status_frame = ttk.Frame(self.main_frame)
        status_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)

        self.status_var = tk.StringVar(value="Статус: Не авторизован")
        status_label = ttk.Label(status_frame, textvariable=self.status_var,
                                 foreground="red", font=("Arial", 10, "bold"))
        status_label.pack(side=tk.LEFT, padx=5)

    def create_output_settings(self):
        """Создание настроек сохранения"""
        output_frame = ttk.LabelFrame(self.main_frame, text="Настройки сохранения", padding="10")
        output_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=5)

        # Папка
        ttk.Label(output_frame, text="Папка:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.folder_path_var = tk.StringVar()
        folder_entry = ttk.Entry(output_frame, textvariable=self.folder_path_var, width=40)
        folder_entry.grid(row=0, column=1, pady=2)
        self.context_menu.add_to_entry(folder_entry)

        ttk.Button(output_frame, text="Обзор", command=self.app.browse_folder).grid(row=0, column=2, padx=5)
        ttk.Button(output_frame, text="По умолчанию",
                   command=self.app.set_default_folder).grid(row=0, column=3, padx=5)

        # Информация о папке по умолчанию
        default_folder = self.app.file_manager.get_default_save_folder()
        ttk.Label(output_frame, text=f"По умолчанию: {default_folder}",
                  foreground="gray").grid(row=1, column=1, sticky=tk.W, pady=2)

    def create_notification_settings(self):
        """Создание настроек уведомлений"""
        notification_frame = ttk.LabelFrame(self.main_frame, text="Настройки уведомлений", padding="10")
        notification_frame.grid(row=8, column=0, sticky=(tk.W, tk.E), pady=5)

        # Создаем сетку для уведомлений
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
        """Создание кнопок управления"""
        button_frame = ttk.Frame(self.main_frame)
        button_frame.grid(row=9, column=0, pady=10)

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

    def create_log(self):
        """Создание журнала"""
        log_frame = ttk.LabelFrame(self.main_frame, text="Журнал", padding="5")
        log_frame.grid(row=10, column=0, sticky=(tk.W, tk.E), pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, width=90)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def scroll_to_top(self):
        """Прокрутка к началу"""
        self.canvas.yview_moveto(0)

    def scroll_to_bottom(self):
        """Прокрутка к концу"""
        self.canvas.yview_moveto(1)