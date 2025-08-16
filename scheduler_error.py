# scheduler.py - News Scheduling Module
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import schedule
import threading
from database import Database
from channel_manager import ChannelManager
import config

logger = logging.getLogger(__name__)

class NewsScheduler:
    def __init__(self):
        self.db = Database()
        self.channel_manager = ChannelManager()
        self.running = False
        self.scheduler_thread = None
    
    def start(self):
        """Scheduler start करता है"""
        if not self.running:
            self.running = True
            
            # Schedule daily auto posts
            for time_str in config.AUTO_POST_TIMES:
                schedule.every().day.at(time_str).do(self._run_async, self.auto_post_news)
            
            # Schedule daily analytics report
            if config.ANALYTICS_ENABLED:
                schedule.every().day.at(config.DAILY_REPORT_TIME).do(
                    self._run_async, self.send_daily_report
                )
            
            # Schedule database cleanup (weekly)
            schedule.every().monday.at("02:00").do(self._cleanup_database)
            
            # Schedule backup (daily)
            if config.BACKUP_ENABLED:
                schedule.every().day.at("01:00").do(self._backup_database)
            
            # Start scheduler thread
            self.scheduler_thread = threading.Thread(target=self._run_scheduler)
            self.scheduler_thread.daemon = True
            self.scheduler_thread.start()
            
            logger.info("News scheduler started successfully")
    
    def stop(self):
        """Scheduler stop करता है"""
        self.running = False
        schedule.clear()
        logger.info("News scheduler stopped")
    
    def _run_scheduler(self):
        """Scheduler का main loop"""
        while self.running:
            schedule.run_pending()
            threading.Event().wait(1)
    
    def _run_async(self, coro):
        """Async function को sync context में run करता है"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(coro())
            loop.close()
        except Exception as e:
            logger.error(f"Error running scheduled task: {e}")
    
    async def auto_post_news(self):
        """Scheduled news posts करता है"""
        try:
            # Get pending scheduled posts
            with self.db._get_connection() as conn:
                posts = conn.execute('''
                    SELECT * FROM scheduled_posts 
                    WHERE status = 'pending' 
                    AND datetime(scheduled_time) <= datetime('now')
                    ORDER BY scheduled_time ASC
                    LIMIT 5
                ''').fetchall()
            
            for post in posts:
                try:
                    result = await self.channel_manager.post_to_channel(post['content'])
                    
                    if result['success']:
                        # Update status
                        with self.db._get_connection() as conn:
                            conn.execute('''
                                UPDATE scheduled_posts 
                                SET status = 'posted', posted_at = ?, message_id = ?
                                WHERE id = ?
                            ''', (datetime.now(), result['message_id'], post['id']))
                            conn.commit()
                        
                        logger.info(f"Scheduled post {post['id']} posted successfully")
                    else:
                        logger.error(f"Failed to post scheduled content {post['id']}")
                
                except Exception as e:
                    logger.error(f"Error posting scheduled content {post['id']}: {e}")
                    
                # Rate limiting
                await asyncio.sleep(5)
                
        except Exception as e:
            logger.error(f"Error in auto_post_news: {e}")
    
    async def send_daily_report(self):
        """Daily analytics report भेजता है"""
        try:
            from analytics import Analytics
            analytics = Analytics()
            
            # Get daily stats
            today_stats = self.db.get_daily_stats()
            yesterday_stats = self.db.get_daily_stats(
                (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            )
            
            report_text = f"""
📊 **Daily Bot Report - {today_stats['date']}**

**Today's Performance:**
👥 Active Users: {today_stats['active_users']}
📰 News Processed: {today_stats['total_news']}
📈 Avg Improvement: {today_stats['avg_improvement']} chars
📤 Posts Created: {today_stats['total_posts']}

**Comparison with Yesterday:**
👥 Users: {today_stats['active_users']} vs {yesterday_stats['active_users']} ({self._calculate_change(today_stats['active_users'], yesterday_stats['active_users'])})
📰 News: {today_stats['total_news']} vs {yesterday_stats['total_news']} ({self._calculate_change(today_stats['total_news'], yesterday_stats['total_news'])})

**System Status:** ✅ All systems operational

Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            # Send to admins
            for admin_id in config.ADMIN_USER_IDS:
                try:
                    await self.channel_manager.bot.send_message(
                        chat_id=admin_id,
                        text=report_text,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Failed to send daily report to admin {admin_id}: {e}")
            
            logger.info("Daily report sent to admins")
            
        except Exception as e:
            logger.error(f"Error sending daily report: {e}")
    
    def _calculate_change(self, current: int, previous: int) -> str:
        """Change percentage calculate करता है"""
        if previous == 0:
            return "+100%" if current > 0 else "0%"
        
        change = ((current - previous) / previous) * 100
        sign = "+" if change > 0 else ""
        return f"{sign}{change:.1f}%"
    
    def _cleanup_database(self):
        """Database cleanup करता है"""
        try:
            self.db.cleanup_old_data(30)  # 30 days old data
            logger.info("Database cleanup completed")
        except Exception as e:
            logger.error(f"Database cleanup failed: {e}")
    
    def _backup_database(self):
        """Database backup करता है"""
        try:
            if self.db.backup_database(config.BACKUP_PATH):
                logger.info("Database backup completed")
            else:
                logger.error("Database backup failed")
        except Exception as e:
            logger.error(f"Database backup error: {e}")
    
    def schedule_post(self, content: str, scheduled_time: datetime) -> bool:
        """नया post schedule करता है"""
        try:
            with self.db._get_connection() as conn:
                conn.execute('''
                    INSERT INTO scheduled_posts (content, scheduled_time, status)
                    VALUES (?, ?, 'pending')
                ''', (content, scheduled_time))
                conn.commit()
            
            logger.info(f"Post scheduled for {scheduled_time}")
            return True
            
        except Exception as e:
            logger.error(f"Error scheduling post: {e}")
            return False
    
    def get_scheduled_posts(self, status: str = None) -> List[Dict[str, Any]]:
        """Scheduled posts की list return करता है"""
        try:
            with self.db._get_connection() as conn:
                if status:
                    posts = conn.execute('''
                        SELECT * FROM scheduled_posts 
                        WHERE status = ?
                        ORDER BY scheduled_time ASC
                    ''', (status,)).fetchall()
                else:
                    posts = conn.execute('''
                        SELECT * FROM scheduled_posts 
                        ORDER BY scheduled_time DESC
                    ''').fetchall()
                
                return [dict(post) for post in posts]
                
        except Exception as e:
            logger.error(f"Error getting scheduled posts: {e}")
            return []
    
    def cancel_scheduled_post(self, post_id: int) -> bool:
        """Scheduled post को cancel करता है"""
        try:
            with self.db._get_connection() as conn:
                conn.execute('''
                    UPDATE scheduled_posts 
                    SET status = 'cancelled'
                    WHERE id = ? AND status = 'pending'
                ''', (post_id,))
                conn.commit()
                
                if conn.total_changes > 0:
                    logger.info(f"Scheduled post {post_id} cancelled")
                    return True
                else:
                    logger.warning(f"Could not cancel post {post_id} - not found or already processed")
                    return False
                    
        except Exception as e:
            logger.error(f"Error cancelling scheduled post {post_id}: {e}")
            return False

# error_handler.py - Error Handling Module
import logging
import traceback
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, Application
import config

logger = logging.getLogger(__name__)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global error handler"""
    try:
        # Log the error
        logger.error(msg="Exception while handling an update:", exc_info=context.error)
        
        # Get traceback
        tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
        tb_string = ''.join(tb_list)
        
        # Prepare error message
        error_message = f"""
🚨 **Bot Error Occurred**

**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Error Type:** {type(context.error).__name__}
**Error Message:** {str(context.error)}

**Update Info:**
{update if update else 'No update available'}

**Traceback:**
```
{tb_string[-1000:]}  # Last 1000 chars
```
"""
        
        # Send error to admins
        for admin_id in config.ADMIN_USER_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=error_message,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send error message to admin {admin_id}: {e}")
        
        # Send user-friendly message if possible
        if update and hasattr(update, 'effective_chat') and update.effective_chat:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ कुछ technical error आई है। Admin को notify कर दिया गया है। कृपया बाद में try करें।"
                )
            except Exception as e:
                logger.error(f"Failed to send error message to user: {e}")
                
    except Exception as e:
        logger.error(f"Error in error handler: {e}")

def setup_error_handler(application: Application) -> None:
    """Error handler को application में setup करता है"""
    application.add_error_handler(error_handler)
    logger.info("Error handler setup completed")

# requirements.txt content
REQUIREMENTS_TXT = """
python-telegram-bot==20.7
openai==1.3.0
python-dotenv==1.0.0
schedule==1.2.0
psutil==5.9.6
asyncio==3.4.3
sqlite3
logging
datetime
threading
typing
"""

# .env template
ENV_TEMPLATE = """
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
CHANNEL_ID=@yourchannelusername
CHANNEL_LINK=https://t.me/yourchannelusername

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Webhook Configuration (if not using polling)
WEBHOOK_URL=
WEBHOOK_PORT=8443
"""

# Installation और Setup Instructions
SETUP_INSTRUCTIONS = """
🚀 **Telegram News Bot Setup Instructions**

## 1. Prerequisites Install करें:
```bash
pip install python-telegram-bot openai python-dotenv schedule psutil
```

## 2. Environment Variables Setup करें:
- `.env` file बनाएं और अपनी API keys डालें:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
CHANNEL_ID=@yourchannelusername  
OPENAI_API_KEY=your_openai_api_key_here
```

## 3. Configuration Update करें:
- `config.py` में अपने admin user IDs add करें
- Channel settings adjust करें
- Rate limits set करें

## 4. Bot Run करें:
```bash
python main_bot.py
```

## 5. Bot को Channel का Admin बनाएं:
- अपने Telegram channel में जाएं
- Bot को administrator बनाएं
- "Post messages" permission दें

## 6. Testing:
- Bot को `/start` message भेजें
- कोई news text भेजकर test करें
- Admin panel `/admin` से check करें

## Features:
✅ AI-powered news enhancement
✅ Automatic channel posting
✅ User authentication
✅ Rate limiting
✅ Analytics & statistics
✅ Admin panel
✅ Scheduled posts
✅ Error handling & logging
✅ Database backup
✅ Multi-category support

## Troubleshooting:
- Bot token correct है?
- OpenAI API key valid है?
- Channel ID correct format में है? (@username)
- Bot को channel में admin permissions हैं?
- Database file writable है?

## Support:
किसी भी issue के लिए logs check करें: `bot.log`
"""