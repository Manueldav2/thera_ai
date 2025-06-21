from supabase_client import supabase
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_connection():
    try:
        # Simplest possible test - just try to connect
        response = supabase.auth.get_session()
        logger.info("Successfully connected to Supabase!")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {str(e)}")
        return False

if __name__ == "__main__":
    test_connection() 