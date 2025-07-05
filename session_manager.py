from supabase_client import supabase
import bcrypt
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

class SessionManager:
    @staticmethod
    def create_user(email: str, password: str):
        # Hash password
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        
        # Create user in database
        result = supabase.table('users').insert({
            'email': email,
            'password_hash': password_hash
        }).execute()
        
        return result.data[0] if result.data else None

    @staticmethod
    def login_user(email: str, password: str):
        # Get user from database
        result = supabase.table('users').select('*').eq('email', email).execute()
        if not result.data:
            return None
            
        user = result.data[0]
        
        # Verify password
        if not bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
            return None
            
        # Create new session
        session = supabase.table('sessions').insert({
            'user_id': user['user_id']
        }).execute()
        
        return session.data[0] if session.data else None

    @staticmethod
    def ensure_user_exists(user_id: str, email: str = None) -> bool:
        """Ensure user exists in the database"""
        try:
            # Check if user exists
            result = supabase.table('users')\
                .select('*')\
                .eq('id', user_id)\
                .execute()
            
            if result.data:
                # Update last_active
                supabase.table('users')\
                    .update({'last_active': datetime.utcnow().isoformat()})\
                    .eq('id', user_id)\
                    .execute()
                return True
            
            # Create new user if doesn't exist
            new_user = {
                'id': user_id,
                'email': email,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'last_active': datetime.utcnow().isoformat()
            }
            
            result = supabase.table('users')\
                .insert(new_user)\
                .execute()
            
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error ensuring user exists: {str(e)}")
            return False

    @staticmethod
    def get_session_conversations(user_id: str):
        """Get all conversations for user"""
        try:
            # Ensure user exists
            SessionManager.ensure_user_exists(user_id)
            
            # Get conversations
            result = supabase.table('conversations')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('created_at', desc=False)\
                .execute()
                
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error getting conversations: {str(e)}")
            return []

    @staticmethod
    def store_conversation(user_id: str, user_message: str, ai_response: str, metadata: dict = None):
        """Store new conversation"""
        try:
            # Ensure user exists
            SessionManager.ensure_user_exists(user_id)
            
            # Store conversation
            result = supabase.table('conversations')\
                .insert({
                    'user_id': user_id,
                    'user_message': user_message,
                    'ai_response': ai_response,
                    'metadata': metadata or {},
                    'created_at': datetime.utcnow().isoformat()
                })\
                .execute()
            
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error storing conversation: {str(e)}")
            return None

    @staticmethod
    def update_session_activity(user_id: str):
        """Update user's last active timestamp"""
        try:
            # Ensure user exists
            SessionManager.ensure_user_exists(user_id)
            
            # Update last_active
            supabase.table('users')\
                .update({'last_active': datetime.utcnow().isoformat()})\
                .eq('id', user_id)\
                .execute()
        except Exception as e:
            logger.error(f"Error updating session activity: {str(e)}") 