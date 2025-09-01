#!/usr/bin/env python3
"""
Test script to verify Supabase database connection
"""

import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

def test_connection_string():
    """Test and display the connection string processing"""
    
    # Get the original connection string
    original_url = os.environ.get('DATABASE_URL')
    print(f"Original DATABASE_URL: {original_url}")
    
    if not original_url:
        print("❌ No DATABASE_URL found in environment variables")
        return False
    
    if 'postgresql://' not in original_url:
        print("❌ DATABASE_URL is not a PostgreSQL connection string")
        return False
    
    try:
        # Remove postgresql:// prefix
        url_without_prefix = original_url.replace('postgresql://', '')
        
        # Split by the LAST @ to separate auth from host (password may contain @ symbols)
        if '@' in url_without_prefix:
            # Find the last occurrence of @
            last_at_index = url_without_prefix.rindex('@')
            auth_part = url_without_prefix[:last_at_index]
            host_part = url_without_prefix[last_at_index + 1:]
            
            # Split auth part to get username and password
            if ':' in auth_part:
                username, password = auth_part.split(':', 1)
                
                print(f"Username: {username}")
                print(f"Password: {password}")
                print(f"Host: {host_part}")
                
                # URL encode the password
                encoded_password = quote_plus(password)
                print(f"Encoded password: {encoded_password}")
                
                # Reconstruct the connection string
                encoded_url = f"postgresql://{username}:{encoded_password}@{host_part}"
                print(f"Encoded DATABASE_URL: {encoded_url}")
                
                return True
            else:
                print("❌ No password found in connection string")
                return False
        else:
            print("❌ Invalid connection string format")
            return False
            
    except Exception as e:
        print(f"❌ Error processing connection string: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Testing Supabase Connection String...")
    print("=" * 50)
    
    success = test_connection_string()
    
    if success:
        print("\n✅ Connection string processing successful!")
        print("You can now run: python run.py")
    else:
        print("\n❌ Connection string processing failed!")
        print("Please check your .env file and DATABASE_URL")
