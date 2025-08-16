# config.py - Configuration File
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Telegram Bot Settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@yourchannelusername")
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/yourchannelusername")

# AI API Settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")
AI_MODEL = "gpt-3.5-turbo"  # या "gpt-4" if you have access

# Admin Settings
ADMIN_USER_IDS = [
    123456789,  # Your telegram user ID
    987654321,  # Another admin ID
]

# Database Settings
DATABASE_NAME = "news_bot.db"
BACKUP_INTERVAL = 24  # hours

# Rate Limiting
MAX_REQUESTS_PER_HOUR = 10
MAX_REQUESTS_PER_DAY = 50

# News Processing Settings
MIN_NEWS_LENGTH = 50
MAX_NEWS_LENGTH = 2000
AI_PROMPT_TEMPLATE = """
आपको एक news article दिया गया है। कृपया इसे निम्नलिखित तरीकों से improve करें:

1. Professional और engaging language में rewrite करें
2. Missing context या background information add करें  
3. Important facts और statistics add करें
4. Proper formatting के साथ present करें
5. Hindi और English दोनों में readable बनाएं

Original News:
{original_news}

Requirements:
- Professional tone maintain करें
- Factual accuracy ensure करें
- 200-500 words में limit रखें
- Emojis का sensible use करें
- Clear headlines और subheadings use करें

Enhanced News:
"""

# Scheduler Settings
AUTO_POST_TIMES = ["09:00", "14:00", "20:00"]  # Daily auto post times
TIMEZONE = "Asia/Kolkata"

# Error Handling
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Analytics Settings
ANALYTICS_ENABLED = True
DAILY_REPORT_TIME = "23:59"

# Backup Settings
BACKUP_ENABLED = True
BACKUP_PATH = "./backups/"
MAX_BACKUP_FILES = 7  # Keep last 7 backups

# Logging Settings
LOG_LEVEL = "INFO"
LOG_FILE = "bot.log"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB

# Feature Flags
ENABLE_CATEGORIES = True
ENABLE_SCHEDULING = True
ENABLE_ANALYTICS = True
ENABLE_MULTI_LANGUAGE = False

# News Categories
NEWS_CATEGORIES = {
    "🏛️": "Politics",
    "💰": "Business", 
    "⚽": "Sports",
    "🎬": "Entertainment",
    "🔬": "Technology",
    "🌍": "International",
    "🏥": "Health",
    "🎓": "Education",
    "🌦️": "Weather",
    "🚨": "Breaking"
}

# Response Messages
MESSAGES = {
    "unauthorized": "❌ आप इस bot को use करने के लिए authorized नहीं हैं। Admin से contact करें।",
    "processing": "🔄 आपकी news को AI से enhance कर रहा हूं... कृपया wait करें।",
    "success": "✅ News successfully processed और channel में post हो गई!",
    "error": "❌ कुछ error आई है। कृपया बाद में try करें।",
    "rate_limit": "⏰ आपने rate limit exceed कर दिया है। कुछ देर बाद try करें।",
    "too_short": f"📝 News कम से कम {MIN_NEWS_LENGTH} characters की होनी चाहिए।",
    "too_long": f"📝 News {MAX_NEWS_LENGTH} characters से ज्यादा नहीं होनी चाहिए।"
}

# Webhook Settings (if using webhook instead of polling)
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8443"))

# Security Settings
ALLOWED_UPDATES = ["message", "callback_query", "inline_query"]
API_TIMEOUT = 30  # seconds