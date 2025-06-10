from django.db import models

class Credor(models.Model):
    nome = models.CharField(max_length=255, unique=True)
    email = models.EmailField(blank=True, null=True)  # não obrigatório
    periodo = models.CharField(max_length=20, blank=True, null=True)
    enviado = models.BooleanField(default=False)
    data_envio = models.DateTimeField(null=True, blank=True)
    grupo = models.ForeignKey('Grupo', on_delete=models.SET_NULL, null=True, blank=True, related_name='credores')  # NOVO

    def __str__(self):
        return self.nome

    def nome_pasta(self):
        return f"{self.nome.upper()}"

    def atualizar_periodo(self):
        ultimo_rendimento = self.rendimento_set.order_by('-periodo').first()
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

    def __str__(self):
        return f"{self.credor.nome} - PGC {self.numero_pgc} ({self.periodo})"
    
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
