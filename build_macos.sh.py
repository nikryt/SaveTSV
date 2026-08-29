#!/bin/bash

echo "========================================"
echo "Сборка Google Sheets Sync для macOS"
echo "========================================"
echo ""

# Очистка предыдущей сборки
echo "[1/7] Очистка предыдущей сборки..."
rm -rf build dist *.spec
echo "Готово."
echo ""

# Установка зависимостей
echo "[2/7] Установка зависимостей..."
python3 -m pip install --upgrade pip
pip3 install -r requirements.txt
pip3 install pyinstaller
echo "Готово."
echo ""

# Сборка приложения
echo "[3/7] Сборка приложения..."
pyinstaller --onefile \
    --windowed \
    --name "GoogleSheetsSync" \
    --icon "icon.icns" \
    --add-data "config.json:." \
    --hidden-import=googleapiclient.discovery \
    --hidden-import=google_auth_oauthlib \
    --hidden-import=google.auth.transport.requests \
    --hidden-import=google.oauth2.credentials \
    --hidden-import=pystray \
    --hidden-import=PIL \
    --collect-all googleapiclient \
    --collect-all google_auth_oauthlib \
    --collect-all pystray \
    --collect-all PIL \
    main.py
echo "Готово."
echo ""

# Создание папки для распространения
echo "[4/7] Создание папки для распространения..."
rm -rf GoogleSheetsSync_macOS
mkdir -p GoogleSheetsSync_macOS/SaveSheets
echo "Готово."
echo ""

# Копирование файлов
echo "[5/7] Копирование файлов..."
cp dist/GoogleSheetsSync GoogleSheetsSync_macOS/
if [ -f "config.json" ]; then
    cp config.json GoogleSheetsSync_macOS/
fi
if [ -f "credentials.json" ]; then
    cp credentials.json GoogleSheetsSync_macOS/
fi

# Создание README
echo "Создание README..."
cat > GoogleSheetsSync_macOS/README.txt << 'EOF'
Google Sheets Sync

Установка:
1. Поместите файл credentials.json в эту папку
2. Запустите GoogleSheetsSync

Первый запуск:
1. Нажмите "1. Авторизация"
2. Введите ID таблицы Google Sheets
3. Нажмите "Получить листы"
4. Выберите листы для сохранения
5. Нажмите "2. Сохранить сейчас" для теста
6. Нажмите "3. Запустить авто-сохранение"

Файлы:
- SaveSheets/ - папка для сохранения TSV файлов
- config.json - файл конфигурации
- credentials.json - файл авторизации Google API

Примечание:
При первом запуске macOS может заблокировать приложение.
Если это произошло, выполните в терминале:
xattr -d com.apple.quarantine /путь/к/GoogleSheetsSync
EOF
echo "Готово."
echo ""

# Создание DMG
echo "[6/7] Создание DMG..."
if command -v create-dmg &> /dev/null; then
    create-dmg \
        --volname "Google Sheets Sync" \
        --window-pos 200 120 \
        --window-size 800 400 \
        --icon-size 100 \
        --icon "GoogleSheetsSync" 200 190 \
        --hide-extension "GoogleSheetsSync" \
        --app-drop-link 600 185 \
        "GoogleSheetsSync.dmg" \
        "GoogleSheetsSync_macOS/"
else
    echo "create-dmg не найден, создаю простой DMG..."
    hdiutil create -volname "Google Sheets Sync" \
        -srcfolder "GoogleSheetsSync_macOS" \
        -ov -format UDZO \
        "GoogleSheetsSync.dmg"
fi
echo "Готово."
echo ""

# Создание ZIP архива
echo "[7/7] Создание ZIP архива..."
zip -r GoogleSheetsSync_macOS.zip GoogleSheetsSync_macOS/
echo "Готово."
echo ""

echo "========================================"
echo "Сборка завершена успешно!"
echo "========================================"
echo ""
echo "Файлы:"
echo "- GoogleSheetsSync_macOS/ - папка с приложением"
echo "- GoogleSheetsSync.dmg - установщик DMG"
echo "- GoogleSheetsSync_macOS.zip - ZIP архив"
echo ""