"""One-shot setup: create tables + demo users.

    cd backend && python seed.py
"""
from database.db import init_db, seed_users

if __name__ == "__main__":
    init_db()
    seed_users()
    print("✓ Database initialised (backend/database/bugtrack.db)")
    print("✓ Demo users created:")
    print("  admin     -> admin@bugtrack.dev   / admin123")
    print("  developer -> dev@bugtrack.dev     / dev123")
    print("  developer -> dev2@bugtrack.dev    / dev2123")
    print("  tester    -> tester@bugtrack.dev  / tester123")
