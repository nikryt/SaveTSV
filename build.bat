@echo off
chcp 65001 >nul
echo ========================================
echo Сборка Google Sheets Sync (Python 3.13)
echo ========================================
echo.

:: Очистка предыдущей сборки
echo [1/8] Очистка предыдущей сборки...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "*.spec" del /q "*.spec"
if exist "__pycache__" rmdir /s /q "__pycache__"
if exist "ui\__pycache__" rmdir /s /q "ui\__pycache__"
echo Готово.
echo.

:: Установка правильных версий для Python 3.13
echo [2/8] Установка зависимостей...
python -m pip install --upgrade pip
echo Установка PyInstaller...
pip install pyinstaller>=6.10.0
echo Установка Pillow...
pip install --upgrade Pillow
echo Установка остальных зависимостей...
pip install -r requirements.txt
echo Готово.
echo.

:: Проверка установки
echo [3/8] Проверка установки...
python -c "import PyInstaller; print('PyInstaller version:', PyInstaller.__version__)"
python -c "import PIL; print('Pillow version:', PIL.__version__)"
python -c "import pystray; print('pystray OK')"
echo Готово.
echo.

:: Сборка приложения
echo [4/8] Сборка приложения...
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "GoogleSheetsSync" ^
    --clean ^
    --noconfirm ^
    --noupx ^
    --exclude-module tkinter.test ^
    --exclude-module unittest ^
    --exclude-module pydoc ^
    --exclude-module doctest ^
    --hidden-import=googleapiclient.discovery ^
    --hidden-import=google_auth_oauthlib ^
    --hidden-import=google.auth.transport.requests ^
    --hidden-import=google.oauth2.credentials ^
    --collect-all googleapiclient ^
    --collect-all google_auth_oauthlib ^
    main.py
echo Готово.
echo.

:: Проверка сборки
echo [5/8] Проверка сборки...
if exist "dist\GoogleSheetsSync.exe" (
    echo Сборка успешна!
    echo Размер файла:
    dir "dist\GoogleSheetsSync.exe" | findstr "GoogleSheetsSync.exe"
) else (
    echo Ошибка: файл не найден
    echo Пробуем альтернативный метод...
    goto alternative_build
)
echo Готово.
echo.
goto create_portable

:alternative_build
echo.
echo [6/8] Альтернативная сборка...
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "GoogleSheetsSync" ^
    --clean ^
    --noconfirm ^
    --hidden-import=googleapiclient.discovery ^
    --hidden-import=google_auth_oauthlib ^
    --collect-all googleapiclient ^
    --collect-all google_auth_oauthlib ^
    main.py

if exist "dist\GoogleSheetsSync.exe" (
    echo Альтернативная сборка успешна!
) else (
    echo Ошибка сборки!
    pause
    exit /b 1
)

:create_portable
:: Создание папки для распространения
echo.
echo [7/8] Создание папки для распространения...
if exist "GoogleSheetsSync_Portable" rmdir /s /q "GoogleSheetsSync_Portable"
mkdir "GoogleSheetsSync_Portable"
mkdir "GoogleSheetsSync_Portable\SaveSheets"
echo Готово.
echo.

:: Копирование файлов
echo [8/8] Копирование файлов...
copy "dist\GoogleSheetsSync.exe" "GoogleSheetsSync_Portable\"
if exist "config.json" copy "config.json" "GoogleSheetsSync_Portable\"
if exist "credentials.json" copy "credentials.json" "GoogleSheetsSync_Portable\"

:: Создание README
(
echo Google Sheets Sync
echo.
echo Установка:
echo 1. Поместите credentials.json в эту папку
echo 2. Запустите GoogleSheetsSync.exe
echo.
echo Примечание:
echo - Папка SaveSheets создается автоматически
echo - config.json создается при первом сохранении настроек
) > "GoogleSheetsSync_Portable\README.txt"

echo Готово.
echo.

echo ========================================
echo Сборка завершена успешно!
echo ========================================
echo.
echo Файлы:
echo - GoogleSheetsSync_Portable\GoogleSheetsSync.exe
echo - GoogleSheetsSync_Portable\README.txt
echo.
pause