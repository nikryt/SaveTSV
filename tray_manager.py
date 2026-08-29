import threading
import tkinter as tk

try:
    import pystray
    from PIL import Image, ImageDraw

    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False


class TrayManager:
    def __init__(self, app):
        self.app = app
        self.tray_icon = None
        self.tray_thread = None
        self.is_available = TRAY_AVAILABLE

    def create_tray_image(self, is_running=False, theme="light"):
        """Создание изображения для трея"""
        if not self.is_available:
            return None

        if theme == "dark":
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

    def setup(self, callbacks):
        """Настройка иконки в трее"""
        if not self.is_available:
            return False

        try:
            menu = pystray.Menu(
                pystray.MenuItem("Показать", callbacks.get('show', lambda: None), default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "Автосохранение",
                    pystray.Menu(
                        pystray.MenuItem(
                            "Включить",
                            callbacks.get('start', lambda: None),
                            checked=lambda item: self.app.is_running
                        ),
                        pystray.MenuItem(
                            "Выключить",
                            callbacks.get('stop', lambda: None),
                            checked=lambda item: not self.app.is_running
                        )
                    )
                ),
                pystray.MenuItem("Сохранить сейчас", callbacks.get('save', lambda: None)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Выход", callbacks.get('quit', lambda: None))
            )

            image = self.create_tray_image(False, "light")
            self.tray_icon = pystray.Icon("google_sheets_sync", image, "Google Sheets Sync", menu)

            self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            self.tray_thread.start()

            return True
        except Exception as e:
            print(f"Ошибка создания иконки в трее: {str(e)}")
            return False

    def update_icon(self, is_running=False, theme="light"):
        """Обновление иконки в трее"""
        if self.tray_icon:
            self.tray_icon.icon = self.create_tray_image(is_running, theme)

    def notify(self, title, message):
        """Показать уведомление"""
        if self.tray_icon:
            self.tray_icon.notify(title, message)

    def stop(self):
        """Остановка трея"""
        if self.tray_icon:
            self.tray_icon.stop()