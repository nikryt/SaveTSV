import os
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox


class Logger:
    def __init__(self, log_text_widget=None):
        self.log_text = log_text_widget
        self.log_file = None
        self.auto_save = False

    def set_log_widget(self, log_text_widget):
        """Установка виджета для логирования"""
        self.log_text = log_text_widget

    def log(self, message):
        """Логирование сообщения"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"

        # Вывод в консоль
        print(log_message)

        # Вывод в GUI
        if self.log_text is not None:
            try:
                self.log_text.insert(tk.END, log_message + "\n")
                self.log_text.see(tk.END)
            except:
                pass

    def save_to_file(self, parent=None):
        """Сохранение журнала в файл"""
        try:
            if self.log_text is None:
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"log_{timestamp}.txt"

            file_path = filedialog.asksaveasfilename(
                parent=parent,
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
                return True

        except Exception as e:
            self.log(f"Ошибка сохранения журнала: {str(e)}")
            return False

    def clear(self):
        """Очистка журнала"""
        if self.log_text is not None:
            self.log_text.delete("1.0", tk.END)