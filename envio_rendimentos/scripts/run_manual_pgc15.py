import os
import sys
# setup django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'envio_rendimentos.settings')
import django
django.setup()

from core.services.pgc_processor.process_pgcs import process_pgc_file

if __name__ == '__main__':
    process_pgc_file(r'c:\PGC\envio_rendimentos\arquivos_gerados\PGC\15\PGC 15.xlsx', request_id='manual-pgc15-1', pgc_prefix='SPORTS')
