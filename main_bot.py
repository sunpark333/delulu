# main_bot.py - Main Telegram Bot File
import asyncio
import logging
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes,
    CallbackQueryHandler
)
from news_processor import NewsProcessor
from channel_manager import ChannelManager
from auth_manager import AuthManager
from admin_commands import AdminCommands
from database import Database
from analytics import Analytics
from scheduler import NewsScheduler
from error_handler import setup_error_handler
import config

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NewsBot:
    def __init__(self):
        self.db = Database()
        self.news_processor = NewsProcessor()
        self.channel_manager = ChannelManager()
        self.auth_manager = AuthManager()
        self.admin_commands = AdminCommands()
        self.analytics = Analytics()
        self.scheduler = NewsScheduler()
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler"""
        user_id = update.effective_user.id
        username = update.effective_user.username
        
        # User ko database mein add karo
        self.db.add_user(user_id, username)
        
        welcome_text = """
🔥 **News AI Bot में आपका स्वागत है!** 🔥

📰 **क्या करता है यह बॉट:**
• आपकी भेजी गई news को AI से professional बनाता है
• Extra information add करता है
• आपके channel में auto-post करता है

🚀 **कैसे इस्तेमाल करें:**
1. मुझे कोई भी news भेजें
2. मैं उसे AI से improve करूंगा
3. Auto आपके channel में post हो जाएगी

📊 Commands:
/start - Bot शुरू करें
/help - Help देखें
/stats - Statistics देखें
/settings - Settings change करें

🔐 **Admin Commands:**
/admin - Admin panel (केवल authorized users)
"""
        
        keyboard = [
            [InlineKeyboardButton("📊 Stats", callback_data="stats")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
            [InlineKeyboardButton("❓ Help", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
        
        # Analytics update
        self.analytics.log_user_action(user_id, "start_command")

    async def process_news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Main news processing function"""
        user_id = update.effective_user.id
        
        # Check if user is authorized
        if not self.auth_manager.is_authorized(user_id):
            await update.message.reply_text("❌ आप authorized नहीं हैं। Admin से contact करें।")
            return
            
        original_news = update.message.text
        
        # Processing message भेजें
        processing_msg = await update.message.reply_text("🔄 News को AI से improve कर रहा हूं... कृपया wait करें।")
        
        try:
            # News को AI से process करें
            processed_news = await self.news_processor.enhance_news(original_news)
            
            # Channel में post करें
            post_result = await self.channel_manager.post_to_channel(processed_news)
            
            if post_result:
                # Database में save करें
                self.db.save_news_entry(user_id, original_news, processed_news)
                
                # Success message
                success_text = f"""
✅ **News successfully processed और post हो गई!**

📝 **Original Length:** {len(original_news)} characters
📝 **Improved Length:** {len(processed_news)} characters
📈 **Improvement:** {len(processed_news) - len(original_news)} characters added

🔗 **Channel Link:** {config.CHANNEL_LINK}
"""
                
                keyboard = [
                    [InlineKeyboardButton("📊 View Stats", callback_data="stats")],
                    [InlineKeyboardButton("🔄 Process Another", callback_data="process_another")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await processing_msg.edit_text(success_text, reply_markup=reply_markup, parse_mode='Markdown')
                
                # Analytics
                self.analytics.log_news_processed(user_id, len(original_news), len(processed_news))
                
            else:
                await processing_msg.edit_text("❌ Channel में post करने में error आई। Admin को contact करें।")
                
        except Exception as e:
            logger.error(f"Error processing news: {e}")
            await processing_msg.edit_text("❌ News process करने में error आई। कृपया बाद में try करें।")

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        if data == "stats":
            stats = self.analytics.get_user_stats(user_id)
            stats_text = f"""
📊 **आपकी Statistics:**

📰 Total News Processed: {stats['total_news']}
📈 Characters Added: {stats['total_improvement']}
🕒 Last Activity: {stats['last_activity']}
📅 Member Since: {stats['join_date']}

🏆 **आपका Rank:** #{stats['user_rank']} (Top {stats['percentile']}%)
"""
            await query.edit_message_text(stats_text, parse_mode='Markdown')
            
        elif data == "settings":
            settings_text = """
⚙️ **Settings:**

🌐 Language: Hindi (Default)
📊 Analytics: Enabled
🔔 Notifications: Enabled
🕒 Auto-post Time: Immediate

💡 Contact admin to change settings.
"""
            await query.edit_message_text(settings_text, parse_mode='Markdown')
            
        elif data == "help":
            help_text = """
❓ **Help Guide:**

📝 **News भेजने का तरीका:**
1. सिर्फ news text type करके भेजें
2. कोई command की जरूरत नहीं
3. Bot automatically process करेगा

🎯 **Best Results के लिए:**
• Clear और complete news भेजें
• Facts include करें
• Minimum 50 characters का news भेजें

📞 **Support:** @youradmin
"""
            await query.edit_message_text(help_text, parse_mode='Markdown')

    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin panel access"""
        user_id = update.effective_user.id
        
        if not self.auth_manager.is_admin(user_id):
            await update.message.reply_text("❌ आप admin नहीं हैं।")
            return
            
        await self.admin_commands.show_admin_panel(update, context)

    def run_bot(self):
        """Start the bot"""
        # Build application
        app = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()
        
        # Setup error handler
        setup_error_handler(app)
        
        # Add handlers
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("admin", self.admin_panel))
        app.add_handler(CallbackQueryHandler(self.button_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_news))
        
        # Start scheduler
        self.scheduler.start()
        
        logger.info("🚀 Bot started successfully!")
        
        # Run the bot
        app.run_polling()

if __name__ == "__main__":
    bot = NewsBot()
    bot.run_bot()