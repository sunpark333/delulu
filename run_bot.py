# run_bot.py - Bot Startup Script
#!/usr/bin/env python3
"""
Telegram News AI Bot
एक advanced Telegram bot जो news को AI से enhance करके channel में post करता है
"""

import os
import sys
import logging
from pathlib import Path

# Add current directory to Python path
sys.path.append(str(Path(__file__).parent))

def setup_logging():
    """Enhanced logging setup"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('bot.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def check_requirements():
    """Check if all required packages are installed"""
    required_packages = [
        'telegram', 'openai', 'schedule', 'psutil', 'dotenv'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("📦 Install करें: pip install python-telegram-bot openai schedule psutil python-dotenv")
        return False
    
    return True

def check_config():
    """Check if configuration is properly set"""
    try:
        import config
        
        # Check required settings
        required_settings = [
            'TELEGRAM_BOT_TOKEN',
            'OPENAI_API_KEY', 
            'CHANNEL_ID',
            'ADMIN_USER_IDS'
        ]
        
        missing_settings = []
        for setting in required_settings:
            value = getattr(config, setting, None)
            if not value or (isinstance(value, str) and 'YOUR_' in value.upper()):
                missing_settings.append(setting)
        
        if missing_settings:
            print(f"❌ Missing configuration: {', '.join(missing_settings)}")
            print("⚙️ कृपया config.py में proper values set करें")
            return False
        
        return True
        
    except ImportError:
        print("❌ config.py file नहीं मिली")
        return False

def create_directories():
    """Create required directories"""
    directories = ['backups', 'logs']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)

def main():
    """Main function to start the bot"""
    print("🤖 Starting Telegram News AI Bot...")
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Check configuration  
    if not check_config():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    try:
        # Import and start bot
        from main_bot import NewsBot
        
        logger.info("🚀 Initializing News Bot...")
        bot = NewsBot()
        
        logger.info("✅ Bot started successfully!")
        print("✅ Bot is running! Press Ctrl+C to stop.")
        
        # Start the bot
        bot.run_bot()
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
        print("\n🛑 Bot stopped successfully!")
        
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        print(f"💥 Error starting bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()