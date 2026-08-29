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

# Для трея
try:
    import pystray
    from PIL import Image, ImageDraw

    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False


class GoogleSheetsSyncApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Google Sheets Sync")
        self.root.geometry("860x1120")

        self.sheets_service = None
        self.is_running = False
        self.monitoring_thread = None
        self.scheduler_thread = None
        self.config_file = 'config.json'
        self.available_sheets = []
        self.sheet_names_cache = {}
        self.auto_filename = tk.BooleanVar(value=True)
        self.tray_icon = None
        self.theme_var = tk.StringVar(value="light")

        # Данные для мониторинга
        self.last_data_hash = {}
        self.last_check_time = {}

        # Инициализируем log_text как None
        self.log_text = None

        # Определяем ОС и настройки
        self.detect_os_settings()

        # Определяем правильный путь к исполняемому файлу
        self.app_dir = self.get_app_directory()

        self.init_ui()
        self.load_config()

        # Применяем тему
        self.apply_theme()

        # Настройка трея
        self.setup_tray()

        # Настройка контекстных меню
        self.setup_context_menus()

    def detect_os_settings(self):
        """Определение операционной системы и настроек"""
        self.os_type = platform.system()
        self.os_release = platform.release()

        if self.os_type == 'Windows':
            self.default_encoding = 'utf-8'  # UTF-8 для Windows
            self.newline_mode = '\r\n'
            self.path_separator = '\\'
            self.is_windows = True
            self.is_macos = False
        elif self.os_type == 'Darwin':
            self.default_encoding = 'utf-8'
            self.newline_mode = '\n'
            self.path_separator = '/'
            self.is_windows = False
            self.is_macos = True
        else:
            self.default_encoding = 'utf-8'
            self.newline_mode = '\n'
            self.path_separator = '/'
            self.is_windows = False
            self.is_macos = False

        print(f"Операционная система: {self.os_type} {self.os_release}")

    def get_app_directory(self):
        """Получение правильной директории приложения"""
        if getattr(sys, 'frozen', False):
            if hasattr(self, 'is_macos') and self.is_macos:
                if '.app' in sys.executable:
                    app_path = os.path.dirname(sys.executable)
                    bundle_path = os.path.dirname(os.path.dirname(app_path))
                    return bundle_path
                else:
                    return os.path.dirname(os.path.abspath(sys.executable))
            else:
                return os.path.dirname(os.path.abspath(sys.executable))
        else:
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

    def setup_context_menus(self):
        """Настройка контекстных меню для журнала"""
        self.log_menu = tk.Menu(self.root, tearoff=0)
        self.log_menu.add_command(label="Копировать", command=self.copy_log_selection)
        self.log_menu.add_command(label="Выделить всё", command=self.select_all_log)
        self.log_menu.add_separator()
        self.log_menu.add_command(label="Очистить журнал", command=self.clear_log)
        self.log_menu.add_command(label="Сохранить журнал в файл", command=self.save_log_to_file)

        if self.log_text:
            self.log_text.bind("<Button-3>", self.show_log_menu)
            self.log_text.bind("<Button-2>", self.show_log_menu)

    def show_log_menu(self, event):
        """Показать контекстное меню журнала"""
        try:
            self.log_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.log_menu.grab_release()

    def copy_log_selection(self):
        """Копировать выделенный текст из журнала"""
        try:
            selected_text = self.log_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
            self.log("Текст скопирован в буфер обмена")
        except tk.TclError:
            messagebox.showinfo("Информация", "Выделите текст для копирования")

    def select_all_log(self):
        """Выделить весь текст в журнале"""
        self.log_text.tag_add(tk.SEL, "1.0", tk.END)
        self.log_text.mark_set(tk.INSERT, "1.0")
        self.log_text.see(tk.INSERT)
        return 'break'

    def clear_log(self):
        """Очистить журнал"""
        if messagebox.askyesno("Подтверждение", "Очистить журнал?"):
            self.log_text.delete("1.0", tk.END)
            self.log("Журнал очищен")

    def save_log_to_file(self):
        """Сохранить журнал в файл"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"log_{timestamp}.txt"

            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("Log files", "*.log"), ("All files", "*.*")],
                initialfile=default_filename,
                title="Сохранить журнал"
            )

            if file_path:
                log_content = self.log_text.get("1.0", tk.END)

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)

                self.log(f"Журнал сохранен в: {file_path}")
                if self.notify_success_var.get():
                    messagebox.showinfo("Успех", f"Журнал сохранен в:\n{file_path}")

        except Exception as e:
            self.log(f"Ошибка сохранения журнала: {str(e)}")
            if self.notify_error_var.get():
                messagebox.showerror("Ошибка", f"Ошибка сохранения журнала: {str(e)}")

    def apply_theme(self):
        """Применение темы оформления"""
        if self.theme_var.get() == "dark":
            bg_color = '#2b2b2b'
            fg_color = '#ffffff'
            select_color = '#404040'
            entry_bg = '#3c3c3c'
            entry_fg = '#ffffff'
            button_bg = '#404040'
            button_fg = '#ffffff'
            label_bg = '#2b2b2b'
            label_fg = '#ffffff'
        else:
            bg_color = '#f0f0f0'
            fg_color = '#000000'
            select_color = '#0078d7'
            entry_bg = '#ffffff'
            entry_fg = '#000000'
            button_bg = '#e1e1e1'
            button_fg = '#000000'
            label_bg = '#f0f0f0'
            label_fg = '#000000'

        style = ttk.Style()
        style.theme_use('clam')

        style.configure('TFrame', background=bg_color)
        style.configure('TLabel', background=label_bg, foreground=label_fg)
        style.configure('TLabelframe', background=bg_color, foreground=fg_color)
        style.configure('TLabelframe.Label', background=bg_color, foreground=fg_color)
        style.configure('TButton', background=button_bg, foreground=button_fg)
        style.map('TButton',
                  background=[('active', select_color), ('pressed', select_color)],
                  foreground=[('active', '#ffffff'), ('pressed', '#ffffff')])
        style.configure('TCheckbutton', background=bg_color, foreground=fg_color)
        style.map('TCheckbutton',
                  background=[('active', bg_color)],
                  foreground=[('active', fg_color)])
        style.configure('TRadiobutton', background=bg_color, foreground=fg_color)
        style.map('TRadiobutton',
                  background=[('active', bg_color)],
                  foreground=[('active', fg_color)])
        style.configure('TEntry', fieldbackground=entry_bg, foreground=entry_fg)
        style.configure('TCombobox', fieldbackground=entry_bg, foreground=entry_fg)
        style.configure('TSpinbox', fieldbackground=entry_bg, foreground=entry_fg)

        self.root.configure(bg=bg_color)

        if self.log_text:
            if self.theme_var.get() == "dark":
                self.log_text.configure(bg='#1e1e1e', fg='#ffffff', insertbackground='#ffffff')
            else:
                self.log_text.configure(bg='#ffffff', fg='#000000', insertbackground='#000000')

        self.current_theme = {
            'bg': bg_color,
            'fg': fg_color,
            'select': select_color
        }

    def toggle_theme(self):
        """Переключение темы"""
        if self.theme_var.get() == "light":
            self.theme_var.set("dark")
        else:
            self.theme_var.set("light")
        self.apply_theme()
        self.log(f"Применена {'темная' if self.theme_var.get() == 'dark' else 'светлая'} тема")
        self.theme_button.config(text="☀️ Светлая тема" if self.theme_var.get() == "dark" else "🌙 Темная тема")

    def create_tray_image(self, is_running=False):
        """Создание изображения для трея"""
        if self.theme_var.get() == "dark":
            bg_color = '#2b2b2b' if not is_running else '#004d00'
        else:
            bg_color = '#f0f0f0' if not is_running else '#00cc00'

        image = Image.new('RGB', (64, 64), color=bg_color)
        draw = ImageDraw.Draw(image)

        if is_running:
            draw.ellipse([20, 20, 44, 44], fill='#00ff00')
            draw.ellipse([28, 28, 36, 36], fill='#00cc00')
        else:
            draw.ellipse([20, 20, 44, 44], fill='#808080')
            draw.ellipse([28, 28, 36, 36], fill='#666666')

        return image

    def setup_tray(self):
        """Настройка иконки в трее"""
        if not TRAY_AVAILABLE:
            self.log("Библиотеки для трея не установлены. Установите: pip install pystray pillow")
            return

        try:
            menu = pystray.Menu(
                pystray.MenuItem("Показать", self.show_window, default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "Автосохранение",
                    pystray.Menu(
                        pystray.MenuItem(
                            "Включить",
                            self.enable_autosave_from_tray,
                            checked=lambda item: self.is_running
                        ),
                        pystray.MenuItem(
                            "Выключить",
                            self.disable_autosave_from_tray,
                            checked=lambda item: not self.is_running
                        )
                    )
                ),
                pystray.MenuItem("Сохранить сейчас", self.save_now_from_tray),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Выход", self.quit_app)
            )

            image = self.create_tray_image(self.is_running)
            self.tray_icon = pystray.Icon("google_sheets_sync", image, "Google Sheets Sync", menu)

            self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            self.tray_thread.start()

            self.log("Иконка в трее создана")
        except Exception as e:
            self.log(f"Ошибка создания иконки в трее: {str(e)}")

    def update_tray_icon(self):
        """Обновление иконки в трее"""
        if self.tray_icon:
            self.tray_icon.icon = self.create_tray_image(self.is_running)

    def show_window(self):
        """Показать окно"""
        self.root.after(0, self._show_window)

    def _show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide_window(self):
        """Скрыть окно в трей"""
        self.root.withdraw()
        if self.tray_icon:
            self.tray_icon.notify("Приложение свернуто в трей", "Google Sheets Sync продолжает работать")

    def quit_app(self):
        """Полное закрытие приложения"""
        self.root.after(0, self.on_closing)

    def enable_autosave_from_tray(self):
        """Включение автосохранения из трея"""
        if not self.is_running:
            self.root.after(0, self.start_autosave)

    def disable_autosave_from_tray(self):
        """Выключение автосохранения из трея"""
        if self.is_running:
            self.root.after(0, self.stop_autosave)

    def save_now_from_tray(self):
        """Сохранение из трея"""
        self.root.after(0, self.save_now)

    def start_autosave(self):
        """Запуск автосохранения"""
        if not self.sheets_service:
            if self.notify_error_var.get():
                messagebox.showwarning("Предупреждение", "Сначала авторизуйтесь")
            return

        self.is_running = True
        self.start_btn.config(text="Остановить авто-сохранение")
        self.start_monitoring()
        self.update_tray_icon()

        self.log("Авто-сохранение запущено")

        if self.tray_icon:
            self.tray_icon.notify("Автосохранение включено", "Google Sheets Sync начал мониторинг изменений")

    def stop_autosave(self):
        """Остановка автосохранения"""
        self.is_running = False
        self.start_btn.config(text="Запустить авто-сохранение")
        self.stop_monitoring()
        self.update_tray_icon()

        self.log("Авто-сохранение остановлено")

        if self.tray_icon:
            self.tray_icon.notify("Автосохранение выключено", "Мониторинг изменений остановлен")

    def toggle_auto_save(self):
        """Переключение автосохранения"""
        if not self.is_running:
            self.start_autosave()
        else:
            self.stop_autosave()

    def add_context_menu_to_entry(self, entry_widget):
        """Добавление контекстного меню к полю ввода"""
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Вырезать", command=lambda: entry_widget.event_generate('<<Cut>>'))
        menu.add_command(label="Копировать", command=lambda: entry_widget.event_generate('<<Copy>>'))
        menu.add_command(label="Вставить", command=lambda: entry_widget.event_generate('<<Paste>>'))
        menu.add_separator()
        menu.add_command(label="Выделить всё", command=lambda: entry_widget.select_range(0, tk.END))

        def show_menu(event):
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        entry_widget.bind("<Button-3>", show_menu)
        entry_widget.bind("<Button-2>", show_menu)

    def init_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Верхняя панель
        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)

        os_info = f"ОС: {self.os_type} | Кодировка: {self.default_encoding}"
        ttk.Label(top_frame, text=os_info, foreground="blue").pack(side=tk.LEFT, padx=5)

        self.theme_button = ttk.Button(top_frame,
                                       text="🌙 Темная тема" if self.theme_var.get() == "light" else "☀️ Светлая тема",
                                       command=self.toggle_theme)
        self.theme_button.pack(side=tk.RIGHT, padx=5)

        # Configuration section
        config_frame = ttk.LabelFrame(main_frame, text="Настройки подключения", padding="10")
        config_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)

        # Spreadsheet ID
        ttk.Label(config_frame, text="Spreadsheet ID:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.spreadsheet_id_var = tk.StringVar()
        spreadsheet_entry = ttk.Entry(config_frame, textvariable=self.spreadsheet_id_var, width=50)
        spreadsheet_entry.grid(row=0, column=1, pady=2)
        ttk.Button(config_frame, text="Получить листы", command=self.get_sheet_list).grid(row=0, column=2, padx=5)
        self.add_context_menu_to_entry(spreadsheet_entry)

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
        self.add_context_menu_to_entry(self.encoding_combo)

        # Line endings selection
        ttk.Label(config_frame, text="Переносы строк:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.newline_var = tk.StringVar(value='windows' if self.is_windows else 'unix')
        newline_frame = ttk.Frame(config_frame)
        newline_frame.grid(row=4, column=1, sticky=tk.W, pady=2)

        ttk.Radiobutton(newline_frame, text="Windows (CRLF)", variable=self.newline_var,
                        value="windows").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(newline_frame, text="Unix (LF)", variable=self.newline_var,
                        value="unix").pack(side=tk.LEFT, padx=5)

        # Sheet 1 settings
        sheet1_frame = ttk.LabelFrame(config_frame, text="Лист 1", padding="5")
        sheet1_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(sheet1_frame, text="Лист:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.sheet1_selection_frame = ttk.Frame(sheet1_frame)
        self.sheet1_selection_frame.grid(row=0, column=1, sticky=tk.W, pady=2)

        self.sheet1_name_var = tk.StringVar()
        self.sheet1_name_combo = ttk.Combobox(self.sheet1_selection_frame, textvariable=self.sheet1_name_var, width=30)
        self.sheet1_name_combo.bind('<<ComboboxSelected>>', self.on_sheet1_selected)
        self.add_context_menu_to_entry(self.sheet1_name_combo)

        self.sheet1_index_var = tk.IntVar(value=0)
        self.sheet1_index_spinbox = ttk.Spinbox(self.sheet1_selection_frame, from_=0, to=100,
                                                textvariable=self.sheet1_index_var, width=10)
        self.sheet1_index_spinbox.bind('<KeyRelease>', self.on_sheet1_index_changed)
        self.sheet1_index_spinbox.bind('<ButtonRelease>', self.on_sheet1_index_changed)
        self.add_context_menu_to_entry(self.sheet1_index_spinbox)

        self.sheet1_index_label = ttk.Label(self.sheet1_selection_frame, text="", foreground="blue")

        ttk.Label(sheet1_frame, text="Файл:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.sheet1_filename_var = tk.StringVar(value="sheet1.tsv")
        self.sheet1_filename_entry = ttk.Entry(sheet1_frame, textvariable=self.sheet1_filename_var, width=40)
        self.sheet1_filename_entry.grid(row=1, column=1, sticky=tk.W, pady=2)
        self.add_context_menu_to_entry(self.sheet1_filename_entry)

        ttk.Label(sheet1_frame, text="Проверять каждые (сек):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.sheet1_check_interval_var = tk.IntVar(value=30)
        sheet1_interval_spinbox = ttk.Spinbox(sheet1_frame, from_=5, to=3600,
                                              textvariable=self.sheet1_check_interval_var,
                                              width=10)
        sheet1_interval_spinbox.grid(row=2, column=1, sticky=tk.W, pady=2)
        self.add_context_menu_to_entry(sheet1_interval_spinbox)

        self.sheet1_save_enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(sheet1_frame, text="Сохранять этот лист",
                        variable=self.sheet1_save_enabled_var).grid(row=3, column=1, sticky=tk.W, pady=2)

        # Sheet 2 settings
        sheet2_frame = ttk.LabelFrame(config_frame, text="Лист 2", padding="5")
        sheet2_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(sheet2_frame, text="Лист:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.sheet2_selection_frame = ttk.Frame(sheet2_frame)
        self.sheet2_selection_frame.grid(row=0, column=1, sticky=tk.W, pady=2)

        self.sheet2_name_var = tk.StringVar()
        self.sheet2_name_combo = ttk.Combobox(self.sheet2_selection_frame, textvariable=self.sheet2_name_var, width=30)
        self.sheet2_name_combo.bind('<<ComboboxSelected>>', self.on_sheet2_selected)
        self.add_context_menu_to_entry(self.sheet2_name_combo)

        self.sheet2_index_var = tk.IntVar(value=1)
        self.sheet2_index_spinbox = ttk.Spinbox(self.sheet2_selection_frame, from_=0, to=100,
                                                textvariable=self.sheet2_index_var, width=10)
        self.sheet2_index_spinbox.bind('<KeyRelease>', self.on_sheet2_index_changed)
        self.sheet2_index_spinbox.bind('<ButtonRelease>', self.on_sheet2_index_changed)
        self.add_context_menu_to_entry(self.sheet2_index_spinbox)

        self.sheet2_index_label = ttk.Label(self.sheet2_selection_frame, text="", foreground="blue")

        ttk.Label(sheet2_frame, text="Файл:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.sheet2_filename_var = tk.StringVar(value="sheet2.tsv")
        self.sheet2_filename_entry = ttk.Entry(sheet2_frame, textvariable=self.sheet2_filename_var, width=40)
        self.sheet2_filename_entry.grid(row=1, column=1, sticky=tk.W, pady=2)
        self.add_context_menu_to_entry(self.sheet2_filename_entry)

        ttk.Label(sheet2_frame, text="Проверять каждые (сек):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.sheet2_check_interval_var = tk.IntVar(value=300)
        sheet2_interval_spinbox = ttk.Spinbox(sheet2_frame, from_=5, to=3600,
                                              textvariable=self.sheet2_check_interval_var,
                                              width=10)
        sheet2_interval_spinbox.grid(row=2, column=1, sticky=tk.W, pady=2)
        self.add_context_menu_to_entry(sheet2_interval_spinbox)

        self.sheet2_save_enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(sheet2_frame, text="Сохранять этот лист",
                        variable=self.sheet2_save_enabled_var).grid(row=3, column=1, sticky=tk.W, pady=2)

        # Output settings
        output_frame = ttk.LabelFrame(main_frame, text="Настройки сохранения", padding="10")
        output_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(output_frame, text="Папка:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.folder_path_var = tk.StringVar()
        folder_entry = ttk.Entry(output_frame, textvariable=self.folder_path_var, width=40)
        folder_entry.grid(row=0, column=1, pady=2)
        self.add_context_menu_to_entry(folder_entry)

        ttk.Button(output_frame, text="Обзор", command=self.browse_folder).grid(row=0, column=2, padx=5)
        ttk.Button(output_frame, text="По умолчанию", command=self.set_default_folder).grid(row=0, column=3, padx=5)

        default_folder = self.get_default_save_folder()
        ttk.Label(output_frame, text=f"По умолчанию: {default_folder}",
                  foreground="gray").grid(row=1, column=1, sticky=tk.W, pady=2)

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

        ttk.Button(button_frame, text="Свернуть в трей", command=self.hide_window).pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="Сохранить журнал", command=self.save_log_to_file).pack(side=tk.LEFT, padx=5)

        # Status
        self.status_var = tk.StringVar(value="Статус: Не авторизован")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, foreground="red", font=("Arial", 10, "bold"))
        status_label.grid(row=5, column=0, pady=5)

        # Log
        ttk.Label(main_frame, text="Журнал:").grid(row=6, column=0, sticky=tk.W)
        self.log_text = scrolledtext.ScrolledText(main_frame, height=12, width=90)
        self.log_text.grid(row=7, column=0, pady=5)

        # Выводим информацию
        self.log(f"Операционная система: {self.os_type} {self.os_release}")
        self.log(f"Кодировка по умолчанию: {self.default_encoding}")
        self.log(f"Папка приложения: {self.app_dir}")
        self.log("Используйте правую кнопку мыши для копирования из журнала")
        self.log("Стандартные сочетания клавиш (Ctrl+C, Ctrl+V) работают в полях ввода")

        # Initialize UI state
        self.toggle_selection_method()
        self.toggle_auto_filename()

    def get_newline_chars(self):
        """Получение символов переноса строки"""
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

        for widget in self.sheet1_selection_frame.winfo_children():
            widget.pack_forget()
        for widget in self.sheet2_selection_frame.winfo_children():
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
        """Обновление меток с именами листов"""
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

    def validate_spreadsheet_id(self, spreadsheet_id):
        """Проверка и нормализация ID таблицы"""
        spreadsheet_id = spreadsheet_id.strip()

        if 'docs.google.com' in spreadsheet_id:
            import re
            match = re.search(r'/d/([a-zA-Z0-9-_]+)', spreadsheet_id)
            if match:
                spreadsheet_id = match.group(1)
                self.log(f"Извлечен ID из URL: {spreadsheet_id}")
                self.spreadsheet_id_var.set(spreadsheet_id)
            else:
                self.log("Не удалось извлечь ID из URL")
                return None

        if not spreadsheet_id or len(spreadsheet_id) < 10:
            self.log(f"Некорректный ID таблицы: {spreadsheet_id}")
            return None

        return spreadsheet_id

    def get_sheet_list(self):
        """Получение списка листов из Google Sheets"""
        if not self.sheets_service:
            messagebox.showwarning("Предупреждение", "Сначала авторизуйтесь")
            return

        spreadsheet_id = self.validate_spreadsheet_id(self.spreadsheet_id_var.get())

        if not spreadsheet_id:
            if self.notify_error_var.get():
                messagebox.showerror("Ошибка", "Некорректный ID таблицы")
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
            error_message = str(e)

            if "404" in error_message:
                self.log("Таблица не найдена. Проверьте ID таблицы.")
                if self.notify_error_var.get():
                    messagebox.showerror("Ошибка",
                                         "Таблица не найдена.\n\n"
                                         "Проверьте:\n"
                                         "1. Правильность ID таблицы\n"
                                         "2. Доступ к таблице для вашего аккаунта\n"
                                         "3. Что таблица не удалена")
            elif "403" in error_message:
                self.log("Нет доступа к таблице.")
                if self.notify_error_var.get():
                    messagebox.showerror("Ошибка",
                                         "Нет доступа к таблице.\n\n"
                                         "Убедитесь, что:\n"
                                         "1. Таблица доступна для вашего аккаунта\n"
                                         "2. Вы вошли в правильный Google аккаунт")
            else:
                self.log(f"Ошибка получения списка листов: {error_message}")
                if self.notify_error_var.get():
                    messagebox.showerror("Ошибка", f"Ошибка получения списка листов: {error_message}")

    def log(self, message):
        """Логирование с проверкой наличия log_text"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"

        print(log_message)

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

                theme = config.get('theme', 'light')
                self.theme_var.set(theme)

                sheets = config.get('sheets', [])

                if selection_method == "by_name":
                    if len(sheets) > 0:
                        self.sheet1_name_var.set(sheets[0].get('name', ''))
                        self.sheet1_filename_var.set(sheets[0].get('output_filename', 'sheet1.tsv'))
                        self.sheet1_check_interval_var.set(sheets[0].get('check_interval', 30))
                        self.sheet1_save_enabled_var.set(sheets[0].get('save_enabled', True))
                    if len(sheets) > 1:
                        self.sheet2_name_var.set(sheets[1].get('name', ''))
                        self.sheet2_filename_var.set(sheets[1].get('output_filename', 'sheet2.tsv'))
                        self.sheet2_check_interval_var.set(sheets[1].get('check_interval', 300))
                        self.sheet2_save_enabled_var.set(sheets[1].get('save_enabled', True))
                else:
                    if len(sheets) > 0:
                        self.sheet1_index_var.set(sheets[0].get('index', 0))
                        self.sheet1_filename_var.set(sheets[0].get('output_filename', 'sheet1.tsv'))
                        self.sheet1_check_interval_var.set(sheets[0].get('check_interval', 30))
                        self.sheet1_save_enabled_var.set(sheets[0].get('save_enabled', True))
                    if len(sheets) > 1:
                        self.sheet2_index_var.set(sheets[1].get('index', 1))
                        self.sheet2_filename_var.set(sheets[1].get('output_filename', 'sheet2.tsv'))
                        self.sheet2_check_interval_var.set(sheets[1].get('check_interval', 300))
                        self.sheet2_save_enabled_var.set(sheets[1].get('save_enabled', True))

                folder_path = config.get('output_folder', '')
                if not folder_path:
                    folder_path = self.get_default_save_folder()
                self.folder_path_var.set(folder_path)

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
                        'output_filename': self.sheet1_filename_var.get(),
                        'check_interval': self.sheet1_check_interval_var.get(),
                        'save_enabled': self.sheet1_save_enabled_var.get()
                    },
                    {
                        'name': self.sheet2_name_var.get(),
                        'output_filename': self.sheet2_filename_var.get(),
                        'check_interval': self.sheet2_check_interval_var.get(),
                        'save_enabled': self.sheet2_save_enabled_var.get()
                    }
                ]
            else:
                sheets = [
                    {
                        'index': self.sheet1_index_var.get(),
                        'output_filename': self.sheet1_filename_var.get(),
                        'check_interval': self.sheet1_check_interval_var.get(),
                        'save_enabled': self.sheet1_save_enabled_var.get()
                    },
                    {
                        'index': self.sheet2_index_var.get(),
                        'output_filename': self.sheet2_filename_var.get(),
                        'check_interval': self.sheet2_check_interval_var.get(),
                        'save_enabled': self.sheet2_save_enabled_var.get()
                    }
                ]

            config = {
                'spreadsheet_id': self.spreadsheet_id_var.get(),
                'selection_method': selection_method,
                'auto_filename': self.auto_filename.get(),
                'encoding': self.encoding_var.get(),
                'newline_mode': self.newline_var.get(),
                'theme': self.theme_var.get(),
                'sheets': sheets,
                'output_folder': self.folder_path_var.get(),
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

            if index in self.sheet_names_cache:
                return self.sheet_names_cache[index]
            elif index < len(self.available_sheets):
                return self.available_sheets[index]
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

            if self.sheet1_save_enabled_var.get():
                sheet1_identifier = self.get_sheet_identifier(1)
                filename1 = self.sheet1_filename_var.get().strip()
                if sheet1_identifier and filename1:
                    self.save_sheet_to_tsv(spreadsheet_id, sheet1_identifier, output_folder, filename1)

            if self.sheet2_save_enabled_var.get():
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
        """Сохранение листа в TSV"""
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

            self.log(f"Сохранено: {filename} (лист: {sheet_identifier})")

        except Exception as e:
            raise Exception(f"Ошибка сохранения листа '{sheet_identifier}': {str(e)}")

    def start_monitoring(self):
        """Запуск мониторинга изменений"""
        self.monitoring_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitoring_thread.start()

        self.last_check_time = {
            1: time.time(),
            2: time.time()
        }

    def monitor_loop(self):
        """Цикл мониторинга изменений"""
        while self.is_running:
            try:
                spreadsheet_id = self.spreadsheet_id_var.get().strip()

                if spreadsheet_id:
                    current_time = time.time()

                    if (self.sheet1_save_enabled_var.get() and
                            current_time - self.last_check_time.get(1, 0) >= self.sheet1_check_interval_var.get()):
                        self.check_and_save_sheet(1)
                        self.last_check_time[1] = current_time

                    if (self.sheet2_save_enabled_var.get() and
                            current_time - self.last_check_time.get(2, 0) >= self.sheet2_check_interval_var.get()):
                        self.check_and_save_sheet(2)
                        self.last_check_time[2] = current_time

                time.sleep(5)

            except Exception as e:
                self.log(f"Ошибка в цикле мониторинга: {str(e)}")
                time.sleep(10)

    def check_and_save_sheet(self, sheet_number):
        """Проверка и сохранение конкретного листа"""
        try:
            spreadsheet_id = self.spreadsheet_id_var.get().strip()

            if not spreadsheet_id:
                return

            self.refresh_sheet_names()

            sheet_identifier = self.get_sheet_identifier(sheet_number)

            if not sheet_identifier:
                return

            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=sheet_identifier
            ).execute()

            current_hash = hash(str(result))

            if sheet_number not in self.last_data_hash or self.last_data_hash[sheet_number] != current_hash:
                self.log(f"Обнаружены изменения в листе {sheet_number}")

                if self.notify_changes_var.get():
                    self.root.after(0, lambda: messagebox.showinfo("Изменения",
                                                                   "Обнаружены изменения в таблице. Обнови в PhotoMechanic, Reload All. Выполняется сохранение файлов..."))

                if sheet_number == 1:
                    filename = self.sheet1_filename_var.get().strip()
                else:
                    filename = self.sheet2_filename_var.get().strip()

                if filename:
                    output_folder = self.get_output_folder()
                    self.save_sheet_to_tsv(spreadsheet_id, sheet_identifier, output_folder, filename)

                self.last_data_hash[sheet_number] = current_hash

        except Exception as e:
            self.log(f"Ошибка проверки листа {sheet_number}: {str(e)}")

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
        self.stop_monitoring()

        if self.tray_icon:
            self.tray_icon.stop()

        self.root.destroy()


def main():
    app = GoogleSheetsSyncApp()
    app.run()


if __name__ == '__main__':
    main()