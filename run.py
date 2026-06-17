#!/usr/bin/env python3
"""
Quick start script for local development.
Run: python run.py
"""
from app import app, init_db

if __name__ == '__main__':
    print("=" * 55)
    print("  KSU Smart Attendance System")
    print("  Faculty of Artificial Intelligence")
    print("  Kafrelsheikh University")
    print("=" * 55)
    init_db()
    print("\n  Server starting at → http://localhost:5000")
    print("  Demo login: admin@kfu.edu.eg / admin123")
    print("  Press CTRL+C to stop\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
