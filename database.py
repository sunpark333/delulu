# database.py - Database Management Module
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import config
import threading

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.db_name = config.DATABASE_NAME
        self.lock = threading.Lock()
        self._create_tables()
    
    def _get_connection(self):
        """Database connection बनाता है"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _create_tables(self):
        """सभी required tables बनाता है"""
        with self._get_connection() as conn:
            # Users table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    is_authorized BOOLEAN DEFAULT FALSE,
                    is_admin BOOLEAN DEFAULT FALSE,
                    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_requests INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')
            
            # News entries table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS news_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    original_news TEXT NOT NULL,
                    enhanced_news TEXT NOT NULL,
                    category TEXT,
                    original_length INTEGER,
                    enhanced_length INTEGER,
                    processing_time REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Channel posts table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS channel_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER UNIQUE,
                    chat_id TEXT,
                    content TEXT NOT NULL,
                    category TEXT,
                    post_time TIMESTAMP,
                    is_deleted BOOLEAN DEFAULT FALSE,
                    views INTEGER DEFAULT 0,
                    reactions INTEGER DEFAULT 0
                )
            ''')
            
            # Rate limiting table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS rate_limits (
                    user_id INTEGER PRIMARY KEY,
                    hourly_count INTEGER DEFAULT 0,
                    daily_count INTEGER DEFAULT 0,
                    last_hour_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_day_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Scheduled posts table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS scheduled_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    scheduled_time TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    posted_at TIMESTAMP,
                    message_id INTEGER
                )
            ''')
            
            # Analytics table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action_type TEXT NOT NULL,
                    action_data TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Admin logs table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS admin_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    action TEXT NOT NULL,
                    target_user_id INTEGER,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            logger.info("Database tables created successfully")
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """नया user add करता है या existing को update करता है"""
        with self.lock:
            with self._get_connection() as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO users 
                    (user_id, username, first_name, last_name, last_activity)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, username, first_name, last_name, datetime.now()))
                conn.commit()
    
    def save_news_entry(self, user_id: int, original_news: str, enhanced_news: str, 
                       category: str = None, processing_time: float = None):
        """News entry को database में save करता है"""
        with self.lock:
            with self._get_connection() as conn:
                conn.execute('''
                    INSERT INTO news_entries 
                    (user_id, original_news, enhanced_news, category, 
                     original_length, enhanced_length, processing_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, original_news, enhanced_news, category,
                    len(original_news), len(enhanced_news), processing_time
                ))
                
                # User की total requests update करें
                conn.execute('''
                    UPDATE users SET total_requests = total_requests + 1,
                    last_activity = ? WHERE user_id = ?
                ''', (datetime.now(), user_id))
                
                conn.commit()
    
    def save_channel_post(self, post_data: Dict[str, Any]):
        """Channel post details save करता है"""
        with self.lock:
            with self._get_connection() as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO channel_posts 
                    (message_id, chat_id, content, category, post_time)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    post_data['message_id'],
                    post_data['chat_id'],
                    post_data['content'],
                    post_data.get('category'),
                    post_data['post_time']
                ))
                conn.commit()
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """User की statistics return करता है"""
        with self._get_connection() as conn:
            user_data = conn.execute('''
                SELECT total_requests, join_date, last_activity 
                FROM users WHERE user_id = ?
            ''', (user_id,)).fetchone()
            
            if not user_data:
                return {}
            
            news_stats = conn.execute('''
                SELECT COUNT(*) as count, 
                       SUM(enhanced_length - original_length) as total_improvement
                FROM news_entries WHERE user_id = ?
            ''', (user_id,)).fetchone()
            
            # User rank calculate करें
            rank = conn.execute('''
                SELECT COUNT(*) + 1 as rank FROM users 
                WHERE total_requests > (
                    SELECT total_requests FROM users WHERE user_id = ?
                )
            ''', (user_id,)).fetchone()['rank']
            
            total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            percentile = round((1 - rank / total_users) * 100, 1) if total_users > 0 else 0
            
            return {
                'total_news': news_stats['count'] or 0,
                'total_improvement': news_stats['total_improvement'] or 0,
                'join_date': user_data['join_date'],
                'last_activity': user_data['last_activity'],
                'user_rank': rank,
                'percentile': percentile
            }
    
    def update_rate_limit(self, user_id: int):
        """Rate limit counters update करता है"""
        now = datetime.now()
        with self.lock:
            with self._get_connection() as conn:
                # Current limits check करें
                current = conn.execute('''
                    SELECT * FROM rate_limits WHERE user_id = ?
                ''', (user_id,)).fetchone()
                
                if not current:
                    # नया entry बनाएं
                    conn.execute('''
                        INSERT INTO rate_limits (user_id, hourly_count, daily_count)
                        VALUES (?, 1, 1)
                    ''', (user_id,))
                else:
                    hour_reset = datetime.fromisoformat(current['last_hour_reset'])
                    day_reset = datetime.fromisoformat(current['last_day_reset'])
                    
                    # Hourly reset check
                    if now - hour_reset > timedelta(hours=1):
                        hourly_count = 1
                        hour_reset_time = now
                    else:
                        hourly_count = current['hourly_count'] + 1
                        hour_reset_time = hour_reset
                    
                    # Daily reset check
                    if now - day_reset > timedelta(days=1):
                        daily_count = 1
                        day_reset_time = now
                    else:
                        daily_count = current['daily_count'] + 1
                        day_reset_time = day_reset
                    
                    conn.execute('''
                        UPDATE rate_limits SET 
                        hourly_count = ?, daily_count = ?,
                        last_hour_reset = ?, last_day_reset = ?
                        WHERE user_id = ?
                    ''', (hourly_count, daily_count, hour_reset_time, day_reset_time, user_id))
                
                conn.commit()
    
    def check_rate_limit(self, user_id: int) -> Dict[str, bool]:
        """Rate limit status check करता है"""
        with self._get_connection() as conn:
            limits = conn.execute('''
                SELECT * FROM rate_limits WHERE user_id = ?
            ''', (user_id,)).fetchone()
            
            if not limits:
                return {"hourly_ok": True, "daily_ok": True}
            
            return {
                "hourly_ok": limits['hourly_count'] < config.MAX_REQUESTS_PER_HOUR,
                "daily_ok": limits['daily_count'] < config.MAX_REQUESTS_PER_DAY
            }
    
    def get_top_users(self, limit: int = 10) -> List[Dict]:
        """Top users की list return करता है"""
        with self._get_connection() as conn:
            users = conn.execute('''
                SELECT user_id, username, total_requests, 
                       COUNT(ne.id) as news_count
                FROM users u
                LEFT JOIN news_entries ne ON u.user_id = ne.user_id
                WHERE u.is_active = TRUE
                GROUP BY u.user_id
                ORDER BY total_requests DESC
                LIMIT ?
            ''', (limit,)).fetchall()
            
            return [dict(user) for user in users]
    
    def get_daily_stats(self, date: str = None) -> Dict[str, Any]:
        """Daily statistics return करता है"""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
            
        with self._get_connection() as conn:
            stats = conn.execute('''
                SELECT 
                    COUNT(DISTINCT user_id) as active_users,
                    COUNT(*) as total_news,
                    AVG(enhanced_length - original_length) as avg_improvement
                FROM news_entries 
                WHERE DATE(created_at) = ?
            ''', (date,)).fetchone()
            
            posts = conn.execute('''
                SELECT COUNT(*) as total_posts
                FROM channel_posts 
                WHERE DATE(post_time) = ?
            ''', (date,)).fetchone()
            
            return {
                "date": date,
                "active_users": stats['active_users'] or 0,
                "total_news": stats['total_news'] or 0,
                "avg_improvement": round(stats['avg_improvement'] or 0, 2),
                "total_posts": posts['total_posts'] or 0
            }
    
    def backup_database(self, backup_path: str) -> bool:
        """Database का backup बनाता है"""
        try:
            import shutil
            backup_file = f"{backup_path}/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(self.db_name, backup_file)
            logger.info(f"Database backup created: {backup_file}")
            return True
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False
    
    def cleanup_old_data(self, days: int = 30):
        """पुराना data cleanup करता है"""
        cutoff_date = datetime.now() - timedelta(days=days)
        with self.lock:
            with self._get_connection() as conn:
                # Old analytics entries delete करें
                conn.execute('''
                    DELETE FROM analytics WHERE timestamp < ?
                ''', (cutoff_date,))
                
                # Old rate limit entries reset करें
                conn.execute('''
                    DELETE FROM rate_limits WHERE last_day_reset < ?
                ''', (cutoff_date,))
                
                conn.commit()
                logger.info(f"Cleaned up data older than {days} days")
    
    def get_active_subscribers(self) -> List[int]:
        """Active subscribers की list return करता है"""
        with self._get_connection() as conn:
            subscribers = conn.execute('''
                SELECT user_id FROM users 
                WHERE is_active = TRUE AND is_authorized = TRUE
            ''').fetchall()
            
            return [sub['user_id'] for sub in subscribers]