#!/usr/bin/env python3
"""
Runner untuk aplikasi INEMI yang terintegrasi dengan MySQL
"""

import os
import sys

# Add backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app_integrated import create_app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
