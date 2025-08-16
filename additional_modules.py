# rate_limiter.py - Rate Limiting Module
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
from database import Database
import config

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self):
        self.db = Database()
    
    def check_rate_limit(self, user_id: int) -> bool:
        """
        User की rate limit check करता है
        Returns True if user can make request, False if rate limited
        """
        try:
            limits = self.db.check_rate_limit(user_id)
            
            # Check if user exceeds limits
            if not limits["hourly_ok"]:
                logger.warning(f"User {user_id} exceeded hourly rate limit")
                return False
            
            if not limits["daily_ok"]:
                logger.warning(f"User {user_id} exceeded daily rate limit")
                return False
            
            # Update counters
            self.db.update_rate_limit(user_id)
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit for {user_id}: {e}")
            return True  # Allow request if error occurs
    
    def get_user_limits(self, user_id: int) -> Dict[str, Any]:
        """User की current rate limit status return करता है"""
        try:
            with self.db._get_connection() as conn:
                limits = conn.execute('''
                    SELECT * FROM rate_limits WHERE user_id = ?
                ''', (user_id,)).fetchone()
                
                if not limits:
                    return {
                        "hourly_remaining": config.MAX_REQUESTS_PER_HOUR,
                        "daily_remaining": config.MAX_REQUESTS_PER_DAY,
                        "hourly_reset": "1 hour",
                        "daily_reset": "24 hours"
                    }
                
                now = datetime.now()
                hour_reset = datetime.fromisoformat(limits['last_hour_reset'])
                day_reset = datetime.fromisoformat(limits['last_day_reset'])
                
                # Calculate remaining requests
                hourly_remaining = max(0, config.MAX_REQUESTS_PER_HOUR - limits['hourly_count'])
                daily_remaining = max(0, config.MAX_REQUESTS_PER_DAY - limits['daily_count'])
                
                # Calculate reset times
                hour_reset_time = (hour_reset + timedelta(hours=1) - now).total_seconds()
                day_reset_time = (day_reset + timedelta(days=1) - now).total_seconds()
                
                return {
                    "hourly_remaining": hourly_remaining,
                    "daily_remaining": daily_remaining,
                    "hourly_reset": f"{int(hour_reset_time // 60)} minutes" if hour_reset_time > 0 else "Now",
                    "daily_reset": f"{int(day_reset_time // 3600)} hours" if day_reset_time > 0 else "Now"
                }
                
        except Exception as e:
            logger.error(f"Error getting user limits for {user_id}: {e}")
            return {}

# categorizer.py - News Categorization Module
import re
import logging
from typing import Dict, List
import config

logger = logging.getLogger(__name__)

class NewsCategori:
    def __init__(self):
        self.category_keywords = {
            "🏛️ Politics": [
                "politics", "राजनीति", "election", "चुनाव", "minister", "मंत्री", 
                "party", "पार्टी", "government", "सरकार", "parliament", "संसद",
                "modi", "मोदी", "congress", "कांग्रेस", "bjp", "योगी", "yogi"
            ],
            "💰 Business": [
                "business", "व्यापार", "market", "बाजार", "economy", "अर्थव्यवस्था",
                "rupee", "रुपया", "stock", "शेयर", "company", "कंपनी", "profit",
                "money", "पैसा", "investment", "निवेश", "bank", "बैंक"
            ],
            "⚽ Sports": [
                "cricket", "क्रिकेट", "football", "फुटबॉल", "sports", "खेल",
                "match", "मैच", "player", "खिलाड़ी", "team", "टीम", "olympics",
                "kohli", "कोहली", "dhoni", "धोनी", "fifa", "ipl"
            ],
            "🎬 Entertainment": [
                "bollywood", "बॉलीवूड", "actor", "अभिनेता", "actress", "अभिनेत्री",
                "movie", "फिल्म", "cinema", "सिनेमा", "tv", "टीवी", "celebrity",
                "shah rukh", "शाहरुख", "salman", "सलमान", "aamir", "आमिर"
            ],
            "🔬 Technology": [
                "technology", "तकनीक", "tech", "टेक", "smartphone", "स्मार्टफोन",
                "computer", "कंप्यूटर", "internet", "इंटरनेट", "ai", "artificial",
                "google", "गूगल", "apple", "एप्पल", "microsoft", "माइक्रोसॉफ्ट"
            ],
            "🌍 International": [
                "america", "अमेरिका", "china", "चीन", "pakistan", "पाकिस्तान",
                "russia", "रूस", "international", "अंतर्राष्ट्रीय", "world", "विश्व",
                "ukraine", "यूक्रेन", "biden", "बाइडेन", "putin", "पुतिन"
            ],
            "🏥 Health": [
                "health", "स्वास्थ्य", "hospital", "अस्पताल", "doctor", "डॉक्टर",
                "medicine", "दवा", "covid", "कोविड", "vaccine", "वैक्सीन",
                "disease", "बीमारी", "treatment", "इलाज", "medical", "मेडिकल"
            ],
            "🎓 Education": [
                "education", "शिक्षा", "school", "स्कूल", "college", "कॉलेज",
                "university", "विश्वविद्यालय", "student", "छात्र", "exam", "परीक्षा",
                "neet", "नीट", "jee", "जेईई", "upsc", "यूपीएससी"
            ],
            "🌦️ Weather": [
                "weather", "मौसम", "rain", "बारिश", "temperature", "तापमान",
                "cyclone", "चक्रवात", "flood", "बाढ़", "drought", "सूखा",
                "monsoon", "मानसून", "heat", "गर्मी", "cold", "ठंड"
            ],
            "🚨 Breaking": [
                "breaking", "ब्रेकिंग", "urgent", "अर्जेंट", "alert", "अलर्ट",
                "emergency", "आपातकाल", "accident", "दुर्घटना", "fire", "आग",
                "crime", "अपराध", "murder", "हत्या", "robbery", "लूट"
            ]
        }
    
    def detect_category(self, news_text: str) -> str:
        """News text का category detect करता है"""
        try:
            news_lower = news_text.lower()
            category_scores = {}
            
            for category, keywords in self.category_keywords.items():
                score = 0
                for keyword in keywords:
                    if keyword.lower() in news_lower:
                        score += 1
                category_scores[category] = score
            
            # Highest score वाला category return करें
            if category_scores and max(category_scores.values()) > 0:
                best_category = max(category_scores, key=category_scores.get)
                logger.info(f"Detected category: {best_category}")
                return best_category
            
            # Default category
            return "🔔 General"
            
        except Exception as e:
            logger.error(f"Error detecting category: {e}")
            return "🔔 General"
    
    def get_category_stats(self) -> Dict[str, int]:
        """सभी categories की statistics return करता है"""
        try:
            from database import Database
            db = Database()
            
            with db._get_connection() as conn:
                stats = conn.execute('''
                    SELECT category, COUNT(*) as count 
                    FROM news_entries 
                    WHERE category IS NOT NULL 
                    GROUP BY category
                    ORDER BY count DESC
                ''').fetchall()
                
                return {stat['category']: stat['count'] for stat in stats}
                
        except Exception as e:
            logger.error(f"Error getting category stats: {e}")
            return {}

# analytics.py - Analytics Module
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from database import Database
import config

logger = logging.getLogger(__name__)

class Analytics:
    def __init__(self):
        self.db = Database()
    
    def log_user_action(self, user_id: int, action_type: str, action_data: str = None):
        """User action को log करता है"""
        try:
            with self.db._get_connection() as conn:
                conn.execute('''
                    INSERT INTO analytics (user_id, action_type, action_data)
                    VALUES (?, ?, ?)
                ''', (user_id, action_type, action_data))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error logging user action: {e}")
    
    def log_news_processed(self, user_id: int, original_length: int, enhanced_length: int):
        """News processing को log करता है"""
        improvement = enhanced_length - original_length
        action_data = f"original:{original_length},enhanced:{enhanced_length},improvement:{improvement}"
        self.log_user_action(user_id, "news_processed", action_data)
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """User की detailed statistics return करता है"""
        return self.db.get_user_stats(user_id)
    
    def get_daily_analytics(self, date: str = None) -> Dict[str, Any]:
        """Daily analytics return करता है"""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            with self.db._get_connection() as conn:
                # User actions
                actions = conn.execute('''
                    SELECT action_type, COUNT(*) as count
                    FROM analytics
                    WHERE DATE(timestamp) = ?
                    GROUP BY action_type
                ''', (date,)).fetchall()
                
                # Top users
                top_users = conn.execute('''
                    SELECT user_id, COUNT(*) as actions
                    FROM analytics
                    WHERE DATE(timestamp) = ?
                    GROUP BY user_id
                    ORDER BY actions DESC
                    LIMIT 5
                ''', (date,)).fetchall()
                
                return {
                    "date": date,
                    "actions": {action['action_type']: action['count'] for action in actions},
                    "top_users": [dict(user) for user in top_users]
                }
                
        except Exception as e:
            logger.error(f"Error getting daily analytics: {e}")
            return {"date": date, "actions": {}, "top_users": []}
    
    def get_weekly_report(self) -> Dict[str, Any]:
        """Weekly analytics report generate करता है"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        try:
            daily_stats = []
            for i in range(7):
                date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
                stats = self.db.get_daily_stats(date)
                daily_stats.append(stats)
            
            # Weekly totals
            total_users = sum(day['active_users'] for day in daily_stats)
            total_news = sum(day['total_news'] for day in daily_stats)
            total_posts = sum(day['total_posts'] for day in daily_stats)
            
            return {
                "week_start": start_date.strftime('%Y-%m-%d'),
                "week_end": end_date.strftime('%Y-%m-%d'),
                "daily_stats": daily_stats,
                "totals": {
                    "active_users": total_users,
                    "news_processed": total_news,
                    "posts_created": total_posts
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating weekly report: {e}")
            return {}