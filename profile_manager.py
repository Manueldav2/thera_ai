from supabase_client import supabase
import json
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ProfileManager:
    @staticmethod
    def get_user_profile(user_id: str) -> Dict:
        """Get user profile information"""
        try:
            result = supabase.table('user_profiles')\
                .select('*')\
                .eq('user_id', user_id)\
                .single()\
                .execute()
            
            if result.data:
                return result.data
            
            # Create profile if it doesn't exist
            new_profile = {
                'user_id': user_id,
                'personal_info': {},
                'relationships': {},
                'important_events': [],
                'preferences': {},
                'goals': []
            }
            result = supabase.table('user_profiles')\
                .insert(new_profile)\
                .execute()
            
            return result.data[0] if result.data else new_profile
        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            return {}

    @staticmethod
    def update_profile_field(user_id: str, field: str, data: Any) -> bool:
        """Update a specific field in the user profile"""
        try:
            result = supabase.table('user_profiles')\
                .update({field: data})\
                .eq('user_id', user_id)\
                .execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error updating profile field: {str(e)}")
            return False

    @staticmethod
    def extract_personal_info(message: str, current_info: Dict) -> Dict:
        """Extract personal information from user messages"""
        try:
            # Use OpenAI to extract relevant information
            from thera_ai import therapist
            
            prompt = f"""
            Given the user's message and their current stored information, extract any new personal information mentioned.
            Focus on relationships, important life events, preferences, and goals.
            
            Current stored information:
            {json.dumps(current_info, indent=2)}
            
            User message:
            {message}
            
            Return ONLY a JSON object with the following structure (only include fields where new information was found):
            {{
                "personal_info": {{}},
                "relationships": {{}},
                "important_events": [],
                "preferences": {{}},
                "goals": []
            }}
            """
            
            response = therapist.openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an AI designed to extract personal information from conversations. Only return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                response_format={ "type": "json_object" }
            )
            
            new_info = json.loads(response.choices[0].message.content)
            return new_info
        except Exception as e:
            logger.error(f"Error extracting personal info: {str(e)}")
            return {}

    @staticmethod
    def update_profile_from_message(user_id: str, message: str) -> bool:
        """Update user profile based on new message content"""
        try:
            # Get current profile
            current_profile = ProfileManager.get_user_profile(user_id)
            
            # Extract new information
            new_info = ProfileManager.extract_personal_info(message, current_profile)
            
            # Update each field if new information exists
            for field, data in new_info.items():
                if data:  # Only update if there's new information
                    current_data = current_profile.get(field, {} if isinstance(data, dict) else [])
                    
                    if isinstance(data, dict):
                        current_data.update(data)
                    elif isinstance(data, list):
                        current_data.extend(data)
                    
                    ProfileManager.update_profile_field(user_id, field, current_data)
            
            return True
        except Exception as e:
            logger.error(f"Error updating profile from message: {str(e)}")
            return False

    @staticmethod
    def get_profile_context(user_id: str) -> str:
        """Get formatted context string from user profile"""
        try:
            profile = ProfileManager.get_user_profile(user_id)
            if not profile:
                return ""
            
            context_parts = []
            
            if profile.get('personal_info'):
                context_parts.append("Personal Information:")
                for k, v in profile['personal_info'].items():
                    context_parts.append(f"- {k}: {v}")
            
            if profile.get('relationships'):
                context_parts.append("\nRelationships:")
                for person, details in profile['relationships'].items():
                    context_parts.append(f"- {person}: {details}")
            
            if profile.get('important_events'):
                context_parts.append("\nImportant Life Events:")
                for event in profile['important_events']:
                    context_parts.append(f"- {event}")
            
            if profile.get('preferences'):
                context_parts.append("\nPreferences:")
                for k, v in profile['preferences'].items():
                    context_parts.append(f"- {k}: {v}")
            
            if profile.get('goals'):
                context_parts.append("\nGoals:")
                for goal in profile['goals']:
                    context_parts.append(f"- {goal}")
            
            return "\n".join(context_parts)
        except Exception as e:
            logger.error(f"Error getting profile context: {str(e)}")
            return "" 