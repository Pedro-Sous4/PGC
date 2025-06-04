from django.shortcuts import render, redirect, get_object_or_404
from .forms import UploadFileForm
from .models import Credor, Rendimento
from .forms import CredorForm, RendimentoForm
import pandas as pd
from django.contrib import messages
from django.http import FileResponse
from .utils import gerar_pdf_relatorio
from .utils import enviar_email_com_pdf
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from django.core.paginator import Paginator
import csv
from django.http import HttpResponse
import openpyxl
import io
import zipfile
from django.db.models import Q
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.db import models  # <-- ADICIONE ESTA LINHA!
from .forms import RendimentoForm
from datetime import datetime
import os
from django.conf import settings


def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Faz login automático após cadastro
            return redirect('index')  # Redireciona para página inicial
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

def index(request):
    return render(request, 'core/index.html')

@login_required
def dashboard(request):
    enviados = Credor.objects.filter(enviado=True)
    nao_enviados = Credor.objects.filter(enviado=False)

    enviados_paginator = Paginator(enviados, 5)
    nao_enviados_paginator = Paginator(nao_enviados, 5)

    enviados_page = enviados_paginator.get_page(request.GET.get('enviados_page'))
    nao_enviados_page = nao_enviados_paginator.get_page(request.GET.get('nao_enviados_page'))

    enviados_total = enviados.count()
    nao_enviados_total = nao_enviados.count()

    periodos = Credor.objects.values('periodo').annotate(total=models.Count('id')).order_by('periodo')

    context = {
        'enviados': enviados_total,
        'nao_enviados': nao_enviados_total,
        'periodos_labels': [p['periodo'] for p in periodos],
        'periodos_totais': [p['total'] for p in periodos],
        'enviados_paginator': enviados_paginator,
        'enviados_page': enviados_page,
        'nao_enviados_paginator': nao_enviados_paginator,
        'nao_enviados_page': nao_enviados_page,
    }
    return render(request, 'core/dashboard.html', context)


    status = request.GET.get('status')
    order = request.GET.get('order', 'nome')
    direction = request.GET.get('dir', 'asc')
    busca = request.GET.get('busca', '')

    Credors = Credor.objects.all()

    if status == 'enviados':
        Credors = Credors.filter(enviado=True)
    elif status == 'nao_enviados':
        Credors = Credors.filter(enviado=False)

    if busca:
        Credors = Credors.filter(
            Q(nome__icontains=busca) | 
            Q(cpf__icontains=busca) | 
            Q(matricula__icontains=busca)
        )

    if direction == 'desc':
        Credors = Credors.order_by(f'-{order}')
    else:
        Credors = Credors.order_by(order)

    paginator = Paginator(Credors, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'core/listar_Credors.html', {
        'page_obj': page_obj,
        'status': status,
        'order': order,
        'direction': direction,
        'busca': busca
    })

def download_modelo_planilha(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Modelo Credores"

    # Cabeçalho
    ws.append(['nome', 'email', 'cpf', 'matricula', 'periodo', 'rendimento'])

    # Exemplo opcional
    ws.append(['João Silva', 'joao@email.com', '123.456.789-00', '001', '05/2025', '7500.00'])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=modelo_Credors.xlsx'
    return response

def gerar_pdf_view(request, Credor_id):
    Credor = Credor.objects.get(id=Credor_id)
    pdf_path = gerar_pdf_relatorio(Credor)
    
    return FileResponse(open(pdf_path, 'rb'), as_attachment=True, filename=f'relatorio_{Credor.cpf}.pdf')

def enviar_emails_view(request):
    if request.method == 'POST':
        periodo = request.POST.get('periodo')
        Credors = Credor.objects.filter(enviado=False, periodo=periodo)
        enviados = 0
        for f in Credors:
            try:
                enviar_email_com_pdf(f)
                enviados += 1
            except Exception as e:
                print(f"Erro ao enviar para {f.email}: {e}")

        messages.success(request, f'{enviados} e-mails enviados para o período {periodo}!')
    
    return render(request, 'core/enviar_emails_periodo.html')

def enviar_email_individual(request, Credor_id):
    Credor = get_object_or_404(Credor, id=Credor_id)
    try:
        enviar_email_com_pdf(Credor)
        messages.success(request, f'E-mail enviado para {Credor.nome} com sucesso!')
    except Exception as e:
        messages.error(request, f'Erro ao enviar para {Credor.nome}: {e}')
    
    return redirect('listar_Credors')

@csrf_exempt
def enviar_emails_selecionados(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        ids = data.get('ids', [])
        enviados = 0

        for id in ids:
            Credor = Credor.objects.get(id=id)
            try:
                enviar_email_com_pdf(Credor)
                enviados += 1
            except Exception as e:
                print(f"Erro ao enviar para {Credor.email}: {e}")

        return JsonResponse({'mensagem': f'{enviados} e-mails enviados com sucesso!'})

    return JsonResponse({'mensagem': 'Método inválido'}, status=405)

@csrf_exempt
def excluir_Credors_selecionados(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        ids = data.get('ids', [])
        excluidos = 0

        for id in ids:
            try:
                Credor = Credor.objects.get(id=id)
                Credor.delete()
                excluidos += 1
            except Credor.DoesNotExist:
                continue

        return JsonResponse({'mensagem': f'{excluidos} funcionário(s) excluído(s) com sucesso.'})

    return JsonResponse({'mensagem': 'Método inválido'}, status=405)

def excluir_Credor(request, Credor_id):
    Credor = get_object_or_404(Credor, id=Credor_id)
    Credor.delete()
    messages.success(request, 'Funcionário excluído com sucesso.')
    return redirect('listar_Credors')

def exportar_Credors(request):
    status = request.GET.get('status')

    Credors = Credor.objects.all()
    if status == 'enviados':
        Credors = Credors.filter(enviado=True)
    elif status == 'nao_enviados':
        Credors = Credors.filter(enviado=False)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="Credors.csv"'

    writer = csv.writer(response)
    writer.writerow(['Nome', 'Email', 'CPF', 'Matrícula', 'Enviado'])

    for f in Credors:
        writer.writerow([f.nome, f.email, f.cpf, f.matricula, 'Sim' if f.enviado else 'Não'])

    return response

def exportar_Credors_excel(request):
    status = request.GET.get('status')

    Credors = Credor.objects.all()
    if status == 'enviados':
        Credors = Credors.filter(enviado=True)
    elif status == 'nao_enviados':
        Credors = Credors.filter(enviado=False)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Credores"

    # Cabeçalho
    ws.append(['Nome', 'Email', 'CPF', 'Matrícula', 'Enviado'])

    for f in Credors:
        ws.append([
            f.nome,
            f.email,
            f.cpf,
            f.matricula,
            'Sim' if f.enviado else 'Não'
        ])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=Credors.xlsx'
    wb.save(response)
    return response

@csrf_exempt
def exportar_pdfs_selecionados(request):

    if request.method == 'POST':
        data = json.loads(request.body)
        ids = data.get('ids', [])

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            for id in ids:
                Credor = Credor.objects.get(id=id)
                pdf_path = gerar_pdf_relatorio(Credor)
                zip_file.write(pdf_path, arcname=f"{Credor.nome}.pdf")

        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename=relatorios.zip'
        return response

    return JsonResponse({'mensagem': 'Método inválido'}, status=405)

@csrf_exempt
def alterar_status_selecionados(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        ids = data.get('ids', [])
        status = data.get('status', False)

        atualizados = Credor.objects.filter(id__in=ids).update(enviado=status)
        return JsonResponse({'mensagem': f'Status alterado para {atualizados} funcionário(s).'})

    return JsonResponse({'mensagem': 'Método inválido'}, status=405)

def atualizar_periodo_view(request, Credor_id):
    Credor = get_object_or_404(Credor, id=Credor_id)
    Credor.atualizar_periodo()

@login_required
def listar_Credores(request):
    Credores = Credor.objects.all()
    return render(request, 'core/listar_credores.html', {'Credores': Credores})

@login_required
def editar_Credor(request, Credor_id):
    Credor = get_object_or_404(Credor, pk=Credor_id)
    if request.method == 'POST':
        form = CredorForm(request.POST, instance=Credor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Credor atualizado com sucesso!')
            return redirect('listar_Credor')
    else:
        form = CredorForm(instance=Credor)
    return render(request, 'core/editar_Credor.html', {'form': form})

@login_required
def detalhe_rendimentos(request, Credor_id):
    Credor = get_object_or_404(Credor, pk=Credor_id)
    rendimentos = Credor.rendimentos.all()
    return render(request, 'core/detalhe_rendimentos.html', {'Credor': Credor, 'rendimentos': rendimentos})

@login_required
def adicionar_rendimento(request, Credor_id):
    Credor = get_object_or_404(Credor, pk=Credor_id)
    if request.method == 'POST':
        form = RendimentoForm(request.POST)
        if form.is_valid():
            rendimento = form.save(commit=False)
            rendimento.Credor = Credor
            rendimento.save()
            Credor.atualizar_periodo()
            messages.success(request, 'Rendimento adicionado com sucesso!')
            return redirect('detalhe_rendimentos', Credor_id=Credor.id)
    else:
        form = RendimentoForm()
    return render(request, 'core/adicionar_rendimento.html', {'form': form, 'Credor': Credor})

@login_required
def editar_rendimento(request, rendimento_id):
    rendimento = get_object_or_404(Rendimento, pk=rendimento_id)
    if request.method == 'POST':
        form = RendimentoForm(request.POST, instance=rendimento)
        if form.is_valid():
            form.save()
            rendimento.Credor.atualizar_periodo()
            messages.success(request, 'Rendimento atualizado com sucesso!')
            return redirect('detalhe_rendimentos', Credor_id=rendimento.Credor.id)
    else:
        form = RendimentoForm(instance=rendimento)
    return render(request, 'core/editar_rendimento.html', {'form': form, 'Credor': rendimento.Credor})

@login_required
def excluir_rendimento(request, rendimento_id):
    rendimento = get_object_or_404(Rendimento, pk=rendimento_id)
    Credor_id = rendimento.Credor.id
    rendimento.delete()
    messages.success(request, 'Rendimento excluído com sucesso!')
    return redirect('detalhe_rendimentos', Credor_id=Credor_id)
    rendimento = get_object_or_404(Rendimento, id=rendimento_id)
    Credor_id = rendimento.Credor.id
    rendimento.delete()
    Credor.objects.get(id=Credor_id).atualizar_periodo()
    messages.success(request, 'Rendimento excluído com sucesso!')
    return redirect('detalhe_rendimentos', Credor_id=Credor_id)



@login_required
def upload_emails(request):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']

        # Lê a planilha de emails
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        elif file.name.endswith('.xlsx'):
            df = pd.read_excel(file)
        else:
            messages.error(request, 'Formato de arquivo inválido. Envie .csv ou .xlsx.')
            return redirect('upload_emails')

        # Normaliza colunas
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

        required_cols = {'nome', 'email'}
        missing_cols = required_cols - set(df.columns)

        if missing_cols:
            messages.error(request, f'Colunas obrigatórias ausentes: {missing_cols}')
            return redirect('upload_emails')

        atualizados = 0
        criados = 0

        for _, row in df.iterrows():
            nome = row['nome']
            email = row['email']

            credor, created = Credor.objects.get_or_create(nome=nome, defaults={'email': email})
            if not created:
                credor.email = email  # Atualiza email caso já exista
                credor.save()
                atualizados += 1
            else:
                criados += 1

        messages.success(
            request,
            f'Upload concluído! {criados} credor(es) criado(s), {atualizados} credor(es) atualizado(s).'
        )
        return redirect('upload_emails')

    return render(request, 'core/upload_emails.html')


@login_required
def upload_planilha(request):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        
        # Lê a planilha PGC base
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        elif file.name.endswith('.xlsx'):
            df = pd.read_excel(file, sheet_name=None)  # Todas as abas
        else:
            messages.error(request, 'Formato de arquivo inválido. Envie .csv ou .xlsx.')
            return redirect('upload_planilha')

        # Normaliza colunas: tira espaços, pontos, deixa minúsculo
        def normalize_cols(df):
            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('.', '')
            return df

        base_df = None
        for sheet_name, sheet_df in df.items():
            if 'base' in sheet_name.lower():
                base_df = normalize_cols(sheet_df)
                break

        if base_df is None:
            messages.error(request, 'A aba BASE PGC 26 não foi encontrada na planilha.')
            return redirect('upload_planilha')

        # Pega lista de credores únicos
        credores = base_df['credor'].unique()

        for credor_nome in credores:
            credor_df = base_df[base_df['credor'] == credor_nome]

            # Cria ou atualiza o credor
            credor, created = Credor.objects.get_or_create(nome=credor_nome, defaults={'email': ''})
            credor.periodo = datetime.now().strftime('%m/%Y')  # Atualiza com mês/ano atual
            credor.save()

            # Gera diretório de saída
            output_dir = os.path.join(settings.MEDIA_ROOT, 'arquivos_gerados', credor_nome.replace(' ', '_'))
            os.makedirs(output_dir, exist_ok=True)

            # ➡️ 1. Emissão
            emissao = (credor_df.groupby(['empresa', 'credor'])
                       .agg({'valor_original': 'sum'})
                       .reset_index())
            if 'cnpj' in credor_df.columns:
                emissao['cnpj'] = credor_df.groupby(['empresa', 'credor'])['cnpj'].first().values
                emissao = emissao[['empresa', 'credor', 'cnpj', 'valor_original']]
            else:
                emissao = emissao[['empresa', 'credor', 'valor_original']]
            emissao_file = os.path.join(output_dir, f"{credor_nome} - PGC EMISSÃO.xlsx")
            emissao.to_excel(emissao_file, index=False)

            # ➡️ 2. Extrato
            extrato_cols = ['empresa', 'credor', 'documento', 'cliente', 'parcela', 
                            'dt_emissao', 'valor_original', 'dt_vencimento', 'obs_baixa']
            missing_cols = [col for col in extrato_cols if col not in credor_df.columns]
            if missing_cols:
                messages.warning(request, f'Faltando colunas para EXTRATO do credor {credor_nome}: {missing_cols}')
            else:
                extrato = credor_df[extrato_cols]
                extrato_file = os.path.join(output_dir, f"{credor_nome} - EXTRATO.xlsx")
                extrato.to_excel(extrato_file, index=False)

            # ➡️ 3. Produtividade
            produtividade_cols = ['empresa', 'credor', 'documento', 'cliente', 'parcela', 
                                  'dt_emissao', 'valor_original', 'dt_vencimento']
            missing_cols = [col for col in produtividade_cols if col not in credor_df.columns]
            if missing_cols:
                messages.warning(request, f'Faltando colunas para PRODUTIVIDADE do credor {credor_nome}: {missing_cols}')
            else:
                produtividade = credor_df[produtividade_cols]
                produtividade_file = os.path.join(output_dir, f"{credor_nome} - PRODUTIVIDADE.xlsx")
                produtividade.to_excel(produtividade_file, index=False)

            # ➡️ 4. PGC 26
            pgc_cols = ['empresa', 'credor', 'documento', 'cliente', 'parcela', 
                        'dt_emissao', 'valor_original']
            missing_cols = [col for col in pgc_cols if col not in credor_df.columns]
            if missing_cols:
                messages.warning(request, f'Faltando colunas para PGC 26 do credor {credor_nome}: {missing_cols}')
            else:
                pgc = credor_df[pgc_cols]
                pgc_file = os.path.join(output_dir, f"{credor_nome} - PGC 26.xlsx")
                pgc.to_excel(pgc_file, index=False)

        messages.success(request, 'Planilha processada com sucesso! Arquivos gerados para cada credor.')
        return redirect('upload_planilha')

    return render(request, 'core/upload_planilha.html')

