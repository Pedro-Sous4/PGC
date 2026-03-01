#!/usr/bin/env python
import os
import json
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "envio_rendimentos.settings")
django.setup()

from core.services.pgc_processor.process_pgcs import get_progress
from django.conf import settings

# Find the latest processing UUID
proc_dir = os.path.join(settings.MEDIA_ROOT, "processing")
if os.path.exists(proc_dir):
    uuids = sorted(
        [d for d in os.listdir(proc_dir) if os.path.isdir(os.path.join(proc_dir, d))],
        key=lambda x: os.path.getmtime(os.path.join(proc_dir, x)),
        reverse=True
    )
    
    if uuids:
        latest_uuid = uuids[0]
        print(f"Testing get_progress() with UUID: {latest_uuid}\n")
        
        progress = get_progress(latest_uuid)
        
        if progress:
            print(f"✅ get_progress() returned data!")
            print(f"Status: {progress.get('status')}")
            print(f"Processed: {progress.get('processed')} / {progress.get('total_credores')}")
            print(f"Logs in response: {len(progress.get('logs', []))}")
            print(f"\nFirst 5 logs:")
            for i, log in enumerate(progress.get('logs', [])[:5]):
                print(f"  {i+1}. [{log.get('type')}] {log.get('msg')}")
            
            # Test JSON serializability
            try:
                json_str = json.dumps(progress, ensure_ascii=False, indent=2)
                print(f"\n✅ Progress is JSON serializable!")
                print(f"JSON size: {len(json_str)} bytes")
            except Exception as e:
                print(f"\n❌ Error serializing to JSON: {e}")
        else:
            print("❌ get_progress() returned None!")
    else:
        print("No processing directories found")
else:
    print(f"Processing directory does not exist: {proc_dir}")
