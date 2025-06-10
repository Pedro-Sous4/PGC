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
from .utils import normalizar_planilha_origem  # certifique-se que esta função está no utils.py
from .utils import normalizar_nome, normalizar_planilha_origem, extrair_minimos_de_planilha
import logging
from .utils import normalizar_nome
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import numbers
logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(message)s')
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

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

        caminho_salvo = salvar_arquivo_temporario(file, numero_pgc)
        logging.debug(f"[UPLOAD] Planilha salva em: {caminho_salvo}")

        caminho_normalizado = normalizar_planilha_origem(caminho_salvo, numero_pgc)
        logging.debug(f"[UPLOAD] Planilha normalizada em: {caminho_normalizado}")

        planilha = {
            nome: normalizar_colunas_simples(df)
            for nome, df in pd.read_excel(caminho_normalizado, sheet_name=None).items()
        }

        base_df = extrato_df = produtividade_df = None
        for nome_aba, df in planilha.items():
            if 'base' in nome_aba.lower():
                base_df = df
            elif 'extrato' in nome_aba.lower():
                extrato_df = df
            elif 'produtividade' in nome_aba.lower():
                produtividade_df = df

        if base_df is None:
            messages.error(request, 'A aba BASE não foi encontrada.')
            return redirect('upload_planilha')

        if 'credor' not in base_df.columns:
            messages.error(request, "Coluna 'credor' ausente na planilha BASE.")
            logging.error(f"[UPLOAD] Colunas da BASE: {list(base_df.columns)}")
            return redirect('upload_planilha')

        periodo = datetime.now().strftime('%m/%Y')

        def colunas_existem(df, colunas):
            return all(col in df.columns for col in colunas)

        def salvar_com_formatacao(df, caminho):
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            for r in dataframe_to_rows(df, index=False, header=True):
                ws.append(r)
            for col in ws.iter_cols(min_row=2):
                header = ws.cell(row=1, column=col[0].col_idx).value
                if header and 'data' in header.lower():
                    for cell in col:
                        cell.number_format = 'DD/MM/YYYY'
                elif header and 'valor' in header.lower():
                    for cell in col:
                        cell.number_format = 'R$ #,##0.00'
            for col in ws.columns:
                max_length = 0
                col_letter = col[0].column_letter
                for cell in col:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                ws.column_dimensions[col_letter].width = max_length + 2
            wb.save(caminho)

        for nome in base_df['credor'].unique():
            df_credor = base_df[base_df['credor'] == nome]
            df_extrato = extrato_df[extrato_df['credor'] == nome] if extrato_df is not None else None
            df_prod = produtividade_df[produtividade_df['credor'] == nome] if produtividade_df is not None else None

            credor = Credor.objects.filter(nome__iexact=nome).first()
            if not credor:
                credor = Credor.objects.create(nome=nome, email='', periodo=periodo)
            else:
                credor.periodo = periodo
                credor.save()

            if 'valor_original' not in df_credor.columns:
                messages.error(request, f"A planilha de {nome} não contém a coluna 'valor_original'.")
                logging.warning(f"[UPLOAD] Colunas para {nome}: {list(df_credor.columns)}")
                continue

            HistoricoPGC.objects.create(
                credor=credor,
                numero_pgc=numero_pgc,
                periodo=periodo,
                valor_total=df_credor['valor_original'].sum()
            )

            pasta_saida = os.path.join(settings.MEDIA_ROOT, 'PGC', str(numero_pgc), credor.nome_pasta())
            os.makedirs(pasta_saida, exist_ok=True)

            df_emissao = df_credor.groupby(['empresa', 'credor'], as_index=False)['valor_original'].sum()
            empresas = EmpresaPagadora.objects.all()
            mapa_cnpj = {e.nome_completo.strip().upper(): e.cnpj for e in empresas}
            df_emissao['cnpj'] = df_emissao['empresa'].str.upper().map(mapa_cnpj)

            arquivos = {
                'PGC EMISSÃO': df_emissao[['empresa', 'credor', 'cnpj', 'valor_original']],
                'EXTRATO': None,
                'PRODUTIVIDADE': (
                    df_prod[['empresa', 'credor', 'documento', 'cliente', 'parcela', 'dt_emissao', 'valor_original', 'dt_vencimento']]
                    if df_prod is not None and colunas_existem(df_prod, ['empresa', 'credor', 'documento', 'cliente', 'parcela', 'dt_emissao', 'valor_original', 'dt_vencimento'])
                    else None
                ),
                f'PGC {numero_pgc}': (
                    df_credor[['empresa', 'credor', 'documento', 'cliente', 'parcela', 'dt_emissao', 'valor_original']]
                    if colunas_existem(df_credor, ['empresa', 'credor', 'documento', 'cliente', 'parcela', 'dt_emissao', 'valor_original'])
                    else None
                ),
            }

            if df_extrato is not None:
                colunas_obrigatorias = ['empresa', 'credor', 'documento', 'cliente', 'parcela', 'dt_emissao', 'valor_original', 'dt_vencimento']
                colunas_presentes = [col for col in colunas_obrigatorias if col in df_extrato.columns]
                if 'obs_baixa' in df_extrato.columns:
                    colunas_presentes.append('obs_baixa')
                if len(colunas_presentes) >= len(colunas_obrigatorias):
                    arquivos['EXTRATO'] = df_extrato[colunas_presentes]
                else:
                    logging.warning(f"[EXTRATO] Colunas insuficientes para gerar extrato de {nome}: {df_extrato.columns.tolist()}")

            nome_arquivo_seguro = re.sub(r'[\/:*?"<>|]', '_', nome)
            for nome_arq, df_arq in arquivos.items():
                if df_arq is not None:
                    nome_completo = f'{nome_arquivo_seguro} - {nome_arq}.xlsx'
                    caminho_arquivo = os.path.join(pasta_saida, nome_completo)
                    salvar_com_formatacao(df_arq, caminho_arquivo)
                    logging.info(f"[UPLOAD] Arquivo salvo: {caminho_arquivo}")

        try:
            wb = load_workbook(caminho_salvo, data_only=True)
            aba_nome = next((s for s in wb.sheetnames if s.strip().upper().startswith("PGC")), None)
            if aba_nome:
                ws = wb[aba_nome]
                header1 = [str(ws.cell(row=6, column=col).value or '').strip() for col in range(1, ws.max_column + 1)]
                header2 = [str(ws.cell(row=7, column=col).value or '').strip() for col in range(1, ws.max_column + 1)]
                colunas = [f'{a} {b}'.strip().lower().replace(' ', '_').replace('.', '') for a, b in zip(header1, header2)]

                dados = [
                    [cell.value for cell in row]
                    for row in ws.iter_rows(min_row=8, max_col=ws.max_column)
                ]
                df_minimo = pd.DataFrame(dados, columns=colunas)
                colunas_desejadas = ['credor', 'minimofixo_garantido_para_emissao_nf', 'empresa_emissao_nf', 'cnpj']
                df_minimo = df_minimo[colunas_desejadas].dropna(subset=['credor'])
                caminho_minimo = os.path.join(settings.MEDIA_ROOT, 'PGC', str(numero_pgc), 'mínimo.xlsx')
                salvar_com_formatacao(df_minimo, caminho_minimo)
                logging.info(f"[MÍNIMO] Planilha de mínimos salva em: {caminho_minimo}")
            else:
                logging.warning(f"[MÍNIMO] Aba PGC {numero_pgc} não encontrada para mínimos.")
        except Exception as e:
            logging.error(f"[MÍNIMO] Erro ao gerar planilha de mínimos: {e}")
            messages.warning(request, f"Erro ao gerar planilha de mínimos: {e}")

        messages.success(request, f'Upload do PGC {numero_pgc} processado com sucesso!')
        return redirect('upload_planilha')

    return render(request, 'core/upload_planilha.html')
'''
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
        periodo_atual = datetime.today().strftime('%m/%Y')

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



@login_required
def upload_planilha(request):
    if request.method == 'POST' and request.FILES.get('file'):
        numero_pgc = request.POST.get('numero_pgc')
        file = request.FILES['file']

        if not numero_pgc:
            messages.error(request, 'Informe o número do PGC.')
            return redirect('upload_planilha')

        if file.name.endswith('.csv'):
            messages.error(request, 'Apenas planilhas .xlsx são suportadas.')
            return redirect('upload_planilha')
        elif file.name.endswith('.xlsx'):
            df_dict = pd.read_excel(file, sheet_name=None)
        else:
            messages.error(request, 'Formato de arquivo inválido.')
            return redirect('upload_planilha')

        def normalize_cols(df):
            return df.rename(columns=lambda col: col.strip().lower().replace(' ', '_').replace('.', ''))

        base_df = None
        for sheet_name, sheet_df in df_dict.items():
            if 'base' in sheet_name.lower():
                base_df = normalize_cols(sheet_df)
                break

        if base_df is None:
            messages.error(request, 'A aba BASE PGC não foi encontrada.')
            return redirect('upload_planilha')

        periodo = datetime.now().strftime('%m/%Y')

        credores = base_df['credor'].unique()
        for nome in credores:
            df_credor = base_df[base_df['credor'] == nome]
            credor_encontrado = None
            for c in Credor.objects.all():
                if normalizar_nome(c.nome) == normalizar_nome(nome):
                    credor_encontrado = c
                    break

            if credor_encontrado:
                credor = credor_encontrado
                credor.periodo = periodo
                credor.save()
            else:
                credor = Credor.objects.create(nome=nome, email='', periodo=periodo)
            credor.periodo = periodo
            credor.save()

            HistoricoPGC.objects.create(
                credor=credor,
                numero_pgc=numero_pgc,
                periodo=periodo,
                valor_total=df_credor['valor_original'].sum()
            )

            pasta_saida = os.path.join(settings.MEDIA_ROOT, 'PGC', str(numero_pgc), credor.nome_pasta())
            os.makedirs(pasta_saida, exist_ok=True)

            try:
                arquivos = {
                    'PGC EMISSÃO': df_credor.groupby(['empresa', 'credor', 'cnpj'], as_index=False)['valor_original'].sum(),
                    'EXTRATO': df_credor[['empresa', 'credor', 'documento', 'cliente', 'parcela', 'dt_emissao', 'valor_original', 'dt_vencimento', 'obs_baixa']],
                    'PRODUTIVIDADE': df_credor[['empresa', 'credor', 'documento', 'cliente', 'parcela', 'dt_emissao', 'valor_original', 'dt_vencimento']],
                    f'PGC {numero_pgc}': df_credor[['empresa', 'credor', 'documento', 'cliente', 'parcela', 'dt_emissao', 'valor_original']],
                }

                nome_arquivo_seguro = nome.replace('/', '_').replace('\\', '_').replace(':', '').replace('*', '').replace('?', '').replace('"', '').replace('<', '').replace('>', '').replace('|', '')

                for nome_arq, df_arq in arquivos.items():
                    nome_completo = f'{nome_arquivo_seguro} - {nome_arq}.xlsx'
                    caminho_arquivo = os.path.join(pasta_saida, nome_completo)
                    df_arq.to_excel(caminho_arquivo, index=False)

            except Exception as e:
                messages.error(request, f'Erro ao gerar arquivos para {nome}: {e}')
                continue

        messages.success(request, f'Upload do PGC {numero_pgc} processado com sucesso!')
        return redirect('upload_planilha')

    return render(request, 'core/upload_planilha.html')


def abrir_pasta_explorer(request, credor_id, numero_pgc):
    credor = get_object_or_404(Credor, pk=credor_id)
    pasta = os.path.join("C:\\PGC\\envio_rendimentos\\arquivos_gerados\\PGC", str(numero_pgc), credor.nome_pasta())
    if os.path.exists(pasta):
        os.startfile(pasta)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


    nome = re.sub(r'^\d+\s*-\s*', '', nome)  # remove prefixo tipo "16273 - "
    nome = re.sub(r'\s*\([^)]*\)', '', nome)  # remove sufixo tipo "(CONSULTOR)"
    return nome.strip().upper()