from django.db import models
from core.normalizacao import normalizar_nome


SMALL_WORDS = {
    'da', 'de', 'do', 'das', 'dos', 'e', 'von', 'van', 'del', 'la', 'le', 'di', 'du'
}


def titlecase_name(name: str) -> str:
    if not name:
        return ''
    # collapse whitespace
    cleaned = ' '.join(name.split())
    parts = cleaned.lower().split(' ')
    out = []
    for i, w in enumerate(parts):
        # handle hyphenated parts (e.g., anne-marie)
        subparts = w.split('-')
        new_sub = []
        for sub in subparts:
            if i > 0 and sub in SMALL_WORDS:
                new_sub.append(sub)
            else:
                new_sub.append(sub.capitalize())
        out.append('-'.join(new_sub))
    return ' '.join(out)


class Credor(models.Model):
    nome = models.CharField(max_length=255, unique=True)

    nome_normalizado = models.CharField(
        max_length=255,
        db_index=True,
        editable=False,
        default=""
    )

    email = models.EmailField(blank=True, null=True)
    periodo = models.CharField(max_length=20, blank=True, null=True)
    enviado = models.BooleanField(default=False)
    data_envio = models.DateTimeField(null=True, blank=True)
    grupo = models.ForeignKey(
        "Grupo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="credores"
    )

    def save(self, *args, **kwargs):
        # Normaliza o nome para exibição: Title Case com exceções para preposições
        if self.nome:
            cleaned = str(self.nome).strip()
            if cleaned:
                cleaned = titlecase_name(cleaned)
                self.nome = cleaned

        # Campo de busca/index permanece em formato normalizado (sem acentos, maiúsculas)
        self.nome_normalizado = normalizar_nome(self.nome)
        super().save(*args, **kwargs)

    # Campos que não podem ser alterados por importações de PGC
    PROTECTED_FIELDS = {'nome', 'email'}

    @classmethod
    def get_or_create_by_nome(cls, nome_display, defaults=None, allow_protected_update=False):
        """Retorna (credor, created) procurando primeiro por nome_normalizado.

        Comportamento resiliente a condições de corrida (IntegrityError) quando
        múltiplos processos tentam criar o mesmo credor com formatações
        diferentes do `nome`.

        Parâmetros:
        - defaults: dict com campos a aplicar no create/possible update
        - allow_protected_update: quando True, permite aplicar também campos em
          `PROTECTED_FIELDS` durante updates (usado por fluxos administrativos
          como upload de emails). Padrão: False (bloqueia alterações em nome/email).
        """
        import logging
        from django.db import IntegrityError, transaction
        from core.normalizacao import normalizar_nome as normalizar_nome_db

        logger = logging.getLogger(__name__)

        defaults = dict(defaults or {})
        nome_norm = normalizar_nome_db(nome_display)

        # Busca direta pelo campo indexado
        credor = cls.objects.filter(nome_normalizado=nome_norm).first()
        if credor:
            # Se permitido, aplica também campos protegidos (ex: upload admin)
            if allow_protected_update:
                updates = dict(defaults or {})
                if updates:
                    for k, v in updates.items():
                        setattr(credor, k, v)
                    credor.save(update_fields=list(updates.keys()))
                return credor, False

            # Caso contrário, bloqueia mudanças em campos protegidos
            protected_attempts = {k: v for k, v in (defaults or {}).items() if k in cls.PROTECTED_FIELDS}
            if protected_attempts:
                logger.warning(
                    "Bloqueado update de campos protegidos para Credor(id=%s): %s",
                    credor.id, list(protected_attempts.keys())
                )
            allowed_updates = {k: v for k, v in (defaults or {}).items() if k not in cls.PROTECTED_FIELDS}
            if allowed_updates:
                for k, v in allowed_updates.items():
                    setattr(credor, k, v)
                credor.save(update_fields=list(allowed_updates.keys()))
            return credor, False

        # Tenta criar com transação; em caso de IntegrityError, tenta recuperar
        try:
            with transaction.atomic():
                params = {'nome': nome_display}
                if defaults:
                    params.update(defaults)
                credor = cls.objects.create(**params)
            return credor, True
        except IntegrityError:
            # fallback: outra thread/processo criou o registro
            credor = cls.objects.filter(nome_normalizado=nome_norm).first() or cls.objects.filter(nome__iexact=nome_display).first()
            if credor:
                # Se permitido, aplicar também campos protegidos no fallback
                if allow_protected_update:
                    updates = dict(defaults or {})
                    if updates:
                        for k, v in updates.items():
                            setattr(credor, k, v)
                        credor.save(update_fields=list(updates.keys()))
                    return credor, False

                # Mesmo comportamento: não sobrescrever campos protegidos em updates
                protected_attempts = {k: v for k, v in (defaults or {}).items() if k in cls.PROTECTED_FIELDS} if defaults else {}
                if protected_attempts:
                    logger.warning(
                        "Bloqueado update de campos protegidos (fallback) para Credor(id=%s): %s",
                        credor.id, list(protected_attempts.keys())
                    )
                allowed_updates = {k: v for k, v in (defaults or {}).items() if k not in cls.PROTECTED_FIELDS}
                if allowed_updates:
                    for k, v in allowed_updates.items():
                        setattr(credor, k, v)
                    credor.save(update_fields=list(allowed_updates.keys()))
                return credor, False
            # se não conseguiu recuperar, relança a exceção
            raise

    def __str__(self):
        return self.nome

    def nome_pasta(self):
        # Retorna o nome do credor padronizado para uso em pastas (title-case)
        return titlecase_name(str(self.nome).strip()) if self.nome else ""

    def update_from_pgc(self, data: dict):
        """Atualiza campos do Credor a partir de dados de um PGC.

        - Campos em `PROTECTED_FIELDS` são bloqueados quando a instância já
          existe; tentativas de alteração são registradas em warning.
        - Outros campos são aplicados e salvo apenas se houver mudanças.

        Retorna um dict com as chaves 'updated' e 'blocked' listando os nomes
        dos campos atualizados e os que foram bloqueados.
        """
        import logging
        logger = logging.getLogger(__name__)

        data = dict(data or {})
        # Detecta tentativas de alteração em campos protegidos
        blocked = [k for k in data.keys() if k in self.PROTECTED_FIELDS and getattr(self, k) != data.get(k)]
        if blocked:
            logger.warning(
                "Bloqueado update de campos protegidos via PGC para Credor(id=%s): %s",
                self.id, blocked
            )

        # Aplica apenas campos permitidos
        allowed = {k: v for k, v in data.items() if k not in self.PROTECTED_FIELDS}
        to_update = []
        for k, v in allowed.items():
            if hasattr(self, k) and getattr(self, k) != v:
                setattr(self, k, v)
                to_update.append(k)

        if to_update:
            self.save(update_fields=to_update)

        return {'updated': to_update, 'blocked': blocked}

    def atualizar_periodo(self):
        # usar related_name definido em Rendimento: 'rendimentos'
        ultimo_rendimento = self.rendimentos.order_by('-periodo').first()
        if ultimo_rendimento:
            self.periodo = ultimo_rendimento.periodo
            self.save()

class Rendimento(models.Model):
    Credor = models.ForeignKey(Credor, related_name='rendimentos', on_delete=models.CASCADE)
    periodo = models.CharField(max_length=20, blank=True, null=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f'{self.Credor.nome} - {self.periodo} - R${self.valor}'

class HistoricoPGC(models.Model):
    credor = models.ForeignKey(Credor, on_delete=models.CASCADE, related_name='historicos')
    numero_pgc = models.PositiveIntegerField()
    periodo = models.CharField(max_length=20, blank=True, null=True)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    data_envio = models.DateTimeField(auto_now_add=True)
    grupo = models.ForeignKey(
        'Grupo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historicos'
    )

    def __str__(self):
        return f"{self.credor.nome} - PGC {self.numero_pgc} ({self.periodo})"

# Registro de envios por credor/histórico
class EmailLog(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('sending', 'Enviando'),
        ('sent', 'Enviado'),
        ('failed', 'Falha'),
    ]

    historico = models.ForeignKey(HistoricoPGC, on_delete=models.CASCADE, related_name='email_logs')
    credor = models.ForeignKey(Credor, on_delete=models.CASCADE, related_name='email_logs')
    numero_pgc = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, null=True)
    attempts = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (('historico', 'credor'),)

    def __str__(self):
        return f"EmailLog(credor={self.credor.nome}, pgc={self.numero_pgc}, status={self.status})"

class Grupo(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome
    
class EmpresaPagadora(models.Model):
    nome_curto = models.CharField(max_length=255)  # nome que aparece na aba 'PGC XX'
    nome_completo = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.nome_completo} ({self.cnpj})"


# Sinais: quando um HistoricoPGC é criado, marca o credor como não enviado
# e cria/atualiza um EmailLog com status pendente.
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

@receiver(post_save, sender=HistoricoPGC)
def historico_created(sender, instance, created, **kwargs):
    if created:
        try:
            credor = instance.credor
            credor.enviado = False
            credor.data_envio = None
            credor.save(update_fields=['enviado', 'data_envio'])
            # cria um EmailLog pendente para esse historico e credor
            EmailLog.objects.update_or_create(
                historico=instance,
                credor=credor,
                defaults={
                    'numero_pgc': instance.numero_pgc or 0,
                    'status': 'pending',
                    'error_message': None,
                    'attempts': 0,
                    'last_attempt_at': None,
                    'sent_at': None,
                }
            )
        except Exception:
            # não propaga erros do sinal
            pass

