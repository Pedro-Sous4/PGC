from django.shortcuts import render, redirect, get_object_or_404
from .forms import UploadFileForm
from .models import Employee, Rendimento
from .forms import EmployeeForm
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
    enviados = Employee.objects.filter(enviado=True)
    nao_enviados = Employee.objects.filter(enviado=False)

    enviados_paginator = Paginator(enviados, 5)
    nao_enviados_paginator = Paginator(nao_enviados, 5)

    enviados_page = enviados_paginator.get_page(request.GET.get('enviados_page'))
    nao_enviados_page = nao_enviados_paginator.get_page(request.GET.get('nao_enviados_page'))

    enviados_total = enviados.count()
    nao_enviados_total = nao_enviados.count()

    periodos = Employee.objects.values('periodo').annotate(total=models.Count('id')).order_by('periodo')

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

@login_required
def listar_funcionarios(request):
    status = request.GET.get('status')
    order = request.GET.get('order', 'nome')
    direction = request.GET.get('dir', 'asc')
    busca = request.GET.get('busca', '')

    funcionarios = Employee.objects.all()

    if status == 'enviados':
        funcionarios = funcionarios.filter(enviado=True)
    elif status == 'nao_enviados':
        funcionarios = funcionarios.filter(enviado=False)

    if busca:
        funcionarios = funcionarios.filter(
            Q(nome__icontains=busca) | 
            Q(cpf__icontains=busca) | 
            Q(matricula__icontains=busca)
        )

    if direction == 'desc':
        funcionarios = funcionarios.order_by(f'-{order}')
    else:
        funcionarios = funcionarios.order_by(order)

    paginator = Paginator(funcionarios, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'core/listar_funcionarios.html', {
        'page_obj': page_obj,
        'status': status,
        'order': order,
        'direction': direction,
        'busca': busca
    })

@login_required
def upload_planilha(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo = form.cleaned_data['arquivo']

            try:
                if arquivo.name.endswith('.csv'):
                    df = pd.read_csv(arquivo)
                else:
                    df = pd.read_excel(arquivo)
            except Exception as e:
                messages.error(request, f'Erro ao ler a planilha: {e}')
                return redirect('upload_planilha')

            # Normalize colunas
            df.columns = df.columns.str.lower().str.strip()

            obrigatorias = {'nome', 'email', 'cpf'}
            if not obrigatorias.issubset(set(df.columns)):
                messages.error(request, 'A planilha deve conter as colunas: nome, email, cpf.')
                return redirect('upload_planilha')

            criados = 0
            ignorados = 0

            for _, row in df.iterrows():
                nome = row.get('nome')
                email = row.get('email')
                cpf = row.get('cpf')
                matricula = row.get('matricula') or ''
                periodo = row.get('periodo') or ''
                rendimento_valor = row.get('rendimento')

                if not nome or not email or not cpf:
                    ignorados += 1
                    continue

                if Employee.objects.filter(email=email).exists() or Employee.objects.filter(cpf=cpf).exists():
                    ignorados += 1
                    continue

                try:
                    emp = Employee(
                        nome=nome,
                        email=email,
                        cpf=cpf,
                        matricula=matricula,
                        periodo=periodo
                    )
                    emp.save()

                    # Se rendimento informado, cria também
                    if pd.notna(rendimento_valor) and rendimento_valor != '':
                        Rendimento.objects.create(
                            employee=emp,
                            periodo=periodo,
                            valor=rendimento_valor
                        )
                        # Atualiza período no employee com método
                        emp.atualizar_periodo()

                    criados += 1
                except Exception as e:
                    ignorados += 1
                    print(f"Erro ao salvar {nome}: {e}")

            messages.success(request, f'Importação finalizada: {criados} criados, {ignorados} ignorados.')
            return redirect('upload_planilha')

    else:
        form = UploadFileForm()

    return render(request, 'core/upload_planilha.html', {'form': form})

def download_modelo_planilha(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Modelo Funcionários"

    # Cabeçalho
    ws.append(['nome', 'email', 'cpf', 'matricula', 'periodo', 'rendimento'])

    # Exemplo opcional
    ws.append(['João Silva', 'joao@email.com', '123.456.789-00', '001', '05/2025', '7500.00'])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=modelo_funcionarios.xlsx'
    return response

def gerar_pdf_view(request, employee_id):
    employee = Employee.objects.get(id=employee_id)
    pdf_path = gerar_pdf_relatorio(employee)
    
    return FileResponse(open(pdf_path, 'rb'), as_attachment=True, filename=f'relatorio_{employee.cpf}.pdf')

def enviar_emails_view(request):
    if request.method == 'POST':
        periodo = request.POST.get('periodo')
        funcionarios = Employee.objects.filter(enviado=False, periodo=periodo)
        enviados = 0
        for f in funcionarios:
            try:
                enviar_email_com_pdf(f)
                enviados += 1
            except Exception as e:
                print(f"Erro ao enviar para {f.email}: {e}")

        messages.success(request, f'{enviados} e-mails enviados para o período {periodo}!')
    
    return render(request, 'core/enviar_emails_periodo.html')


def editar_funcionario(request, employee_id):
    funcionario = get_object_or_404(Employee, id=employee_id)
    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=funcionario)
        if form.is_valid():
            form.save()
            messages.success(request, 'Funcionário atualizado com sucesso!')
            return redirect('listar_funcionarios')
    else:
        form = EmployeeForm(instance=funcionario)
    
    return render(request, 'core/editar_funcionario.html', {'form': form})

def enviar_email_individual(request, employee_id):
    funcionario = get_object_or_404(Employee, id=employee_id)
    try:
        enviar_email_com_pdf(funcionario)
        messages.success(request, f'E-mail enviado para {funcionario.nome} com sucesso!')
    except Exception as e:
        messages.error(request, f'Erro ao enviar para {funcionario.nome}: {e}')
    
    return redirect('listar_funcionarios')

@csrf_exempt
def enviar_emails_selecionados(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        ids = data.get('ids', [])
        enviados = 0

        for id in ids:
            funcionario = Employee.objects.get(id=id)
            try:
                enviar_email_com_pdf(funcionario)
                enviados += 1
            except Exception as e:
                print(f"Erro ao enviar para {funcionario.email}: {e}")

        return JsonResponse({'mensagem': f'{enviados} e-mails enviados com sucesso!'})

    return JsonResponse({'mensagem': 'Método inválido'}, status=405)

@csrf_exempt
def excluir_funcionarios_selecionados(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        ids = data.get('ids', [])
        excluidos = 0

        for id in ids:
            try:
                funcionario = Employee.objects.get(id=id)
                funcionario.delete()
                excluidos += 1
            except Employee.DoesNotExist:
                continue

        return JsonResponse({'mensagem': f'{excluidos} funcionário(s) excluído(s) com sucesso.'})

    return JsonResponse({'mensagem': 'Método inválido'}, status=405)

def excluir_funcionario(request, employee_id):
    funcionario = get_object_or_404(Employee, id=employee_id)
    funcionario.delete()
    messages.success(request, 'Funcionário excluído com sucesso.')
    return redirect('listar_funcionarios')

def exportar_funcionarios(request):
    status = request.GET.get('status')

    funcionarios = Employee.objects.all()
    if status == 'enviados':
        funcionarios = funcionarios.filter(enviado=True)
    elif status == 'nao_enviados':
        funcionarios = funcionarios.filter(enviado=False)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="funcionarios.csv"'

    writer = csv.writer(response)
    writer.writerow(['Nome', 'Email', 'CPF', 'Matrícula', 'Enviado'])

    for f in funcionarios:
        writer.writerow([f.nome, f.email, f.cpf, f.matricula, 'Sim' if f.enviado else 'Não'])

    return response

def exportar_funcionarios_excel(request):
    status = request.GET.get('status')

    funcionarios = Employee.objects.all()
    if status == 'enviados':
        funcionarios = funcionarios.filter(enviado=True)
    elif status == 'nao_enviados':
        funcionarios = funcionarios.filter(enviado=False)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Funcionários"

    # Cabeçalho
    ws.append(['Nome', 'Email', 'CPF', 'Matrícula', 'Enviado'])

    for f in funcionarios:
        ws.append([
            f.nome,
            f.email,
            f.cpf,
            f.matricula,
            'Sim' if f.enviado else 'Não'
        ])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=funcionarios.xlsx'
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
                funcionario = Employee.objects.get(id=id)
                pdf_path = gerar_pdf_relatorio(funcionario)
                zip_file.write(pdf_path, arcname=f"{funcionario.nome}.pdf")

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

        atualizados = Employee.objects.filter(id__in=ids).update(enviado=status)
        return JsonResponse({'mensagem': f'Status alterado para {atualizados} funcionário(s).'})

    return JsonResponse({'mensagem': 'Método inválido'}, status=405)

def atualizar_periodo_view(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    employee.atualizar_periodo()

@login_required
def detalhe_rendimentos(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    rendimentos = employee.rendimentos.all().order_by('-periodo')
    return render(request, 'core/detalhe_rendimentos.html', {'employee': employee, 'rendimentos': rendimentos})

@login_required
def adicionar_rendimento(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    if request.method == 'POST':
        form = RendimentoForm(request.POST)
        if form.is_valid():
            rendimento = form.save(commit=False)
            rendimento.employee = employee
            rendimento.save()
            employee.atualizar_periodo()
            messages.success(request, 'Rendimento adicionado com sucesso!')
            return redirect('detalhe_rendimentos', employee_id=employee.id)
    else:
        form = RendimentoForm()
    return render(request, 'core/rendimento_form.html', {'form': form, 'employee': employee})

@login_required
def editar_rendimento(request, rendimento_id):
    rendimento = get_object_or_404(Rendimento, id=rendimento_id)
    if request.method == 'POST':
        form = RendimentoForm(request.POST, instance=rendimento)
        if form.is_valid():
            form.save()
            rendimento.employee.atualizar_periodo()
            messages.success(request, 'Rendimento atualizado com sucesso!')
            return redirect('detalhe_rendimentos', employee_id=rendimento.employee.id)
    else:
        form = RendimentoForm(instance=rendimento)
    return render(request, 'core/rendimento_form.html', {'form': form, 'employee': rendimento.employee})

@login_required
def excluir_rendimento(request, rendimento_id):
    rendimento = get_object_or_404(Rendimento, id=rendimento_id)
    employee_id = rendimento.employee.id
    rendimento.delete()
    Employee.objects.get(id=employee_id).atualizar_periodo()
    messages.success(request, 'Rendimento excluído com sucesso!')
    return redirect('detalhe_rendimentos', employee_id=employee_id)