import os
p=r'c:\PGC\envio_rendimentos\arquivos_gerados\PGC\15'
for name in os.listdir(p):
    if 'THIAGO' in name.upper():
        print(repr(name))
