from django.http import HttpResponse
from django.shortcuts import get_object_or_404

# Stub temporário para evitar quebra do projeto
# A implementação real do PDF será feita futuramente

def gerar_pdf_rendimento(request, rendimento_id=None, *args, **kwargs):
    """
    Função placeholder para geração de PDF de rendimento.
    Evita erros de import enquanto a funcionalidade real
    ainda não foi implementada.
    """

    return HttpResponse(
        "Geração de PDF em desenvolvimento.",
        content_type="text/plain"
    )
