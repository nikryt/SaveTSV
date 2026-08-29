import tkinter as tk
from tkinter import ttk


class HotkeyManager:
    def __init__(self, root):
        self.root = root
        self.setup_hotkeys()

    def setup_hotkeys(self):
        """Настройка глобальных горячих клавиш"""
        # Привязываем горячие клавиши
        self.root.bind_all('<Control-c>', self.handle_copy)
        self.root.bind_all('<Control-v>', self.handle_paste)
        self.root.bind_all('<Control-x>', self.handle_cut)
        self.root.bind_all('<Control-a>', self.handle_select_all)

        # Для macOS
        self.root.bind_all('<Command-c>', self.handle_copy)
        self.root.bind_all('<Command-v>', self.handle_paste)
        self.root.bind_all('<Command-x>', self.handle_cut)
        self.root.bind_all('<Command-a>', self.handle_select_all)

    def get_focused_widget(self):
        """Получение сфокусированного виджета"""
        try:
            return self.root.focus_get()
        except:
            return None

    def handle_copy(self, event=None):
        """Обработка Ctrl+C"""
        widget = self.get_focused_widget()

        if widget is None:
            return None

        try:
            widget_type = widget.winfo_class()

            if widget_type in ('Entry', 'TEntry', 'TCombobox', 'TSpinbox'):
                widget.event_generate('<<Copy>>')
                return 'break'
            elif widget_type == 'Text':
                self.copy_from_text(widget)
                return 'break'
        except Exception as e:
            print(f"Error in copy: {e}")

        return None

    def handle_paste(self, event=None):
        """Обработка Ctrl+V"""
        widget = self.get_focused_widget()

        if widget is None:
            return None

        try:
            widget_type = widget.winfo_class()

            if widget_type in ('Entry', 'TEntry', 'TCombobox', 'TSpinbox'):
                widget.event_generate('<<Paste>>')
                return 'break'
        except Exception as e:
            print(f"Error in paste: {e}")

        return None

    def handle_cut(self, event=None):
        """Обработка Ctrl+X"""
        widget = self.get_focused_widget()

        if widget is None:
            return None

        try:
            widget_type = widget.winfo_class()

            if widget_type in ('Entry', 'TEntry', 'TCombobox', 'TSpinbox'):
                widget.event_generate('<<Cut>>')
                return 'break'
        except Exception as e:
            print(f"Error in cut: {e}")

        return None

    def handle_select_all(self, event=None):
        """Обработка Ctrl+A"""
        widget = self.get_focused_widget()

        if widget is None:
            return None

        try:
            widget_type = widget.winfo_class()

            if widget_type in ('Entry', 'TEntry', 'TCombobox', 'TSpinbox'):
                widget.select_range(0, tk.END)
                widget.icursor(tk.END)
                return 'break'
            elif widget_type == 'Text':
                widget.tag_add(tk.SEL, "1.0", tk.END)
                widget.mark_set(tk.INSERT, "1.0")
                widget.see(tk.INSERT)
                return 'break'
        except Exception as e:
            print(f"Error in select all: {e}")

        return None

    def copy_from_text(self, text_widget):
        """Копирование из текстового виджета"""
        try:
            # Пробуем скопировать выделенный текст
            selected_text = text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
            text_widget.tag_remove(tk.SEL, "1.0", tk.END)
        except tk.TclError:
            # Если нет выделения, пробуем скопировать все
            try:
                all_text = text_widget.get("1.0", tk.END)
                self.root.clipboard_clear()
                self.root.clipboard_append(all_text.strip())
            except:
                pass