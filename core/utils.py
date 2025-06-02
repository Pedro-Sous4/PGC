from django.template.loader import render_to_string
from weasyprint import HTML
import tempfile, os
from django.core.mail import EmailMessage
from .models import Employee

def gerar_pdf_relatorio(employee):
    html_string = render_to_string('core/relatorio_pdf.html', {'employee': employee})
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as output:
        HTML(string=html_string).write_pdf(output.name)
        return output.name

def enviar_email_com_pdf(employee):
    pdf_path = gerar_pdf_relatorio(employee)

    assunto = 'Seu Relatório de Rendimentos'
    mensagem = f"Olá {employee.nome},\n\nSegue em anexo seu relatório de rendimentos.\n\nAtenciosamente,\nEquipe Financeiro"

    email = EmailMessage(
        assunto,
        mensagem,
        to=[employee.email],
    )

    email.attach_file(pdf_path)
    email.send()

    # Marcar como enviado
    employee.enviado = True
    employee.save()

    # Remover arquivo temporário
    os.remove(pdf_path)
