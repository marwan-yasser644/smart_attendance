#!/usr/bin/env python3
"""
Create the first DEAN account.

The first DEAN is created manually by the developer (no public registration
exists). This script works against whatever database `DATABASE_URL` points to
(Neon/PostgreSQL in production, or local SQLite in development).

Usage:
    # interactive
    python create_dean.py

    # non-interactive (e.g. CI / one-off)
    python create_dean.py --name "Prof. Dean" --email dean@kfu.edu.eg \
        --username dean --password 'StrongPass123'

The created DEAN is active and is NOT forced to change the password
(set --force-change to require a change on first login instead).
"""
import argparse
import getpass
import sys

from app import app, db
from app.models import ROLE_DEAN, Lecturer


def main() -> int:
    parser = argparse.ArgumentParser(description="Create the first DEAN account.")
    parser.add_argument('--name')
    parser.add_argument('--email')
    parser.add_argument('--username')
    parser.add_argument('--password')
    parser.add_argument('--force-change', action='store_true',
                        help='Require the DEAN to change the password on first login.')
    args = parser.parse_args()

    name = args.name or input('Full name: ').strip()
    email = (args.email or input('Email: ')).strip().lower()
    username = (args.username or input('Username: ')).strip()
    password = args.password or getpass.getpass('Password (min 8 chars): ')

    if not all([name, email, username, password]):
        print('ERROR: name, email, username and password are all required.')
        return 1
    if len(password) < 8:
        print('ERROR: password must be at least 8 characters.')
        return 1

    with app.app_context():
        if Lecturer.query.filter_by(email=email).first():
            print(f'ERROR: a user with email {email} already exists.')
            return 1
        if Lecturer.query.filter(db.func.lower(Lecturer.username) == username.lower()).first():
            print(f'ERROR: a user with username {username} already exists.')
            return 1

        dean = Lecturer(
            name=name,
            email=email,
            username=username,
            is_active=True,
            must_change_password=bool(args.force_change),
        )
        dean.set_role(ROLE_DEAN)
        dean.set_password(password)
        db.session.add(dean)
        db.session.commit()
        print(f'[OK] DEAN account created: {email} (username: {username})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
