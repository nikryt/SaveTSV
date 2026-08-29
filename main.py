#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
import time
import threading
import platform
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# Импорт модулей
from config import ConfigManager
from logger import Logger
from theme_manager import ThemeManager
from tray_manager import TrayManager
from google_sheets import GoogleSheetsManager
from file_manager import FileManager
from ui_components import UIContextMenu


class GoogleSheetsSyncApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Google Sheets Sync")
        self.root.geometry("760x1120")

        # Инициализация менеджеров
        self.file_manager = FileManager()
        self.app_dir = self.file_manager.get_app_directory()
        self.logger = Logger()
        self.config_manager = ConfigManager(self.app_dir)
        self.theme_manager = ThemeManager(self.root)
        self.tray_manager = TrayManager(self)
        self.sheets_manager = None

        # Переменные состояния
        self.is_running = False
        self.monitoring_thread = None
        self.available_sheets = []
        self.sheet_names_cache = {}
        self.auto_filename = tk.BooleanVar(value=True)

        # Данные для мониторинга
        self.last_data_hash = {}
        self.last_check_time = {}

        # Инициализация UI
        self.init_ui()

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

    def detect_os(self):
        """Определение операционной системы"""
        self.os_type = platform.system()
        self.is_windows = self.os_type == 'Windows'
        self.is_macos = self.os_type == 'Darwin'
        self.default_encoding = 'utf-8'
        self.logger.log(f"Операционная система: {self.os_type}")

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Верхняя панель
        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)

        self.theme_button = ttk.Button(top_frame, text="🌙 Темная тема",
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
        UIContextMenu.add_to_entry(spreadsheet_entry, self.root)

        # Метод выбора
        ttk.Label(config_frame, text="Метод выбора:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.selection_method = tk.StringVar(value="by_name")
        method_frame = ttk.Frame(config_frame)
        method_frame.grid(row=1, column=1, sticky=tk.W, pady=2)

        ttk.Radiobutton(method_frame, text="По имени", variable=self.selection_method,
                        value="by_name", command=self.toggle_selection_method).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(method_frame, text="По индексу", variable=self.selection_method,
                        value="by_index", command=self.toggle_selection_method).pack(side=tk.LEFT, padx=5)

        # Автоопределение имени файла
        self.auto_filename_check = ttk.Checkbutton(config_frame,
                                                   text="Автоматически использовать имя листа как имя файла",
                                                   variable=self.auto_filename,
                                                   command=self.toggle_auto_filename)
        self.auto_filename_check.grid(row=2, column=1, sticky=tk.W, pady=5)

        # Кодировка
        ttk.Label(config_frame, text="Кодировка:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.encoding_var = tk.StringVar(value='utf-8')
        encoding_combo = ttk.Combobox(config_frame, textvariable=self.encoding_var,
                                      values=['utf-8', 'utf-8-sig', 'cp1251', 'cp866', 'koi8-r'],
                                      width=20)
        encoding_combo.grid(row=3, column=1, sticky=tk.W, pady=2)
        UIContextMenu.add_to_entry(encoding_combo, self.root)

        # Переносы строк
        ttk.Label(config_frame, text="Переносы строк:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.newline_var = tk.StringVar(value='unix')
        newline_frame = ttk.Frame(config_frame)
        newline_frame.grid(row=4, column=1, sticky=tk.W, pady=2)

        ttk.Radiobutton(newline_frame, text="Windows (CRLF)", variable=self.newline_var,
                        value="windows").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(newline_frame, text="Unix (LF)", variable=self.newline_var,
                        value="unix").pack(side=tk.LEFT, padx=5)

        # Лист 1
        self.create_sheet_settings(config_frame, 1, 5)

        # Лист 2
        self.create_sheet_settings(config_frame, 2, 6)

        # Настройки сохранения
        output_frame = ttk.LabelFrame(main_frame, text="Настройки сохранения", padding="10")
        output_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(output_frame, text="Папка:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.folder_path_var = tk.StringVar()
        folder_entry = ttk.Entry(output_frame, textvariable=self.folder_path_var, width=40)
        folder_entry.grid(row=0, column=1, pady=2)
        UIContextMenu.add_to_entry(folder_entry, self.root)

        ttk.Button(output_frame, text="Обзор", command=self.browse_folder).grid(row=0, column=2, padx=5)
        ttk.Button(output_frame, text="По умолчанию", command=self.set_default_folder).grid(row=0, column=3, padx=5)

        # Уведомления
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

        # Кнопки
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, pady=10)

        self.auth_btn = ttk.Button(button_frame, text="1. Авторизация", command=self.authenticate_google)
        self.auth_btn.pack(side=tk.LEFT, padx=5)

        self.save_btn = ttk.Button(button_frame, text="2. Сохранить сейчас", command=self.save_now, state=tk.DISABLED)
        self.save_btn.pack(side=tk.LEFT, padx=5)

        self.start_btn = ttk.Button(button_frame, text="3. Запустить авто-сохранение",
                                    command=self.toggle_auto_save, state=tk.DISABLED)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="Сохранить конфигурацию", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Свернуть в трей", command=self.hide_window).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Сохранить журнал", command=self.save_log).pack(side=tk.LEFT, padx=5)

        # Статус
        self.status_var = tk.StringVar(value="Статус: Не авторизован")
        ttk.Label(main_frame, textvariable=self.status_var,
                  foreground="red", font=("Arial", 10, "bold")).grid(row=5, column=0, pady=5)

        # Журнал
        ttk.Label(main_frame, text="Журнал:").grid(row=6, column=0, sticky=tk.W)
        self.log_text = scrolledtext.ScrolledText(main_frame, height=12, width=90)
        self.log_text.grid(row=7, column=0, pady=5)

        # Подключаем логгер к виджету
        self.logger.set_log_widget(self.log_text)

        # Инициализация UI
        self.toggle_selection_method()
        self.toggle_auto_filename()

    def create_sheet_settings(self, parent, sheet_number, row):
        """Создание настроек для листа"""
        frame = ttk.LabelFrame(parent, text=f"Лист {sheet_number}", padding="5")
        frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        # Выбор листа
        ttk.Label(frame, text="Лист:").grid(row=0, column=0, sticky=tk.W, pady=2)
        selection_frame = ttk.Frame(frame)
        selection_frame.grid(row=0, column=1, sticky=tk.W, pady=2)

        if sheet_number == 1:
            self.sheet1_name_var = tk.StringVar()
            self.sheet1_name_combo = ttk.Combobox(selection_frame, textvariable=self.sheet1_name_var, width=30)
            self.sheet1_name_combo.bind('<<ComboboxSelected>>', self.on_sheet1_selected)
            UIContextMenu.add_to_entry(self.sheet1_name_combo, self.root)

            self.sheet1_index_var = tk.IntVar(value=0)
            self.sheet1_index_spinbox = ttk.Spinbox(selection_frame, from_=0, to=100,
                                                    textvariable=self.sheet1_index_var, width=10)
            self.sheet1_index_spinbox.bind('<KeyRelease>', self.on_sheet1_index_changed)
            self.sheet1_index_spinbox.bind('<ButtonRelease>', self.on_sheet1_index_changed)
            UIContextMenu.add_to_entry(self.sheet1_index_spinbox, self.root)

            self.sheet1_index_label = ttk.Label(selection_frame, text="", foreground="blue")

            # Файл
            ttk.Label(frame, text="Файл:").grid(row=1, column=0, sticky=tk.W, pady=2)
            self.sheet1_filename_var = tk.StringVar(value="sheet1.tsv")
            self.sheet1_filename_entry = ttk.Entry(frame, textvariable=self.sheet1_filename_var, width=40)
            self.sheet1_filename_entry.grid(row=1, column=1, sticky=tk.W, pady=2)
            UIContextMenu.add_to_entry(self.sheet1_filename_entry, self.root)

            # Интервал
            ttk.Label(frame, text="Проверять каждые (сек):").grid(row=2, column=0, sticky=tk.W, pady=2)
            self.sheet1_check_interval_var = tk.IntVar(value=30)
            sheet1_interval = ttk.Spinbox(frame, from_=5, to=3600,
                                          textvariable=self.sheet1_check_interval_var, width=10)
            sheet1_interval.grid(row=2, column=1, sticky=tk.W, pady=2)
            UIContextMenu.add_to_entry(sheet1_interval, self.root)

            self.sheet1_save_enabled_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(frame, text="Сохранять этот лист",
                            variable=self.sheet1_save_enabled_var).grid(row=3, column=1, sticky=tk.W, pady=2)
        else:
            self.sheet2_name_var = tk.StringVar()
            self.sheet2_name_combo = ttk.Combobox(selection_frame, textvariable=self.sheet2_name_var, width=30)
            self.sheet2_name_combo.bind('<<ComboboxSelected>>', self.on_sheet2_selected)
            UIContextMenu.add_to_entry(self.sheet2_name_combo, self.root)

            self.sheet2_index_var = tk.IntVar(value=1)
            self.sheet2_index_spinbox = ttk.Spinbox(selection_frame, from_=0, to=100,
                                                    textvariable=self.sheet2_index_var, width=10)
            self.sheet2_index_spinbox.bind('<KeyRelease>', self.on_sheet2_index_changed)
            self.sheet2_index_spinbox.bind('<ButtonRelease>', self.on_sheet2_index_changed)
            UIContextMenu.add_to_entry(self.sheet2_index_spinbox, self.root)

            self.sheet2_index_label = ttk.Label(selection_frame, text="", foreground="blue")

            # Файл
            ttk.Label(frame, text="Файл:").grid(row=1, column=0, sticky=tk.W, pady=2)
            self.sheet2_filename_var = tk.StringVar(value="sheet2.tsv")
            self.sheet2_filename_entry = ttk.Entry(frame, textvariable=self.sheet2_filename_var, width=40)
            self.sheet2_filename_entry.grid(row=1, column=1, sticky=tk.W, pady=2)
            UIContextMenu.add_to_entry(self.sheet2_filename_entry, self.root)

            # Интервал
            ttk.Label(frame, text="Проверять каждые (сек):").grid(row=2, column=0, sticky=tk.W, pady=2)
            self.sheet2_check_interval_var = tk.IntVar(value=300)
            sheet2_interval = ttk.Spinbox(frame, from_=5, to=3600,
                                          textvariable=self.sheet2_check_interval_var, width=10)
            sheet2_interval.grid(row=2, column=1, sticky=tk.W, pady=2)
            UIContextMenu.add_to_entry(sheet2_interval, self.root)

            self.sheet2_save_enabled_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(frame, text="Сохранять этот лист",
                            variable=self.sheet2_save_enabled_var).grid(row=3, column=1, sticky=tk.W, pady=2)

    def setup_context_menus(self):
        """Настройка контекстных меню"""
        callbacks = {
            'clear': self.clear_log,
            'save': self.save_log
        }
        UIContextMenu.add_to_text(self.log_text, self.root, callbacks)

    def apply_theme(self):
        """Применение темы"""
        self.theme_manager.apply_theme(self.log_text)

    def toggle_theme(self):
        """Переключение темы"""
        self.theme_manager.toggle_theme(self.log_text)
        theme_name = self.theme_manager.theme_var.get()
        self.theme_button.config(text="☀️ Светлая тема" if theme_name == "dark" else "🌙 Темная тема")
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
        method = self.selection_method.get()

        # Очищаем фреймы
        for widget in self.sheet1_name_combo.master.winfo_children():
            widget.pack_forget()
        for widget in self.sheet2_name_combo.master.winfo_children():
            widget.pack_forget()

        if method == "by_name":
            self.sheet1_name_combo.pack(side=tk.LEFT)
            self.sheet2_name_combo.pack(side=tk.LEFT)
        else:
            self.sheet1_index_spinbox.pack(side=tk.LEFT)
            self.sheet1_index_label.pack(side=tk.LEFT, padx=(10, 0))
            self.sheet2_index_spinbox.pack(side=tk.LEFT)
            self.sheet2_index_label.pack(side=tk.LEFT, padx=(10, 0))
            self.update_index_labels()

    def toggle_auto_filename(self):
        """Переключение автоопределения имени файла"""
        if self.auto_filename.get():
            self.sheet1_filename_entry.config(state=tk.DISABLED)
            self.sheet2_filename_entry.config(state=tk.DISABLED)
        else:
            self.sheet1_filename_entry.config(state=tk.NORMAL)
            self.sheet2_filename_entry.config(state=tk.NORMAL)

    def get_current_sheet_name(self, sheet_number):
        """Получение имени текущего листа"""
        if self.selection_method.get() == "by_name":
            return self.sheet1_name_var.get().strip() if sheet_number == 1 else self.sheet2_name_var.get().strip()
        else:
            index = self.sheet1_index_var.get() if sheet_number == 1 else self.sheet2_index_var.get()
            if index in self.sheet_names_cache:
                return self.sheet_names_cache[index]
            elif index < len(self.available_sheets):
                return self.available_sheets[index]
        return None

    def update_filename_from_sheet(self):
        """Обновление имени файла из имени листа"""
        if not self.auto_filename.get():
            return

        for sheet_num in [1, 2]:
            sheet_name = self.get_current_sheet_name(sheet_num)
            if sheet_name:
                safe_name = self.file_manager.sanitize_filename(sheet_name)
                if sheet_num == 1:
                    self.sheet1_filename_var.set(f"{safe_name}.tsv")
                else:
                    self.sheet2_filename_var.set(f"{safe_name}.tsv")

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

    def update_index_labels(self):
        """Обновление меток индексов"""
        if self.available_sheets:
            for sheet_num in [1, 2]:
                index = self.sheet1_index_var.get() if sheet_num == 1 else self.sheet2_index_var.get()
                label = self.sheet1_index_label if sheet_num == 1 else self.sheet2_index_label
                if index < len(self.available_sheets):
                    label.config(text=f"→ {self.available_sheets[index]}")
                else:
                    label.config(text="→ Индекс вне диапазона")

    def authenticate_google(self):
        """Авторизация в Google"""
        if not self.sheets_manager:
            self.sheets_manager = GoogleSheetsManager(self.app_dir, self.logger)

        if self.sheets_manager.authenticate():
            self.status_var.set("Статус: Авторизован")
            self.save_btn.config(state=tk.NORMAL)
            self.start_btn.config(state=tk.NORMAL)

            if self.spreadsheet_id_var.get():
                self.get_sheet_list()

    def get_sheet_list(self):
        """Получение списка листов"""
        if not self.sheets_manager:
            messagebox.showwarning("Предупреждение", "Сначала авторизуйтесь")
            return

        spreadsheet_id = self.spreadsheet_id_var.get().strip()

        if 'docs.google.com' in spreadsheet_id:
            import re
            match = re.search(r'/d/([a-zA-Z0-9-_]+)', spreadsheet_id)
            if match:
                spreadsheet_id = match.group(1)
                self.spreadsheet_id_var.set(spreadsheet_id)

        sheets = self.sheets_manager.get_sheet_list(spreadsheet_id)

        if sheets:
            self.available_sheets = [sheet['name'] for sheet in sheets]
            self.sheet_names_cache = {sheet['index']: sheet['name'] for sheet in sheets}

            self.sheet1_name_combo['values'] = self.available_sheets
            self.sheet2_name_combo['values'] = self.available_sheets

            max_index = len(self.available_sheets) - 1
            self.sheet1_index_spinbox.config(to=max_index)
            self.sheet2_index_spinbox.config(to=max_index)

            self.update_index_labels()
            self.update_filename_from_sheet()

    def save_now(self):
        """Немедленное сохранение"""
        if not self.sheets_manager or not self.sheets_manager.service:
            messagebox.showwarning("Предупреждение", "Сначала авторизуйтесь")
            return

        spreadsheet_id = self.spreadsheet_id_var.get().strip()
        output_folder = self.folder_path_var.get().strip() or self.file_manager.get_default_save_folder()
        self.file_manager.ensure_folder_exists(output_folder)

        newline = '\r\n' if self.newline_var.get() == 'windows' else '\n'
        encoding = self.encoding_var.get()

        for sheet_num in [1, 2]:
            save_enabled = self.sheet1_save_enabled_var.get() if sheet_num == 1 else self.sheet2_save_enabled_var.get()
            if not save_enabled:
                continue

            sheet_identifier = self.get_current_sheet_name(sheet_num)
            filename = self.sheet1_filename_var.get() if sheet_num == 1 else self.sheet2_filename_var.get()

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
        self.start_btn.config(text="Остановить авто-сохранение")
        self.start_monitoring()
        self.tray_manager.update_icon(True, self.theme_manager.theme_var.get())
        self.logger.log("Авто-сохранение запущено")

    def stop_autosave(self):
        """Остановка автосохранения"""
        self.is_running = False
        self.start_btn.config(text="Запустить авто-сохранение")
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

    def monitor_loop(self):
        """Цикл мониторинга"""
        while self.is_running:
            try:
                current_time = time.time()

                for sheet_num in [1, 2]:
                    save_enabled = self.sheet1_save_enabled_var.get() if sheet_num == 1 else self.sheet2_save_enabled_var.get()
                    check_interval = self.sheet1_check_interval_var.get() if sheet_num == 1 else self.sheet2_check_interval_var.get()

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
            spreadsheet_id = self.spreadsheet_id_var.get().strip()
            sheet_identifier = self.get_current_sheet_name(sheet_number)

            if not spreadsheet_id or not sheet_identifier:
                return

            data = self.sheets_manager.get_sheet_data(spreadsheet_id, sheet_identifier)
            if not data:
                return

            current_hash = hash(str(data))

            if sheet_number not in self.last_data_hash or self.last_data_hash[sheet_number] != current_hash:
                self.logger.log(f"Обнаружены изменения в листе {sheet_number}")

                if self.notify_changes_var.get():
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
        self.folder_path_var.set(default_folder)
        self.logger.log(f"Установлена папка по умолчанию: {default_folder}")

    def browse_folder(self):
        """Выбор папки"""
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path_var.set(folder)

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
            self.spreadsheet_id_var.set(config.get('spreadsheet_id', ''))
            self.selection_method.set(config.get('selection_method', 'by_name'))
            self.auto_filename.set(config.get('auto_filename', True))
            self.encoding_var.set(config.get('encoding', 'utf-8'))
            self.newline_var.set(config.get('newline_mode', 'unix'))
            self.theme_manager.theme_var.set(config.get('theme', 'light'))

            sheets = config.get('sheets', [])

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

            folder_path = config.get('output_folder', '')
            self.folder_path_var.set(folder_path or self.file_manager.get_default_save_folder())

            notifications = config.get('notifications', {})
            self.notify_success_var.set(notifications.get('success', True))
            self.notify_error_var.set(notifications.get('error', True))
            self.notify_autosave_var.set(notifications.get('autosave', False))
            self.notify_changes_var.set(notifications.get('changes', True))

    def save_config(self):
        """Сохранение конфигурации"""
        sheets = []

        for i in range(2):
            sheet_num = i + 1
            if self.selection_method.get() == "by_name":
                sheet_config = {
                    'name': self.sheet1_name_var.get() if sheet_num == 1 else self.sheet2_name_var.get(),
                    'output_filename': self.sheet1_filename_var.get() if sheet_num == 1 else self.sheet2_filename_var.get(),
                    'check_interval': self.sheet1_check_interval_var.get() if sheet_num == 1 else self.sheet2_check_interval_var.get(),
                    'save_enabled': self.sheet1_save_enabled_var.get() if sheet_num == 1 else self.sheet2_save_enabled_var.get()
                }
            else:
                sheet_config = {
                    'index': self.sheet1_index_var.get() if sheet_num == 1 else self.sheet2_index_var.get(),
                    'output_filename': self.sheet1_filename_var.get() if sheet_num == 1 else self.sheet2_filename_var.get(),
                    'check_interval': self.sheet1_check_interval_var.get() if sheet_num == 1 else self.sheet2_check_interval_var.get(),
                    'save_enabled': self.sheet1_save_enabled_var.get() if sheet_num == 1 else self.sheet2_save_enabled_var.get()
                }
            sheets.append(sheet_config)

        config = {
            'spreadsheet_id': self.spreadsheet_id_var.get(),
            'selection_method': self.selection_method.get(),
            'auto_filename': self.auto_filename.get(),
            'encoding': self.encoding_var.get(),
            'newline_mode': self.newline_var.get(),
            'theme': self.theme_manager.theme_var.get(),
            'sheets': sheets,
            'output_folder': self.folder_path_var.get(),
            'notifications': {
                'success': self.notify_success_var.get(),
                'error': self.notify_error_var.get(),
                'autosave': self.notify_autosave_var.get(),
                'changes': self.notify_changes_var.get()
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


def main():
    app = GoogleSheetsSyncApp()
    app.run()


if __name__ == '__main__':
    main()