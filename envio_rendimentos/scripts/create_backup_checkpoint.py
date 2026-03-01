import sys
import os
import shutil
import json
from datetime import datetime


def make_backup_and_checkpoint(pgc_number: str):
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'arquivos_gerados', 'PGC', str(pgc_number))
    if not os.path.isdir(base):
        print(f"Pasta PGC não encontrada: {base}")
        return 2

    backups_dir = os.path.join(os.path.dirname(base), 'backups')
    os.makedirs(backups_dir, exist_ok=True)

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_name = f"PGC_{pgc_number}_backup_{ts}"
    zip_path = os.path.join(backups_dir, zip_name)

    # create zip (shutil will add .zip)
    shutil.make_archive(zip_path, 'zip', base)

    # build checkpoint
    creditors = [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))]
    creditors.sort()
    prod_present = []
    prod_missing = []

    for cred in creditors:
        cred_dir = os.path.join(base, cred)
        has_prod = False
        for f in os.listdir(cred_dir):
            if 'PRODUTIVIDADE' in f.upper():
                has_prod = True
                break
        if has_prod:
            prod_present.append(cred)
        else:
            prod_missing.append(cred)

    checkpoint = {
        'pgc': str(pgc_number),
        'timestamp': ts,
        'zip_file': os.path.basename(zip_path) + '.zip',
        'total_creditors': len(creditors),
        'prod_present_count': len(prod_present),
        'prod_missing_count': len(prod_missing),
        'prod_missing': prod_missing,
    }

    ck_name = f"checkpoint_PGC_{pgc_number}_{ts}.json"
    ck_path = os.path.join(backups_dir, ck_name)
    with open(ck_path, 'w', encoding='utf-8') as fh:
        json.dump(checkpoint, fh, ensure_ascii=False, indent=2)

    print(f"Backup criado: {os.path.join(backups_dir, zip_name + '.zip')}")
    print(f"Checkpoint criado: {ck_path}")
    print(f"Total credores: {len(creditors)} | Prod presentes: {len(prod_present)} | Prod ausentes: {len(prod_missing)}")
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Uso: python create_backup_checkpoint.py <PGC_NUMBER>')
        sys.exit(1)
    pgc = sys.argv[1]
    sys.exit(make_backup_and_checkpoint(pgc))
