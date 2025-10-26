#!/usr/bin/env python3
"""
Lightweight database connectivity check.
"""

from app import app
from models import db, User

def main() -> None:
    print("=== DB Connectivity Check ===")
    with app.app_context():
        uri = app.config.get('SQLALCHEMY_DATABASE_URI')
        print(f"SQLALCHEMY_DATABASE_URI: {uri}")
        try:
            with db.engine.connect() as conn:
                result = conn.execute(db.text('SELECT 1'))
                one = result.scalar()
                print(f"SELECT 1 => {one}")
        except Exception as e:
            print(f"Connection error: {e}")
            return

        try:
            count = db.session.query(User).count()
            print(f"users count: {count}")
        except Exception as e:
            print(f"Query error on users: {e}")

if __name__ == '__main__':
    main()



