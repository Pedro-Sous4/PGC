from django.db import transaction
import unicodedata
import re

from core.models import Credor, HistoricoPGC, Rendimento


def normalizar_nome(nome):
    if not nome:
        return ""

    nome = str(nome)

    nome = re.sub(r"\([^)]*\)", "", nome)
    nome = re.sub(r"^\d+\s*-\s*", "", nome)
    nome = re.sub(r"\s+", " ", nome.strip())

    nome = unicodedata.normalize("NFKD", nome.upper())
    nome = "".join(c for c in nome if not unicodedata.combining(c))

    return nome


@transaction.atomic
def corrigir_credores_duplicados():
    print("🔍 Iniciando correção de credores duplicados...")

    mapa = {}
    total_mesclados = 0

    credores = Credor.objects.all().order_by("id")

    for credor in credores:
        chave = normalizar_nome(credor.nome)

        if chave not in mapa:
            mapa[chave] = credor
            continue

        principal = mapa[chave]
        duplicado = credor

        print(
            f"🔁 Mesclando: [{duplicado.id}] {duplicado.nome} "
            f"→ [{principal.id}] {principal.nome}"
        )

        # 🔄 Migra históricos
        HistoricoPGC.objects.filter(credor=duplicado).update(credor=principal)

        # 🔄 Migra rendimentos (CORRIGIDO)
        Rendimento.objects.filter(Credor=duplicado).update(Credor=principal)

        # 🧠 Preserva dados úteis
        if not principal.email and duplicado.email:
            principal.email = duplicado.email

        principal.enviado = principal.enviado or duplicado.enviado
        principal.save()

        duplicado.delete()
        total_mesclados += 1

    print(f"✅ Correção concluída! {total_mesclados} credores mesclados.")
