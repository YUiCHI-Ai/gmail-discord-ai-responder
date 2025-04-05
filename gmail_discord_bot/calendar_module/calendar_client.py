import os
import pickle
import datetime
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pathlib import Path

from ..config import config
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class CalendarClient:
    def __init__(self):
        self.creds = None
        self.service = None
        self.initialize_service()
    def initialize_service(self):
        """GoogleカレンダーAPIサービスの初期化"""
        token_exists = os.path.exists(config.CALENDAR_TOKEN_FILE)
        token_has_content = token_exists and os.path.getsize(config.CALENDAR_TOKEN_FILE) > 0
        
        if token_has_content:
            try:
                with open(config.CALENDAR_TOKEN_FILE, 'rb') as token:
                    self.creds = pickle.load(token)
                logger.info("カレンダートークンを読み込みました")
            except (EOFError, pickle.UnpicklingError) as e:
                logger.error(f"カレンダートークンの読み込みに失敗しました: {e}")
                self.creds = None
        
        # 認証情報がない、または期限切れの場合
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    config.CALENDAR_CREDENTIALS_FILE, config.CALENDAR_SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            # トークンを保存
            with open(config.CALENDAR_TOKEN_FILE, 'wb') as token:
                pickle.dump(self.creds, token)
        
        self.service = build('calendar', 'v3', credentials=self.creds)
        logger.info("GoogleカレンダーAPIサービスが初期化されました")
    
    def get_calendar_list(self):
        """利用可能なカレンダーのリストを取得"""
        try:
            calendars = self.service.calendarList().list().execute()
            return calendars.get('items', [])
        except Exception as e:
            logger.error(f"カレンダーリスト取得エラー: {e}")
            return []
    
    def get_events(self, calendar_id='primary', time_min=None, time_max=None, max_results=10):
        """指定期間のイベントを取得"""
        try:
            # デフォルトは現在から1週間
            if not time_min:
                time_min = datetime.datetime.utcnow().isoformat() + 'Z'
            if not time_max:
                time_max = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            return events_result.get('items', [])
        
        except Exception as e:
            logger.error(f"イベント取得エラー: {e}")
            return []
    
    def get_free_busy(self, calendar_ids=['primary'], time_min=None, time_max=None):
        """指定期間の空き状況を取得"""
        try:
            # デフォルトは現在から1週間
            if not time_min:
                time_min = datetime.datetime.utcnow().isoformat() + 'Z'
            if not time_max:
                time_max = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).isoformat() + 'Z'
            
            body = {
                "timeMin": time_min,
                "timeMax": time_max,
                "items": [{"id": calendar_id} for calendar_id in calendar_ids]
            }
            
            free_busy_result = self.service.freebusy().query(body=body).execute()
            return free_busy_result
        
        except Exception as e:
            logger.error(f"空き状況取得エラー: {e}")
            return {}