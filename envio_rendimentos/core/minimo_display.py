def format_empresa_para_exibicao(empresa):
    """Retorna a string de exibição da empresa removendo o prefixo numérico "{numero} - " quando presente.

    Importante: este helper **não** altera o valor original armazenado, apenas a string usada para exibição.
    """
    try:
        if not empresa or not isinstance(empresa, str):
            return empresa
        # Remove tudo até e incluindo o primeiro " - " (ex.: "24 - NOME" -> "NOME")
        if ' - ' in empresa:
            return empresa.split(' - ', 1)[1].strip()
        return empresa.strip()
    except Exception:
        return empresa
