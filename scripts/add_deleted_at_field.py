#!/usr/bin/env python3
"""
Add deleted_at field to users table for soft delete functionality
"""

import os
import sys
from supabase import create_client

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def main():
    """Add deleted_at field to users table"""
    try:
        # Supabase connection
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            print("Supabase credentials not found in environment variables")
            sys.exit(1)

        supabase = create_client(supabase_url, supabase_key)

        print("Adding deleted_at field to users table...")

        # Add deleted_at column to users table
        sql = """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP DEFAULT NULL;
        """

        result = supabase.rpc('exec_sql', {'sql': sql}).execute()

        if result.data:
            print("Successfully added deleted_at field to users table")
        else:
            print("Failed to add deleted_at field")
            sys.exit(1)

        # Create index for performance
        index_sql = """
        CREATE INDEX IF NOT EXISTS idx_users_deleted_at
        ON users (deleted_at)
        WHERE deleted_at IS NOT NULL;
        """

        index_result = supabase.rpc('exec_sql', {'sql': index_sql}).execute()

        if index_result.data:
            print("Successfully created index for deleted_at field")
        else:
            print("Warning: Could not create index for deleted_at field")

        print("Database migration completed successfully!")

    except Exception as e:
        print(f"Error during migration: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()