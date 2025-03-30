import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config

def test_config_loading():
    """設定が正しく読み込まれるかテスト"""
    assert config.DISCORD_BOT_TOKEN is not None
    assert config.OPENAI_API_KEY is not None
    assert len(config.GMAIL_SCOPES) > 0
    print("設定ファイルのテスト成功")

if __name__ == "__main__":
    test_config_loading()