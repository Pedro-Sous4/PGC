import sys
import os
import re
from datetime import datetime
from core.formatting import format_workbook


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python format_credor_xlsx.py <PGC_NUMBER>')
        sys.exit(1)
    pgc = sys.argv[1]
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'arquivos_gerados', 'PGC', str(pgc))
    if not os.path.isdir(base):
        print('PGC folder not found:', base)
        sys.exit(2)

    formatted = 0
    for cred in os.listdir(base):
        cred_dir = os.path.join(base, cred)
        if not os.path.isdir(cred_dir):
            continue
        for fname in os.listdir(cred_dir):
            if fname.lower().endswith('.xlsx'):
                path = os.path.join(cred_dir, fname)
                try:
                    format_workbook(path)
                    formatted += 1
                    print('Formatted:', path)
                except Exception as e:
                    print('Error formatting', path, e)

    print(f'Done. Formatted {formatted} files in PGC {pgc}.')
