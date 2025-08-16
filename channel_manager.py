# channel_manager.py - Channel Management Module
import logging
from typing import Optional, Dict, Any
from telegram import Bot
from telegram.error import TelegramError
import config
from database import Database
import asyncio

logger = logging.getLogger(__name__)

class ChannelManager:
    def __init__(self):
        self.bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
        self.db = Database()
        
    async def post_to_channel(self, content: str, parse_mode: str = 'Markdown') -> Dict[str, Any]:
        """
        Channel में news post करता है
        Returns: Dict with success status and message details
        """
        try:
            # Content validation
            if not self._validate_content(content):
                raise ValueError("Invalid content for posting")
            
            # Post to main channel
            message = await self.bot.send_message(
                chat_id=config.CHANNEL_ID,
                text=content,
                parse_mode=parse_mode,
                disable_web_page_preview=False
            )
            
            # Save post details to database
            post_data = {
                "message_id": message.message_id,
                "chat_id": message.chat.id,
                "content": content,
                "post_time": message.date,
                "success": True
            }
            
            self.db.save_channel_post(post_data)
            
            logger.info(f"News posted successfully to channel. Message ID: {message.message_id}")
            
            return {
                "success": True,
                "message_id": message.message_id,
                "post_url": f"https://t.me/{config.CHANNEL_ID.replace('@', '')}/{message.message_id}",
                "post_time": message.date
            }
            
        except TelegramError as e:
            logger.error(f"Telegram error while posting: {e}")
            return {
                "success": False,
                "error": f"Telegram error: {str(e)}",
                "error_type": "telegram_error"
            }
        except Exception as e:
            logger.error(f"General error while posting: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "general_error"
            }
    
    async def schedule_post(self, content: str, scheduled_time: str) -> Dict[str, Any]:
        """
        Scheduled post के लिए content save करता है
        """
        try:
            schedule_data = {
                "content": content,
                "scheduled_time": scheduled_time,
                "status": "pending",
                "created_at": datetime.now()
            }
            
            schedule_id = self.db.save_scheduled_post(schedule_data)
            
            return {
                "success": True,
                "schedule_id": schedule_id,
                "scheduled_time": scheduled_time
            }
            
        except Exception as e:
            logger.error(f"Error scheduling post: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def edit_channel_post(self, message_id: int, new_content: str) -> bool:
        """
        Channel post को edit करता है
        """
        try:
            await self.bot.edit_message_text(
                chat_id=config.CHANNEL_ID,
                message_id=message_id,
                text=new_content,
                parse_mode='Markdown'
            )
            
            # Database में update करें
            self.db.update_channel_post(message_id, new_content)
            
            logger.info(f"Post {message_id} edited successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error editing post {message_id}: {e}")
            return False
    
    async def delete_channel_post(self, message_id: int) -> bool:
        """
        Channel से post delete करता है
        """
        try:
            await self.bot.delete_message(
                chat_id=config.CHANNEL_ID,
                message_id=message_id
            )
            
            # Database में status update करें
            self.db.mark_post_deleted(message_id)
            
            logger.info(f"Post {message_id} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting post {message_id}: {e}")
            return False
    
    async def get_channel_stats(self) -> Dict[str, Any]:
        """
        Channel की statistics return करता है
        """
        try:
            chat = await self.bot.get_chat(config.CHANNEL_ID)
            
            stats = {
                "channel_title": chat.title,
                "member_count": await self.bot.get_chat_member_count(config.CHANNEL_ID),
                "total_posts": self.db.get_total_posts_count(),
                "posts_today": self.db.get_posts_count_today(),
                "last_post_time": self.db.get_last_post_time()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting channel stats: {e}")
            return {"error": str(e)}
    
    async def pin_message(self, message_id: int) -> bool:
        """
        Message को channel में pin करता है
        """
        try:
            await self.bot.pin_chat_message(
                chat_id=config.CHANNEL_ID,
                message_id=message_id,
                disable_notification=True
            )
            
            logger.info(f"Message {message_id} pinned successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error pinning message {message_id}: {e}")
            return False
    
    async def send_poll_to_channel(self, question: str, options: list) -> Dict[str, Any]:
        """
        Channel में poll भेजता है
        """
        try:
            message = await self.bot.send_poll(
                chat_id=config.CHANNEL_ID,
                question=question,
                options=options,
                is_anonymous=True,
                allows_multiple_answers=False
            )
            
            return {
                "success": True,
                "message_id": message.message_id,
                "poll_id": message.poll.id
            }
            
        except Exception as e:
            logger.error(f"Error sending poll: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _validate_content(self, content: str) -> bool:
        """
        Post content को validate करता है
        """
        if not content or not content.strip():
            return False
        if len(content) > 4096:  # Telegram message limit
            return False
        return True
    
    async def send_media_post(self, content: str, media_url: str, media_type: str = "photo") -> Dict[str, Any]:
        """
        Media के साथ post भेजता है
        """
        try:
            if media_type == "photo":
                message = await self.bot.send_photo(
                    chat_id=config.CHANNEL_ID,
                    photo=media_url,
                    caption=content,
                    parse_mode='Markdown'
                )
            elif media_type == "video":
                message = await self.bot.send_video(
                    chat_id=config.CHANNEL_ID,
                    video=media_url,
                    caption=content,
                    parse_mode='Markdown'
                )
            
            return {
                "success": True,
                "message_id": message.message_id,
                "media_type": media_type
            }
            
        except Exception as e:
            logger.error(f"Error sending media post: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def broadcast_to_subscribers(self, content: str) -> Dict[str, Any]:
        """
        Subscribers को direct message भेजता है
        """
        subscribers = self.db.get_active_subscribers()
        success_count = 0
        failed_count = 0
        
        for subscriber_id in subscribers:
            try:
                await self.bot.send_message(
                    chat_id=subscriber_id,
                    text=content,
                    parse_mode='Markdown'
                )
                success_count += 1
                await asyncio.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Failed to send to {subscriber_id}: {e}")
                failed_count += 1
        
        return {
            "total_sent": success_count,
            "failed": failed_count,
            "total_subscribers": len(subscribers)
        }