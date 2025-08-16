# admin_commands.py - Admin Commands Module
import logging
from typing import Dict, Any, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from auth_manager import AuthManager
from database import Database
from analytics import Analytics
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AdminCommands:
    def __init__(self):
        self.auth_manager = AuthManager()
        self.db = Database()
        self.analytics = Analytics()
    
    async def show_admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin panel display करता है"""
        admin_text = """
🔐 **Admin Panel**

👨‍💼 **User Management:**
• View pending users
• Authorize/Revoke users
• Ban/Unban users
• View authorized users

📊 **Analytics:**
• Daily statistics
• User analytics
• Channel performance
• Bot health

⚙️ **Settings:**
• Bot configuration
• Channel settings
• Rate limits
• Backup management

📝 **Logs:**
• Admin logs
• Error logs
• User activity

Choose an option:
"""
        
        keyboard = [
            [
                InlineKeyboardButton("👥 Users", callback_data="admin_users"),
                InlineKeyboardButton("📊 Stats", callback_data="admin_stats")
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings"),
                InlineKeyboardButton("📝 Logs", callback_data="admin_logs")
            ],
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="admin_refresh"),
                InlineKeyboardButton("❌ Close", callback_data="admin_close")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                admin_text, 
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                admin_text, 
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    async def handle_admin_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin callback queries handle करता है"""
        query = update.callback_query
        data = query.data
        
        if data == "admin_users":
            await self.show_user_management(update, context)
        elif data == "admin_stats":
            await self.show_admin_stats(update, context)
        elif data == "admin_settings":
            await self.show_admin_settings(update, context)
        elif data == "admin_logs":
            await self.show_admin_logs(update, context)
        elif data.startswith("authorize_"):
            user_id = int(data.split("_")[1])
            await self.authorize_user_callback(update, context, user_id)
        elif data.startswith("ban_"):
            user_id = int(data.split("_")[1])
            await self.ban_user_callback(update, context, user_id)
    
    async def show_user_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """User management panel दिखाता है"""
        pending_users = self.auth_manager.get_pending_users()
        authorized_users = self.auth_manager.get_authorized_users()
        
        text = f"""
👥 **User Management**

📋 **Pending Users:** {len(pending_users)}
✅ **Authorized Users:** {len(authorized_users)}

**Recent Pending Users:**
"""
        
        for user in pending_users[:5]:
            username = user['username'] or "No username"
            join_date = user['join_date'][:10] if user['join_date'] else "Unknown"
            text += f"• {username} (ID: {user['user_id']}) - {join_date}\n"
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Authorize Users", callback_data="show_pending"),
                InlineKeyboardButton("👥 View All Users", callback_data="show_all_users")
            ],
            [
                InlineKeyboardButton("🚫 Banned Users", callback_data="show_banned"),
                InlineKeyboardButton("📊 User Stats", callback_data="user_stats")
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            text, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin statistics दिखाता है"""
        today_stats = self.db.get_daily_stats()
        yesterday_stats = self.db.get_daily_stats(
            (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        )
        
        # Channel stats
        from channel_manager import ChannelManager
        channel_manager = ChannelManager()
        channel_stats = await channel_manager.get_channel_stats()
        
        text = f"""
📊 **Bot Statistics**

**Today ({today_stats['date']}):**
👥 Active Users: {today_stats['active_users']}
📰 News Processed: {today_stats['total_news']}
📈 Avg Improvement: {today_stats['avg_improvement']} chars
📤 Posts: {today_stats['total_posts']}

**Yesterday:**
👥 Users: {yesterday_stats['active_users']}
📰 News: {yesterday_stats['total_news']}

**Channel Stats:**
📺 Channel: {channel_stats.get('channel_title', 'N/A')}
👥 Members: {channel_stats.get('member_count', 'N/A')}
📝 Total Posts: {channel_stats.get('total_posts', 'N/A')}

**Top Users Today:**
"""
        
        top_users = self.db.get_top_users(5)
        for i, user in enumerate(top_users, 1):
            username = user['username'] or f"User {user['user_id']}"
            text += f"{i}. {username} - {user['total_requests']} requests\n"
        
        keyboard = [
            [
                InlineKeyboardButton("📈 Daily Report", callback_data="daily_report"),
                InlineKeyboardButton("📊 Weekly Stats", callback_data="weekly_stats")
            ],
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats"),
                InlineKeyboardButton("🔙 Back", callback_data="admin_back")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            text, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_admin_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin settings panel दिखाता है"""
        text = """
⚙️ **Bot Settings**

**Current Configuration:**
🤖 AI Model: GPT-3.5 Turbo
⏱️ Rate Limit: 10/hour, 50/day
📝 Min News Length: 50 chars
📝 Max News Length: 2000 chars
🔄 Auto Backup: Enabled
📊 Analytics: Enabled

**Channel Settings:**
📺 Channel: @yourchannel
🔗 Auto Post: Enabled
⏰ Post Times: 9:00, 14:00, 20:00

**Actions Available:**
"""
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Update Limits", callback_data="update_limits"),
                InlineKeyboardButton("📺 Channel Config", callback_data="channel_config")
            ],
            [
                InlineKeyboardButton("💾 Backup Now", callback_data="backup_now"),
                InlineKeyboardButton("🧹 Cleanup Data", callback_data="cleanup_data")
            ],
            [
                InlineKeyboardButton("🔧 AI Settings", callback_data="ai_settings"),
                InlineKeyboardButton("🔙 Back", callback_data="admin_back")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            text, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_admin_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin logs दिखाता है"""
        logs = self.auth_manager.get_admin_logs(10)
        
        text = "📝 **Recent Admin Logs:**\n\n"
        
        for log in logs:
            admin_name = log['admin_username'] or f"Admin {log['admin_id']}"
            target_name = log['target_username'] or f"User {log['target_user_id']}"
            timestamp = log['timestamp'][:16] if log['timestamp'] else "Unknown"
            
            text += f"⏰ {timestamp}\n"
            text += f"👨‍💼 {admin_name}\n"
            text += f"🎯 Action: {log['action']}\n"
            text += f"👤 Target: {target_name}\n"
            text += f"📝 Details: {log['details']}\n\n"
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="admin_logs"),
                InlineKeyboardButton("📊 Error Logs", callback_data="error_logs")
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            text, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def authorize_user_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """User authorization callback"""
        admin_id = update.callback_query.from_user.id
        
        if self.auth_manager.authorize_user(user_id, admin_id):
            text = f"✅ User {user_id} has been authorized successfully!"
        else:
            text = f"❌ Failed to authorize user {user_id}"
        
        await update.callback_query.answer(text)
        # Refresh the user management panel
        await self.show_user_management(update, context)
    
    async def ban_user_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """User ban callback"""
        admin_id = update.callback_query.from_user.id
        
        if self.auth_manager.ban_user(user_id, admin_id, "Banned by admin"):
            text = f"🚫 User {user_id} has been banned!"
        else:
            text = f"❌ Failed to ban user {user_id}"
        
        await update.callback_query.answer(text)
        await self.show_user_management(update, context)
    
    async def broadcast_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """सभी users को message broadcast करता है"""
        if not self.auth_manager.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Only admins can use this command.")
            return
        
        if not context.args:
            await update.message.reply_text("📢 Usage: /broadcast <message>")
            return
        
        message = " ".join(context.args)
        
        from channel_manager import ChannelManager
        channel_manager = ChannelManager()
        result = await channel_manager.broadcast_to_subscribers(message)
        
        response = f"""
📢 **Broadcast Results:**

✅ Successfully sent: {result['total_sent']}
❌ Failed: {result['failed']}
👥 Total subscribers: {result['total_subscribers']}
"""
        
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def get_user_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """किसी specific user की information देता है"""
        if not self.auth_manager.is_admin(update.effective_user.id):
            return
        
        if not context.args:
            await update.message.reply_text("👤 Usage: /userinfo <user_id>")
            return
        
        try:
            user_id = int(context.args[0])
            permissions = self.auth_manager.get_user_permissions(user_id)
            stats = self.db.get_user_stats(user_id)
            
            text = f"""
👤 **User Information: {user_id}**

🔐 **Permissions:**
• Authorized: {"✅" if permissions['is_authorized'] else "❌"}
• Admin: {"✅" if permissions['is_admin'] else "❌"}
• Active: {"✅" if permissions['is_active'] else "❌"}
• Can Post: {"✅" if permissions['can_post'] else "❌"}

📊 **Statistics:**
• Total News: {stats.get('total_news', 0)}
• Characters Added: {stats.get('total_improvement', 0)}
• Join Date: {stats.get('join_date', 'Unknown')}
• Last Activity: {stats.get('last_activity', 'Unknown')}
• Rank: #{stats.get('user_rank', 'N/A')}
"""
            
            await update.message.reply_text(text, parse_mode='Markdown')
            
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def backup_database(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Database backup manually trigger करता है"""
        if not self.auth_manager.is_admin(update.effective_user.id):
            return
        
        if self.db.backup_database(config.BACKUP_PATH):
            await update.message.reply_text("💾 Database backup created successfully!")
        else:
            await update.message.reply_text("❌ Backup failed. Check logs for details.")
    
    async def cleanup_old_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """पुराना data cleanup करता है"""
        if not self.auth_manager.is_admin(update.effective_user.id):
            return
        
        days = 30
        if context.args and context.args[0].isdigit():
            days = int(context.args[0])
        
        self.db.cleanup_old_data(days)
        await update.message.reply_text(f"🧹 Cleaned up data older than {days} days.")
    
    async def get_system_health(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """System health check करता है"""
        if not self.auth_manager.is_admin(update.effective_user.id):
            return
        
        import psutil
        import os
        
        # System metrics
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Database size
        db_size = os.path.getsize(config.DATABASE_NAME) / (1024 * 1024)  # MB
        
        text = f"""
🏥 **System Health Check**

🖥️ **System Resources:**
• CPU Usage: {cpu_percent}%
• Memory: {memory.percent}% ({memory.available // (1024**3)} GB free)
• Disk: {disk.percent}% ({disk.free // (1024**3)} GB free)

💾 **Database:**
• Size: {db_size:.2f} MB
• Status: {"✅ Healthy" if db_size < 100 else "⚠️ Large"}

🤖 **Bot Status:**
• Active: ✅
• Uptime: {self._get_uptime()}
• Errors: {self._get_error_count()}
"""
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    def _get_uptime(self) -> str:
        """Bot uptime calculate करता है"""
        # This would need to be implemented based on when bot started
        return "Unknown"
    
    def _get_error_count(self) -> int:
        """Recent error count return करता है"""
        # This would need to read from error logs
        return 0