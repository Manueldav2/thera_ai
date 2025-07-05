from supabase_client import supabase
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_tables():
    try:
        # Read the SQL file
        sql_file_path = os.path.join(os.path.dirname(__file__), 'create_tables.sql')
        with open(sql_file_path, 'r') as f:
            sql = f.read()
        
        # Split SQL into individual statements
        sql_statements = sql.split(';')
        
        # Execute each statement separately
        for statement in sql_statements:
            statement = statement.strip()
            if statement:  # Skip empty statements
                try:
                    logger.info(f"Executing SQL statement: {statement[:100]}...")  # Log first 100 chars
                    response = supabase.rpc('exec_sql', {'query': statement}).execute()
                    logger.info("Statement executed successfully!")
                except Exception as stmt_error:
                    logger.error(f"Error executing statement: {str(stmt_error)}")
                    raise
        
        logger.info("All tables created successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create tables: {str(e)}")
        return False

if __name__ == "__main__":
    create_tables() 