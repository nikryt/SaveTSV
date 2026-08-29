import tkinter as tk
from tkinter import ttk


class ThemeManager:
    def __init__(self, root):
        self.root = root
        self.current_theme = "light"
        self.theme_var = tk.StringVar(value="light")

    def get_theme_colors(self):
        """Получение цветов для текущей темы"""
        if self.theme_var.get() == "dark":
            return {
                'bg': '#2b2b2b',
                'fg': '#ffffff',
                'select': '#404040',
                'entry_bg': '#3c3c3c',
                'entry_fg': '#ffffff',
                'button_bg': '#404040',
                'button_fg': '#ffffff',
                'label_bg': '#2b2b2b',
                'label_fg': '#ffffff',
                'log_bg': '#1e1e1e',
                'log_fg': '#ffffff',
                'canvas_bg': '#2b2b2b'
            }
        else:
            return {
                'bg': '#f0f0f0',
                'fg': '#000000',
                'select': '#0078d7',
                'entry_bg': '#ffffff',
                'entry_fg': '#000000',
                'button_bg': '#e1e1e1',
                'button_fg': '#000000',
                'label_bg': '#f0f0f0',
                'label_fg': '#000000',
                'log_bg': '#ffffff',
                'log_fg': '#000000',
                'canvas_bg': '#f0f0f0'
            }

    def apply_theme(self, log_text_widget=None, canvas_widget=None):
        """Применение темы к приложению"""
        colors = self.get_theme_colors()

        style = ttk.Style()
        style.theme_use('clam')

        # Настройка стилей ttk
        style.configure('TFrame', background=colors['bg'])
        style.configure('TLabel', background=colors['label_bg'], foreground=colors['label_fg'])
        style.configure('TLabelframe', background=colors['bg'], foreground=colors['fg'])
        style.configure('TLabelframe.Label', background=colors['bg'], foreground=colors['fg'])
        style.configure('TButton', background=colors['button_bg'], foreground=colors['button_fg'])
        style.map('TButton',
                  background=[('active', colors['select']), ('pressed', colors['select'])],
                  foreground=[('active', '#ffffff'), ('pressed', '#ffffff')])
        style.configure('TCheckbutton', background=colors['bg'], foreground=colors['fg'])
        style.map('TCheckbutton',
                  background=[('active', colors['bg'])],
                  foreground=[('active', colors['fg'])])
        style.configure('TRadiobutton', background=colors['bg'], foreground=colors['fg'])
        style.map('TRadiobutton',
                  background=[('active', colors['bg'])],
                  foreground=[('active', colors['fg'])])
        style.configure('TEntry', fieldbackground=colors['entry_bg'], foreground=colors['entry_fg'])
        style.configure('TCombobox', fieldbackground=colors['entry_bg'], foreground=colors['entry_fg'])
        style.configure('TSpinbox', fieldbackground=colors['entry_bg'], foreground=colors['entry_fg'])

        # Настройка основного окна
        self.root.configure(bg=colors['bg'])

        # Настройка Canvas
        if canvas_widget:
            canvas_widget.configure(bg=colors['canvas_bg'])

        # Настройка журнала
        if log_text_widget:
            log_text_widget.configure(
                bg=colors['log_bg'],
                fg=colors['log_fg'],
                insertbackground=colors['log_fg']
            )

        self.current_theme = self.theme_var.get()
        return colors

    def toggle_theme(self, log_text_widget=None, canvas_widget=None):
        """Переключение темы"""
        if self.theme_var.get() == "light":
            self.theme_var.set("dark")
        else:
            self.theme_var.set("light")

        return self.apply_theme(log_text_widget, canvas_widget)