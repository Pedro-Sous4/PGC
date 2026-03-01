from django.shortcuts import render, redirect, get_object_or_404
from .models import Credor, Rendimento, HistoricoPGC, Grupo, EmpresaPagadora
from .forms import CredorForm, RendimentoForm, UploadPGCForm
from django.contrib import messages
from django.http import FileResponse, HttpResponse, JsonResponse, HttpResponseRedirect
from .utils import gerar_pdf_relatorio, enviar_email_com_arquivos, normalizar_colunas_simples
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from datetime import datetime
import pandas as pd
import openpyxl
import io
import json
import csv
import zipfile
import os
from django.conf import settings
import csv
from django.core.mail import EmailMessage
import re
from django.utils import timezone
from .models import EmpresaPagadora  
import difflib
from openpyxl import load_workbook
import unicodedata
import logging
from .utils import normalizar_nome
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import numbers
#logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(message)s')
#logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
from .utils import (
    logger,
    salvar_planilha_temporaria,
    normalizar_colunas_com_duas_linhas,
    salvar_minimos_como_excel,
    obter_minimo_garantido_para_credor,
    normalizar_nome,
    normalizar_planilha_origem,
    gerar_pdf_relatorio,
    enviar_email_com_arquivos,
    extrair_minimos_robusto,
    extrair_dados_planilhas,
    gerar_arquivos_credor,
    normalizar_e_salvar_planilha_base,
    
)

import threading
from django.http import JsonResponse, Http404
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from core.utils_progress import init_progress
from core.utils_lgm import processar_pgc_lgm, reprocessar_credores
from core.services.pgc_processor.process_pgcs import process_pgc_file, get_progress


from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.http import require_GET
import os
from .utils import obter_minimo_garantido_para_credor

from core import utils as core_utils


from .utils import (
    carregar_mensagens,
    salvar_mensagens,
    MENSAGEM_PADRAO,
        INFO_MINIMO_PADRAO,
        INFO_DESCONTOS_PADRAO,
    obter_minimo_garantido_para_credor,  # já existe em utils.py
)

def salvar_arquivo_temporario(file, numero_pgc):
    pasta_destino = os.path.join(settings.MEDIA_ROOT, 'planilhas_recebidas')
    os.makedirs(pasta_destino, exist_ok=True)
    nome_arquivo = f"PGC_{numero_pgc}.xlsx"
    caminho_arquivo = os.path.join(pasta_destino, nome_arquivo)
    with open(caminho_arquivo, 'wb') as f:
        for chunk in file.chunks():
            f.write(chunk)
    return caminho_arquivo

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

def index(request):
    return render(request, 'core/index.html')

@login_required
def dashboard(request):
    grupo_id = request.GET.get('grupo_id')
    grupos = Grupo.objects.all()

    # Filtro de grupo
    if grupo_id:
        enviados = Credor.objects.filter(enviado=True, grupo_id=grupo_id).order_by('nome')
        nao_enviados = Credor.objects.filter(enviado=False, grupo_id=grupo_id).order_by('nome')
    else:
        enviados = Credor.objects.filter(enviado=True).order_by('nome')
        nao_enviados = Credor.objects.filter(enviado=False).order_by('nome')

    # Paginação
    enviados_page = Paginator(enviados, 1000).get_page(request.GET.get('enviados_page'))
    nao_enviados_page = Paginator(nao_enviados, 1000).get_page(request.GET.get('nao_enviados_page'))

    # Contadores
    enviados_count = enviados.count()
    nao_enviados_count = nao_enviados.count()

    # Dados para o gráfico por número do PGC
    pgc_labels = HistoricoPGC.objects.values_list('numero_pgc', flat=True).distinct().order_by('numero_pgc')
    pgc_totais = []
    for numero in pgc_labels:
        total = Credor.objects.filter(historicos__numero_pgc=numero)
        if grupo_id:
            total = total.filter(grupo_id=grupo_id)
        pgc_totais.append(total.count())

    context = {
        'enviados_page': enviados_page,
        'nao_enviados_page': nao_enviados_page,
        'enviados': enviados_count,
        'nao_enviados': nao_enviados_count,
        'pgc_labels': json.dumps(list(pgc_labels)),
        'pgc_totais': json.dumps(pgc_totais),
        'grupos': grupos,
        'grupo_id': int(grupo_id) if grupo_id else None,
    }

    return render(request, 'core/dashboard.html', context)


# @login_required
# def listar_Credores(request):
#     busca = request.GET.get('busca', '')
#     status = request.GET.get('status', '')
#     order = request.GET.get('order', 'nome')
#     direction = request.GET.get('dir', 'asc')

#     credores = Credor.objects.all()

#     if status == 'enviados':
#         credores = credores.filter(enviado=True)
#     elif status == 'nao_enviados':
#         credores = credores.filter(enviado=False)

#     if busca:
#         credores = credores.filter(Q(nome__icontains=busca))

#     if direction == 'desc':
#         credores = credores.order_by(f'-{order}')
#     else:
#         credores = credores.order_by(order)

#     paginator = Paginator(credores, 10)
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)

#     return render(request, 'core/listar_credores.html', {
#         'page_obj': page_obj,
#         'status': status,
#         'busca': busca,
#         'order': order,
#         'direction': direction,
#     })

@login_required
def listar_Credores(request):
    busca = request.GET.get('busca', '').strip()
    status = request.GET.get('status', '')
    pgc = request.GET.get('pgc', '').strip()
    grupo = request.GET.get('grupo', '').strip()
    order = request.GET.get('order', 'nome')
    direction = request.GET.get('dir', 'asc')

    # ✅ SEMPRE começa como QuerySet
    credores = Credor.objects.all()

    # 🔎 Busca por nome
    if busca:
        credores = credores.filter(nome__icontains=busca)

    # 📌 Status
    if status == 'enviados':
        credores = credores.filter(enviado=True)
    elif status == 'nao_enviados':
        credores = credores.filter(enviado=False)

    # 📎 Filtro por PGC (FK reversa)
    if pgc:
        credores = credores.filter(
            historicos__numero_pgc=pgc
        ).distinct()

    # 👥 Filtro por Grupo
    if grupo:
        credores = credores.filter(grupo__id=grupo)

    # 🔃 Ordenação
    if direction == 'desc':
        credores = credores.order_by(f'-{order}')
    else:
        credores = credores.order_by(order)

    # 📄 Paginação (SÓ NO FINAL)
    paginator = Paginator(credores, 1000)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Buscar grupos para o filtro
    from core.models import Grupo
    grupos = Grupo.objects.all()

    return render(request, 'core/listar_credores.html', {
        'page_obj': page_obj,
        'status': status,
        'busca': busca,
        'pgc': pgc,
        'grupo': grupo,
        'order': order,
        'direction': direction,
        'grupos': grupos,
    })

@login_required
def editar_Credor(request, credor_id):
    credor = get_object_or_404(Credor, pk=credor_id)
    if request.method == 'POST':
        form = CredorForm(request.POST, instance=credor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Credor atualizado com sucesso!')
            return redirect('listar_Credores')
    else:
        form = CredorForm(instance=credor)
    return render(request, 'core/editar_Credor.html', {'form': form})

@login_required
def detalhe_rendimentos(request, credor_id):
    credor = get_object_or_404(Credor, pk=credor_id)
    rendimentos = credor.rendimentos.all()
    historicos = credor.historicos.all()
    return render(request, 'core/detalhe_rendimentos.html', {
        'Credor': credor, 
        'rendimentos': rendimentos,
        'historicos': historicos
    })

@login_required
def adicionar_rendimento(request, credor_id):
    credor = get_object_or_404(Credor, pk=credor_id)
    if request.method == 'POST':
        form = RendimentoForm(request.POST)
        if form.is_valid():
            rendimento = form.save(commit=False)
            rendimento.Credor = credor
            rendimento.save()
            credor.atualizar_periodo()
            # Atualiza/Cria HistoricoPGC para o período do rendimento
            try:
                from .models import HistoricoPGC
                periodo = rendimento.periodo
                numero_pgc = form.cleaned_data.get('numero_pgc') or 0
                # soma dos rendimentos para o período (usando Django ORM aggregation)
                from django.db.models import Sum
                agg = credor.rendimentos.filter(periodo=periodo).aggregate(total=Sum('valor'))
                total = agg.get('total') or 0
                historico = HistoricoPGC.objects.filter(credor=credor, periodo=periodo).first()
                if historico:
                    historico.valor_total = total
                    # atualiza numero_pgc se informado no form
                    if numero_pgc:
                        historico.numero_pgc = numero_pgc
                    historico.save(update_fields=['valor_total'])
                else:
                    # marcar como manual com numero_pgc 0
                    HistoricoPGC.objects.create(credor=credor, numero_pgc=numero_pgc or 0, periodo=periodo, valor_total=total, grupo=getattr(credor, 'grupo', None))
            except Exception:
                # não interrompe o fluxo principal se houver erro ao atualizar histórico
                pass
            messages.success(request, 'Rendimento adicionado com sucesso!')
            return redirect('detalhe_rendimentos', credor_id=credor.id)
    else:
        form = RendimentoForm()
    return render(request, 'core/adicionar_rendimento.html', {'form': form, 'Credor': credor})

@login_required
@login_required
def editar_rendimento(request, rendimento_id):
    rendimento = get_object_or_404(Rendimento, pk=rendimento_id)
    if request.method == 'POST':
        old_periodo = rendimento.periodo
        form = RendimentoForm(request.POST, instance=rendimento)
        if form.is_valid():
            rendimento = form.save()
            rendimento.Credor.atualizar_periodo()
            # atualizar históricos para o período antigo e novo
            try:
                from .models import HistoricoPGC
                from django.db.models import Sum
                credor = rendimento.Credor
                periods = set(filter(None, [old_periodo, rendimento.periodo]))
                for p in periods:
                    agg = credor.rendimentos.filter(periodo=p).aggregate(total=Sum('valor'))
                    total = agg.get('total') or 0
                    historico = HistoricoPGC.objects.filter(credor=credor, periodo=p).first()
                    if total and historico:
                        historico.valor_total = total
                        # se o form fornecer numero_pgc, atualiza também
                        numero_pgc = form.cleaned_data.get('numero_pgc')
                        if numero_pgc:
                            historico.numero_pgc = numero_pgc
                        historico.save(update_fields=['valor_total'])
                    elif total and not historico:
                        HistoricoPGC.objects.create(credor=credor, numero_pgc=form.cleaned_data.get('numero_pgc') or 0, periodo=p, valor_total=total, grupo=getattr(credor, 'grupo', None))
                    elif not total and historico:
                        historico.delete()
            except Exception:
                pass
            messages.success(request, 'Rendimento atualizado com sucesso!')
            return redirect('detalhe_rendimentos', credor_id=rendimento.Credor.id)
    else:
        form = RendimentoForm(instance=rendimento)
    return render(request, 'core/editar_rendimento.html', {'form': form, 'Credor': rendimento.Credor})

@login_required
def excluir_rendimento(request, rendimento_id):
    rendimento = get_object_or_404(Rendimento, pk=rendimento_id)
    credor = rendimento.Credor
    periodo = rendimento.periodo
    rendimento.delete()
    # atualizar/remoção do HistoricoPGC correspondente
    try:
        from .models import HistoricoPGC
        from django.db.models import Sum
        agg = credor.rendimentos.filter(periodo=periodo).aggregate(total=Sum('valor'))
        total = agg.get('total') or 0
        historico = HistoricoPGC.objects.filter(credor=credor, periodo=periodo).first()
        if total and historico:
            historico.valor_total = total
            historico.save(update_fields=['valor_total'])
        elif not total and historico:
            historico.delete()
    except Exception:
        pass
    messages.success(request, 'Rendimento excluído com sucesso!')
    return redirect('detalhe_rendimentos', credor_id=credor.id)

@login_required
def editar_historico_pgc(request, historico_id):
    """Edita um registro de HistoricoPGC"""
    historico = get_object_or_404(HistoricoPGC, pk=historico_id)
    if request.method == 'POST':
        historico.valor_total = request.POST.get('valor_total', historico.valor_total)
        historico.periodo = request.POST.get('periodo', historico.periodo)
        historico.numero_pgc = request.POST.get('numero_pgc', historico.numero_pgc)
        historico.save()
        messages.success(request, 'Histórico PGC atualizado com sucesso!')
        return redirect('detalhe_rendimentos', credor_id=historico.credor.id)
    
    return render(request, 'core/editar_historico_pgc.html', {'historico': historico, 'Credor': historico.credor})

@login_required
def excluir_historico_pgc(request, historico_id):
    """Exclui um registro de HistoricoPGC"""
    historico = get_object_or_404(HistoricoPGC, pk=historico_id)
    credor_id = historico.credor.id
    historico.delete()
    messages.success(request, 'Histórico PGC excluído com sucesso!')
    return redirect('detalhe_rendimentos', credor_id=credor_id)

@login_required
def excluir_Credor(request, credor_id):
    credor = get_object_or_404(Credor, id=credor_id)
    credor.delete()
    messages.success(request, 'Credor excluído com sucesso.')
    return redirect('listar_Credores')

@login_required
def gerar_pdf_view(request, credor_id):
    credor = get_object_or_404(Credor, id=credor_id)
    pdf_path = gerar_pdf_relatorio(credor)
    return FileResponse(open(pdf_path, 'rb'), as_attachment=True, filename=f'relatorio_{credor.nome}.pdf')

@login_required
def enviar_email_individual(request, credor_id):
    credor = get_object_or_404(Credor, id=credor_id)
    try:
        enviar_email_com_arquivos(credor)
        credor.enviado = True
        credor.save()
        messages.success(request, f'E-mail enviado para {credor.nome} com sucesso!')
    except Exception as e:
        messages.error(request, f'Erro ao enviar para {credor.nome}: {e}')
    
    return redirect('listar_Credores')

@csrf_exempt
def enviar_emails_selecionados(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        ids = data.get('ids', [])
        enviados = []
        falharam = []

        for id in ids:
            try:
                credor = Credor.objects.get(id=id)

                # Envia e-mail e atualiza status apenas se sucesso
                if enviar_email_com_arquivos(credor):
                    credor.enviado = True
                    credor.save()
                    enviados.append(credor.nome)
                else:
                    falharam.append(credor.nome)
            except Credor.DoesNotExist:
                falharam.append(f"ID {id} (não encontrado)")

        return JsonResponse({
            'mensagem': f'{len(enviados)} e-mails enviados com sucesso.',
            'enviados': enviados,
            'falharam': falharam
        })

    return JsonResponse({'mensagem': 'Método inválido'}, status=405)

@csrf_exempt
def excluir_Credores_selecionados(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        ids = data.get('ids', [])
        excluidos = 0

        for id in ids:
            try:
                credor = Credor.objects.get(id=id)
                credor.delete()
                excluidos += 1
            except Credor.DoesNotExist:
                continue

        return JsonResponse({'mensagem': f'{excluidos} credor(es) excluído(s) com sucesso.'})
    return JsonResponse({'mensagem': 'Método inválido'}, status=405)

@csrf_exempt
def alterar_status_selecionados(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        ids = data.get('ids', [])
        status = data.get('status', False)

        atualizados = Credor.objects.filter(id__in=ids).update(enviado=status)
        return JsonResponse({'mensagem': f'Status alterado para {atualizados} credor(es).'})

    return JsonResponse({'mensagem': 'Método inválido'}, status=405)

@login_required
def exportar_Credores(request):
    status = request.GET.get('status')
    grupo = request.GET.get('grupo', '').strip()

    credores = Credor.objects.all()
    if status == 'enviados':
        credores = credores.filter(enviado=True)
    elif status == 'nao_enviados':
        credores = credores.filter(enviado=False)
    
    if grupo:
        credores = credores.filter(grupo__id=grupo)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="credores.csv"'

    writer = csv.writer(response)
    writer.writerow(['Nome', 'Email', 'Grupo', 'Enviado'])

    for c in credores:
        writer.writerow([c.nome, c.email, c.grupo.nome if c.grupo else '—', 'Sim' if c.enviado else 'Não'])

    return response

@login_required
def exportar_Credores_excel(request):
    status = request.GET.get('status')
    grupo = request.GET.get('grupo', '').strip()

    credores = Credor.objects.all()
    if status == 'enviados':
        credores = credores.filter(enviado=True)
    elif status == 'nao_enviados':
        credores = credores.filter(enviado=False)
    
    if grupo:
        credores = credores.filter(grupo__id=grupo)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Credores"

    ws.append(['Nome', 'Email', 'Grupo', 'Enviado'])

    for c in credores:
        ws.append([c.nome, c.email, c.grupo.nome if c.grupo else '—', 'Sim' if c.enviado else 'Não'])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=credores.xlsx'
    wb.save(response)
    return response

@csrf_exempt
@login_required
def exportar_pdfs_selecionados(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        ids = data.get('ids', [])

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            for credor_id in ids:
                try:
                    credor = Credor.objects.get(id=credor_id)
                    pdf_path = gerar_pdf_relatorio(credor)
                    zip_file.write(pdf_path, arcname=f"{credor.nome}.pdf")
                except Credor.DoesNotExist:
                    continue
                except Exception as e:
                    print(f"Erro ao gerar PDF para credor {credor_id}: {e}")
                    continue

        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="relatorios.zip"'
        return response

    return JsonResponse({'mensagem': 'Método inválido'}, status=405)

from .utils import normalizar_nome_completo

@login_required
def upload_emails(request):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']

        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        elif file.name.endswith('.xlsx'):
            df = pd.read_excel(file)
        else:
            messages.error(request, 'Formato de arquivo inválido. Envie .csv ou .xlsx.')
            return redirect('upload_emails')

        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

        required_cols = {'nome', 'email', 'grupo'}
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            messages.error(request, f'Colunas obrigatórias ausentes: {missing_cols}')
            return redirect('upload_emails')

        atualizados = 0
        criados = 0
        periodo_atual = datetime.today().strftime('%m/%Y')

        for _, row in df.iterrows():
            nome_original = str(row['nome']).strip()
            nome = normalizar_nome_completo(nome_original)
            email = str(row['email']).strip()
            grupo_nome = str(row['grupo']).strip()

            grupo = Grupo.objects.filter(nome__iexact=grupo_nome).first()
            if not grupo:
                messages.error(request, f"Grupo '{grupo_nome}' não encontrado para o credor '{nome_original}'.")
                continue

            # Para evitar colisões de unicidade causadas pela normalização feita no save(),
            # tentamos localizar primeiro pelo nome normalizado (sem acentos/maiúsculas).
            from django.db import IntegrityError, transaction
            from core.normalizacao import normalizar_nome as normalizar_nome_db

            nome_norm = normalizar_nome_db(nome)

            # Usar factory resiliente; neste fluxo de upload de emails
            # queremos permitir atualização de campos protegidos (email)
            credor, created = Credor.get_or_create_by_nome(nome, defaults={'email': email, 'periodo': periodo_atual, 'grupo': grupo}, allow_protected_update=True)
            if created:
                criados += 1
            else:
                atualizados += 1

        messages.success(request, f'Upload concluído! {criados} criado(s), {atualizados} atualizado(s).')
        return redirect('upload_emails')

    return render(request, 'core/upload_emails.html')

def abrir_pasta_explorer(request, credor_id, numero_pgc):
    credor = get_object_or_404(Credor, pk=credor_id)
    nome_para_exibicao = str(credor.nome).strip().upper()
    pasta = os.path.join("C:\\PGC\\envio_rendimentos\\arquivos_gerados\\PGC", str(numero_pgc), nome_para_exibicao)
    if os.path.exists(pasta):
        os.startfile(pasta)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    nome = re.sub(r'^\d+\s*-\s*', '', nome)  # remove prefixo tipo "16273 - "
    nome = re.sub(r'\s*\([^)]*\)', '', nome)  # remove sufixo tipo "(CONSULTOR)"
    return nome.strip().upper()
'''
@login_required
def upload_planilha(request):
    if request.method == 'POST' and request.FILES.get('file'):
        numero_pgc = request.POST.get('numero_pgc')
        file = request.FILES['file']

        if not numero_pgc:
            messages.error(request, 'Informe o número do PGC.')
            return redirect('upload_planilha')

        if not file.name.endswith('.xlsx'):
            messages.error(request, 'Apenas planilhas .xlsx são suportadas.')
            return redirect('upload_planilha')

        try:
            caminho_temporario = salvar_planilha_temporaria(file, numero_pgc)
            caminho_tratado = normalizar_planilha_origem(caminho_temporario, numero_pgc)
            planilha = pd.read_excel(caminho_tratado, sheet_name=None)
        except Exception as e:
            logger.error(f"[UPLOAD] Erro ao processar planilha: {e}")
            messages.error(request, 'Erro ao ler a planilha.')
            return redirect('upload_planilha')

        base_df = None
        produtividade_df = None
        extrato_df = None
        aba_minimo_df = None

        for nome_aba, df in planilha.items():
            nome = nome_aba.lower()
            if 'base' in nome:
                base_df = normalizar_colunas_simples(df.copy())
            elif 'produtividade' in nome:
                produtividade_df = normalizar_colunas_simples(df.copy())
            elif 'extrato' in nome:
                extrato_df = normalizar_colunas_simples(df.copy())
            elif nome.startswith(f"pgc {numero_pgc.lower()}"):
                aba_minimo_df = normalizar_colunas_com_duas_linhas(df.copy())

        if base_df is None:
            logger.error("[UPLOAD] Aba BASE não encontrada.")
            messages.error(request, 'A aba BASE não foi localizada.')
            return redirect('upload_planilha')

        if 'credor' not in base_df.columns:
            logger.error(f"[UPLOAD] Coluna 'credor' ausente na planilha BASE.")
            messages.error(request, "Coluna 'credor' ausente na planilha BASE.")
            return redirect('upload_planilha')

        # Trata mínimo se possível
        minimos_df = None
        if aba_minimo_df is not None:
            try:
                minimos_df = extrair_minimos_de_planilha(aba_minimo_df)
                salvar_minimos_como_excel(minimos_df, numero_pgc)
            except Exception as e:
                logger.warning(f"[UPLOAD] Falha ao processar mínimos: {e}")

        periodo = datetime.now().strftime('%m/%Y')
        credores = base_df['credor'].unique()

        for nome in credores:
            df_credor = base_df[base_df['credor'] == nome]
            df_prod_credor = produtividade_df[produtividade_df['credor'] == nome] if produtividade_df is not None else None
            df_ext_credor = extrato_df[extrato_df['credor'] == nome] if extrato_df is not None else None

            credor_obj = Credor.objects.filter(nome__iexact=nome).first()
            if not credor_obj:
                # Use resilient helper to avoid races and ensure normalization
                credor_obj, _ = Credor.get_or_create_by_nome(nome, defaults={'email': '', 'periodo': periodo})
            else:
                credor_obj.periodo = periodo
                credor_obj.save()

            HistoricoPGC.objects.create(
                credor=credor_obj,
                numero_pgc=numero_pgc,
                periodo=periodo,
                valor_total=df_credor['valor_original'].sum(),
                grupo=getattr(credor_obj, 'grupo', None)
            )

            # Pastas devem usar o NOME PARA EXIBIÇÃO em MAIÚSCULAS com espaços
            nome_para_exibicao = str(credor_obj.nome).strip().upper()
            pasta_saida = os.path.join(settings.MEDIA_ROOT, 'PGC', str(numero_pgc), nome_para_exibicao)
            os.makedirs(pasta_saida, exist_ok=True)

            try:
                # === Gerar planilha PGC EMISSÃO com CNPJ ===
                df_emissao = df_credor.groupby(['empresa', 'credor'], as_index=False)['valor_original'].sum()

                df_emissao['cnpj'] = df_emissao['empresa'].apply(lambda nome:
                    EmpresaPagadora.objects.filter(nome_curto__iexact=nome).first().cnpj
                    if EmpresaPagadora.objects.filter(nome_curto__iexact=nome).exists()
                    else None
                )
                df_emissao['empresa'] = df_emissao['empresa'].apply(lambda nome:
                    EmpresaPagadora.objects.filter(nome_curto__iexact=nome).first().nome_completo
                    if EmpresaPagadora.objects.filter(nome_curto__iexact=nome).exists()
                    else nome
                )

                for nome_empresa in df_emissao['empresa'].unique():
                    if pd.isna(nome_empresa) or not EmpresaPagadora.objects.filter(nome_completo__iexact=nome_empresa).exists():
                        logger.warning(f"[EMISSÃO] Empresa não cadastrada: {nome_empresa}")

                numero_pgc_str = str(numero_pgc).zfill(3)
                arquivos = {
                    f'PGC {numero_pgc_str} EMISSÃO': df_emissao,
                    f'PGC {numero_pgc_str}': df_credor[['empresa', 'credor', 'documento', 'cliente', 'parcela', 'dt_emissao', 'valor_original']],
                }

                if df_ext_credor is not None:
                    arquivos['EXTRATO'] = df_ext_credor[['empresa', 'credor', 'documento', 'cliente', 'parcela', 'dt_emissao', 'valor_original', 'dt_vencimento', 'obs_baixa']]

                if df_prod_credor is not None:
                    arquivos['PRODUTIVIDADE'] = df_prod_credor[['empresa', 'credor', 'documento', 'cliente', 'parcela', 'dt_emissao', 'valor_original', 'dt_vencimento']]

                nome_arquivo_seguro = re.sub(r'[\\/:"*?<>|]', '', nome).upper()

                for nome_arq, df_arq in arquivos.items():
                    caminho_arquivo = os.path.join(pasta_saida, f'{nome_arquivo_seguro} - {nome_arq}.xlsx')
                    df_arq.to_excel(caminho_arquivo, index=False)

            except Exception as e:
                logger.error(f"Erro ao gerar arquivos para {nome}: {e}")
                messages.error(request, f"Erro ao gerar arquivos para {nome}: {e}")
                continue

        messages.success(request, f'Upload do PGC {numero_pgc} processado com sucesso!')
        return redirect('upload_planilha')

    return render(request, 'core/upload_planilha.html')
'''

def _normalize_name(name):
    if not name:
        return ''
    import re, unicodedata
    name = re.sub(r"^\d+\s*-\s*", "", name)
    name = re.sub(r"\s*\([^)]*\)", "", name)
    name = unicodedata.normalize('NFKD', name.upper())
    return ''.join(c for c in name if not unicodedata.combining(c)).strip()

from difflib import get_close_matches

def encontrar_coluna_semelhante(coluna_alvo, colunas_existentes):
    correspondencias = get_close_matches(coluna_alvo.lower(), colunas_existentes, n=1, cutoff=0.6)
    return correspondencias[0] if correspondencias else None

def extrair_minimos_de_planilha_flex(df):
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

from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
import os
import pandas as pd
from datetime import datetime
from django.conf import settings

@login_required
def upload_planilha(request):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        numero_pgc = request.POST.get('numero_pgc')

        if not numero_pgc:
            messages.error(request, 'Informe o número do PGC.')
            return redirect('upload_planilha')

        try:
            # ============================
            # 1. SALVA PLANILHA ORIGINAL
            # ============================
            caminho_temporario = salvar_planilha_temporaria(file, numero_pgc)

            # ============================
            # 2. NORMALIZA E GERA BASE / EXTRATO / PROD
            # ============================
            pasta_pgc = normalizar_e_salvar_planilha_base(
                caminho_temporario,
                numero_pgc
            )

            # ============================
            # 3. GERA MÍNIMO
            # ============================
            planilhas = pd.ExcelFile(caminho_temporario)
            aba_pgcs = planilhas.parse(planilhas.sheet_names[-1])

            df_minimo = extrair_minimos_robusto(
                aba_pgcs,
                caminho_temporario,
                numero_pgc
            )

            salvar_minimos_como_excel(df_minimo, numero_pgc)

        except Exception as e:
            messages.error(request, f'Erro ao processar planilha: {e}')
            return redirect('upload_planilha')

        # ============================
        # 4. PROCESSAMENTO POR CREDOR
        # ============================
        try:
            base_path = os.path.join(
                settings.MEDIA_ROOT,
                'PGC',
                str(numero_pgc),
                f'BASE PGC {numero_pgc}.xlsx'
            )

            base_df = pd.read_excel(base_path)
            base_df = normalizar_colunas_simples(base_df)

            periodo = datetime.today().strftime('%m/%Y')

            credores_map = {
                normalizar_nome(c.nome): c
                for c in Credor.objects.all()
            }

            for nome in base_df['credor'].unique():
                df_credor = base_df[base_df['credor'] == nome]
                nome_norm = normalizar_nome(nome)

                credor = credores_map.get(nome_norm)

                if not credor:
                    credor, _ = Credor.get_or_create_by_nome(nome.strip(), defaults={'email': '', 'periodo': periodo})
                else:
                    credor.periodo = periodo
                    credor.save()

                HistoricoPGC.objects.create(
                    credor=credor,
                    numero_pgc=numero_pgc,
                    periodo=periodo,
                    valor_total=df_credor['valor_original'].sum(),
                    grupo=getattr(credor, 'grupo', None)
                )

                try:
                    gerar_arquivos_credor(
                        credor=credor,
                        numero_pgc=numero_pgc,
                        base_df=base_df,
                        extrato_df=None,
                        prod_df=None,
                        minimo_df=None,
                        pasta_pgc=os.path.join(
                            settings.MEDIA_ROOT,
                            'PGC',
                            str(numero_pgc)
                        )
                    )
                except Exception as e:
                    messages.warning(
                        request,
                        f"Erro ao gerar arquivos para {nome}: {e}"
                    )

            messages.success(
                request,
                f'Planilha PGC {numero_pgc} processada com sucesso.'
            )

        except Exception as e:
            messages.error(
                request,
                f'Erro ao montar arquivos por credor: {e}'
            )

        return redirect('upload_planilha')

    return render(request, 'core/upload_planilha.html')

@login_required
def historico_envios_email(request):
    caminho_log = os.path.join(settings.MEDIA_ROOT, 'envios_email.xlsx')
    if os.path.exists(caminho_log):
        df = pd.read_excel(caminho_log)
        registros = df.to_dict(orient='records')
    else:
        registros = []
    return render(request, 'core/historico_envios_email.html', {'registros': registros})

@login_required
def enviar_emails_view(request):
    # --- Dados básicos ---
    grupos = Grupo.objects.all()
    numeros_pgc = (
        HistoricoPGC.objects.values_list("numero_pgc", flat=True)
        .distinct()
        .order_by("numero_pgc")
    )
    mensagens_salvas = carregar_mensagens()
    mensagem_padrao = mensagens_salvas.get("mensagem", MENSAGEM_PADRAO)
    info_minimo_padrao = mensagens_salvas.get("info_minimo", INFO_MINIMO_PADRAO)
    info_descontos_padrao = mensagens_salvas.get("info_descontos", INFO_DESCONTOS_PADRAO)

    # Parâmetros do GET para manter seleção
    grupo_id_sel = request.GET.get("grupo_id")
    filtro_tipo_sel = request.GET.get("filtro_tipo") or "todos"
    credor_id_sel = request.GET.get("credor_id")
    empresa_id_sel = request.GET.get("empresa_id")
    numero_pgc_sel = request.GET.get("numero_pgc")

    # Listas auxiliares
    credores_do_grupo = Credor.objects.none()
    if grupo_id_sel:
        try:
            grupo_sel = Grupo.objects.get(id=grupo_id_sel)
            credores_do_grupo = Credor.objects.filter(grupo=grupo_sel).order_by("nome")
        except Grupo.DoesNotExist:
            grupo_sel = None

    empresas = EmpresaPagadora.objects.all().order_by("nome_completo")

    # --- POST: envio ---
    if request.method == "POST":
        numero_pgc = request.POST.get("numero_pgc")
        grupo_id = request.POST.get("grupo_id")
        filtro_tipo = request.POST.get("filtro_tipo", "todos")
        credor_id = request.POST.get("credor_id")
        empresa_id = request.POST.get("empresa_id")

        mensagem_personalizada = request.POST.get("mensagem", mensagem_padrao)
        info_minimo_template = request.POST.get("info_minimo", info_minimo_padrao)
        info_descontos_template = request.POST.get("info_descontos", mensagens_salvas.get('info_descontos', ''))
        # Lista de credores marcados no checkbox (OPÇÃO 1)
        credor_ids = request.POST.getlist("credor_ids")


        # validações
        if not grupo_id or not numero_pgc:
            messages.error(request, "Selecione um grupo e um número de PGC.")
            return redirect("enviar_emails_view")

        try:
            grupo = Grupo.objects.get(id=grupo_id)
        except Grupo.DoesNotExist:
            messages.error(request, "Grupo não encontrado.")
            return redirect("enviar_emails_view")

        base_qs = Credor.objects.filter(
            historicos__numero_pgc=numero_pgc,
            grupo=grupo,
        ).distinct()

        # Filtragem
        if filtro_tipo == "credor":
            if not credor_id:
                messages.error(request, "Selecione um credor quando usar o filtro por Credor.")
                return redirect("enviar_emails_view")
            qs = base_qs.filter(id=credor_id)
        elif filtro_tipo == "empresa":
            if not empresa_id:
                messages.error(request, "Selecione uma empresa quando usar o filtro por Empresa.")
                return redirect("enviar_emails_view")
            qs = base_qs  # (ajuste depois se quiser filtrar pela BASE)
        else:
            qs = base_qs.filter(enviado=False)
        # Se vieram checkboxes marcados, respeita apenas eles
        if credor_ids:
            qs = qs.filter(id__in=credor_ids)
        logger.info(f"[ENVIO] Total selecionado para envio: {qs.count()} credores")


        enviados = 0
        pgc_str = str(int(numero_pgc))  # garante string UMA VEZ

        for credor in qs:
            try:
                historico = (
                    credor.historicos.filter(numero_pgc=numero_pgc)
                    .order_by("-id")
                    .first()
                ) or credor.historicos.order_by("-id").first()

                # ===== MÍNIMO GARANTIDO =====
                info_minimo_dict = obter_minimo_garantido_para_credor(
                    credor.nome,
                    numero_pgc
                )

                if info_minimo_dict:
                    valor = float(info_minimo_dict.get("valor", 0) or 0)
                    valor_formatado = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    info_minimo_texto = info_minimo_template.format(
                        valor_formatado=valor_formatado,
                        empresa=info_minimo_dict.get("empresa", ""),
                        cnpj=info_minimo_dict.get("cnpj", ""),
                    )
                else:
                    info_minimo_texto = ""

                # ===== DESCONTOS =====
                try:
                    info_descontos_texto = core_utils.formatar_info_descontos_para_email(credor.nome, numero_pgc, template=info_descontos_template)
                except Exception:
                    info_descontos_texto = ''

                corpo_email = mensagem_personalizada.format(
                    credor=credor,
                    historico=historico,
                    info_minimo=info_minimo_texto,
                    info_descontos=info_descontos_texto,
                )

                # ===== PASTA DO CREDOR =====
                base_pgc = os.path.join(settings.MEDIA_ROOT, 'PGC', pgc_str)
                # Verificar se a pasta base do PGC existe
                if not os.path.isdir(base_pgc):
                    raise FileNotFoundError(f"Pasta do PGC não encontrada: {base_pgc}")
                # usar função utilitária que procura case-insensitive diretamente dentro do PGC
                pasta_credor = core_utils.encontrar_pasta_case_insensitive(base_pgc, credor.nome)
                if not pasta_credor:
                    raise FileNotFoundError(f"Pasta do credor '{credor.nome}' não encontrada dentro de {base_pgc}. Verifique se a pasta existe e está normalizada.")

                anexos = [
                    os.path.join(pasta_credor, f)
                    for f in os.listdir(pasta_credor)
                    if f.lower().endswith('.xlsx')
                ]

                if not anexos:
                    raise FileNotFoundError("Nenhum arquivo XLSX encontrado")

                # ===== ENVIO =====
                assunto = f"Relatórios financeiros PGC {historico.numero_pgc}"
                try:
                    assunto_enc = str(__import__('email').header.Header(assunto, 'utf-8'))
                except Exception:
                    assunto_enc = assunto
                email = EmailMessage(
                    assunto_enc,
                    corpo_email,
                    settings.DEFAULT_FROM_EMAIL,
                    [credor.email]
                )
                try:
                    email.encoding = 'utf-8'
                except Exception:
                    pass

                for arq in anexos:
                    email.attach_file(arq)

                # registra tentativa no EmailLog
                try:
                    from .models import EmailLog
                    from django.utils import timezone as dj_timezone
                    log, created = EmailLog.objects.get_or_create(historico=historico, credor=credor, defaults={
                        'numero_pgc': historico.numero_pgc or 0,
                        'status': 'sending',
                        'attempts': 1,
                        'last_attempt_at': dj_timezone.now(),
                    })
                    if not created:
                        log.status = 'sending'
                        log.attempts = (log.attempts or 0) + 1
                        log.last_attempt_at = dj_timezone.now()
                        log.save()
                except Exception:
                    log = None

                try:
                    email.send(fail_silently=False)

                    credor.enviado = True
                    credor.data_envio = timezone.now()
                    credor.save(update_fields=["enviado", "data_envio"])

                    # atualiza log
                    try:
                        if log:
                            log.status = 'sent'
                            log.sent_at = dj_timezone.now()
                            log.error_message = None
                            log.save()
                    except Exception:
                        pass

                    enviados += 1

                except Exception as e:
                    logger.error(f"Erro ao enviar para {credor.nome}: {e}")
                    try:
                        credor.enviado = False
                        credor.save(update_fields=['enviado'])
                    except Exception:
                        pass
                    try:
                        if log:
                            log.status = 'failed'
                            log.error_message = str(e)
                            log.save()
                    except Exception:
                        pass

            except Exception as e:
                logger.error(f"Erro geral ao processar credor {credor.nome}: {e}")

        messages.success(request, f"{enviados} e-mails enviados para o grupo {grupo.nome} no PGC {numero_pgc}.")
        return redirect("enviar_emails_view")  # <-- RETORNO GARANTIDO NO POST

    # --- GET: sempre retorna render ---
    # monta relatório de envio por PGC (sent / not sent)
    envio_report = None
    if numero_pgc_sel and grupo_id_sel:
        try:
            from .models import EmailLog
            pgc = int(numero_pgc_sel)
            sent = []
            pending = []
            grupo_sel_obj = Grupo.objects.get(id=grupo_id_sel)
            credores_group = Credor.objects.filter(grupo=grupo_sel_obj).order_by('nome')
            for c in credores_group:
                historico = c.historicos.filter(numero_pgc=pgc).order_by('-id').first()
                if not historico:
                    continue
                log = EmailLog.objects.filter(historico=historico, credor=c).first()
                entry = {
                    'credor': c,
                    'historico': historico,
                    'status': log.status if log else ('sent' if c.enviado else 'pending'),
                    'error': log.error_message if log and log.error_message else None,
                    'attempts': log.attempts if log else 0,
                    'sent_at': log.sent_at if log else c.data_envio,
                }
                if entry['status'] == 'sent':
                    sent.append(entry)
                else:
                    pending.append(entry)
            envio_report = {'sent': sent, 'pending': pending}
        except Exception:
            envio_report = None

    contexto = {
        "grupos": grupos,
        "numeros_pgc": numeros_pgc,
        "grupo_id_sel": int(grupo_id_sel) if grupo_id_sel else None,
        "filtro_tipo_sel": filtro_tipo_sel,
        "credor_id_sel": int(credor_id_sel) if credor_id_sel else None,
        "empresa_id_sel": int(empresa_id_sel) if empresa_id_sel else None,
        "numero_pgc_sel": numero_pgc_sel,
        "credores_do_grupo": credores_do_grupo,
        "empresas": empresas,
        "mensagem": mensagem_padrao,
        "info_minimo": info_minimo_padrao,
        "info_descontos": info_descontos_padrao,
        "envio_report": envio_report,
    }
    return render(request, "core/enviar_emails_periodo.html", contexto)

# ------------- ADICIONAR NOVO CREDOR MANUALMENTE -------------
@login_required
def adicionar_credor(request):
    grupos = Grupo.objects.all()

    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        email = request.POST.get('email', '').strip()
        grupo_id = request.POST.get('grupo')

        if not nome or not grupo_id:
            messages.error(request, 'Preencha todos os campos obrigatórios.')
            return redirect('listar_Credores')

        grupo = get_object_or_404(Grupo, id=grupo_id)
        periodo_atual = datetime.today().strftime('%m/%Y')

        credor, created = Credor.get_or_create_by_nome(
            nome_display=nome,
            defaults={
                'email': email,
                'grupo': grupo,
                'periodo': periodo_atual,
            }
        )

        if not created:
            messages.info(request, f'O credor "{nome}" já existia e foi atualizado.')
        else:
            messages.success(request, f'Credor "{nome}" criado com sucesso!')

        return redirect('listar_Credores')

    return render(request, 'core/adicionar_credor.html', {'grupos': grupos})

@login_required
def editar_mensagem_email(request):
    """
    GET: carrega mensagem padrão/personalizada para edição.
    POST: salva mensagem e texto de 'info_minimo' no JSON.
    """
    if request.method == "POST":
        mensagem = request.POST.get("mensagem", "").strip()
        info_minimo = request.POST.get("info_minimo", "").strip()
        info_descontos = request.POST.get("info_descontos", "").strip()
        if not mensagem:
            messages.error(request, "A mensagem não pode ser vazia.")
        else:
            salvar_mensagens(
                mensagem or MENSAGEM_PADRAO,
                info_minimo or INFO_MINIMO_PADRAO,
                info_descontos or INFO_DESCONTOS_PADRAO,
            )
            messages.success(request, "Mensagem de e-mail atualizada com sucesso!")
        return redirect("editar_mensagem_email")

    mensagens = carregar_mensagens()
    # mensagens é {'mensagem': ..., 'info_minimo': ...}
    return render(request, "core/enviar_emails.html", mensagens)

# ---------------------------
# Views para Laghetto Sports
# ---------------------------
import os
import threading
import logging
from uuid import uuid4

from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)

def laghetto_sports_view(request):
    if request.method == "POST":

        if "arquivo" not in request.FILES:
            return JsonResponse({
                "status": "error",
                "message": "Nenhum arquivo enviado"
            }, status=400)

        uploaded_file = request.FILES["arquivo"]
        request_id = str(uuid4())

        print(f"\n{'='*60}")
        print(f"[SPORTS] Requisição de upload recebida")
        print(f"[SPORTS] Request ID: {request_id}")
        print(f"[SPORTS] Arquivo: {uploaded_file.name}")
        print(f"{'='*60}\n")

        # 📁 Pasta de processamento
        process_dir = os.path.join(
            settings.MEDIA_ROOT, "processing", request_id
        )
        os.makedirs(process_dir, exist_ok=True)

        # 📄 Caminho final do arquivo
        file_path = os.path.join(process_dir, uploaded_file.name)

        # 🔥 Salva o arquivo ANTES da thread
        with open(file_path, "wb+") as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        logger.info(f"[PGC] Arquivo salvo em {file_path}")
        print(f"[SPORTS] ✅ Arquivo salvo: {file_path}")

        # 🔥 Thread recebe SOMENTE o caminho
        thread = threading.Thread(
            target=process_pgc_file,
            kwargs={
                "file_path": file_path,
                "request_id": request_id,
                "pgc_prefix": "SPORTS"            
                },
            daemon=True
        )
        thread.start()
        print(f"[SPORTS] 🚀 Thread iniciada para processamento\n")

        return JsonResponse({
            "status": "started",
            "request_id": request_id
        })

    # GET
    return render(request, "core/laghetto_sports.html")

@require_GET
def laghetto_pgc_status(request, request_id):
    """
    Retorna o JSON de progresso para o frontend.
    """
    progresso = get_progress(request_id)

    # Se progresso é None, ainda não começou (thread nem escreveu o arquivo)
    if not progresso or progresso.get("status") == "not_found":
        return JsonResponse({
            "status": "starting",
            "percent": 0,
            "processed": 0,
            "request_id": request_id
        })

    return JsonResponse(progresso)

@require_GET
def laghetto_pgc_download(request, request_id):
    progresso = get_progress(request_id)

    if not progresso or progresso.get("status") != "completed":
        raise Http404("Processamento ainda não finalizado")

    zip_path = progresso.get("zip_path")

    if not zip_path:
        raise Http404("Arquivo ZIP ainda não foi gerado")

    if not os.path.exists(zip_path):
        raise Http404("Arquivo ZIP não encontrado")

    return FileResponse(
        open(zip_path, "rb"),
        as_attachment=True,
        filename=os.path.basename(zip_path)
    )

################################################################################

# ============================
# LGM - Upload e Progresso
# ============================

import threading

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from core.utils_progress import init_progress, log_progress, set_credor_status
from core.utils_lgm import processar_pgc_lgm
from core.utils_files import salvar_planilha_temporaria_lgm

@login_required
@csrf_exempt
def lgm_view(request):
    """
    Upload do PGC LGM
    Inicia processamento assíncrono com barra de progresso
    """
    if request.method == "POST":

        arquivo = request.FILES.get("arquivo")
        if not arquivo:
            return JsonResponse(
                {"status": "error", "message": "Arquivo não enviado"},
                status=400
            )

        # 1️⃣ Inicializa controle de progresso
        request_id = init_progress()
        # Log inicial para garantir visibilidade no card de logs
        log_progress(request_id, "✅ Upload recebido e controle de progresso inicializado")

        try:
            # 2️⃣ Salva arquivo ANTES da thread
            caminho_arquivo = salvar_planilha_temporaria_lgm(arquivo)
        except Exception as e:
            return JsonResponse(
                {
                    "status": "error",
                    "message": f"Erro ao salvar arquivo: {e}"
                },
                status=500
            )

        # 3️⃣ Processamento em background
        thread = threading.Thread(
            target=processar_pgc_lgm,
            args=(request_id, caminho_arquivo),
            daemon=True
        )
        thread.start()

        # DEBUG: log the presence of ajax headers to progress logs for troubleshooting
        try:
            log_progress(request_id, f"DEBUG_HEADERS: X-Requested-With={request.headers.get('X-Requested-With')} Accept={request.headers.get('Accept')}")
        except Exception:
            pass

        # If the request is AJAX (fetch from the page), return JSON as before.
        # Otherwise (regular form submission without JS), render the page with the request_id
        # so the UI can show the progress card and start polling automatically.
        # Robust AJAX detection: check headers case-insensitively and META keys
        is_ajax = (
            (request.headers.get('x-requested-with') or request.headers.get('X-Requested-With') or request.META.get('HTTP_X_REQUESTED_WITH')) == 'XMLHttpRequest'
            or 'application/json' in (request.headers.get('accept') or request.META.get('HTTP_ACCEPT',''))
        )
        # log resolved ajax detection for debugging
        try:
            log_progress(request_id, f"DEBUG_AJAX_DETECTED: {is_ajax}")
        except Exception:
            pass
        if is_ajax:
            return JsonResponse({
                "status": "started",
                "request_id": request_id
            })
        else:
            # record that we chose to render HTML fallback and include request_id
            try:
                log_progress(request_id, f"DEBUG_RENDER_HTML_WITH_REQUEST_ID={request_id}")
            except Exception:
                pass
            return render(request, "core/lgm.html", {"request_id": request_id})

    return render(request, "core/lgm.html")
@require_GET
@login_required
def lgm_status(request, request_id):
    """
    Endpoint de status para barra de progresso do LGM
    """
    # Usa o mesmo store em memória que o processador LGM (utils_progress)
    from core.utils_progress import get_progress as _get_progress
    progresso = _get_progress(request_id)

    if not progresso:
        return JsonResponse({"status": "not_found"}, status=404)

    return JsonResponse(progresso)


@require_GET
@login_required
def lgm_errors(request, request_id):
    """Retorna lista de erros estruturados para um request_id (se existir)."""
    caminho = os.path.join(settings.MEDIA_ROOT, 'processing', request_id, 'errors.json')
    if not os.path.exists(caminho):
        return JsonResponse({'errors': []})

    with open(caminho, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return JsonResponse({'errors': data})


@require_GET
@login_required
def lgm_credores(request, request_id):
    """Retorna metadados dos credores processados para um determinado request_id."""
    caminho = os.path.join(settings.MEDIA_ROOT, 'processing', request_id, 'credores.json')
    if not os.path.exists(caminho):
        return JsonResponse({'credores': {}})

    with open(caminho, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return JsonResponse({'credores': data})


@csrf_exempt
@login_required
def lgm_resolve_errors(request, request_id):
    """Marca erros como resolvidos (ignorados) para credores selecionados."""
    if request.method != 'POST':
        return JsonResponse({'message': 'Método inválido'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'message': 'Payload inválido'}, status=400)

    credores = data.get('credores', [])
    if not isinstance(credores, list):
        return JsonResponse({'message': 'Campo credores deve ser uma lista'}, status=400)

    from core.utils_progress import resolve_errors_for_credor, set_credor_status

    for slug in credores:
        resolve_errors_for_credor(request_id, slug)
        set_credor_status(request_id, slug, 'IGNORED')

    return JsonResponse({'status': 'ok', 'resolved': credores})


@csrf_exempt
@login_required
def lgm_reprocess(request):
    """Endpoint para reprocessar credores seletivamente.

    Body JSON: { "request_id": "<id>", "credores": ["slug1", "slug2"] }
    """
    if request.method != 'POST':
        return JsonResponse({'message': 'Método inválido'}, status=405)

    data = json.loads(request.body)
    request_id = data.get('request_id')
    credores = data.get('credores', [])

    if not request_id or not credores:
        return JsonResponse({'message': 'request_id e credores são obrigatórios'}, status=400)

    # spawn thread para reprocessamento
    # criar job id e iniciar contagem
    import uuid
    job_id = str(uuid.uuid4())
    from core.utils_progress import start_reprocess_job
    start_reprocess_job(request_id, job_id, total=len(credores))

    # Use a wrapper to import and call reprocessar_credores inside the thread to avoid NameError/import-order issues
    def _run_reprocess(rid, credos, user, jid):
        from core.utils_lgm import reprocessar_credores
        reprocessar_credores(rid, credos, initiated_by=user, job_id=jid)

    t = threading.Thread(target=_run_reprocess, args=(request_id, credores, request.user.username, job_id), daemon=True)
    t.start()

    return JsonResponse({'status': 'reprocessing_started', 'request_id': request_id, 'credores': credores, 'job_id': job_id})


@require_GET
@login_required
def lgm_reprocess_status(request, job_id):
    from core.utils_progress import get_reprocess_job
    job = get_reprocess_job(job_id)
    if not job:
        return JsonResponse({'status': 'not_found'}, status=404)
    return JsonResponse(job)


# Small endpoint to satisfy Chrome DevTools auto-discovery
# Some browsers/extensions try to fetch: /.well-known/appspecific/com.chrome.devtools.json
# Return 204 to avoid noisy 404 logs.
def chrome_devtools_manifest(request):
    return HttpResponse(status=204)


import logging
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from .models import Rendimento
from .utils_pdf import gerar_pdf_rendimento
logger = logging.getLogger(__name__)
@login_required
@login_required
def gerar_pdf_individual(request, rendimento_id):
    rendimento = get_object_or_404(Rendimento, id=rendimento_id)
    try:        
        pdf_path = gerar_pdf_rendimento(rendimento)
        with open(pdf_path, 'rb') as pdf_file:
            response = HttpResponse(pdf_file.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="Rendimento_{rendimento.id}.pdf"'
            return response
    except Exception as e:
        logger.error(f"Erro ao gerar PDF para rendimento {rendimento_id}: {e}")
        messages.error(request, 'Erro ao gerar o PDF do rendimento.')
        return redirect('detalhe_rendimentos', credor_id=rendimento.Credor.id)


