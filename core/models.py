from django.db import models

class Credor(models.Model):
    nome = models.CharField(max_length=255, unique=True)
    email = models.EmailField(blank=True, null=True)  # não obrigatório
    periodo = models.CharField(max_length=20, default='05/2025')
    enviado = models.BooleanField(default=False)
    data_envio = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.nome

    def atualizar_periodo(self):
        ultimo_rendimento = self.rendimento_set.order_by('-periodo').first()
        if ultimo_rendimento:
            self.periodo = ultimo_rendimento.periodo
            self.save()

class Rendimento(models.Model):
    Credor = models.ForeignKey(Credor, related_name='rendimentos', on_delete=models.CASCADE)
    periodo = models.CharField(max_length=7)
    valor = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f'{self.Credor.nome} - {self.periodo} - R${self.valor}'
