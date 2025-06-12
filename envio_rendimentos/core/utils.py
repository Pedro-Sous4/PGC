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
from weasyprint import HTML
from .models import Credor, HistoricoPGC, EmpresaPagadora
from difflib import get_close_matches
import openpyxl

# Configuração de logger
logger = logging.getLogger("envios")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.FileHandler(os.path.join(settings.MEDIA_ROOT, 'envios.log'))
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def normalizar_nome(nome):
    if not nome:
        return ''
    nome = re.sub(r'^\d+\s*-\s*', '', nome)  # remove prefixo tipo "123 -"
    nome = re.sub(r'\s*\([^)]*\)', '', nome)  # remove "(CONSULTOR)"
    nome = unicodedata.normalize('NFKD', nome.upper())
    return ''.join(c for c in nome if not unicodedata.combining(c)).strip().lower()

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

def normalizar_colunas_com_duas_linhas(df, header_start=5):
    # Força conversão para string antes do join
    df.columns = (
        df.iloc[header_start:header_start+2]
        .fillna('')
        .astype(str)  # <- transforma tudo em string
        .agg(' '.join)
        .str.strip()
        .str.lower()
        .str.replace(' ', '_')
        .str.replace('.', '')
    )
    df = df.iloc[header_start+2:].reset_index(drop=True)
    return df



### REMOVIDA: função duplicada
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

def extrair_dados_planilhas(planilhas_dict, numero_pgc):
    base_df = produtividade_df = extrato_df = aba_pgcs = None
    for nome_aba, df in planilhas_dict.items():
        nome = nome_aba.strip().lower()
        if 'base' in nome:
            base_df = normalizar_colunas_simples(df.copy())
        elif 'produtividade' in nome:
            produtividade_df = normalizar_colunas_simples(df.copy())
        elif 'extrato' in nome:
            extrato_df = normalizar_colunas_simples(df.copy())
        elif nome.startswith(f"pgc {str(numero_pgc).lower()}"):
            aba_pgcs = df.copy()
    if base_df is None:
        raise ValueError('A aba "BASE" não foi encontrada.')
    return base_df, produtividade_df, extrato_df, aba_pgcs


#logger = logging.getLogger(__name__)

def normalizar_nome(nome):
    return str(nome).strip().upper().replace("  ", " ")

def obter_minimo_garantido_para_credor(nome_credor, numero_pgc):
    caminho_minimo = os.path.join(settings.MEDIA_ROOT, 'PGC', str(numero_pgc), 'mínimo.xlsx')
    if not os.path.exists(caminho_minimo):
        logger.warning(f"[MÍNIMO] mínimo.xlsx não encontrado: {caminho_minimo}")
        return None

    try:
        df = pd.read_excel(caminho_minimo)
        nome_normalizado = normalizar_nome(nome_credor)
        for _, row in df.iterrows():
            if normalizar_nome(str(row['credor'])) == nome_normalizado:
                return {
                    'valor': row['minimo'],
                    'empresa': row['empresa'],
                    'cnpj': row['cnpj']
                }
    except Exception as e:
        logger.error(f"[MÍNIMO] Erro ao ler mínimo.xlsx: {e}")
    return None

def gerar_arquivos_credor(credor, numero_pgc):
    def nome_limpo(texto):
        texto = re.sub(r"^\d+\s*-\s*", "", str(texto))
        texto = re.sub(r"\s*\([^)]*\)", "", texto)
        texto = unicodedata.normalize('NFKD', texto.upper())
        return ''.join(c for c in texto if not unicodedata.combining(c)).strip()

    nome_credor_normalizado = nome_limpo(credor.nome)
    nome_arquivo_credor = nome_credor_normalizado.title()

    pasta_origem = os.path.join(settings.MEDIA_ROOT, 'PGC', str(numero_pgc))
    pasta_saida = os.path.join(pasta_origem, f'{nome_arquivo_credor}')
    os.makedirs(pasta_saida, exist_ok=True)

    def carregar_df(nome_arquivo):
        caminho = os.path.join(pasta_origem, nome_arquivo)
        return pd.read_excel(caminho) if os.path.exists(caminho) else None

    base_df = carregar_df(f"BASE PGC {numero_pgc}.xlsx")
    extrato_df = carregar_df("EXTRATO.xlsx")
    prod_df = carregar_df("PRODUTIVIDADE.xlsx")
    minimo_path = os.path.join(pasta_origem, 'mínimo.xlsx')

    arquivos = {}

    # Renomeia coluna 'credor' se necessário
    for df in [extrato_df, prod_df]:
        if df is not None and 'credor' not in df.columns:
            for col in df.columns:
                if 'credor' in col.lower():
                    df.rename(columns={col: 'credor'}, inplace=True)

    # === BASE
    if base_df is not None:
        base_df['credor_normalizado'] = base_df['credor'].astype(str).apply(nome_limpo)
        df_base = base_df[base_df['credor_normalizado'] == nome_credor_normalizado]
        colunas_base = ['empresa', 'credor', 'documento', 'cliente', 'parcela', 'dt_emissao', 'valor_original']
        if all(col in df_base.columns for col in colunas_base):
            arquivos[f'{nome_arquivo_credor} - PGC {numero_pgc}.xlsx'] = df_base[colunas_base]

        # === EMISSÃO
        if not df_base.empty:
            emissao_rows = []
            CAMINHO_EMPRESAS = r"C:\PGC\envio_rendimentos\arquivos_gerados\EMPRESAS_NOMECURTO_CNPJ.xlsx"

            try:
                df_empresas = pd.read_excel(CAMINHO_EMPRESAS)
                df_empresas['empresa_normalizada'] = df_empresas['nome_curto'].astype(str).apply(nome_limpo)
            except Exception:
                df_empresas = pd.DataFrame()

            for empresa, grupo in df_base.groupby('empresa'):
                empresa_limpa = nome_limpo(empresa)
                cnpj = None

                if not df_empresas.empty:
                    linha = df_empresas[df_empresas['empresa_normalizada'] == empresa_limpa]
                    if not linha.empty:
                        cnpj = linha.iloc[0]['cnpj']

                cnpj = cnpj if cnpj else "CNPJ NÃO ENCONTRADO"

                emissao_rows.append({
                    'EMPRESA': empresa,
                    'CREDOR': credor.nome,
                    'CNPJ PARA EMISSÃO': cnpj,
                    'VALOR': grupo['valor_original'].sum()
                })

            df_emissao = pd.DataFrame(emissao_rows)
            arquivos[f'{nome_arquivo_credor} - PGC {numero_pgc} EMISSÃO.xlsx'] = df_emissao

    # === EXTRATO
    if extrato_df is not None:
        extrato_df['credor_normalizado'] = extrato_df['credor'].astype(str).apply(nome_limpo)
        df_ext = extrato_df[extrato_df['credor_normalizado'] == nome_credor_normalizado]
        colunas_ext = ['empresa', 'credor', 'documento', 'cliente', 'parcela', 'dt_emissao', 'valor_original', 'dt_vencimento']
        if all(col in df_ext.columns for col in colunas_ext):
            final_cols = colunas_ext + (['obs_baixa'] if 'obs_baixa' in df_ext.columns else [])
            arquivos[f'{nome_arquivo_credor} - EXTRATO.xlsx'] = df_ext[final_cols]

    # === PRODUTIVIDADE
    if prod_df is not None:
        prod_df['credor_normalizado'] = prod_df['credor'].astype(str).apply(nome_limpo)
        df_prod = prod_df[prod_df['credor_normalizado'] == nome_credor_normalizado]
        colunas_prod = ['empresa', 'credor', 'documento', 'cliente', 'parcela', 'dt_emissao', 'valor_original', 'dt_vencimento']
        if all(col in df_prod.columns for col in colunas_prod):
            mes_ano = datetime.today().strftime("%B-%Y").upper()
            arquivos[f'{nome_arquivo_credor} - PRODUTIVIDADE {mes_ano}.xlsx'] = df_prod[colunas_prod]

    # === SALVAR
    for nome_arquivo, df in arquivos.items():
        caminho_final = os.path.join(pasta_saida, nome_arquivo)
        df.to_excel(caminho_final, index=False)



#logger = logging.getLogger(__name__)

def encontrar_coluna_semelhante(coluna_alvo, colunas_existentes):
    correspondencias = get_close_matches(coluna_alvo.lower(), colunas_existentes, n=1, cutoff=0.6)
    return correspondencias[0] if correspondencias else None

def extrair_minimos_com_base_em_titulos(df):
    colunas_esperadas = {
        'credor': 'credor',
        'minimofixo_garantido_para_emissao_nf': 'minimo',
        'empresa_emissao_nf': 'empresa',
        'cnpj': 'cnpj'
    }
    colunas_existentes = [col.lower() for col in df.columns]
    mapeamento = {}

    for alvo, novo_nome in colunas_esperadas.items():
        coluna_encontrada = encontrar_coluna_semelhante(alvo, colunas_existentes)
        if not coluna_encontrada:
            raise ValueError(f'Coluna semelhante a "{alvo}" não encontrada.')
        mapeamento[coluna_encontrada] = novo_nome

    df = df.rename(columns=mapeamento)
    return df[['credor', 'minimo', 'empresa', 'cnpj']].dropna(subset=['credor'])

def extrair_minimos_por_coluna_fixa(caminho_arquivo, numero_pgc):
    wb = openpyxl.load_workbook(caminho_arquivo, data_only=True)
    aba_nome = f"PGC {numero_pgc}"
    aba = wb[aba_nome] if aba_nome in wb.sheetnames else wb.active
    ws = aba

    dados = []
    for row in ws.iter_rows(min_row=8):
        # Evita erro de índice
        if len(row) < 38:
            continue

        try:
            credor = row[29].value  # AD
            minimo = row[35].value  # AJ
            empresa = row[36].value  # AK
            cnpj = row[37].value    # AL
        except IndexError:
            continue

        if credor and minimo and empresa and cnpj:
            dados.append({
                'credor': str(credor).strip(),
                'minimo': minimo,
                'empresa': str(empresa).strip(),
                'cnpj': str(cnpj).strip()
            })

    if not dados:
        raise ValueError("Nenhuma linha válida encontrada na aba de mínimos.")

    return pd.DataFrame(dados)

def extrair_minimos_robusto(aba_pgcs_df, caminho_arquivo, numero_pgc):
    """
    Tenta extrair os dados de mínimo de forma resiliente:
    1. Primeiro tenta com os títulos normalizados
    2. Se falhar, tenta pelas posições fixas (colunas AD, AJ, AK, AL)
    """
    if aba_pgcs_df is not None:
        try:
            df_titulos = normalizar_colunas_com_duas_linhas(aba_pgcs_df.copy())
            logger.info("[MÍNIMO] Extração por título foi bem-sucedida.")
            return extrair_minimos_com_base_em_titulos(df_titulos)
        except Exception as e1:
            logger.warning(f'[MÍNIMO] Falha na extração por título: {e1}')
    else:
        logger.warning("[MÍNIMO] DataFrame da aba PGC está ausente.")

    # Fallback por posição
    try:
        logger.info("[MÍNIMO] Tentando extração por posição fixa.")
        return extrair_minimos_por_coluna_fixa(caminho_arquivo, numero_pgc)
    except Exception as e2:
        logger.error(f'[MÍNIMO] Falha também na extração por posição fixa: {e2}')
        raise Exception(f'Erro ao extrair dados de mínimo: {e2}')

'''###############################################################'''

def gerar_pdf_relatorio(credor):
    html_string = render_to_string('core/relatorio_pdf.html', {'Credor': credor})
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as output:
        HTML(string=html_string).write_pdf(output.name)
        return output.name


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

    # Verifica presença de mínimo
    info_minimo = ''
    caminho_minimo = os.path.join(settings.MEDIA_ROOT, 'PGC', str(historico.numero_pgc), 'mínimo.xlsx')
    if os.path.exists(caminho_minimo):
        try:
            df_minimo = pd.read_excel(caminho_minimo)
            for _, row in df_minimo.iterrows():
                if normalizar_nome(row['credor']) == normalizar_nome(credor.nome):
                    valor = row['minimo']
                    empresa = row['empresa']
                    cnpj = row['cnpj']
                    info_minimo = f"""
Mínimo garantido no valor de R$ {valor:,.2f}. Emitir nota para {empresa} - {cnpj}.
Notas devem ser enviadas até às 12h de QUARTA-FEIRA, dia 16/{historico.periodo}.

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

A PARTIR DE SETEMBRO/2024 AS NOTAS DEVEM SER EMITIDAS PARA AS EMPRESAS QUE CONSTAM NA PLANILHA "PGC {historico.numero_pgc} EMISSÃO".

{info_minimo}
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


def normalizar_colunas_simples(df):
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace('.', '', regex=False)
        .str.replace(' ', '_')
        .str.replace('ã', 'a')
        .str.replace('é', 'e')
        .str.replace('ç', 'c')
        .str.replace('ê', 'e')
        .str.replace('í', 'i')
    )
    return df


def normalizar_e_salvar_planilha_base(path_origem, numero_pgc):
    import os
    import pandas as pd
    from django.conf import settings

    planilhas = pd.read_excel(path_origem, sheet_name=None)
    pasta_saida = os.path.join(settings.MEDIA_ROOT, 'PGC', str(numero_pgc))
    os.makedirs(pasta_saida, exist_ok=True)

    numero_pgc_str = str(numero_pgc).zfill(2)
    pgc_tag = f"pgc{numero_pgc_str}"

    for nome_aba, df in planilhas.items():
        nome = nome_aba.strip().lower().replace(" ", "").replace("_", "")

        if nome.startswith(f"base{pgc_tag}"):
            df_base = normalizar_colunas_simples(df)
            df_base.to_excel(os.path.join(pasta_saida, f'BASE PGC {numero_pgc}.xlsx'), index=False)

        elif "extrato" in nome and "credor" in nome:
            df_ext = normalizar_colunas_simples(df)
            df_ext.to_excel(os.path.join(pasta_saida, 'EXTRATO.xlsx'), index=False)

        elif "produtividade" in nome:
            df_prod = normalizar_colunas_simples(df)
            df_prod.to_excel(os.path.join(pasta_saida, 'PRODUTIVIDADE.xlsx'), index=False)

        elif nome == pgc_tag:
            df.to_excel(os.path.join(pasta_saida, f'PGC {numero_pgc}.xlsx'), index=False)

    return os.path.join(pasta_saida, f'PGC {numero_pgc}.xlsx')
