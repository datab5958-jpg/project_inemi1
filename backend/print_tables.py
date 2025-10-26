#!/usr/bin/env python3
"""
Print database tables, row counts, and up to 5 sample rows per table.
"""

from app import app
from models import db

def main() -> None:
    print("=== Table Inspection ===")
    with app.app_context():
        uri = app.config.get('SQLALCHEMY_DATABASE_URI')
        print(f"SQLALCHEMY_DATABASE_URI: {uri}")

        # First, validate connector and basic connectivity
        try:
            print("Connecting to database engine...")
            with db.engine.connect() as conn:
                from sqlalchemy import text
                res = conn.execute(text('SELECT 1'))
                print(f"Engine SELECT 1 => {res.scalar()}")
        except Exception as e:
            print(f"Engine connection error: {e}")
            print("Hint: Ensure MySQL is running and install driver: pip install mysql-connector-python")
            return

        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            # Fallback for MySQL if inspector returns empty: use SHOW TABLES
            if not tables:
                print("Inspector returned no tables, trying SHOW TABLES...")
                with db.engine.connect() as conn:
                    rows = conn.execute(text('SHOW TABLES')).fetchall()
                    tables = [row[0] for row in rows]
            if not tables:
                print("No tables found.")
                return

            for table in sorted(tables):
                print(f"\n--- {table} ---")
                try:
                    # Count rows
                    count = db.session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    total = count.scalar() or 0
                    print(f"rows: {total}")

                    # Show up to 5 rows
                    sample = db.session.execute(text(f"SELECT * FROM {table} LIMIT 5"))
                    rows = sample.mappings().all()
                    if rows:
                        for i, row in enumerate(rows, 1):
                            print(f"[{i}] {dict(row)}")
                    else:
                        print("(no rows)")
                except Exception as e:
                    print(f"Error reading {table}: {e}")
        except Exception as e:
            print(f"Inspector error: {e}")

if __name__ == '__main__':
    main()


