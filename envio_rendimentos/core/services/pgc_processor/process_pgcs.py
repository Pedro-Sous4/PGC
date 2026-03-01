import os
import json
import re
import logging
from uuid import uuid4
from datetime import datetime

import pandas as pd
from django.conf import settings
from django.db import close_old_connections, IntegrityError

from core import utils as core_utils
from core.models import Credor, HistoricoPGC, Grupo
from core.db_utils import _resilient_get_or_create

logger = logging.getLogger("pgc_debug")

# ======================================================
# Infra
# ======================================================

def log(msg):
    logger.info(msg)
    print(f"[PGC] {msg}")


def ensure_dir(path):
    path = os.path.abspath(path)
    os.makedirs(path, exist_ok=True)
    return path


def write_progress(folder, data):
    with open(
        os.path.join(folder, "progress.json"),
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def append_log(folder, progress, msg, type="info", credor=None):
    entry = {
        "type": type,
        "msg": msg,
        "time": datetime.now().strftime("%H:%M:%S"),
    }
    if credor:
        entry["credor"] = credor

    if "logs" not in progress:
        progress["logs"] = []

    progress["logs"].append(entry)
    write_progress(folder, progress)


def normalize_df(df):
    if df is None:
        return None

    df = df.copy()
    df.columns = df.columns.str.lower().str.strip()
    # Limpa espaços em strings em todas as células (element-wise)
    try:
        df = df.applymap(lambda x: str(x).strip() if pd.notna(x) and isinstance(x, str) else x)
    except Exception:
        # fallback: se applymap falhar por algum motivo, retorna o df sem alterações adicionais
        pass

    return df


def detect_pgc_number(file_path):
    try:
        df = pd.read_excel(file_path, sheet_name=None)
        for sheet_name, sheet_df in df.items():
            sheet_lower = sheet_name.lower()
            if "pgc" in sheet_lower:
                match = re.search(r"pgc\s*(\d+)", sheet_lower)
                if match:
                    return int(match.group(1))

        # Fallback: tenta no nome do arquivo
        filename = os.path.basename(file_path).lower()
        match = re.search(r"pgc\s*(\d+)", filename)
        if match:
            return int(match.group(1))

    except Exception as e:
        log(f"Erro ao detectar número PGC: {e}")

    raise Exception("Número do PGC não encontrado")


def process_credor(
    credor,
    numero_pgc,
    base_df,
    extrato_df=None,
    prod_df=None,
    minimo_df=None,
    pasta_credores=None,
    nome_original=None,
    pgc_prefix=None,
):
    close_old_connections()

    if not pasta_credores:
        raise Exception("pasta_credores não informada")

    nome_norm = core_utils.normalizar_nome_completo(credor.nome)

    log(f"Processando credor: {nome_norm}")

    # Primeiro, tenta match exato por nome normalizado (tolerante a case/whitespace)
    df_base = base_df[base_df["credor_normalizado"].astype(str).str.strip().str.lower() == str(nome_norm).strip().lower()]

    # Se vazio, tenta fallback: usar prefixo numérico do nome original (se disponível)
    if df_base.empty:
        candidate_name = nome_original or credor.nome or ""
        m = re.match(r"\s*(\d{1,6})\s*-", str(candidate_name))
        if m:
            codigo = m.group(1)
            # procura linhas cuja coluna `credor` comece com o codigo seguido de ' - '
            matches = base_df[base_df["credor"].astype(str).str.strip().str.startswith(f"{codigo} -")]
            if not matches.empty:
                df_base = matches

    if df_base.empty:
        raise Exception("BASE vazia para o credor")

    df_extrato = (
        extrato_df[extrato_df["credor_normalizado"] == nome_norm]
        if extrato_df is not None else None
    )

    # Se um prefixo foi informado (ex: SPORTS ou LGM), associa o Credor ao Grupo
    if pgc_prefix:
        try:
            # Use resilient helper to avoid race conditions when creating Grupo by nome
            grupo_nome = pgc_prefix.strip().upper()
            grupo_obj, _ = _resilient_get_or_create(Grupo, grupo_nome, nome_field='nome')
            if credor.grupo_id != grupo_obj.id:
                credor.grupo = grupo_obj
                credor.save(update_fields=['grupo'])
        except Exception:
            grupo_obj = None

    # Determine grupo to attach to historico: prefer explicit grupo_obj, otherwise use credor.grupo
    grupo_for_historico = locals().get('grupo_obj') or getattr(credor, 'grupo', None)

    HistoricoPGC.objects.get_or_create(
        credor=credor,
        numero_pgc=numero_pgc,
        defaults={
            "valor_total": df_base.get("valor_original", pd.Series()).sum(),
            "grupo": grupo_for_historico,
        }
    )

    core_utils.gerar_arquivos_credor(
        credor=credor,
        numero_pgc=numero_pgc,
        base_df=df_base,
        extrato_df=df_extrato,
        prod_df=prod_df,
        minimo_df=minimo_df,
        pasta_pgc=pasta_credores,
    )

    log(f"Finalizado credor: {nome_norm}")
    return nome_norm

# ======================================================
# Função principal
# ======================================================

def process_pgc_file(
    file_path,
    request_id=None,
    pgc_prefix=None,
):
    request_id = request_id or str(uuid4())
    
    # 🔥 Log IMEDIATO antes de qualquer coisa
    print(f"\n[PGC] ========================================")
    print(f"[PGC] INICIANDO PROCESSAMENTO")
    print(f"[PGC] Request ID: {request_id}")
    print(f"[PGC] Arquivo: {file_path}")
    print(f"[PGC] PGC Prefix: {pgc_prefix}")
    print(f"[PGC] ========================================\n")
    logger.info(f"[PGC] Processamento iniciado para {request_id}")

    process_folder = ensure_dir(
        os.path.join(settings.MEDIA_ROOT, "processing", request_id)
    )

    progress = {
        "status": "started",
        "processed": 0,
        "total_credores": 0,
        "percent": 0,
        "current_credor": None,
        "logs": [],
        "errors": [],
        "credores_ok": [],
        "request_id": request_id,
    }

    write_progress(process_folder, progress)
    append_log(process_folder, progress, "Processamento iniciado")

    try:
        close_old_connections()

        if not os.path.exists(file_path):
            error_msg = f"Arquivo não encontrado: {file_path}"
            print(f"[PGC] ERROR: {error_msg}")
            raise Exception(error_msg)

        print(f"[PGC] OK: Arquivo encontrado: {file_path}")
        
        append_log(
            process_folder,
            progress,
            f"Arquivo recebido: {os.path.basename(file_path)}",
        )

        numero_pgc = detect_pgc_number(file_path)
        progress["numero_pgc"] = numero_pgc
        progress["status"] = "processing"

        print(f"[PGC] PGC detectado: {numero_pgc}")
        append_log(process_folder, progress, f"PGC detectado: {numero_pgc}")
        append_log(process_folder, progress, "Normalizando planilhas")

        # ===== GERA BASE =====
        print(f"[PGC] Normalizando arquivo Excel...")
        pasta_pgc = core_utils.normalizar_e_salvar_planilha_base(
            file_path,
            numero_pgc,
            pgc_prefix=pgc_prefix,
        )
        pasta_pgc = ensure_dir(pasta_pgc)
        # If a legacy 'CREDORES' directory exists, warn and suggest migration (do not create new ones)
        legacy_dir = os.path.join(pasta_pgc, 'CREDORES')
        if os.path.isdir(legacy_dir):
            n = len([p for p in os.listdir(legacy_dir) if os.path.isdir(os.path.join(legacy_dir, p))])
            append_log(process_folder, progress, f"⚠️ Diretório legado detectado: '{legacy_dir}' contém {n} pastas. Execute 'scripts/fix_credores_structure.py {numero_pgc}' para migrar.")
            logger.warning(f"[PGC] Legacy 'CREDORES' detected in {pasta_pgc}. Run scripts/fix_credores_structure.py {numero_pgc} to migrate.")

        # Use the PGC folder directly as the base for credor output (no intermediate 'CREDORES' dir)
        pasta_credores = pasta_pgc
        
        print(f"[PGC] OK: Pasta PGC criada: {pasta_pgc} (base para credores)")

        append_log(
            process_folder,
            progress,
            f"Pasta PGC: {pasta_pgc}",
        )

        base_path = os.path.join(pasta_pgc, f"BASE PGC {numero_pgc}.xlsx")
        if not os.path.exists(base_path):
            error_msg = f"BASE PGC não encontrada em {base_path}"
            print(f"[PGC] ERROR: {error_msg}")
            raise Exception(error_msg)

        print(f"[PGC] Lendo BASE PGC...")
        base_df = normalize_df(pd.read_excel(base_path))

        # Garantir existência da coluna 'credor' (tenta detectar nomes semelhantes)
        if "credor" not in base_df.columns:
            candidatos = [c for c in base_df.columns if "credor" in c]
            if candidatos:
                base_df = base_df.rename(columns={candidatos[0]: "credor"})
            else:
                try:
                    from difflib import get_close_matches
                    candidato = get_close_matches("credor", list(base_df.columns), n=1, cutoff=0.6)
                    if candidato:
                        base_df = base_df.rename(columns={candidato[0]: "credor"})
                except Exception:
                    pass

        if "credor" not in base_df.columns:
            error_msg = "Coluna 'credor' não encontrada na BASE PGC"
            print(f"[PGC] ❌ {error_msg}")
            raise Exception(error_msg)

        base_df["credor_normalizado"] = base_df["credor"].apply(
            core_utils.normalizar_nome_completo
        )
        print(f"[PGC] OK: BASE lida com {len(base_df)} registros")

        extrato_df = None
        extrato_path = os.path.join(pasta_pgc, "EXTRATO.xlsx")
        if os.path.exists(extrato_path):
            print(f"[PGC] Lendo EXTRATO...")
            try:
                extrato_df = normalize_df(pd.read_excel(extrato_path))
            except Exception as e:
                print(f"[PGC] WARN: falha ao ler EXTRATO: {e}")
                append_log(process_folder, progress, f"Falha ao ler EXTRATO: {e}", type="warning")
                extrato_df = None

            if extrato_df is not None:
                # tenta localizar coluna 'credor' similar
                if "credor" not in extrato_df.columns:
                    candidatos = [c for c in extrato_df.columns if "credor" in c]
                    if candidatos:
                        extrato_df = extrato_df.rename(columns={candidatos[0]: "credor"})
                    else:
                        try:
                            from difflib import get_close_matches
                            candidato = get_close_matches("credor", list(extrato_df.columns), n=1, cutoff=0.6)
                            if candidato:
                                extrato_df = extrato_df.rename(columns={candidato[0]: "credor"})
                        except Exception:
                            pass
                if "credor" in extrato_df.columns:
                    extrato_df["credor_normalizado"] = extrato_df["credor"].apply(
                        core_utils.normalizar_nome_completo
                    )
                    print(f"[PGC] OK: EXTRATO lido com {len(extrato_df)} registros")

        prod_df = None
        prod_path = os.path.join(pasta_pgc, "PRODUTIVIDADE.xlsx")
        if os.path.exists(prod_path):
            print(f"[PGC] Lendo PRODUTIVIDADE...")
            try:
                prod_df = normalize_df(pd.read_excel(prod_path))
            except Exception as e:
                print(f"[PGC] WARN: falha ao ler PRODUTIVIDADE: {e}")
                append_log(process_folder, progress, f"Falha ao ler PRODUTIVIDADE: {e}", type="warning")
                prod_df = None

            if prod_df is not None:
                # tenta localizar coluna 'credor' similar
                if "credor" not in prod_df.columns:
                    candidatos = [c for c in prod_df.columns if "credor" in c]
                    if candidatos:
                        prod_df = prod_df.rename(columns={candidatos[0]: "credor"})
                    else:
                        try:
                            from difflib import get_close_matches
                            candidato = get_close_matches("credor", list(prod_df.columns), n=1, cutoff=0.6)
                            if candidato:
                                prod_df = prod_df.rename(columns={candidato[0]: "credor"})
                        except Exception:
                            pass
                if "credor" in prod_df.columns:
                    prod_df["credor_normalizado"] = prod_df["credor"].apply(
                        core_utils.normalizar_nome_completo
                    )
                    print(f"[PGC] OK: PRODUTIVIDADE lido com {len(prod_df)} registros")

        credores_nomes = sorted(base_df["credor"].unique())
        total = len(credores_nomes)
        progress["total_credores"] = total
        write_progress(process_folder, progress)
        
        print(f"[PGC] Encontrados {total} credores para processar")
        print(f"[PGC] Iniciando processamento de credores...\n")

        for index, nome in enumerate(credores_nomes, start=1):
            progress["current_credor"] = nome
            print(f"[PGC] [{index}/{total}] Processando: {nome}")

            append_log(
                process_folder,
                progress,
                f"Iniciando credor: {nome}",
                type="credor",
                credor=nome,
            )

            try:
                nome_normalizado = core_utils.normalizar_nome_completo(nome)
                # Try to get or create creditor, ignoring UNIQUE constraint violations
                credor_obj = None
                created = False
                
                # Use helper resilient method to avoid UNIQUE constraint problems
                credor_obj, created = Credor.get_or_create_by_nome(
                    nome_display=nome_normalizado,
                    defaults={
                        "email": "",
                        "periodo": datetime.now().strftime("%m/%Y"),
                    },
                )
                
                action = "criado" if created else "existente"
                print(f"[PGC] Credor {action}: {nome_normalizado}")

                process_credor(
                    credor=credor_obj,
                    numero_pgc=numero_pgc,
                    base_df=base_df,
                    extrato_df=extrato_df,
                    prod_df=prod_df,
                    pasta_credores=pasta_credores,
                    nome_original=nome,
                    pgc_prefix=pgc_prefix,
                )

                progress["processed"] += 1
                progress["credores_ok"].append(nome)
                print(f"[PGC] OK: {nome} processado com sucesso")

            except Exception as e:
                progress["errors"].append({
                    "credor": nome,
                    "error": str(e),
                })
                
                print(f"[PGC] ERROR: Erro no credor {nome}: {str(e)}")

                append_log(
                    process_folder,
                    progress,
                    f"Erro no credor {nome}: {e}",
                    type="error",
                    credor=nome,
                )

            progress["percent"] = round((index / total) * 100, 2)
            write_progress(process_folder, progress)
            print(f"[PGC] Progresso: {progress['percent']}% ({progress['processed']}/{total})")

        progress["status"] = "completed"
        progress["percent"] = 100
        progress["current_credor"] = None

        print(f"\n[PGC] ========================================")
        print(f"[PGC] PROCESSAMENTO FINALIZADO COM SUCESSO")
        print(f"[PGC] Credores processados: {len(progress['credores_ok'])}/{total}")
        print(f"[PGC] Erros: {len(progress['errors'])}")
        print(f"[PGC] ========================================\n")
        
        append_log(process_folder, progress, "Processamento finalizado com sucesso")
        write_progress(process_folder, progress)

        return progress

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"\n[PGC] ========================================")
        print(f"[PGC] ERRO FATAL NO PROCESSAMENTO")
        print(f"[PGC] {str(e)}")
        print(tb)
        print(f"[PGC] ========================================\n")
        
        progress["status"] = "error"
        progress["fatal_error"] = str(e)

        append_log(
            process_folder,
            progress,
            f"Erro fatal: {e}\n{tb}",
            type="error",
        )

        write_progress(process_folder, progress)
        return progress


def get_progress(request_id):
    from django.conf import settings
    path = os.path.join(
        settings.MEDIA_ROOT,
        "processing",
        request_id,
        "progress.json"
    )

    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)