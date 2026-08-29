import tkinter as tk
from tkinter import ttk


class SheetSettingsFrame:
    def __init__(self, parent, sheet_number, context_menu_manager):
        self.parent = parent
        self.sheet_number = sheet_number
        self.context_menu = context_menu_manager

        self.frame = ttk.LabelFrame(parent, text=f"Лист {sheet_number}", padding="5")

        # Переменные
        self.name_var = tk.StringVar()
        self.index_var = tk.IntVar(value=sheet_number - 1)
        self.filename_var = tk.StringVar(value=f"sheet{sheet_number}.tsv")
        self.check_interval_var = tk.IntVar(value=30 if sheet_number == 1 else 300)
        self.save_enabled_var = tk.BooleanVar(value=True)

        self.create_widgets()

    def create_widgets(self):
        """Создание виджетов"""
        # Выбор листа
        ttk.Label(self.frame, text="Лист:").grid(row=0, column=0, sticky=tk.W, pady=2)
        selection_frame = ttk.Frame(self.frame)
        selection_frame.grid(row=0, column=1, sticky=tk.W, pady=2)

        # Комбобокс для выбора по имени
        self.name_combo = ttk.Combobox(selection_frame, textvariable=self.name_var, width=30)
        self.context_menu.add_to_entry(self.name_combo)

        # Спинбокс для выбора по индексу
        self.index_spinbox = ttk.Spinbox(selection_frame, from_=0, to=100,
                                         textvariable=self.index_var, width=10)
        self.context_menu.add_to_entry(self.index_spinbox)

        # Метка с именем листа
        self.index_label = ttk.Label(selection_frame, text="", foreground="blue")

        # Файл
        ttk.Label(self.frame, text="Файл:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.filename_entry = ttk.Entry(self.frame, textvariable=self.filename_var, width=40)
        self.filename_entry.grid(row=1, column=1, sticky=tk.W, pady=2)
        self.context_menu.add_to_entry(self.filename_entry)

        # Интервал проверки
        ttk.Label(self.frame, text="Проверять каждые (сек):").grid(row=2, column=0, sticky=tk.W, pady=2)
        interval_spinbox = ttk.Spinbox(self.frame, from_=5, to=3600,
                                       textvariable=self.check_interval_var, width=10)
        interval_spinbox.grid(row=2, column=1, sticky=tk.W, pady=2)
        self.context_menu.add_to_entry(interval_spinbox)

        # Включение сохранения
        ttk.Checkbutton(self.frame, text="Сохранять этот лист",
                        variable=self.save_enabled_var).grid(row=3, column=1, sticky=tk.W, pady=2)

    def grid(self, **kwargs):
        """Размещение фрейма"""
        self.frame.grid(**kwargs)

    def show_name_selection(self):
        """Показать выбор по имени"""
        self.name_combo.pack(side=tk.LEFT)
        self.index_spinbox.pack_forget()
        self.index_label.pack_forget()

    def show_index_selection(self):
        """Показать выбор по индексу"""
        self.name_combo.pack_forget()
        self.index_spinbox.pack(side=tk.LEFT)
        self.index_label.pack(side=tk.LEFT, padx=(10, 0))

    def update_index_label(self, sheet_name=None):
        """Обновление метки с именем листа"""
        if sheet_name:
            self.index_label.config(text=f"→ {sheet_name}")
        else:
            self.index_label.config(text="→ Индекс вне диапазона")