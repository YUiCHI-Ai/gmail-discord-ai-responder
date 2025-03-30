import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import datetime
import pytz

from gmail_discord_bot.calendar_module.calendar_client import CalendarClient
from gmail_discord_bot.calendar_module.schedule_analyzer import ScheduleAnalyzer

class TestCalendarModule(unittest.TestCase):
    
    @patch('gmail_discord_bot.calendar_module.calendar_client.build')
    @patch('gmail_discord_bot.calendar_module.calendar_client.InstalledAppFlow')
    @patch('gmail_discord_bot.calendar_module.calendar_client.Request')
    def test_calendar_client_initialization(self, mock_request, mock_flow, mock_build):
        """CalendarClientの初期化テスト"""
        # モックの設定
        mock_build.return_value = MagicMock()
        
        # テスト実行
        client = CalendarClient()
        
        # 検証
        self.assertIsNotNone(client.service)
        mock_build.assert_called_once()
    
    def test_schedule_analyzer(self):
        """ScheduleAnalyzerのテスト"""
        # モックのCalendarClientを作成
        mock_client = MagicMock()
        
        # get_eventsの戻り値を設定
        now = datetime.datetime.now()
        tomorrow = now + datetime.timedelta(days=1)
        
        # イベントのモックデータ
        mock_events = [
            {
                'summary': 'テストイベント1',
                'start': {
                    'dateTime': now.replace(hour=10, minute=0).isoformat() + 'Z'
                },
                'end': {
                    'dateTime': now.replace(hour=11, minute=0).isoformat() + 'Z'
                }
            },
            {
                'summary': '終日イベント',
                'start': {
                    'date': tomorrow.date().isoformat()
                },
                'end': {
                    'date': (tomorrow + datetime.timedelta(days=1)).date().isoformat()
                }
            }
        ]
        
        mock_client.get_events.return_value = mock_events
        
        # ScheduleAnalyzerのインスタンス化
        analyzer = ScheduleAnalyzer(calendar_client=mock_client)
        
        # テスト実行
        available_slots = analyzer.get_available_slots(days=3)
        
        # 検証
        self.assertIsInstance(available_slots, list)
        mock_client.get_events.assert_called_once()

if __name__ == '__main__':
    unittest.main()