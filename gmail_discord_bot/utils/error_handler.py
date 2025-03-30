import traceback
import sys
from .logger import setup_logger

logger = setup_logger(__name__)

class EmailBotError(Exception):
    """メールボットの基本例外クラス"""
    def __init__(self, message, original_error=None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)

class APIError(EmailBotError):
    """API呼び出し関連のエラー"""
    pass

class ConfigError(EmailBotError):
    """設定関連のエラー"""
    pass

class DatabaseError(EmailBotError):
    """データベース関連のエラー"""
    pass

class EmailProcessingError(EmailBotError):
    """メール処理関連のエラー"""
    pass

def handle_error(error, context=None):
    """エラーハンドリング共通関数"""
    error_type = type(error).__name__
    error_message = str(error)
    
    # コンテキスト情報があれば追加
    context_info = f" in {context}" if context else ""
    
    # エラーの種類に応じたログレベルでログ出力
    if isinstance(error, EmailBotError):
        logger.error(f"{error_type}{context_info}: {error_message}")
        if error.original_error:
            logger.debug(f"Original error: {error.original_error}")
            logger.debug(traceback.format_exc())
    else:
        logger.critical(f"Unhandled {error_type}{context_info}: {error_message}")
        logger.critical(traceback.format_exc())
    
    return {
        'error_type': error_type,
        'error_message': error_message,
        'context': context
    }

def safe_execute(func, error_context=None, default_return=None):
    """関数を安全に実行するためのデコレータ的関数"""
    try:
        return func()
    except Exception as e:
        handle_error(e, error_context)
        return default_return