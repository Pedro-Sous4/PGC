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

def obter_minimo_garantido_para_credor(credor_nome, numero_pgc):
    caminho_arquivo = os.path.join(settings.MEDIA_ROOT, 'PGC', str(numero_pgc), f'PGC {numero_pgc}.xlsx')
    if not os.path.exists(caminho_arquivo):
        logging.warning(f"[MÍNIMO] Arquivo não encontrado: {caminho_arquivo}")
        return None

    try:
        wb = load_workbook(caminho_arquivo, data_only=True)
    except Exception as e:
        logging.warning(f"[MÍNIMO] Erro ao abrir planilha: {e}")
        return None

    aba = next((s for s in wb.sheetnames if f'PGC {numero_pgc}' in s.upper()), None)
    if not aba:
        logging.warning(f"[MÍNIMO] Aba com nome 'PGC {numero_pgc}' não encontrada.")
        return None

    ws = wb[aba]

    header_row = 7
    col_map = {}
    for idx, cell in enumerate(ws[header_row]):
        value = str(cell.value).strip().upper() if cell.value else ''
        col_map[value] = idx

    try:
        idx_nome = col_map['CREDOR']
        idx_valor = col_map['MINIMO/FIXO GARANTIDO PARA EMISSAO NF']
        idx_empresa = col_map['EMPRESA EMISSÃO NF']
        idx_cnpj = col_map['CNPJ']
    except KeyError as e:
        logging.warning(f"[MÍNIMO] Coluna esperada não encontrada: {e}")
        return None

    nome_alvo = normalizar_nome(credor_nome)
    for row in ws.iter_rows(min_row=header_row + 1):
        nome_planilha = row[idx_nome].value
        if nome_planilha and normalizar_nome(str(nome_planilha)) == nome_alvo:
            minimo = row[idx_valor].value
            empresa = row[idx_empresa].value
            cnpj = row[idx_cnpj].value
            if minimo and empresa and cnpj:
                valor = float(str(minimo).replace("R$", "").replace(".", "").replace(",", "."))
                valor_fmt = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                return {"valor": valor, "valor_formatado": valor_fmt, "empresa": empresa, "cnpj": str(cnpj)}
    logging.info(f"[MÍNIMO] Nenhum valor mínimo encontrado para {credor_nome}")
    return None

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
    enviados_page = Paginator(enviados, 10).get_page(request.GET.get('enviados_page'))
    nao_enviados_page = Paginator(nao_enviados, 10).get_page(request.GET.get('nao_enviados_page'))

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

@login_required
def listar_Credores(request):
    busca = request.GET.get('busca', '')
    status = request.GET.get('status', '')
    order = request.GET.get('order', 'nome')
    direction = request.GET.get('dir', 'asc')

    credores = Credor.objects.all()

    if status == 'enviados':
        credores = credores.filter(enviado=True)
    elif status == 'nao_enviados':
        credores = credores.filter(enviado=False)

    if busca:
        credores = credores.filter(Q(nome__icontains=busca))

    if direction == 'desc':
        credores = credores.order_by(f'-{order}')
    else:
        credores = credores.order_by(order)

    paginator = Paginator(credores, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'core/listar_credores.html', {
        'page_obj': page_obj,
        'status': status,
        'busca': busca,
        'order': order,
        'direction': direction,
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
    return render(request, 'core/detalhe_rendimentos.html', {'Credor': credor, 'rendimentos': rendimentos})

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
            messages.success(request, 'Rendimento adicionado com sucesso!')
            return redirect('detalhe_rendimentos', credor_id=credor.id)
    else:
        form = RendimentoForm()
    return render(request, 'core/adicionar_rendimento.html', {'form': form, 'Credor': credor})

@login_required
def editar_rendimento(request, rendimento_id):
    rendimento = get_object_or_404(Rendimento, pk=rendimento_id)
    if request.method == 'POST':
        form = RendimentoForm(request.POST, instance=rendimento)
        if form.is_valid():
            form.save()
            rendimento.Credor.atualizar_periodo()
            messages.success(request, 'Rendimento atualizado com sucesso!')
            return redirect('detalhe_rendimentos', credor_id=rendimento.Credor.id)
    else:
        form = RendimentoForm(instance=rendimento)
    return render(request, 'core/editar_rendimento.html', {'form': form, 'Credor': rendimento.Credor})

@login_required
def excluir_rendimento(request, rendimento_id):
    rendimento = get_object_or_404(Rendimento, pk=rendimento_id)
    credor_id = rendimento.Credor.id
    rendimento.delete()
    messages.success(request, 'Rendimento excluído com sucesso!')
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
def enviar_emails_view(request):
    grupos = Grupo.objects.all()
    numeros_pgc = HistoricoPGC.objects.values_list('numero_pgc', flat=True).distinct().order_by('numero_pgc')

    if request.method == 'POST':
        numero_pgc = request.POST.get('numero_pgc')
        grupo_id = request.POST.get('grupo_id')

        if not grupo_id or not numero_pgc:
            messages.error(request, 'Selecione um grupo e um número de PGC.')
            return redirect('enviar_emails_view')

        try:
            grupo = Grupo.objects.get(id=grupo_id)
        except Grupo.DoesNotExist:
            messages.error(request, 'Grupo não encontrado.')
            return redirect('enviar_emails_view')

        credores = Credor.objects.filter(enviado=False, grupo=grupo, historicos__numero_pgc=numero_pgc).distinct()
        enviados = 0

        for credor in credores:
            try:
                enviar_email_com_arquivos(credor)
                credor.enviado = True
                credor.data_envio = timezone.now()
                credor.save()
                enviados += 1
            except Exception as e:
                print(f"Erro ao enviar para {credor.nome}: {e}")

        messages.success(request, f'{enviados} e-mails enviados para o grupo {grupo.nome} e PGC {numero_pgc}!')
        return redirect('enviar_emails_view')

    return render(request, 'core/enviar_emails_periodo.html', {'grupos': grupos, 'numeros_pgc': numeros_pgc})


@login_required
def exportar_Credores(request):
    status = request.GET.get('status')

    credores = Credor.objects.all()
    if status == 'enviados':
        credores = credores.filter(enviado=True)
    elif status == 'nao_enviados':
        credores = credores.filter(enviado=False)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="credores.csv"'

    writer = csv.writer(response)
    writer.writerow(['Nome', 'Email', 'Enviado'])

    for c in credores:
        writer.writerow([c.nome, c.email, 'Sim' if c.enviado else 'Não'])

    return response

@login_required
def exportar_Credores_excel(request):
    status = request.GET.get('status')

    credores = Credor.objects.all()
    if status == 'enviados':
        credores = credores.filter(enviado=True)
    elif status == 'nao_enviados':
        credores = credores.filter(enviado=False)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Credores"

    ws.append(['Nome', 'Email', 'Enviado'])

    for c in credores:
        ws.append([c.nome, c.email, 'Sim' if c.enviado else 'Não'])

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
        #periodo_atual = datetime.today().strftime('%m/%Y')
        from dateutil.relativedelta import relativedelta

        data_anterior = pd.to_datetime('today') - relativedelta(months=1)
        periodo_atual = data_anterior.strftime('%m/%Y')
        for _, row in df.iterrows():
            nome = str(row['nome']).strip()
            email = str(row['email']).strip()
            grupo_nome = str(row['grupo']).strip()

            grupo = Grupo.objects.filter(nome__iexact=grupo_nome).first()
            if not grupo:
                messages.error(request, f"Grupo '{grupo_nome}' não encontrado para o credor '{nome}'.")
                continue

            credor, created = Credor.objects.get_or_create(
                nome=nome,
                defaults={
                    'email': email,
                    'periodo': periodo_atual,
                    'grupo': grupo,
                }
            )

            if not created:
                credor.email = email
                credor.periodo = periodo_atual
                credor.grupo = grupo
                credor.save()
                atualizados += 1
            else:
                criados += 1

        messages.success(request, f'Upload concluído! {criados} criado(s), {atualizados} atualizado(s).')
        return redirect('upload_emails')

    return render(request, 'core/upload_emails.html')



def abrir_pasta_explorer(request, credor_id, numero_pgc):
    credor = get_object_or_404(Credor, pk=credor_id)
    pasta = os.path.join("C:\\PGC\\envio_rendimentos\\arquivos_gerados\\PGC", str(numero_pgc), credor.nome_pasta())
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
                credor_obj = Credor.objects.create(nome=nome, email='', periodo=periodo)
            else:
                credor_obj.periodo = periodo
                credor_obj.save()

            HistoricoPGC.objects.create(
                credor=credor_obj,
                numero_pgc=numero_pgc,
                periodo=periodo,
                valor_total=df_credor['valor_original'].sum()
            )

            pasta_saida = os.path.join(settings.MEDIA_ROOT, 'PGC', str(numero_pgc), credor_obj.nome_pasta())
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

                arquivos = {
                    'PGC EMISSÃO': df_emissao,
                    f'PGC {numero_pgc}': df_credor[['empresa', 'credor', 'documento', 'cliente', 'parcela', 'dt_emissao', 'valor_original']],
                }

                if df_ext_credor is not None:
                    arquivos['EXTRATO'] = df_ext_credor[['empresa', 'credor', 'documento', 'cliente', 'parcela', 'dt_emissao', 'valor_original', 'dt_vencimento', 'obs_baixa']]

                if df_prod_credor is not None:
                    arquivos['PRODUTIVIDADE'] = df_prod_credor[['empresa', 'credor', 'documento', 'cliente', 'parcela', 'dt_emissao', 'valor_original', 'dt_vencimento']]

                nome_arquivo_seguro = re.sub(r'[\\/:"*?<>|]', '', nome)

                for nome_arq, df_arq in arquivos.items():
                    caminho_arquivo = os.path.join(pasta_saida, f'{nome_arquivo_seguro} - {nome_arq}.xlsx')
                    df_arq.to_excel(caminho_arquivo, index=False)

                # Salva mínimo se aplicável
                if minimos_df is not None:
                    minimo_credor = obter_minimo_garantido_para_credor(nome, minimos_df)
                    if minimo_credor:
                        caminho_minimo = os.path.join(pasta_saida, 'mínimo.xlsx')
                        pd.DataFrame([{
                            'credor': nome,
                            'minimo': minimo_credor['valor'],
                            'empresa': minimo_credor['empresa'],
                            'cnpj': minimo_credor['cnpj']
                        }]).to_excel(caminho_minimo, index=False)

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

#BONI
@login_required
def upload_planilha(request):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        numero_pgc = request.POST.get('numero_pgc')

        if not numero_pgc:
            messages.error(request, 'Informe o número do PGC.')
            return redirect('upload_planilha')

        try:
            caminho_temporario = salvar_planilha_temporaria(file, numero_pgc)
            caminho_pgcsheet = normalizar_e_salvar_planilha_base(caminho_temporario, numero_pgc)

            # Gerar planilha de mínimo
            aba_pgcs = pd.read_excel(caminho_pgcsheet)
            df_minimo = extrair_minimos_robusto(aba_pgcs, caminho_temporario, numero_pgc)
            salvar_minimos_como_excel(df_minimo, numero_pgc)
            # Gerar planilha EXTRATO.xlsx a partir da original
            try:
                planilhas = pd.ExcelFile(caminho_temporario)
                aba_extrato = next(
                    (n for n in planilhas.sheet_names if "extrato" in n.lower() and "credor" in n.lower()), None
                ) or next(
                    (n for n in planilhas.sheet_names if "exrato" in n.lower() and "credor" in n.lower()), None
                )

                if not aba_extrato:
                    raise Exception("Aba EXTRATO CREDOR não encontrada.")

                df_extrato = pd.read_excel(planilhas, sheet_name=aba_extrato)
                df_extrato = normalizar_colunas_simples(df_extrato)

                pasta_saida = os.path.join(settings.MEDIA_ROOT, 'PGC', str(numero_pgc))
                os.makedirs(pasta_saida, exist_ok=True)
                df_extrato.to_excel(os.path.join(pasta_saida, "EXTRATO.xlsx"), index=False)
                logger.info(f"[EXTRATO] Planilha EXTRATO.xlsx gerada com sucesso em PGC/{numero_pgc}/")
            except Exception as e:
                logger.warning(f"[EXTRATO] Falha ao gerar EXTRATO.xlsx: {e}")


        except Exception as e:
            messages.error(request, f'Erro ao processar planilha: {e}')
            return redirect('upload_planilha')

        # Processar por credor
        try:
                base_file_path = os.path.join(settings.MEDIA_ROOT, 'PGC', str(numero_pgc), f'BASE PGC {numero_pgc}.xlsx')
                base_df = pd.read_excel(base_file_path)

                #periodo = pd.to_datetime('today').strftime('%m/%Y')
                from dateutil.relativedelta import relativedelta
                data_anterior = pd.to_datetime('today') - relativedelta(months=1)
                periodo = data_anterior.strftime('%m/%Y')

                # Mapeia todos os credores existentes com nome normalizado
                credores_existentes = {
                    _normalize_name(c.nome): c for c in Credor.objects.all()
                }

                for nome in base_df['credor'].unique():
                    df_credor = base_df[base_df['credor'] == nome]
                    nome_normalizado = _normalize_name(nome)

                    credor_obj = credores_existentes.get(nome_normalizado)

                    if not credor_obj:
                        credor_obj = Credor.objects.create(nome=nome.strip(), email='', periodo=periodo)
                    else:
                        credor_obj.periodo = periodo
                        credor_obj.save()

                    HistoricoPGC.objects.create(
                        credor=credor_obj,
                        numero_pgc=numero_pgc,
                        periodo=periodo,
                        valor_total=df_credor['valor_original'].sum()
                    )

                    try:
                        gerar_arquivos_credor(credor_obj, numero_pgc)
                    except Exception as e:
                        messages.warning(request, f"Erro ao gerar arquivos para {nome}: {e}")

                messages.success(request, f'Planilha PGC {numero_pgc} processada com sucesso.')
        except Exception as e:
                messages.error(request, f'Erro ao montar arquivos por credor: {e}')


        return redirect('upload_planilha')
    return render(request, 'core/upload_planilha.html')