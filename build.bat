@echo off
echo Очистка предыдущей сборки...
rmdir /s /q build dist 2>nul
del *.spec 2>nul

echo Установка зависимостей...
pip uninstall -y PyQt5 pyinstaller
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo Сборка приложения...
pyinstaller --onefile --windowed --name "GoogleSheetsSync" ^
    --hidden-import=googleapiclient.discovery ^
    --hidden-import=google_auth_oauthlib ^
    --hidden-import=google.auth.transport.requests ^
    --collect-all googleapiclient ^
    --collect-all google_auth_oauthlib ^
    main.py

echo Создание папки с приложением...
mkdir GoogleSheetsSync_Portable 2>nul
copy dist\GoogleSheetsSync.exe GoogleSheetsSync_Portable\
copy config.json GoogleSheetsSync_Portable\
copy credentials.json GoogleSheetsSync_Portable\

echo Готово! Приложение в папке GoogleSheetsSync_Portable
pause