#!/usr/bin/env python3
"""
Migration script to update the password_hash column length from 128 to 255 characters.
This fixes the StringDataRightTruncation error when storing scrypt password hashes.
"""

from app import create_app, db
from sqlalchemy import text

def migrate_password_hash():
    """Migrate the password_hash column to support longer hashes"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if we're using SQLite or PostgreSQL
            engine = db.engine
            dialect = engine.dialect.name
            
            if dialect == 'sqlite':
                # SQLite doesn't support ALTER COLUMN directly, so we need to recreate the table
                print("SQLite detected - recreating user table...")
                
                # Create new table with correct schema
                db.engine.execute(text("""
                    CREATE TABLE user_new (
                        id INTEGER PRIMARY KEY,
                        username VARCHAR(80) UNIQUE NOT NULL,
                        email VARCHAR(120) UNIQUE NOT NULL,
                        password_hash VARCHAR(255),
                        created_at DATETIME
                    )
                """))
                
                # Copy data from old table to new table
                db.engine.execute(text("""
                    INSERT INTO user_new (id, username, email, password_hash, created_at)
                    SELECT id, username, email, password_hash, created_at FROM user
                """))
                
                # Drop old table and rename new table
                db.engine.execute(text("DROP TABLE user"))
                db.engine.execute(text("ALTER TABLE user_new RENAME TO user"))
                
                print("SQLite migration completed successfully!")
                
            elif dialect == 'postgresql':
                # PostgreSQL supports ALTER COLUMN
                print("PostgreSQL detected - altering password_hash column...")
                
                db.engine.execute(text("""
                    ALTER TABLE "user" 
                    ALTER COLUMN password_hash TYPE VARCHAR(255)
                """))
                
                print("PostgreSQL migration completed successfully!")
                
            else:
                print(f"Unsupported database dialect: {dialect}")
                print("Please manually alter the password_hash column to VARCHAR(255)")
                return False
                
            print("Migration completed successfully!")
            return True
            
        except Exception as e:
            print(f"Migration failed: {e}")
            return False

if __name__ == '__main__':
    print("Starting password_hash column migration...")
    success = migrate_password_hash()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
