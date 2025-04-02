from ..chatgpt_module.prompt_generator import PromptGenerator as ChatGPTPromptGenerator
from ..chatgpt_module.response_processor import ResponseProcessor as ChatGPTResponseProcessor
from ..claude_module.prompt_generator import ClaudePromptGenerator
from ..claude_module.response_processor import ClaudeResponseProcessor
from ..config import config
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class AIFactory:
    """AIプロバイダーを選択するためのファクトリークラス"""
    
    @staticmethod
    def create_prompt_generator(provider=None):
        """プロンプト生成クラスを作成"""
        if provider is None:
            provider = config.DEFAULT_AI_PROVIDER
        
        logger.info(f"AIプロバイダー '{provider}' のプロンプト生成クラスを作成")
        
        if provider.lower() == "chatgpt":
            return ChatGPTPromptGenerator()
        elif provider.lower() == "claude":
            return ClaudePromptGenerator()
        else:
            logger.warning(f"未知のAIプロバイダー '{provider}' が指定されました。デフォルトのChatGPTを使用します。")
            return ChatGPTPromptGenerator()
    
    @staticmethod
    def create_response_processor(provider=None):
        """応答処理クラスを作成"""
        if provider is None:
            provider = config.DEFAULT_AI_PROVIDER
        
        logger.info(f"AIプロバイダー '{provider}' の応答処理クラスを作成")
        
        if provider.lower() == "chatgpt":
            return ChatGPTResponseProcessor()
        elif provider.lower() == "claude":
            return ClaudeResponseProcessor()
        else:
            logger.warning(f"未知のAIプロバイダー '{provider}' が指定されました。デフォルトのChatGPTを使用します。")
            return ChatGPTResponseProcessor()