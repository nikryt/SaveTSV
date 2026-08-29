import tkinter as tk
from tkinter import ttk, messagebox


class ContextMenuManager:
    def __init__(self, root):
        self.root = root

    def add_to_entry(self, entry_widget):
        """Добавление контекстного меню к полю ввода"""
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Вырезать", command=lambda: entry_widget.event_generate('<<Cut>>'))
        menu.add_command(label="Копировать", command=lambda: entry_widget.event_generate('<<Copy>>'))
        menu.add_command(label="Вставить", command=lambda: entry_widget.event_generate('<<Paste>>'))
        menu.add_separator()
        menu.add_command(label="Выделить всё",
                         command=lambda: self.select_all_entry(entry_widget))

        def show_menu(event):
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        entry_widget.bind("<Button-3>", show_menu)
        entry_widget.bind("<Button-2>", show_menu)  # для macOS

    def add_to_text(self, text_widget, callbacks=None):
        """Добавление контекстного меню к текстовому полю"""
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Копировать",
                         command=lambda: self.copy_from_text(text_widget))
        menu.add_command(label="Выделить всё",
                         command=lambda: self.select_all_text(text_widget))
        menu.add_separator()

        if callbacks:
            if 'clear' in callbacks:
                menu.add_command(label="Очистить", command=callbacks['clear'])
            if 'save' in callbacks:
                menu.add_command(label="Сохранить в файл", command=callbacks['save'])

        def show_menu(event):
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        text_widget.bind("<Button-3>", show_menu)
        text_widget.bind("<Button-2>", show_menu)  # для macOS

    def select_all_entry(self, entry_widget):
        """Выделить всё в поле ввода"""
        entry_widget.select_range(0, tk.END)
        entry_widget.icursor(tk.END)

    def select_all_text(self, text_widget):
        """Выделить весь текст"""
        text_widget.tag_add(tk.SEL, "1.0", tk.END)
        text_widget.mark_set(tk.INSERT, "1.0")
        text_widget.see(tk.INSERT)

    def copy_from_text(self, text_widget):
        """Копирование из текстового виджета"""
        try:
            selected_text = text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
            text_widget.tag_remove(tk.SEL, "1.0", tk.END)
        except tk.TclError:
            messagebox.showinfo("Информация", "Выделите текст для копирования")