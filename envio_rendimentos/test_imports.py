#!/usr/bin/env python
"""Test the get_progress import to see which one is being used"""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "envio_rendimentos.settings")

import django
django.setup()

# Test which get_progress is imported
from core.services.pgc_processor.process_pgcs import get_progress as get_progress_file
from core.utils_progress import get_progress as get_progress_memory

from django.conf import settings
from pathlib import Path

# Get the latest UUID
proc_dir = Path(settings.MEDIA_ROOT) / "processing"
if proc_dir.exists():
    uuids = sorted(
        [d.name for d in proc_dir.iterdir() if d.is_dir()],
        key=lambda x: (proc_dir / x).stat().st_mtime,
        reverse=True
    )
    
    if uuids:
        test_uuid = uuids[0]
        print(f"Testing with UUID: {test_uuid}")
        
        # Test file-based get_progress
        print("\n=== Testing get_progress_file (from process_pgcs.py) ===")
        result_file = get_progress_file(test_uuid)
        if result_file:
            print(f"✅ Returned data!")
            print(f"   Status: {result_file.get('status')}")
            print(f"   Logs count: {len(result_file.get('logs', []))}")
        else:
            print(f"❌ Returned None!")
        
        # Test memory-based get_progress
        print("\n=== Testing get_progress_memory (from utils_progress.py) ===")
        result_memory = get_progress_memory(test_uuid)
        if result_memory:
            print(f"✅ Returned data!")
            print(f"   Status: {result_memory.get('status')}")
            print(f"   Logs count: {len(result_memory.get('logs', []))}")
        else:
            print(f"❌ Returned None!")
