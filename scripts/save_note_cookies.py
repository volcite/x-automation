#!/usr/bin/env python3
"""
Noteのログインセッション（cookies）を保存するスクリプト。
ブラウザが開くので手動でNoteにログインし、完了後にEnterを押すとcookiesが保存される。

使い方:
  python3 scripts/save_note_cookies.py

出力:
  config/note_cookies.json

注意:
  - VPSで実行する場合は headless=False が使えないため、
    ローカルPCで実行して config/note_cookies.json をVPSにコピーしてください。
  - または、環境変数 NOTE_COOKIES_HEADLESS=1 を設定してヘッドレスモードで
    メールアドレス/パスワードによる自動ログインを試みます。
"""

import asyncio
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COOKIES_PATH = PROJECT_ROOT / "config" / "note_cookies.json"


async def save_cookies_interactive():
    """ブラウザを開いて手動ログイン後にcookiesを保存する"""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            locale="ja-JP",
            viewport={"width": 1280, "height": 900},
        )
        page = await context.new_page()

        print("Noteのログインページを開きます...")
        await page.goto("https://note.com/login")

        print()
        print("=" * 50)
        print("ブラウザでNoteにログインしてください。")
        print("ログイン完了後、このターミナルでEnterを押してください。")
        print("=" * 50)
        print()

        input(">>> ログイン完了後にEnterを押してください: ")

        # ログイン確認
        current_url = page.url
        print(f"現在のURL: {current_url}")

        # cookiesを保存
        COOKIES_PATH.parent.mkdir(parents=True, exist_ok=True)
        await context.storage_state(path=str(COOKIES_PATH))

        await browser.close()

    print(f"\nCookiesを保存しました: {COOKIES_PATH}")
    return True


async def save_cookies_headless():
    """メールアドレス/パスワードでヘッドレスログインしてcookiesを保存する"""
    from playwright.async_api import async_playwright

    email = os.environ.get("NOTE_EMAIL")
    password = os.environ.get("NOTE_PASSWORD")

    if not email or not password:
        print("エラー: 環境変数 NOTE_EMAIL と NOTE_PASSWORD を設定してください。")
        print("  export NOTE_EMAIL='your@email.com'")
        print("  export NOTE_PASSWORD='your_password'")
        sys.exit(1)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-gpu"]
        )
        context = await browser.new_context(
            locale="ja-JP",
            viewport={"width": 1280, "height": 900},
        )
        page = await context.new_page()

        print("Noteにログイン中（ヘッドレスモード）...")
        await page.goto("https://note.com/login", timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=30000)

        # メールアドレス入力
        email_input = page.locator(
            'input[placeholder*="mail@example.com"], '
            'input[type="email"], '
            'input[name="login"], '
            'input[placeholder*="メール"]'
        ).first
        await email_input.fill(email)

        # パスワード入力
        pw_input = page.locator(
            'input[type="password"]'
        ).first
        await pw_input.fill(password)

        # ログインボタン
        login_btn = page.locator(
            'button:has-text("ログイン")'
        ).first
        await login_btn.click()

        # ログイン完了を待機
        await page.wait_for_timeout(5000)
        await page.wait_for_load_state("networkidle", timeout=30000)

        current_url = page.url
        print(f"ログイン後URL: {current_url}")

        if "login" in current_url.lower():
            print("エラー: ログインに失敗しました。認証情報を確認してください。")
            # デバッグ用スクリーンショット
            debug_path = PROJECT_ROOT / "logs" / "note_login_debug.png"
            debug_path.parent.mkdir(exist_ok=True)
            await page.screenshot(path=str(debug_path))
            print(f"デバッグスクリーンショット: {debug_path}")
            await browser.close()
            sys.exit(1)

        # editor.note.com にもアクセスしてcookiesを取得
        print("editor.note.com のセッションを取得中...")
        await page.goto("https://editor.note.com/new", timeout=30000)
        await page.wait_for_timeout(5000)

        # cookiesを保存
        COOKIES_PATH.parent.mkdir(parents=True, exist_ok=True)
        await context.storage_state(path=str(COOKIES_PATH))

        await browser.close()

    print(f"\nCookiesを保存しました: {COOKIES_PATH}")
    return True


def main():
    print("=" * 50)
    print("Note ログインセッション保存ツール")
    print("=" * 50)
    print(f"保存先: {COOKIES_PATH}")
    print()

    if os.environ.get("NOTE_COOKIES_HEADLESS") == "1":
        print("モード: ヘッドレス（自動ログイン）")
        asyncio.run(save_cookies_headless())
    else:
        print("モード: インタラクティブ（ブラウザ手動操作）")
        asyncio.run(save_cookies_interactive())

    print("\n完了しました。")


if __name__ == "__main__":
    main()
