"""
Monty Telegram Bot
Core bot setup with inject-on-notify pattern for context synchronization.
"""
import os
import asyncio
import logging
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

logger = logging.getLogger(__name__)

# Global bot instance
_telegram_bot: Optional['TelegramBot'] = None


class TelegramBot:
    """
    Telegram interface for Monty with inject-on-notify pattern.
    
    When proposals are sent via Telegram, they're also injected into
    the ChatEngine history so users can ask follow-up questions naturally.
    """
    
    def __init__(self, token: str, allowed_user_ids: list[int]):
        self.token = token
        self.allowed_user_ids = allowed_user_ids
        self.application: Optional[Application] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
    def _is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized to interact with bot."""
        if not self.allowed_user_ids:
            return True  # No restrictions if list is empty
        return user_id in self.allowed_user_ids
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user = update.effective_user
        if not self._is_authorized(user.id):
            await update.message.reply_text("⛔ Unauthorized. Contact the bot owner.")
            return
            
        await update.message.reply_text(
            f"👋 Hey {user.first_name}! I'm **Monty**, your crypto trading assistant.\n\n"
            "I'll send you trade proposals when I spot opportunities. "
            "You can approve or reject them right here.\n\n"
            "Just chat with me naturally - ask about prices, your portfolio, or market conditions!\n\n"
            "**Commands:**\n"
            "/portfolio - View your current holdings\n"
            "/status - Check scanning status\n"
            "/settings - Adjust scan interval & expiry",
            parse_mode='Markdown'
        )
    
    async def portfolio_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /portfolio command - quick access to portfolio."""
        if not self._is_authorized(update.effective_user.id):
            return
            
        # Route through ChatEngine for consistency
        response = await self._chat("Show me my portfolio summary")
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        if not self._is_authorized(update.effective_user.id):
            return
        
        # Get actual settings
        settings_info = await self._get_settings()
        
        await update.message.reply_text(
            f"🔄 **Scanner Status**\n\n"
            f"⏱️ Scan interval: every **{settings_info['scan_interval']}** minutes\n"
            f"⏳ Trade expiry: **{settings_info['trade_expiry']}** minutes\n"
            f"💵 Initial balance: **${settings_info['initial_balance']:,.0f}**\n\n"
            "The scanner runs automatically. Use /settings to adjust.",
            parse_mode='Markdown'
        )
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /settings command - show settings with adjustment buttons."""
        if not self._is_authorized(update.effective_user.id):
            return
        
        await self._send_settings_menu(update.message)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages - route to ChatEngine."""
        user = update.effective_user
        if not self._is_authorized(user.id):
            return
            
        user_message = update.message.text
        logger.info(f"[Telegram] Message from {user.first_name}: {user_message}")
        
        # Show typing indicator
        await update.message.chat.send_action('typing')
        
        # Route through ChatEngine
        response = await self._chat(user_message)
        
        # Send response (split if too long)
        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                await update.message.reply_text(response[i:i+4000], parse_mode='Markdown')
        else:
            await update.message.reply_text(response, parse_mode='Markdown')
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks (Approve/Reject/Settings)."""
        query = update.callback_query
        user = update.effective_user
        
        if not self._is_authorized(user.id):
            await query.answer("Unauthorized", show_alert=True)
            return
            
        await query.answer()  # Acknowledge the callback
        
        data = query.data
        
        # Handle "noop" buttons (display-only)
        if data == 'noop':
            return
        
        # Handle settings adjustments
        if data.startswith('set_'):
            settings = await self._get_settings()
            
            if data == 'set_scan_up':
                new_value = min(60, settings['scan_interval'] + 5)
                await self._update_setting('scan_interval', new_value)
            elif data == 'set_scan_down':
                new_value = max(1, settings['scan_interval'] - 5)
                await self._update_setting('scan_interval', new_value)
            elif data == 'set_expiry_up':
                new_value = min(120, settings['trade_expiry'] + 10)
                await self._update_setting('trade_expiry', new_value)
            elif data == 'set_expiry_down':
                new_value = max(5, settings['trade_expiry'] - 10)
                await self._update_setting('trade_expiry', new_value)
            
            # Refresh the settings menu
            await self._send_settings_menu(query.message)
            return
        
        # Handle trigger scan
        if data == 'trigger_scan':
            await query.edit_message_text("🔍 Scanning markets...", parse_mode='Markdown')
            result = await self._trigger_scan()
            # Show result then refresh settings menu
            settings = await self._get_settings()
            text = (
                f"{result}\n\n"
                "⚙️ **Settings**\n\n"
                f"⏱️ **Scan Interval:** {settings['scan_interval']} min\n"
                f"⏳ **Trade Expiry:** {settings['trade_expiry']} min\n"
                f"💵 **Initial Balance:** ${settings['initial_balance']:,.0f}\n\n"
                "_Tap buttons to adjust:_"
            )
            keyboard = [
                [
                    InlineKeyboardButton("⏱️ Scan: ➖", callback_data="set_scan_down"),
                    InlineKeyboardButton(f"{settings['scan_interval']}m", callback_data="noop"),
                    InlineKeyboardButton("⏱️ Scan: ➕", callback_data="set_scan_up"),
                ],
                [
                    InlineKeyboardButton("⏳ Expiry: ➖", callback_data="set_expiry_down"),
                    InlineKeyboardButton(f"{settings['trade_expiry']}m", callback_data="noop"),
                    InlineKeyboardButton("⏳ Expiry: ➕", callback_data="set_expiry_up"),
                ],
                [
                    InlineKeyboardButton("🔍 Trigger Scan Now", callback_data="trigger_scan"),
                ],
            ]
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            return
        
        # Handle trade approve/reject
        if '_' in data:
            action, trade_id = data.split('_', 1)
            trade_id = int(trade_id)
            
            if action == 'approve':
                result = await self._approve_trade(trade_id)
                await query.edit_message_text(
                    query.message.text + f"\n\n✅ **Approved and executed!**\n{result}",
                    parse_mode='Markdown'
                )
                # Inject user action into chat history
                await self._inject_message("user", f"I approved trade #{trade_id}")
                
            elif action == 'reject':
                await self._reject_trade(trade_id)
                await query.edit_message_text(
                    query.message.text + "\n\n❌ **Rejected**",
                    parse_mode='Markdown'
                )
                # Inject user action into chat history
                await self._inject_message("user", f"I rejected trade #{trade_id}")

        
    async def _chat(self, message: str) -> str:
        """Route message through ChatEngine (non-streaming fallback)."""
        def sync_chat():
            from app.core.chat_engine import get_chat_engine
            engine = get_chat_engine()
            result = engine.chat(message)
            return result.get('response', 'Sorry, I encountered an error.')
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_chat)
    
    async def _chat_stream(self, message: str, sent_msg) -> str:
        """
        Stream response with progressive message editing.
        Updates the sent_msg with new content as it arrives.
        """
        import time
        
        def stream_generator():
            """Run the sync generator in a thread-safe way."""
            from app.core.chat_engine import get_chat_engine
            engine = get_chat_engine()
            events = []
            for event in engine.chat_stream(message):
                events.append(event)
            return events
        
        loop = asyncio.get_event_loop()
        
        try:
            # Get all events from the sync generator
            events = await loop.run_in_executor(None, stream_generator)
            
            full_text = ""
            tool_calls = []
            last_edit_time = time.time()
            last_edit_len = 0
            
            for event in events:
                if event.get('type') == 'text':
                    full_text += event.get('delta', '')
                    
                    # Batch edits: update every 500ms or 100 chars
                    now = time.time()
                    if now - last_edit_time > 0.5 or len(full_text) - last_edit_len > 100:
                        try:
                            display_text = self._format_streaming_text(full_text, tool_calls, streaming=True)
                            await sent_msg.edit_text(display_text, parse_mode='Markdown')
                            last_edit_time = now
                            last_edit_len = len(full_text)
                        except Exception as e:
                            # Handle rate limits gracefully
                            if 'retry after' in str(e).lower():
                                await asyncio.sleep(1)
                            logger.debug(f"[Telegram] Edit skipped: {e}")
                            
                elif event.get('type') == 'tool_call':
                    tool_calls.append(event.get('tool', 'unknown'))
                    # Update to show tool being called
                    try:
                        display_text = self._format_streaming_text(full_text, tool_calls, streaming=True)
                        await sent_msg.edit_text(display_text, parse_mode='Markdown')
                    except Exception:
                        pass
                        
                elif event.get('type') == 'done':
                    # Final update without cursor
                    display_text = self._format_streaming_text(full_text, tool_calls, streaming=False)
                    try:
                        await sent_msg.edit_text(display_text, parse_mode='Markdown')
                    except Exception:
                        pass
                    return full_text
            
            return full_text or "No response received."
            
        except Exception as e:
            logger.error(f"[Telegram] Stream error: {e}")
            return f"Sorry, I encountered an error: {str(e)}"
    
    def _format_streaming_text(self, text: str, tool_calls: list, streaming: bool = True) -> str:
        """Format text for Telegram display with tool indicators."""
        parts = []
        
        # Add tool call indicators if any
        if tool_calls:
            tools_str = " ".join([f"🔧 _{t}_" for t in tool_calls])
            parts.append(tools_str)
        
        # Add main text
        if text:
            parts.append(text)
        
        # Add streaming cursor
        if streaming:
            parts.append("▌")
        
        return "\n".join(parts) if parts else "🎩 *Thinking...*"
    
    async def _inject_message(self, role: str, content: str):
        """Inject a message into ChatEngine history."""
        def sync_inject():
            from app.core.chat_engine import get_chat_engine
            engine = get_chat_engine()
            engine.add_message(role, content)
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, sync_inject)
    
    async def _approve_trade(self, trade_id: int) -> str:
        """Approve a trade via ProposalManager."""
        def sync_approve():
            from flask import current_app
            from app.agents.proposals import ProposalManager
            
            with current_app.app_context():
                manager = ProposalManager()
                trade = manager.approve_proposal(trade_id)
                if trade:
                    return f"Executed {trade.action} {trade.symbol} @ ${trade.price:.2f}"
                return "Trade not found or already processed"
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_approve)
    
    async def _reject_trade(self, trade_id: int):
        """Reject a trade via ProposalManager."""
        def sync_reject():
            from flask import current_app
            from app.agents.proposals import ProposalManager
            
            with current_app.app_context():
                manager = ProposalManager()
                manager.reject_proposal(trade_id)
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, sync_reject)
    
    async def _get_settings(self) -> dict:
        """Get current settings from database."""
        def sync_get():
            from app import create_app
            app = create_app()
            with app.app_context():
                from app.models import Settings
                settings = Settings.get_settings()
                return {
                    'scan_interval': settings.scan_interval_minutes,
                    'trade_expiry': settings.trade_expiry_minutes,
                    'initial_balance': settings.initial_balance
                }
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_get)
    
    async def _update_setting(self, setting_name: str, value: int) -> dict:
        """Update a specific setting."""
        def sync_update():
            from app import create_app
            app = create_app()
            with app.app_context():
                from app.models import Settings
                from app.extensions import db
                settings = Settings.get_settings()
                
                if setting_name == 'scan_interval':
                    settings.scan_interval_minutes = value
                    # Reschedule scanner
                    try:
                        from app.core.scheduler_jobs import reschedule_scan
                        reschedule_scan(value)
                    except Exception as e:
                        print(f"[Settings] Could not reschedule: {e}")
                elif setting_name == 'trade_expiry':
                    settings.trade_expiry_minutes = value
                
                db.session.commit()
                return {
                    'scan_interval': settings.scan_interval_minutes,
                    'trade_expiry': settings.trade_expiry_minutes,
                    'initial_balance': settings.initial_balance
                }
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_update)
    
    async def _trigger_scan(self) -> str:
        """Manually trigger a market scan."""
        def sync_scan():
            from app import create_app
            app = create_app()
            with app.app_context():
                try:
                    from app.core.scheduler_jobs import run_market_scan
                    run_market_scan()
                    return "✅ Scan triggered! Check for new proposals."
                except Exception as e:
                    return f"❌ Scan failed: {str(e)}"
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_scan)
    
    async def _send_settings_menu(self, message_or_query):
        """Send settings menu with inline keyboard."""
        settings = await self._get_settings()
        
        text = (
            "⚙️ **Settings**\n\n"
            f"⏱️ **Scan Interval:** {settings['scan_interval']} min\n"
            f"⏳ **Trade Expiry:** {settings['trade_expiry']} min\n"
            f"💵 **Initial Balance:** ${settings['initial_balance']:,.0f}\n\n"
            "_Tap buttons to adjust:_"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("⏱️ Scan: ➖", callback_data="set_scan_down"),
                InlineKeyboardButton(f"{settings['scan_interval']}m", callback_data="noop"),
                InlineKeyboardButton("⏱️ Scan: ➕", callback_data="set_scan_up"),
            ],
            [
                InlineKeyboardButton("⏳ Expiry: ➖", callback_data="set_expiry_down"),
                InlineKeyboardButton(f"{settings['trade_expiry']}m", callback_data="noop"),
                InlineKeyboardButton("⏳ Expiry: ➕", callback_data="set_expiry_up"),
            ],
            [
                InlineKeyboardButton("🔍 Trigger Scan Now", callback_data="trigger_scan"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Handle both Message and CallbackQuery
        if hasattr(message_or_query, 'edit_text'):
            await message_or_query.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await message_or_query.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    def send_proposal_notification(self, message: str, trade_id: int):
        """
        Send a trade proposal notification with Approve/Reject buttons.
        Called from ProposalManager when a new proposal is created.
        """
        if not self.application or not self.allowed_user_ids:
            logger.warning("[Telegram] Cannot send notification - bot not initialized or no users")
            return
            
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{trade_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_{trade_id}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Schedule the async send in the bot's event loop
        async def send():
            for user_id in self.allowed_user_ids:
                try:
                    await self.application.bot.send_message(
                        chat_id=user_id,
                        text=message,
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"[Telegram] Failed to send to {user_id}: {e}")
        
        if self._loop:
            asyncio.run_coroutine_threadsafe(send(), self._loop)
    
    def run(self):
        """Start the bot (blocking)."""
        self.application = Application.builder().token(self.token).build()
        
        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("portfolio", self.portfolio_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("settings", self.settings_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        logger.info("[Telegram] Bot starting...")
        
        # Store the event loop for send_proposal_notification
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


def get_telegram_bot() -> Optional[TelegramBot]:
    """Get the global Telegram bot instance."""
    return _telegram_bot


def start_telegram_bot():
    """
    Initialize and start the Telegram bot.
    Called from run.py in a background thread.
    """
    global _telegram_bot
    
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.info("[Telegram] No TELEGRAM_BOT_TOKEN found, bot disabled")
        return
    
    # Parse allowed user IDs
    allowed_ids_str = os.environ.get('TELEGRAM_ALLOWED_USER_IDS', '')
    allowed_ids = []
    if allowed_ids_str:
        allowed_ids = [int(uid.strip()) for uid in allowed_ids_str.split(',') if uid.strip()]
    
    logger.info(f"[Telegram] Starting bot with {len(allowed_ids)} allowed users")
    
    _telegram_bot = TelegramBot(token, allowed_ids)
    _telegram_bot.run()
