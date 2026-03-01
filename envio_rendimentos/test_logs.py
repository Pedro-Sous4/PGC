import os
import json
from pathlib import Path

proc_dir = Path("arquivos_gerados/processing")
if proc_dir.exists():
    uuids = sorted(
        [d for d in proc_dir.iterdir() if d.is_dir()],
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    if uuids:
        latest = uuids[0]
        progress_file = latest / "progress.json"
        
        if progress_file.exists():
            with open(progress_file, encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"✅ Latest UUID: {latest.name}")
            print(f"Status: {data.get('status')}")
            print(f"Processed: {data.get('processed')}/{data.get('total_credores')}")
            print(f"Logs count: {len(data.get('logs', []))}")
            print("\nFirst 5 logs:")
            for log in data.get('logs', [])[:5]:
                print(f"  - [{log.get('type')}] {log.get('msg')}")
        else:
            print(f"❌ progress.json not found in {latest}")
    else:
        print("❌ No processing directories found")
else:
    print(f"❌ Directory not found: {proc_dir}")
