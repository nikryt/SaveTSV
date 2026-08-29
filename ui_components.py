import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class UIContextMenu:
    @staticmethod
    def add_to_entry(entry_widget, parent):
        """Добавление контекстного меню к полю ввода"""
        menu = tk.Menu(parent, tearoff=0)
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

    @staticmethod
    def add_to_text(text_widget, parent, callbacks=None):
        """Добавление контекстного меню к текстовому полю"""
        menu = tk.Menu(parent, tearoff=0)
        menu.add_command(label="Копировать", command=lambda: UIContextMenu.copy_text(text_widget, parent))
        menu.add_command(label="Выделить всё", command=lambda: text_widget.tag_add(tk.SEL, "1.0", tk.END))
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
        text_widget.bind("<Button-2>", show_menu)

    @staticmethod
    def copy_text(text_widget, parent):
        """Копирование выделенного текста"""
        try:
            selected_text = text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            parent.clipboard_clear()
            parent.clipboard_append(selected_text)
        except tk.TclError:
            messagebox.showinfo("Информация", "Выделите текст для копирования")