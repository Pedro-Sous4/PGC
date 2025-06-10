import os
import re
import unicodedata
import logging
import tempfile
from datetime import datetime
import pandas as pd
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from .models import Credor

# Configuração do logger global
logger = logging.getLogger("envios")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    file_handler = logging.FileHandler(os.path.join(settings.MEDIA_ROOT, 'envios.log'))
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

def gerar_pdf_relatorio(credor):
    html_string = render_to_string('core/relatorio_pdf.html', {'Credor': credor})
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as output:
        HTML(string=html_string).write_pdf(output.name)
        return output.name

def normalizar_nome(nome):
    if not nome:
        return ''
    nome = re.sub(r'\d+\s*-\s*', '', nome)  # Remove "1260 -"
    nome = re.sub(r'\s*\([^)]*\)', '', nome)  # Remove "(CONSULTOR)"
    nome = unicodedata.normalize('NFKD', nome.upper())
    return ''.join(c for c in nome if not unicodedata.combining(c)).strip().lower()

def enviar_email_com_arquivos(credor):
    historico = credor.historicos.order_by('-data_envio').first()
    if not credor.email:
        logger.error(f'Credor {credor.nome} não possui e-mail cadastrado.')
        return False
    if not historico:
        logger.error(f'Credor {credor.nome} não possui histórico PGC registrado.')
        return False

    pasta = os.path.join(settings.MEDIA_ROOT, 'PGC', str(historico.numero_pgc), credor.nome_pasta())
    if not os.path.isdir(pasta):
        logger.error(f'Pasta não encontrada para {credor.nome}.')
        return False

    arquivos = [os.path.join(pasta, f) for f in os.listdir(pasta) if f.endswith('.xlsx')]
    if not arquivos:
        logger.error(f'Nenhum arquivo gerado para {credor.nome}.')
        return False

    # Busca informação de mínimo garantido
    info_minimo = ''
    caminho_minimo = os.path.join(pasta, 'mínimo.xlsx')
    if os.path.exists(caminho_minimo):
        try:
            df_minimo = pd.read_excel(caminho_minimo)
            for _, row in df_minimo.iterrows():
                if normalizar_nome(row['credor']) == normalizar_nome(credor.nome):
                    valor = row['minimo']
                    empresa = row['empresa']
                    cnpj = row['cnpj']
                    info_minimo = f"""
\nMínimo no valor de R$ {valor:,.2f}. Favor emitir para {empresa} {cnpj}
Notas devem ser enviadas até às 12h, de QUARTA-FEIRA, dia 16/{historico.periodo}.
Notas enviadas após o prazo serão programadas para 15 dias após o recebimento.
"""
                    break
        except Exception as e:
            logger.warning(f'Erro ao processar mínimo para {credor.nome}: {e}')

    assunto = f"Relatórios financeiros PGC {historico.numero_pgc}"
    mensagem = f"""{credor.nome},

Olá,

Segue em anexo produtividade, relatório com os bloqueios de comissão (distrato e inadimplência) e relação de clientes repassados.

No e-mail constam 4 planilhas, sendo elas:
- Os valores de cada empresa para emissão - PGC {historico.numero_pgc} EMISSÃO
- o borderô com os clientes que estão sendo repassados - PGC {historico.numero_pgc}
- a produtividade que está com o nome PRODUTIVIDADE {historico.periodo}
- o histórico das comissões que ficaram bloqueadas por inadimplência e/ou distrato - EXTRATO

A PARTIR DE SETEMBRO/2024 AS NOTAS DEVEM SER EMITIDAS PARA AS EMPRESAS QUE CONSTAM NA PLANILHA \"PGC {historico.numero_pgc} EMISSÃO\"{info_minimo}

Atenciosamente,
"""

    email = EmailMessage(assunto, mensagem, settings.DEFAULT_FROM_EMAIL, [credor.email])
    for arq in arquivos:
        email.attach_file(arq)

    try:
        email.send()
        logger.info(f"E-mail enviado com sucesso para {credor.nome} ({credor.email}) com {len(arquivos)} arquivos.")
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar e-mail para {credor.nome}: {e}")
        return False

def salvar_planilha_temporaria(file, numero_pgc):
    pasta = os.path.join(settings.MEDIA_ROOT, 'TEMPORARIOS')
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, f'PGC_{numero_pgc}_ORIGINAL.xlsx')
    with open(caminho, 'wb+') as destino:
        for chunk in file.chunks():
            destino.write(chunk)
    return caminho

def normalizar_planilha_origem(file_path, numero_pgc):
    renomear = {
        'Dt. emissão': 'dt_emissao',
        'Dt. vencimento': 'dt_vencimento',
        'Dt. baixa': 'dt_baixa',
        'Obs. baixa': 'obs_baixa'
    }
    df_dict = pd.read_excel(file_path, sheet_name=None)
    planilhas_tratadas = {
        aba: df.rename(columns=lambda col: renomear.get(str(col).strip(), str(col).strip()))
        for aba, df in df_dict.items()
    }
    pasta_saida = os.path.join('media', 'planilhas_originais_tratadas')
    os.makedirs(pasta_saida, exist_ok=True)
    caminho_final = os.path.join(pasta_saida, f'PGC {numero_pgc}.xlsx')
    with pd.ExcelWriter(caminho_final, engine='openpyxl') as writer:
        for aba, df in planilhas_tratadas.items():
            df.to_excel(writer, sheet_name=aba, index=False)
    return caminho_final

def normalizar_colunas_simples(df):
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('.', '')
    return df

def normalizar_colunas_com_duas_linhas(df, header_start=5):
    df.columns = (
        df.iloc[header_start:header_start+2].fillna('').agg(' '.join)
        .str.strip().str.lower().str.replace(' ', '_').str.replace('.', '')
    )
    df = df.iloc[header_start+2:].reset_index(drop=True)
    return df

def extrair_minimos_de_planilha(df):
    colunas_esperadas = ['credor', 'minimofixo_garantido_para_emissao_nf', 'empresa_emissao_nf', 'cnpj']
    for col in colunas_esperadas:
        if col not in df.columns:
            raise ValueError(f'Coluna obrigatória ausente na aba PGC: {col}')
    return df[colunas_esperadas].dropna(subset=['credor'])

def obter_minimo_garantido_para_credor(nome_credor, planilha_minimos):
    nome_normalizado = normalizar_nome(nome_credor)
    for _, row in planilha_minimos.iterrows():
        if normalizar_nome(row['credor']) == nome_normalizado:
            return {
                'valor': row['minimofixo_garantido_para_emissao_nf'],
                'empresa': row['empresa_emissao_nf'],
                'cnpj': row['cnpj']
            }
    return None

def salvar_minimos_como_excel(df_minimos, numero_pgc):
    pasta = os.path.join(settings.MEDIA_ROOT, 'PGC', str(numero_pgc))
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, 'mínimo.xlsx')
    df_minimos.to_excel(caminho, index=False)
    return caminho

def setup_logger():
    logger = logging.getLogger('pgc_logger')
    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)
        handler = logging.FileHandler(os.path.join(settings.MEDIA_ROOT, 'pgc_debug.log'))
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
