import os
import pickle
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


class GoogleSheetsManager:
    def __init__(self, app_dir, logger=None):
        self.app_dir = app_dir
        self.logger = logger
        self.service = None
        self.SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

    def log(self, message):
        """Логирование"""
        if self.logger:
            self.logger.log(message)
        else:
            print(message)

    def get_credentials_path(self):
        """Получение пути к credentials.json"""
        return os.path.join(self.app_dir, 'credentials.json')

    def get_token_path(self):
        """Получение пути к token.pickle"""
        return os.path.join(self.app_dir, 'token.pickle')

    def authenticate(self):
        """Авторизация в Google"""
        try:
            creds = None

            token_file = self.get_token_path()
            if os.path.exists(token_file):
                with open(token_file, 'rb') as token:
                    creds = pickle.load(token)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    credentials_file = self.get_credentials_path()
                    if not os.path.exists(credentials_file):
                        raise Exception(f"Файл credentials.json не найден в {self.app_dir}")

                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_file, self.SCOPES)
                    creds = flow.run_local_server(port=0)

                with open(token_file, 'wb') as token:
                    pickle.dump(creds, token)

            self.service = build('sheets', 'v4', credentials=creds)
            self.log("Авторизация успешна")
            return True

        except Exception as e:
            self.log(f"Ошибка авторизации: {str(e)}")
            return False

    def get_sheet_list(self, spreadsheet_id):
        """Получение списка листов"""
        if not self.service:
            self.log("Не авторизован")
            return []

        try:
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()

            sheets = []
            for i, sheet in enumerate(spreadsheet.get('sheets', [])):
                sheet_name = sheet['properties']['title']
                sheets.append({
                    'index': i,
                    'name': sheet_name,
                    'title': spreadsheet['properties']['title']
                })

            return sheets

        except Exception as e:
            self.log(f"Ошибка получения списка листов: {str(e)}")
            return []

    def get_sheet_data(self, spreadsheet_id, sheet_identifier):
        """Получение данных листа"""
        if not self.service:
            self.log("Не авторизован")
            return None

        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=sheet_identifier
            ).execute()

            return result.get('values', [])

        except Exception as e:
            self.log(f"Ошибка получения данных листа: {str(e)}")
            return None