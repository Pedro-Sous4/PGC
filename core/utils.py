from django.template.loader import render_to_string
from weasyprint import HTML
import tempfile, os
from django.core.mail import EmailMessage
from .models import Credor

def gerar_pdf_relatorio(Credor):
    html_string = render_to_string('core/relatorio_pdf.html', {'Credor': Credor})
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as output:
        HTML(string=html_string).write_pdf(output.name)
        return output.name

def enviar_email_com_pdf(Credor):
    pdf_path = gerar_pdf_relatorio(Credor)

    assunto = 'Seu Relatório de Rendimentos'
    mensagem = f"Olá {Credor.nome},\n\nSegue em anexo seu relatório de rendimentos.\n\nAtenciosamente,\nEquipe Financeiro"

    email = EmailMessage(
        assunto,
        mensagem,
        to=[Credor.email],
    )

    email.attach_file(pdf_path)
    email.send()

    # Marcar como enviado
    Credor.enviado = True
    Credor.save()

    # Remover arquivo temporário
    os.remove(pdf_path)
