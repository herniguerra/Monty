from app import create_app
import threading
import os

app = create_app()

if __name__ == '__main__':
    # Start Telegram bot in background thread
    # Only start in the reloader child process (or if reloader is disabled)
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        from app.telegram.bot import start_telegram_bot
        telegram_thread = threading.Thread(target=start_telegram_bot, daemon=True)
        telegram_thread.start()
        print("[Telegram] Bot thread started")
    
    app.run(host='0.0.0.0', port=5050, debug=True, use_reloader=True, reloader_type='stat')
