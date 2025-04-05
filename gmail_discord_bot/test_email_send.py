#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gmail APIのメール送信機能をテストするスクリプト
"""

import sys
import argparse
from gmail_discord_bot.gmail_module.gmail_client import GmailClient
from gmail_discord_bot.utils.logger import setup_logger

logger = setup_logger(__name__)

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='Gmail APIのメール送信機能をテストします')
    parser.add_argument('--to', help='送信先メールアドレス（指定がない場合は自分自身に送信）')
    parser.add_argument('--subject', help='メールの件名', default='Gmail API テストメール')
    parser.add_argument('--body', help='メールの本文', default='これはGmail APIのテストメールです。')
    parser.add_argument('--test', action='store_true', help='テスト送信モード（デフォルトのテストメールを送信）')
    parser.add_argument('--reply-to', help='返信対象のメールID（返信テスト用）')
    parser.add_argument('--thread-id', help='スレッドID（返信テスト用）')
    parser.add_argument('--quote', action='store_true', help='元のメッセージを引用する（返信時）')
    
    args = parser.parse_args()
    
    try:
        # Gmail APIクライアントを初期化
        logger.info("Gmail APIクライアントを初期化中...")
        gmail_client = GmailClient()
        
        # 自分のメールアドレスを取得
        my_email = gmail_client.get_user_email()
        logger.info(f"認証されたメールアドレス: {my_email}")
        
        if args.test:
            # テスト送信モード
            logger.info("テスト送信モードを実行中...")
            result = gmail_client.test_send_email(to=args.to)
            if result:
                logger.info(f"テストメール送信成功: ID={result['id']}")
                print(f"✅ テストメールを送信しました！")
                print(f"  送信先: {args.to or my_email}")
                print(f"  メールID: {result['id']}")
                return 0
            else:
                logger.error("テストメール送信失敗")
                print("❌ テストメールの送信に失敗しました。ログを確認してください。")
                return 1
        else:
            # 返信モードかどうかを確認
            if args.reply_to:
                # 返信モード
                to_email = args.to or my_email
                subject = args.subject
                if not subject.lower().startswith('re:'):
                    subject = f"Re: {subject}"
                body = args.body
                
                logger.info(f"メール返信を実行中... 送信先: {to_email}, 返信対象: {args.reply_to}, 引用: {args.quote}")
                result = gmail_client.send_email(
                    to=to_email,
                    subject=subject,
                    body=body,
                    thread_id=args.thread_id,
                    message_id=args.reply_to,
                    quote_original=args.quote
                )
                
                if result:
                    logger.info(f"メール返信成功: ID={result['id']}")
                    print(f"✅ 返信メールを送信しました！")
                    print(f"  送信先: {to_email}")
                    print(f"  件名: {subject}")
                    print(f"  返信対象: {args.reply_to}")
                    if args.thread_id:
                        print(f"  スレッドID: {args.thread_id}")
                    print(f"  引用モード: {'有効' if args.quote else '無効'}")
                    print(f"  メールID: {result['id']}")
                    return 0
                else:
                    logger.error("メール返信失敗")
                    print("❌ 返信メールの送信に失敗しました。ログを確認してください。")
                    return 1
            else:
                # 通常送信モード
                to_email = args.to or my_email
                subject = args.subject
                body = args.body
                
                logger.info(f"メール送信を実行中... 送信先: {to_email}")
                result = gmail_client.send_email(
                    to=to_email,
                    subject=subject,
                    body=body
                )
            
            if result:
                logger.info(f"メール送信成功: ID={result['id']}")
                print(f"✅ メールを送信しました！")
                print(f"  送信先: {to_email}")
                print(f"  件名: {subject}")
                print(f"  メールID: {result['id']}")
                return 0
            else:
                logger.error("メール送信失敗")
                print("❌ メールの送信に失敗しました。ログを確認してください。")
                return 1
    
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        import traceback
        logger.error(f"詳細なエラー情報: {traceback.format_exc()}")
        print(f"❌ エラーが発生しました: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())