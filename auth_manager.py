# auth_manager.py - User Authentication Module
import logging
from typing import List, Dict, Any
from database import Database
import config

logger = logging.getLogger(__name__)

class AuthManager:
    def __init__(self):
        self.db = Database()
        self.admin_ids = set(config.ADMIN_USER_IDS)
    
    def is_authorized(self, user_id: int) -> bool:
        """Check करता है कि user authorized है या नहीं"""
        try:
            # Admin हमेशा authorized होते हैं
            if user_id in self.admin_ids:
                return True
            
            # Database से check करें
            with self.db._get_connection() as conn:
                user = conn.execute('''
                    SELECT is_authorized FROM users WHERE user_id = ?
                ''', (user_id,)).fetchone()
                
                return user and user['is_authorized']
                
        except Exception as e:
            logger.error(f"Error checking authorization for {user_id}: {e}")
            return False
    
    def is_admin(self, user_id: int) -> bool:
        """Check करता है कि user admin है या नहीं"""
        return user_id in self.admin_ids
    
    def authorize_user(self, user_id: int, admin_id: int) -> bool:
        """User को authorize करता है"""
        try:
            if not self.is_admin(admin_id):
                logger.warning(f"Non-admin {admin_id} tried to authorize user {user_id}")
                return False
            
            with self.db._get_connection() as conn:
                conn.execute('''
                    UPDATE users SET is_authorized = TRUE 
                    WHERE user_id = ?
                ''', (user_id,))
                
                # Admin log entry
                conn.execute('''
                    INSERT INTO admin_logs (admin_id, action, target_user_id, details)
                    VALUES (?, 'authorize_user', ?, 'User authorized')
                ''', (admin_id, user_id))
                
                conn.commit()
                
            logger.info(f"User {user_id} authorized by admin {admin_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error authorizing user {user_id}: {e}")
            return False
    
    def revoke_authorization(self, user_id: int, admin_id: int) -> bool:
        """User का authorization revoke करता है"""
        try:
            if not self.is_admin(admin_id):
                return False
            
            with self.db._get_connection() as conn:
                conn.execute('''
                    UPDATE users SET is_authorized = FALSE 
                    WHERE user_id = ?
                ''', (user_id,))
                
                # Admin log entry
                conn.execute('''
                    INSERT INTO admin_logs (admin_id, action, target_user_id, details)
                    VALUES (?, 'revoke_authorization', ?, 'Authorization revoked')
                ''', (admin_id, user_id))
                
                conn.commit()
                
            logger.info(f"Authorization revoked for user {user_id} by admin {admin_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error revoking authorization for {user_id}: {e}")
            return False
    
    def get_authorized_users(self) -> List[Dict[str, Any]]:
        """सभी authorized users की list return करता है"""
        try:
            with self.db._get_connection() as conn:
                users = conn.execute('''
                    SELECT user_id, username, first_name, join_date, 
                           last_activity, total_requests
                    FROM users 
                    WHERE is_authorized = TRUE
                    ORDER BY last_activity DESC
                ''').fetchall()
                
                return [dict(user) for user in users]
                
        except Exception as e:
            logger.error(f"Error getting authorized users: {e}")
            return []
    
    def get_pending_users(self) -> List[Dict[str, Any]]:
        """Authorization pending users की list return करता है"""
        try:
            with self.db._get_connection() as conn:
                users = conn.execute('''
                    SELECT user_id, username, first_name, join_date
                    FROM users 
                    WHERE is_authorized = FALSE AND is_active = TRUE
                    ORDER BY join_date DESC
                ''').fetchall()
                
                return [dict(user) for user in users]
                
        except Exception as e:
            logger.error(f"Error getting pending users: {e}")
            return []
    
    def ban_user(self, user_id: int, admin_id: int, reason: str = "") -> bool:
        """User को ban करता है"""
        try:
            if not self.is_admin(admin_id):
                return False
            
            with self.db._get_connection() as conn:
                conn.execute('''
                    UPDATE users SET is_active = FALSE, is_authorized = FALSE 
                    WHERE user_id = ?
                ''', (user_id,))
                
                # Admin log entry
                conn.execute('''
                    INSERT INTO admin_logs (admin_id, action, target_user_id, details)
                    VALUES (?, 'ban_user', ?, ?)
                ''', (admin_id, user_id, f"User banned. Reason: {reason}"))
                
                conn.commit()
                
            logger.info(f"User {user_id} banned by admin {admin_id}. Reason: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Error banning user {user_id}: {e}")
            return False
    
    def unban_user(self, user_id: int, admin_id: int) -> bool:
        """User को unban करता है"""
        try:
            if not self.is_admin(admin_id):
                return False
            
            with self.db._get_connection() as conn:
                conn.execute('''
                    UPDATE users SET is_active = TRUE 
                    WHERE user_id = ?
                ''', (user_id,))
                
                # Admin log entry
                conn.execute('''
                    INSERT INTO admin_logs (admin_id, action, target_user_id, details)
                    VALUES (?, 'unban_user', ?, 'User unbanned')
                ''', (admin_id, user_id))
                
                conn.commit()
                
            logger.info(f"User {user_id} unbanned by admin {admin_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error unbanning user {user_id}: {e}")
            return False
    
    def get_user_permissions(self, user_id: int) -> Dict[str, bool]:
        """User की permissions return करता है"""
        try:
            with self.db._get_connection() as conn:
                user = conn.execute('''
                    SELECT is_authorized, is_active FROM users WHERE user_id = ?
                ''', (user_id,)).fetchone()
                
                if not user:
                    return {
                        "is_authorized": False,
                        "is_admin": False,
                        "is_active": False,
                        "can_post": False
                    }
                
                is_admin = self.is_admin(user_id)
                
                return {
                    "is_authorized": user['is_authorized'],
                    "is_admin": is_admin,
                    "is_active": user['is_active'],
                    "can_post": user['is_authorized'] and user['is_active']
                }
                
        except Exception as e:
            logger.error(f"Error getting permissions for {user_id}: {e}")
            return {"is_authorized": False, "is_admin": False, "is_active": False, "can_post": False}
    
    def get_admin_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Admin logs return करता है"""
        try:
            with self.db._get_connection() as conn:
                logs = conn.execute('''
                    SELECT al.*, u.username as admin_username, 
                           tu.username as target_username
                    FROM admin_logs al
                    LEFT JOIN users u ON al.admin_id = u.user_id
                    LEFT JOIN users tu ON al.target_user_id = tu.user_id
                    ORDER BY al.timestamp DESC
                    LIMIT ?
                ''', (limit,)).fetchall()
                
                return [dict(log) for log in logs]
                
        except Exception as e:
            logger.error(f"Error getting admin logs: {e}")
            return []
    
    def check_user_exists(self, user_id: int) -> bool:
        """Check करता है कि user database में exist करता है"""
        try:
            with self.db._get_connection() as conn:
                user = conn.execute('''
                    SELECT user_id FROM users WHERE user_id = ?
                ''', (user_id,)).fetchone()
                
                return user is not None
                
        except Exception as e:
            logger.error(f"Error checking user existence {user_id}: {e}")
            return False
    
    def auto_authorize_new_users(self, enabled: bool = False) -> None:
        """Auto authorization setting update करता है"""
        self.auto_auth_enabled = enabled
        logger.info(f"Auto authorization {'enabled' if enabled else 'disabled'}")
    
    def bulk_authorize_users(self, user_ids: List[int], admin_id: int) -> Dict[str, Any]:
        """Multiple users को एक साथ authorize करता है"""
        success_count = 0
        failed_count = 0
        failed_users = []
        
        for user_id in user_ids:
            if self.authorize_user(user_id, admin_id):
                success_count += 1
            else:
                failed_count += 1
                failed_users.append(user_id)
        
        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "failed_users": failed_users,
            "total_processed": len(user_ids)
        }