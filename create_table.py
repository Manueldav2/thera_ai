from supabase_client import supabase
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_table():
    try:
        with open('create_test_table.sql', 'r') as f:
            sql = f.read()
        
        # Execute the SQL
        response = supabase.table('connection_test').select("*").limit(1).execute()
        logger.info("Table already exists or was created successfully!")
        return True
    except Exception as e:
        if 'relation "connection_test" does not exist' in str(e):
            try:
                response = supabase.rpc('exec_sql', {'query': sql}).execute()
                logger.info("Table created successfully!")
                return True
            except Exception as create_error:
                logger.error(f"Failed to create table: {str(create_error)}")
                return False
        else:
            logger.error(f"Error checking table: {str(e)}")
            return False

if __name__ == "__main__":
    create_test_table() 