from supabase_client import supabase
import bcrypt
from datetime import datetime
import uuid

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
    def get_session_conversations(session_id: str):
        # Get all conversations for session
        result = supabase.table('conversations')\
            .select('*')\
            .eq('session_id', session_id)\
            .order('created_at', desc=False)\
            .execute()
            
        return result.data if result.data else []

    @staticmethod
    def store_conversation(session_id: str, user_message: str, ai_response: str, metadata: dict = None):
        # Store new conversation
        result = supabase.table('conversations').insert({
            'session_id': session_id,
            'user_message': user_message,
            'ai_response': ai_response,
            'metadata': metadata or {}
        }).execute()
        
        return result.data[0] if result.data else None

    @staticmethod
    def update_session_activity(session_id: str):
        # Update last_active timestamp
        supabase.table('sessions')\
            .update({'last_active': datetime.utcnow().isoformat()})\
            .eq('session_id', session_id)\
            .execute() 