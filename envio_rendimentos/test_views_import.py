#!/usr/bin/env python
"""Test what get_progress function views.py is importing"""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "envio_rendimentos.settings")

import django
django.setup()

# Import the exact way views.py does it
from core import views

# Check what get_progress is in the views module
if hasattr(views, 'get_progress'):
    print(f"get_progress found in views module: {views.get_progress}")
    print(f"Module: {views.get_progress.__module__}")
    
    # Test it
    result = views.get_progress("0a1ea73a-c569-497c-b31d-c68e998d269e")
    print(f"Result: {result}")
    if result:
        print(f"Logs count: {len(result.get('logs', []))}")
else:
    print("❌ get_progress NOT found in views module")

# Also check what's imported at module level
print(f"\nAll get_progress-related items in views:")
for attr in dir(views):
    if 'get_progress' in attr.lower():
        print(f"  - {attr}")
