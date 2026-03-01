import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','envio_rendimentos.settings')
import django
django.setup()
from core.utils_progress import init_progress, log_error, set_credor_status, get_progress
from pathlib import Path

rid = init_progress()
set_credor_status(rid,'ALANDERSON','processing','Alanderson Jesse da Silva Galvao')
log_error(rid, {'id':'e1','request_id':rid,'credor':'ALANDERSON','credor_display':'Alanderson Jesse da Silva Galvao','step':'processamento','technical':'TestError: falha ao criar credor','friendly':'Erro ao criar credor: duplicidade','type':'duplicidade','time':'00:00:00','retries':0,'resolved':False})
print('rid',rid)
p=Path('arquivos_gerados')/ 'processing'/ rid / 'errors.json'
print('errors exists', p.exists())
print(p.read_text())
p2=Path('arquivos_gerados')/ 'processing'/ rid / 'credores.json'
print('credores exists', p2.exists())
print(p2.read_text())
print('progress keys:', list(get_progress(rid).keys()))
