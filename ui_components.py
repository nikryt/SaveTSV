import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class UIContextMenu:
    @staticmethod
    def add_to_entry(entry_widget, parent):
        """Добавление контекстного меню и горячих клавиш к полю ввода"""
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
        entry_widget.bind("<Button-2>", show_menu)  # для macOS

        # Добавляем горячие клавиши
        entry_widget.bind('<Control-c>', lambda e: entry_widget.event_generate('<<Copy>>'))
        entry_widget.bind('<Control-v>', lambda e: entry_widget.event_generate('<<Paste>>'))
        entry_widget.bind('<Control-x>', lambda e: entry_widget.event_generate('<<Cut>>'))
        entry_widget.bind('<Control-a>', lambda e: UIContextMenu.select_all(entry_widget))

        # Для macOS
        entry_widget.bind('<Command-c>', lambda e: entry_widget.event_generate('<<Copy>>'))
        entry_widget.bind('<Command-v>', lambda e: entry_widget.event_generate('<<Paste>>'))
        entry_widget.bind('<Command-x>', lambda e: entry_widget.event_generate('<<Cut>>'))
        entry_widget.bind('<Command-a>', lambda e: UIContextMenu.select_all(entry_widget))

    @staticmethod
    def select_all(entry_widget):
        """Выделить всё"""
        entry_widget.select_range(0, tk.END)
        entry_widget.icursor(tk.END)
        return 'break'

    @staticmethod
    def add_to_text(text_widget, parent, callbacks=None):
        """Добавление контекстного меню и горячих клавиш к текстовому полю"""
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
        text_widget.bind("<Button-2>", show_menu)  # для macOS

        # Добавляем горячие клавиши
        text_widget.bind('<Control-c>', lambda e: UIContextMenu.copy_text(text_widget, parent))
        text_widget.bind('<Control-a>', lambda e: UIContextMenu.select_all_text(text_widget))

        # Для macOS
        text_widget.bind('<Command-c>', lambda e: UIContextMenu.copy_text(text_widget, parent))
        text_widget.bind('<Command-a>', lambda e: UIContextMenu.select_all_text(text_widget))

    @staticmethod
    def copy_text(text_widget, parent):
        """Копирование выделенного текста"""
        try:
            selected_text = text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            parent.clipboard_clear()
            parent.clipboard_append(selected_text)
            text_widget.tag_remove(tk.SEL, "1.0", tk.END)
            return 'break'
        except tk.TclError:
            messagebox.showinfo("Информация", "Выделите текст для копирования")
            return 'break'

    @staticmethod
    def select_all_text(text_widget):
        """Выделить весь текст"""
        text_widget.tag_add(tk.SEL, "1.0", tk.END)
        text_widget.mark_set(tk.INSERT, "1.0")
        text_widget.see(tk.INSERT)
        return 'break'