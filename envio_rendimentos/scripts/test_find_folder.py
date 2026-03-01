from pathlib import Path
import sys
sys.path.insert(0, r'C:\PGC\envio_rendimentos')
from core.normalizacao import normalizar_nome_completo

pgc = Path(r'C:\PGC\envio_rendimentos\arquivos_gerados\PGC\34')
cred='ALANDERSON JESSE DA SILVA GALVÃO'
norm=normalizar_nome_completo(cred)
print('norm:',norm)
found=None
for p in pgc.iterdir():
    if p.is_dir():
        if normalizar_nome_completo(p.name)==norm:
            found=p
            break
print('found:',found)
