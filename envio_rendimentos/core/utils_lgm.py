import pandas as pd
import traceback
import time
import re
import os
import unicodedata
import uuid
import traceback
from datetime import datetime

from django.utils import timezone
from django.conf import settings
from core.models import Credor, HistoricoPGC
from core.normalizacao import normalizar_nome
from django.db import IntegrityError
import random


# -----------------------------
# Helpers: resilient DB ops
# -----------------------------

def _resilient_get_or_create_credor(nome_normalizado, periodo, request_id, max_retries=10):
    """Try to get_or_create a Credor with retries to handle race conditions.

    Returns the Credor object or raises the last exception.
    """
    from django.db import IntegrityError as _IntegrityError
    # import here to avoid circular imports at module import time
    from core.utils_progress import touch_heartbeat
    from django.db.models.functions import Lower

    for attempt in range(1, max_retries + 1):
        try:
            # Use centralized helper to avoid race conditions and ensure normalization
            credor_obj, created = Credor.get_or_create_by_nome(nome_normalizado, defaults={'email': '', 'periodo': periodo})
            if created:
                log_progress(request_id, f"✅ Credor criado: {nome_normalizado}")
            return credor_obj
        except Exception as e:
            # If helper raised IntegrityError or other DB error, fallback to conservative retries
            log_progress(request_id, f"⚠️ Erro ao criar/obter Credor '{nome_normalizado}': {e}. Tentativa {attempt}/{max_retries}.")
            touch_heartbeat(request_id)
            # Try fallback lookups
            credor_obj = Credor.objects.filter(nome__iexact=nome_normalizado).first()
            if credor_obj:
                return credor_obj
            normalized = unicodedata.normalize("NFKC", nome_normalizado)
            credor_obj = Credor.objects.filter(nome__iexact=normalized).first()
            if credor_obj:
                return credor_obj
            credor_obj = Credor.objects.annotate(lower_nome=Lower('nome')).filter(lower_nome=nome_normalizado.lower()).first()
            if credor_obj:
                return credor_obj
            if attempt < max_retries:
                time.sleep(0.1 * attempt + random.random() * 0.05)
                continue
            else:
                time.sleep(0.5)
                credor_obj = Credor.objects.filter(nome__iexact=nome_normalizado).first()
                if credor_obj:
                    return credor_obj
                raise Credor.DoesNotExist




from .utils_progress import (
    log_progress,
    set_progress,
    finish_progress,
    error_progress,
    log_error,
)






EMPRESAS_PATH = r"C:\PGC\envio_rendimentos\arquivos_gerados\EMPRESAS_NOMECURTO_CNPJ.xlsx"

def carregar_empresas():
    df = pd.read_excel(EMPRESAS_PATH)
    df = normalizar_colunas(df)

    col_nome = encontrar_coluna(df, ["nome_curto", "nome_completo", "empresa"])
    col_cnpj = encontrar_coluna(df, ["cnpj"])

    if not col_nome or not col_cnpj:
        raise Exception(
            "Planilha EMPRESAS_NOMECURTO_CNPJ.xlsx deve conter colunas "
            "'nome_curto' (ou nome_completo) e 'cnpj'"
        )

    # normaliza chave exatamente como vem da BASE PGC
    df[col_nome] = df[col_nome].astype(str).str.strip()
    df[col_cnpj] = df[col_cnpj].astype(str).str.strip()

    return dict(zip(df[col_nome], df[col_cnpj]))








# =========================================================
# UTIL: Normalizar o nome do credor
# =========================================================

def limpar_nome_credor(nome):
    nome = str(nome)

    # remove prefixo numérico "24 - "
    nome = re.sub(r"^\d+\s*-\s*", "", nome)

    # remove textos entre parênteses
    nome = re.sub(r"\(.*?\)", "", nome)

    # normaliza espaços
    nome = re.sub(r"\s+", " ", nome)

    return nome.strip()








# =========================================================
# UTIL: extrair número do PGC a partir do nome das abas
# =========================================================
def extrair_numero_pgc(sheet_names):
    for name in sheet_names:
        match = re.search(r'PGC\s*(\d+)', name, re.IGNORECASE)
        if match:
            return match.group(1)  # Sem zfill, manter número original
    raise Exception("Número do PGC não encontrado nas abas da planilha")


# =========================================================
# UTIL: localizar abas importantes
# =========================================================
def localizar_abas(sheet_names, numero_pgc):
    abas = {}
    # Usar o número como está (com ou sem zero) para localizar as abas
    pgc_original = str(numero_pgc)  # manter exatamente como foi extraído

    for name in sheet_names:
        lname = name.lower().strip()

        if "base" in lname and "pgc" in lname and pgc_original in lname:
            abas["base"] = name
        elif "extrato" in lname:
            abas["extrato"] = name
        elif "produtividade" in lname or "perodutividade" in lname:
            abas["produtividade"] = name
        elif lname.startswith("pgc") and pgc_original in lname:
            abas["minimo"] = name

    faltando = [k for k in ["base", "extrato", "produtividade", "minimo"] if k not in abas]
    if faltando:
        raise Exception(
            f"Aba(s) obrigatória(s) não encontrada(s): {faltando}. "
            f"Abas disponíveis: {sheet_names}"
        )

    return abas


# =========================================================
# UTIL: normalizar colunas
# =========================================================
def normalizar_colunas(df):
    def normalizar(col):
        col = str(col).strip().lower()
        col = unicodedata.normalize("NFKD", col)
        col = col.encode("ascii", "ignore").decode("utf-8")
        col = re.sub(r"[^\w]+", "_", col)
        col = re.sub(r"_+", "_", col)
        return col.strip("_")

    df.columns = [normalizar(c) for c in df.columns]
    return df


# =========================================================
# UTIL: encontrar coluna por candidatos
# =========================================================
def encontrar_coluna(df, candidatos):
    for col in df.columns:
        for c in candidatos:
            if c == col or c in col:
                return col
    return None


# =========================================================
# UTIL: mapear erro técnico para mensagem amigável e tipo
# =========================================================

def map_error_message(e, technical=''):
    s = str(e) if technical == '' else technical

    # Integridade / duplicidade
    if isinstance(e, IntegrityError) or 'UNIQUE constraint' in s:
        return ("Duplicidade detectada: já existe cadastro para este credor.", "duplicidade")

    # Registro não encontrado
    if 'matching query' in s or 'does not exist' in s.lower():
        return ("Credor não encontrado durante a associação.", "not_found")

    # Erros de formato / dados
    if isinstance(e, ValueError) or 'valueerror' in s.lower():
        return ("Erro no formato dos dados do credor.", "format")

    # Erro genérico
    return ("Erro interno ao processar o credor. Verifique o log técnico para mais detalhes.", "unknown")


# =========================================================
# LEITURA DA ABA MINIMO (layout fixo - NOVO PGC)
# =========================================================

def ler_minimo(path, aba):
    """
    Lê a aba de mínimo no layout esperado.

    NOVO LAYOUT PGC:
        CREDOR            -> AG (index 32)
        MINIMO            -> AO (index 40)
        EMPRESA EMISSÃO   -> AP (index 41)
        CNPJ              -> AQ (index 42)

    Observações importantes:
    - Considera as linhas a partir da linha 8 (índice 7) inclusive
    """

    df_raw = pd.read_excel(path, sheet_name=aba, header=None)

    dados = []

    for i in range(7, len(df_raw)):
        credor = df_raw.iloc[i, 32]   # AG
        minimo = df_raw.iloc[i, 40]   # AO
        empresa = df_raw.iloc[i, 41]  # AP
        cnpj = df_raw.iloc[i, 42]     # AQ

        if pd.isna(credor):
            continue

        dados.append({
            "credor": str(credor).strip(),
            "minimo": minimo,
            "empresa_emissao": str(empresa).strip() if not pd.isna(empresa) else "",
            "cnpj": str(cnpj).strip() if not pd.isna(cnpj) else "",
        })

    return pd.DataFrame(dados)




def _normalize_key(s):
    import unicodedata, re
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize('NFKD', s)
    s = s.encode('ascii', 'ignore').decode('utf-8')
    s = re.sub(r"[^a-z0-9]+", ' ', s).strip()
    return s


def gerar_minimo(arquivo_path, aba_minimo, numero_pgc_pasta, base_output, request_id=None):
    """Gera o arquivo `minimo.xlsx` no diretório do PGC.

    Regras aplicadas:
    - Usa a aba identificada como 'minimo' na planilha enviada
    - Considera linhas a partir da linha 8 (inclusa)
    - Mapeia colunas:
        CREDOR <- AJ
        MINIMO/FIXO GARANTIDO PARA EMISSAO NF <- AO
        EMPRESA EMISSÃO NF <- AP
        CNPJ <- obtido via lookup em EMPRESAS_NOMECURTO_CNPJ.xlsx (nome curto)
    - Inclui apenas linhas com valor de mínimo preenchido e diferente de zero
    """
    try:
        df_min = ler_minimo(arquivo_path, aba_minimo)
    except Exception as e:
        if request_id:
            log_progress(request_id, f"⚠️ Falha ao ler aba de mínimo: {e}")
        return

    # Carrega mapa empresa -> cnpj (nome curto)
    try:
        empresas_cnpj_raw = carregar_empresas()
    except Exception:
        empresas_cnpj_raw = {}
        if request_id:
            log_progress(request_id, "⚠️ Falha ao carregar tabela de empresas; CNPJ ficará vazio")

    # normalize keys for robust matching
    empresas_cnpj = { _normalize_key(k): v for k, v in empresas_cnpj_raw.items() }

    if df_min.empty:
        df_out = pd.DataFrame(columns=["CREDOR", "MINIMO/FIXO GARANTIDO PARA EMISSAO NF", "EMPRESA EMISSÃO NF", "CNPJ"])
    else:
        # Garantir que o campo mínimo seja numérico para filtro
        df_min['minimo_num'] = pd.to_numeric(df_min['minimo'], errors='coerce')
        df_valid = df_min[df_min['minimo_num'].notna() & (df_min['minimo_num'] != 0)].copy()

        # Lookup CNPJ by normalized company short name (AP)
        def lookup_cnpj(empresa_val):
            key = _normalize_key(empresa_val)
            return empresas_cnpj.get(key, "")

        df_valid['CNPJ'] = df_valid['empresa_emissao'].apply(lookup_cnpj)

        df_out = df_valid.rename(columns={
            'credor': 'CREDOR',
            'minimo': 'MINIMO/FIXO GARANTIDO PARA EMISSAO NF',
            'empresa_emissao': 'EMPRESA EMISSÃO NF',
        })[["CREDOR", "MINIMO/FIXO GARANTIDO PARA EMISSAO NF", "EMPRESA EMISSÃO NF", "CNPJ"]]

    # Caminho de saída conforme regra (nome em MAIÚSCULAS)
    destino = os.path.join(base_output, 'MINIMO.xlsx')

    try:
        df_out.to_excel(destino, index=False)
        if request_id:
            log_progress(request_id, f"✅ Arquivo MINIMO.xlsx gerado em {destino}")
        # format workbook if available
        try:
            from core.formatting import format_workbook
            format_workbook(destino)
        except Exception:
            pass
    except Exception as e:
        if request_id:
            log_progress(request_id, f"❌ Falha ao salvar MINIMO.xlsx: {e}")
        return


# =========================================================
# PROCESSAMENTO PRINCIPAL
# =========================================================
def processar_pgc_lgm(request_id, arquivo_path):
    """Main processor for LGM PGC.

    This implementation is a focused, robust pipeline:
    - reads xls with timeout
    - extracts PGC number and required sheets
    - reads BASE/EXTRATO/PRODUTIVIDADE with timeouts
    - initializes per-credor metadata
    - loops over credores, writes minimal files, updates per-credor status and global progress
    - touches heartbeat frequently to avoid watchdog false positives
    """
    from core.utils_progress import set_progress, log_progress, touch_heartbeat, set_credor_status, finish_progress, error_progress, init_credores

    try:
        log_progress(request_id, "📄 Iniciando processamento do PGC LGM")

        # Load workbook with timeout
        import concurrent.futures
        def _open_xls(path):
            return pd.ExcelFile(path)

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_open_xls, arquivo_path)
                xls = future.result(timeout=60)
            log_progress(request_id, "✅ Arquivo carregado. Iniciando parsing...")
        except concurrent.futures.TimeoutError:
            log_progress(request_id, "❌ Timeout ao ler arquivo (pd.ExcelFile) — operação demorou mais que 60s")
            error_progress(request_id, 'Timeout ao ler arquivo de entrada')
            return
        except Exception as e:
            log_progress(request_id, f"❌ Erro ao ler arquivo: {e}")
            error_progress(request_id, f'Erro ao ler arquivo: {e}')
            return

        # identify PGC and sheets
        try:
            numero_pgc = extrair_numero_pgc(xls.sheet_names)
            numero_pgc_pasta = str(int(numero_pgc)) if numero_pgc.isdigit() else numero_pgc
            log_progress(request_id, f"🔎 PGC identificado: {numero_pgc} (pasta: {numero_pgc_pasta})")
            abas = localizar_abas(xls.sheet_names, numero_pgc_pasta)
        except Exception as e:
            log_progress(request_id, f"❌ Falha na identificação do PGC/abas: {e}")
            error_progress(request_id, str(e))
            return

        # read the base sheet with timeout
        def _read_sheet(excel, sheet):
            return pd.read_excel(excel, sheet_name=sheet)
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                df_base = normalizar_colunas(executor.submit(_read_sheet, xls, abas['base']).result(timeout=120))
        except concurrent.futures.TimeoutError:
            log_progress(request_id, "❌ Timeout ao ler aba BASE")
            error_progress(request_id, 'Timeout ao ler aba BASE')
            return
        except Exception as e:
            log_progress(request_id, f"❌ Erro ao ler aba BASE: {e}")
            error_progress(request_id, str(e))
            return

        col_credor = encontrar_coluna(df_base, ["credor", "consultor", "corretor", "representante"])
        if not col_credor:
            error_progress(request_id, 'Coluna de credor não encontrada')
            return

        df_base[col_credor] = df_base[col_credor].astype(str).str.strip()
        df_base['credor_limpo'] = df_base[col_credor].apply(limpar_nome_credor)
        df_base['credor_canonico'] = df_base['credor_limpo'].apply(normalizar_nome)

        # identificar colunas auxiliares usadas no processamento
        col_empresa = encontrar_coluna(df_base, ['empresa', 'empresa_emissao', 'empresa_nome', 'fornecedor'])
        col_documento = encontrar_coluna(df_base, ['documento', 'doc', 'num_doc'])
        col_cliente = encontrar_coluna(df_base, ['cliente', 'cliente_nome'])
        col_parcela = encontrar_coluna(df_base, ['parcela', 'parc'])
        col_data = encontrar_coluna(df_base, ['data', 'data_pagamento', 'data_pag'])
        col_valor = encontrar_coluna(df_base, ['valor', 'valor_total', 'valor_pago'])

        credores = df_base['credor_canonico'].dropna().unique().tolist()
        set_progress(request_id, total=len(credores))
        log_progress(request_id, f"👥 {len(credores)} credores encontrados")

        # init per-credor metadata and touch heartbeat
        from core.normalizacao import slugify_name
        credores_map = {slugify_name(c): c for c in credores}
        init_credores(request_id, credores_map)
        touch_heartbeat(request_id)

        # mapa empresa->cnpj usado na emissão (opcional)
        try:
            empresas_cnpj = carregar_empresas()
        except Exception:
            empresas_cnpj = {}
            log_progress(request_id, "⚠️ Falha ao carregar tabela de empresas; emissão terá CNPJ vazio")

        # read other sheets with timeout (extrato, produtividade)
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                df_extrato = normalizar_colunas(executor.submit(_read_sheet, xls, abas['extrato']).result(timeout=120))
                df_prod = normalizar_colunas(executor.submit(_read_sheet, xls, abas['produtividade']).result(timeout=120))
        except concurrent.futures.TimeoutError:
            log_progress(request_id, "❌ Timeout ao ler abas auxiliares")
            error_progress(request_id, 'Timeout ao ler abas auxiliares')
            return
        except Exception as e:
            log_progress(request_id, f"❌ Erro ao ler abas auxiliares: {e}")
            error_progress(request_id, str(e))
            return

        # Ensure extrato/produtividade contain a canonical creditor column
        try:
            # Determine candidate column name for 'credor' in these sheets
            def _prepare_sheet(df, sheet_name):
                if df is None:
                    return pd.DataFrame()
                # prefer the same column used in BASE if present
                col = col_credor if ('col_credor' in locals() and col_credor in df.columns) else encontrar_coluna(df, ["credor", "consultor", "corretor", "representante"])
                if not col:
                    # leave as empty df so later logic logs absence
                    return pd.DataFrame()
                df[col] = df[col].astype(str).str.strip()
                # Use limpar_nome_credor (defined above) to remove prefixes/sufixos
                df['credor_limpo'] = df[col].apply(limpar_nome_credor)
                # Use normalizar_nome (from core.normalizacao) to create canonical form
                df['credor_canonico'] = df['credor_limpo'].apply(normalizar_nome)
                return df

            df_extrato = _prepare_sheet(df_extrato, 'extrato')
            df_prod = _prepare_sheet(df_prod, 'produtividade')
        except Exception as e:
            log_progress(request_id, f"⚠️ Falha ao preparar colunas de credor em extrato/prod: {e}")
            # continue — sheets may simply not have credor column and will be treated as empty

        # base output folder
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        base_output = os.path.join(BASE_DIR, 'arquivos_gerados', 'PGC', str(int(numero_pgc) if numero_pgc.isdigit() else numero_pgc))
        os.makedirs(base_output, exist_ok=True)

        # ✅ Gerar arquivo minimo.xlsx para PGCs do Laghetto Golden (regras específicas)
        try:
            gerar_minimo(arquivo_path, abas['minimo'], numero_pgc_pasta, base_output, request_id=request_id)
        except Exception as e:
            log_progress(request_id, f"⚠️ Falha ao gerar minimo.xlsx: {e}")

        # === Gerar arquivo de DESCONTOS automaticamente (após MINIMO)
        try:
            try:
                from core.utils import processar_minimo_e_descontos_unificado
            except Exception:
                processar_minimo_e_descontos_unificado = None

            if processar_minimo_e_descontos_unificado:
                registros_minimos, registros_retencao, registros_cestas = processar_minimo_e_descontos_unificado(
                    caminho_arquivo=arquivo_path,
                    numero_pgc=numero_pgc_pasta,
                    pasta_saida=base_output,
                    salvar_minimo=False,
                    salvar_descontos=False
                )

                # Monta DataFrame único com apenas linhas que possuem desconto
                rows = []
                for r in registros_retencao or []:
                    v = r.get('valor') if isinstance(r, dict) else None
                    if v is not None and str(v).strip() != '':
                        rows.append({
                            'CREDOR': r.get('credor'),
                            'VALOR': v,
                            'EMPRESA_DESCONTO': r.get('empresa'),
                            'TIPO': 'RETENCAO'
                        })
                for r in registros_cestas or []:
                    v = r.get('valor') if isinstance(r, dict) else None
                    if v is not None and str(v).strip() != '':
                        rows.append({
                            'CREDOR': r.get('credor'),
                            'VALOR': v,
                            'EMPRESA_DESCONTO': r.get('empresa'),
                            'TIPO': 'CESTA'
                        })

                if rows:
                    df_descontos = pd.DataFrame(rows)
                    destino_descontos = os.path.join(base_output, 'DESCONTOS.xlsx')
                    try:
                        df_descontos.to_excel(destino_descontos, index=False)
                        log_progress(request_id, f"✅ Arquivo DESCONTOS.xlsx gerado em {destino_descontos}")
                        try:
                            from core.formatting import format_workbook
                            format_workbook(destino_descontos)
                        except Exception:
                            pass
                    except Exception as e:
                        log_progress(request_id, f"⚠️ Falha ao salvar DESCONTOS.xlsx: {e}")
                else:
                    log_progress(request_id, "ℹ️ Nenhum desconto encontrado; arquivo DESCONTOS.xlsx não será gerado.")
        except Exception as e:
            log_progress(request_id, f"⚠️ Falha ao processar/generar arquivo de descontos: {e}")

        # =====================================================
        # MAPA DE NOME CANÔNICO → NOME EXIBÍVEL
        # (usa o primeiro nome limpo encontrado na planilha)
        # =====================================================
        mapa_nome_exibicao = (
            df_base
            .drop_duplicates("credor_canonico")
            .set_index("credor_canonico")["credor_limpo"]
            .to_dict()
        )

        # =====================================================
        # 7️⃣ LOOP POR CREDOR
        # =====================================================
        periodo = timezone.now().strftime("%m/%Y")
        # nomes de arquivo não devem conter '/', que vira separador de pastas no Windows
        safe_periodo = periodo.replace('/', '-')
        total_credores = len(credores)

        for idx, credor in enumerate(credores, start=1):
            # Log individual do credor sendo processado
            log_progress(request_id, f"📋 Processando credor {idx}/{total_credores}: {credor}")

            # nome para exibição / arquivos (com acento, sem sufixos)
            nome_exibicao = mapa_nome_exibicao.get(credor, credor)
            # nome_para_exibicao: usar para pastas e nomes de arquivos (MAIÚSCULAS, com espaços)
            from core.utils import normalizar_nome_completo
            nome_para_exibicao = normalizar_nome_completo(nome_exibicao)

            # Registrar status individual do credor para permitir reprocessamento seletivo
            from core.normalizacao import normalize_filename
            slug = normalize_filename(credor)
            from core.utils_progress import set_credor_status, touch_heartbeat, set_progress

            # mark as processing and indicate start of per-credor pipeline
            set_credor_status(request_id, slug, 'PROCESSING', display=nome_exibicao, last_step='started')
            # update current_credor and progress percent referring to previous completed ones
            set_progress(request_id, processed=(idx - 1), percent=int((idx - 1) / total_credores * 100), credor=nome_exibicao)
            touch_heartbeat(request_id)

            # -----------------------------
            # PREPARAÇÃO DA PASTA DO CREDOR
            # -----------------------------
            slug = normalize_filename(nome_exibicao)
            # Pastas devem usar o NOME PARA EXIBIÇÃO (sem underscores)
            pasta_credor = os.path.join(base_output, nome_para_exibicao)
            os.makedirs(pasta_credor, exist_ok=True)
            # persistir dados por credor para permitir reprocessamento sem novo upload
            processing_dir = os.path.join(settings.MEDIA_ROOT, 'processing', request_id, 'credores')
            os.makedirs(processing_dir, exist_ok=True)


            # -----------------------------
            # BASE PGC DO CREDOR
            # -----------------------------
            cols = [c for c in [col_empresa, col_credor, col_documento, col_cliente, col_parcela, col_data, col_valor] if c]
            pgc_credor = df_base[
                df_base["credor_canonico"] == normalizar_nome(credor)
            ][cols] if cols else df_base[df_base["credor_canonico"] == normalizar_nome(credor)]

            # serializar os dados essenciais do credor para reprocessamento (JSON)
            try:
                pgc_credor.to_json(os.path.join(processing_dir, f"{slug}.json"), orient='records', force_ascii=False)
                touch_heartbeat(request_id)
            except Exception:
                # fallback para csv
                pgc_credor.to_csv(os.path.join(processing_dir, f"{slug}.csv"), index=False)
                touch_heartbeat(request_id)

            # -------------------------------------------------
            # Normaliza e valida coluna de valor (robustez)
            # -------------------------------------------------
            if col_valor and col_valor in pgc_credor.columns:
                # remove caracteres estranhos e convert commas to dots
                original = pgc_credor[col_valor].astype(str)
                cleaned = original.str.replace(r'[^0-9,\.-]', '', regex=True).str.replace(',', '.', regex=False)
                pgc_credor[col_valor] = pd.to_numeric(cleaned, errors='coerce')

                # registra linhas inválidas e remove antes de prosseguir
                invalid = pgc_credor[pgc_credor[col_valor].isna()]
                if not invalid.empty:
                    for i, row in invalid.iterrows():
                        val = original.loc[i]
                        err_obj = {
                            'id': str(uuid.uuid4()),
                            'request_id': request_id,
                            'credor': nome_normalizado if 'nome_normalizado' in locals() else credor,
                            'credor_display': nome_exibicao if 'nome_exibicao' in locals() else credor,
                            'step': 'processamento',
                            'technical': f"Valor inválido na coluna '{col_valor}': {repr(val)}",
                            'friendly': f"Valor inválido para {credor}: {val}",
                            'type': 'bad_value',
                            'time': datetime.now().strftime('%H:%M:%S'),
                            'retries': 0,
                            'resolved': False,
                        }
                        log_error(request_id, err_obj)
                    # drop invalid rows
                    pgc_credor = pgc_credor[pgc_credor[col_valor].notna()].copy()

            if pgc_credor.empty:
                log_progress(
                    request_id,
                    f"⚠️ Nenhum registro encontrado para o credor {credor}"
                )
                continue

                # =====================================================
            # REGISTRO / ATUALIZAÇÃO DE CREDOR (NOME CANÔNICO)
            # =====================================================
            try:
                nome_normalizado = normalizar_nome(credor)

                # Tenta obter/criar de forma resiliente para evitar IntegrityError
                try:
                    credor_obj = _resilient_get_or_create_credor(nome_normalizado, periodo, request_id, max_retries=6)
                except Exception as e:
                    tb = traceback.format_exc()
                    log_progress(request_id, f"❌ Erro ao criar/obter Credor '{nome_normalizado}': {e}")
                    # registrar erro estruturado por credor e continuar
                    friendly, etype = map_error_message(e, str(e)) if 'map_error_message' in globals() else ("Erro ao criar credor","db_error")
                    err_obj = {
                        'id': str(uuid.uuid4()),
                        'request_id': request_id,
                        'credor': nome_normalizado,
                        'credor_display': nome_exibicao,
                        'step': 'processamento',
                        'technical': str(e) + '\n' + tb,
                        'friendly': friendly,
                        'type': etype,
                        'time': datetime.now().strftime('%H:%M:%S'),
                        'retries': 0,
                        'resolved': False,
                    }
                    log_error(request_id, err_obj)
                    set_credor_status(request_id, nome_normalizado, 'ERROR', display=nome_exibicao, last_step='failed', error_message=friendly)
                    # count as processed attempt and continue
                    set_progress(request_id, processed=idx, percent=int(idx / total_credores * 100), credor=None)
                    touch_heartbeat(request_id)
                    continue

                # Garante atualização do período
                if credor_obj.periodo != periodo:
                    credor_obj.periodo = periodo
                    credor_obj.save(update_fields=["periodo"])

                # =====================================================
                # REGISTRO / ATUALIZAÇÃO DE HISTÓRICO PGC
                # =====================================================
                from decimal import Decimal
                valor_total = pgc_credor[col_valor].sum()
                # ensure Decimal type for DB field
                try:
                    valor_total = Decimal(str(valor_total))
                except Exception:
                    valor_total = Decimal(float(valor_total))
                numero_pgc_int = int(numero_pgc_pasta)  # Usar número sem zeros para o banco

                historico, criado = HistoricoPGC.objects.get_or_create(
                    credor=credor_obj,
                    numero_pgc=numero_pgc_int,
                    defaults={
                        "periodo": periodo,
                        "valor_total": valor_total,
                        "grupo": getattr(credor_obj, 'grupo', None),
                    }
                )

                if not criado:
                    historico.periodo = periodo
                    historico.valor_total = valor_total
                    historico.save(update_fields=["periodo", "valor_total"])

                # -----------------------------
                # ARQUIVO BASE PGC (USADO EM OUTROS FLUXOS)
                # -----------------------------
                pgc_credor.to_excel(
                    os.path.join(
                        pasta_credor,
                        f"{nome_para_exibicao} - PGC {numero_pgc_pasta}.xlsx"
                    ),
                    index=False
                )
                # Format the generated workbook
                try:
                    from core.formatting import format_workbook
                    target_pgc = os.path.join(pasta_credor, f"{nome_para_exibicao} - PGC {numero_pgc_pasta}.xlsx")
                    format_workbook(target_pgc)
                except Exception as e:
                    log_progress(request_id, f"⚠️ Falha ao formatar {target_pgc}: {e}")

                # -----------------------------
                # EMISSÃO
                # -----------------------------
                emissao = (
                    pgc_credor
                    .groupby(col_empresa, as_index=False)[col_valor]
                    .sum()
                )

                emissao.insert(1, "credor", credor)

                emissao["cnpj_para_emissao"] = emissao[col_empresa].apply(
                    lambda x: empresas_cnpj.get(str(x).strip(), "")
                    if pd.notna(x) else ""
                )

                emissao.rename(columns={col_valor: "valor"}, inplace=True)

                emissao = emissao[
                    [col_empresa, "credor", "cnpj_para_emissao", "valor"]
                ]

                emissao.to_excel(
                    os.path.join(
                        pasta_credor,
                        f"{nome_para_exibicao} - PGC {numero_pgc_pasta} EMISSÃO.xlsx"
                    ),
                    index=False
                )
                try:
                    from core.formatting import format_workbook
                    target_emissao = os.path.join(pasta_credor, f"{nome_para_exibicao} - PGC {numero_pgc_pasta} EMISSÃO.xlsx")
                    format_workbook(target_emissao)
                except Exception as e:
                    log_progress(request_id, f"⚠️ Falha ao formatar {target_emissao}: {e}")

                # -----------------------------
                # EXTRATO
                # -----------------------------
                if 'credor_canonico' in df_extrato.columns:
                    extrato_credor = df_extrato[df_extrato["credor_canonico"] == credor]
                else:
                    extrato_credor = pd.DataFrame()

                if not extrato_credor.empty:
                    extrato_credor.to_excel(
                        os.path.join(
                            pasta_credor,
                            f"{nome_para_exibicao} - EXTRATO.xlsx"
                        ),
                        index=False
                    )
                    try:
                        from core.formatting import format_workbook
                        target_extrato = os.path.join(pasta_credor, f"{nome_para_exibicao} - EXTRATO.xlsx")
                        format_workbook(target_extrato)
                    except Exception as e:
                        log_progress(request_id, f"⚠️ Falha ao formatar {target_extrato}: {e}")
                else:
                    # Log se extrato estiver vazio
                    log_progress(request_id, f"⚠️ Nenhum extrato encontrado para {credor}")

                # -----------------------------
                # PRODUTIVIDADE
                # -----------------------------
                if 'credor_canonico' in df_prod.columns:
                    prod_credor = df_prod[df_prod["credor_canonico"] == credor]
                else:
                    prod_credor = pd.DataFrame()

                if not prod_credor.empty:
                    prod_credor.to_excel(
                        os.path.join(
                            pasta_credor,
                            f"{nome_para_exibicao} - PRODUTIVIDADE {safe_periodo}.xlsx"
                        ),
                        index=False
                    )
                    try:
                        from core.formatting import format_workbook
                        target_prod = os.path.join(pasta_credor, f"{nome_para_exibicao} - PRODUTIVIDADE {safe_periodo}.xlsx")
                        format_workbook(target_prod)
                    except Exception as e:
                        log_progress(request_id, f"⚠️ Falha ao formatar {target_prod}: {e}")
                else:
                    # Log se produtividade estiver vazia
                    log_progress(request_id, f"⚠️ Nenhuma produtividade encontrada para {credor}")

                time.sleep(0.03)

            except Exception as e:
                # Captura erros por credor, registra estrutura de erro, salva stack trace e continua
                tb = traceback.format_exc()
                technical = str(e)
                friendly, etype = map_error_message(e, technical)
                err_obj = {
                    "id": str(uuid.uuid4()),
                    "request_id": request_id,
                    "credor": nome_normalizado if 'nome_normalizado' in locals() else slug,
                    "credor_display": nome_exibicao,
                    "step": 'processamento',
                    "technical": technical + '\n' + tb,
                    "friendly": friendly,
                    "type": etype,
                    "time": datetime.now().strftime('%H:%M:%S'),
                    "retries": 0,
                    "resolved": False,
                }
                # write per-credor error trace
                try:
                    err_dir = os.path.join(settings.MEDIA_ROOT, 'processing', request_id, 'credores')
                    os.makedirs(err_dir, exist_ok=True)
                    trace_path = os.path.join(err_dir, f"{slug}_error.txt")
                    with open(trace_path, 'w', encoding='utf-8') as tf:
                        tf.write(tb)
                    log_progress(request_id, f"🔍 Stack trace para {nome_exibicao} escrita em {trace_path}")
                except Exception:
                    pass

                log_error(request_id, err_obj)
                # set per-credor status to ERROR with message
                set_credor_status(request_id, slug, 'ERROR', display=nome_exibicao, last_step='failed', error_message=friendly)
                log_progress(request_id, f"❌ Erro ao processar {nome_exibicao}: {friendly}")
                # count as processed attempt
                set_progress(request_id, processed=idx, percent=int(idx / total_credores * 100), credor=None)
                touch_heartbeat(request_id)
                continue
            # =====================================================
            # REGISTRO / ATUALIZAÇÃO DE HISTÓRICO PGC
            # =====================================================
            from decimal import Decimal
            valor_total = pgc_credor[col_valor].sum()
            try:
                valor_total = Decimal(str(valor_total))
            except Exception:
                valor_total = Decimal(float(valor_total))
            numero_pgc_int = int(numero_pgc_pasta)  # Usar número sem zeros para o banco

            historico, criado = HistoricoPGC.objects.get_or_create(
                credor=credor_obj,
                numero_pgc=numero_pgc_int,
                defaults={
                    "periodo": periodo,
                    "valor_total": valor_total,
                    "grupo": getattr(credor_obj, 'grupo', None),
                }
            )

            if not criado:
                historico.periodo = periodo
                historico.valor_total = valor_total
                historico.save(update_fields=["periodo", "valor_total"])

            

            # marcar sucesso do credor e salvar metadados
            try:
                files_saved = []
                # Collect generated files in the credor folder
                for fname in os.listdir(pasta_credor):
                    files_saved.append(os.path.join(pasta_credor, fname))
                set_credor_status(request_id, slug, 'SUCCESS', display=nome_exibicao, last_step='completed', files=files_saved)
                log_progress(request_id, f"✅ Credor {nome_exibicao} processado com sucesso")
            except Exception:
                # se falhar ao listar arquivos, não abortar o job
                set_credor_status(request_id, slug, 'SUCCESS', display=nome_exibicao, last_step='completed')

            # finalize per-credor progress: increment processed
            set_progress(request_id, processed=idx, percent=int(idx / total_credores * 100), credor=None)
            touch_heartbeat(request_id)

        # Log de resumo final
        log_progress(request_id, f"📊 Resumo: {total_credores} credores processados com sucesso")
        log_progress(request_id, f"📂 Pasta criada: arquivos_gerados/PGC/{numero_pgc_pasta}")
        finish_progress(request_id)
        log_progress(request_id, "🏁 Processamento finalizado com sucesso")
        log_progress(request_id, f"🎯 PGC {numero_pgc_pasta} - Todos os arquivos gerados com sucesso!")


    except Exception as e:
        tb = traceback.format_exc()
        traceback.print_exc()
        log_progress(request_id, f"❌ ERRO FATAL: {str(e)}")
        log_progress(request_id, f"🔍 Verifique o arquivo de origem e tente novamente")
        try:
            friendly, etype = map_error_message(e, str(e))
        except Exception:
            friendly, etype = ("Erro fatal no processamento.", "fatal")
        err_obj = {
            'id': str(uuid.uuid4()),
            'request_id': request_id,
            'credor': None,
            'credor_display': None,
            'step': 'fatal',
            'technical': str(e) + '\n' + tb,
            'friendly': friendly,
            'type': etype,
            'time': datetime.now().strftime('%H:%M:%S'),
            'retries': 0,
            'resolved': False,
        }
        log_error(request_id, err_obj)
        error_progress(request_id, str(e))

def reprocessar_credores(request_id, credor_slugs, initiated_by=None, job_id=None):
    """Reprocess a list of credors using data saved during the initial processing.

    - Loads saved per-credor data from MEDIA_ROOT/processing/<request_id>/credores/<slug>.json
    - Reaplica as etapas necessárias (DB updates and file generation)
    - Updates per-credor status and logs
    - If job_id provided, updates the reprocess job progress
    """
    from core.utils_progress import set_credor_status, log_progress, resolve_errors_for_credor, update_reprocess_job, get_reprocess_job, get_progress, touch_heartbeat
    processing_dir = os.path.join(settings.MEDIA_ROOT, 'processing', request_id, 'credores')

    log_progress(request_id, f"🔁 Reprocessamento iniciado por {initiated_by or 'sistema'}: {len(credor_slugs)} credores")

    total = len(credor_slugs)
    processed = 0

    for slug in credor_slugs:
        # Skip credores already successful
        current = get_progress(request_id).get('credores', {}).get(slug, {})
        if current.get('status') == 'SUCCESS':
            log_progress(request_id, f"ℹ️ Credor {slug} já em SUCCESS — pulando reprocessamento")
            continue

        set_credor_status(request_id, slug, 'PROCESSING', last_step='reprocess_started')

        # update job
        processed += 1
        if job_id:
            update_reprocess_job(job_id, processed=processed, log_msg=f'Iniciando {slug}')
        touch_heartbeat(request_id)

        # load data
        json_path = os.path.join(processing_dir, f"{slug}.json")
        csv_path = os.path.join(processing_dir, f"{slug}.csv")
        if os.path.exists(json_path):
            try:
                df = pd.read_json(json_path, orient='records')
            except Exception as e:
                log_progress(request_id, f"❌ Falha ao ler dados salvos para {slug}: {e}")
                set_credor_status(request_id, slug, 'error')
                if job_id:
                    update_reprocess_job(job_id, log_msg=f'Falha ao ler dados de {slug}')
                continue
        elif os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
            except Exception as e:
                log_progress(request_id, f"❌ Falha ao ler CSV de dados para {slug}: {e}")
                set_credor_status(request_id, slug, 'error')
                if job_id:
                    update_reprocess_job(job_id, log_msg=f'Falha ao ler CSV de {slug}')
                continue
        else:
            log_progress(request_id, f"❌ Dados de reprocessamento não encontrados para {slug}")
            set_credor_status(request_id, slug, 'error')
            if job_id:
                update_reprocess_job(job_id, log_msg=f'Dados não encontrados para {slug}')
            continue

        # Convert back to the structures used in main flow
        try:
            # infer display name from store if possible
            display = get_progress(request_id).get('credores', {}).get(slug, {}).get('display')
            display = display or slug

            # now re-run the minimal necessary steps: credor get_or_create, historico update, files regeneration
            nome_normalizado = slug  # slug is ASCII normalized

            # Prefer the resilient helper to avoid IntegrityError races
            try:
                credor_obj = _resilient_get_or_create_credor(nome_normalizado, timezone.now().strftime('%m/%Y'), request_id, max_retries=6)
            except Exception as e:
                # fallback to the centralized resilient factory which handles normalization + race conditions
                try:
                    credor_obj, _ = Credor.get_or_create_by_nome(
                        nome_normalizado,
                        defaults={
                            'email': '',
                            'periodo': timezone.now().strftime('%m/%Y')
                        }
                    )
                except Exception:
                    # attempt safe retrievals before giving up
                    credor_obj = Credor.objects.filter(nome_normalizado=nome_normalizado).first() or Credor.objects.filter(nome__iexact=nome_normalizado).first()
                    if not credor_obj:
                        normalized = unicodedata.normalize("NFKC", nome_normalizado)
                        credor_obj = Credor.objects.filter(nome__iexact=normalized).first()
                    if not credor_obj:
                        log_progress(request_id, f"❌ Erro ao recuperar/criar credor {display}: {e}")
                        set_credor_status(request_id, slug, 'error')
                        if job_id:
                            update_reprocess_job(job_id, log_msg=f'Erro DB para {slug}')
                        continue
            # create/update historico
            valor_total = df.get(df.columns[-1]).sum() if not df.empty else 0
            numero_pgc_int = None
            # try to find numero_pgc from processing folder structure
            try:
                # assume processing folder is under MEDIA_ROOT/processing/<request_id>/
                numero_pgc_int = int(os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(processing_dir)))))
            except Exception:
                # fallback to 0
                numero_pgc_int = 0

            historico, criado = HistoricoPGC.objects.get_or_create(
                credor=credor_obj,
                numero_pgc=numero_pgc_int,
                defaults={'periodo': timezone.now().strftime('%m/%Y'), 'valor_total': valor_total}
            )
            if not criado:
                historico.valor_total = valor_total
                historico.periodo = timezone.now().strftime('%m/%Y')
                historico.save(update_fields=['valor_total', 'periodo'])

            # regenerate files in output folder using existing slug/folder
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            numero_dir = str(numero_pgc_int)
            base_output = os.path.join(BASE_DIR, 'arquivos_gerados', 'PGC', numero_dir)
            pasta_credor = os.path.join(base_output, slug)
            os.makedirs(pasta_credor, exist_ok=True)

            # reprocess export disabled: avoid creating slug-named duplicate files
            log_progress(request_id, f"ℹ️ Reprocess export disabled for {slug}; skipping slug-based files")

            # mark success
            set_credor_status(request_id, slug, 'processed', display=display)
            log_progress(request_id, f"✅ Reprocessado credor {display} com sucesso")
            # mark previous errors resolved
            resolve_errors_for_credor(request_id, slug)
            if job_id:
                update_reprocess_job(job_id, log_msg=f'Concluído {slug}')
        except Exception as e:
            tb = traceback.format_exc()
            log_progress(request_id, f"❌ Erro durante reprocessamento de {slug}: {e}")
            # register error
            err_obj = {
                'id': str(uuid.uuid4()),
                'request_id': request_id,
                'credor': slug,
                'credor_display': display if 'display' in locals() else slug,
                'step': 'reprocess',
                'technical': str(e) + '\n' + tb,
                'friendly': 'Erro ao reprocessar o credor',
                'type': 'reprocess_error',
                'time': datetime.now().strftime('%H:%M:%S'),
                'retries': 0,
                'resolved': False
            }
            log_error(request_id, err_obj)
            set_credor_status(request_id, slug, 'error')
            if job_id:
                update_reprocess_job(job_id, log_msg=f'Erro em {slug}')
            continue

    log_progress(request_id, f"🔁 Reprocessamento finalizado por {initiated_by or 'sistema'}")
    if job_id:
        update_reprocess_job(job_id, status='completed')

