"""
Vercel WSGI entry point for Flask application.
This file is required for proper Vercel deployment.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

app = create_app()

# Vercel will use this directly
__all__ = ['app']
