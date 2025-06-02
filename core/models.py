from django.db import models

class Employee(models.Model):
    nome = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    cpf = models.CharField(max_length=14, unique=True)
    matricula = models.CharField(max_length=50, null=True, blank=True)
    periodo = models.CharField(max_length=20, default='05/2025')
    enviado = models.BooleanField(default=False)
    data_envio = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.nome

    def atualizar_periodo(self):
        """
        Atualiza automaticamente o campo 'periodo' do funcionário
        com base no último rendimento cadastrado.
        """
        ultimo_rendimento = self.rendimentos.order_by('-periodo').first()
        if ultimo_rendimento:
            self.periodo = ultimo_rendimento.periodo
            self.save()

class Rendimento(models.Model):
    employee = models.ForeignKey(
        Employee, 
        related_name='rendimentos', 
        on_delete=models.CASCADE
    )
    periodo = models.CharField(max_length=7)  # Exemplo: '05/2025'
    valor = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f'{self.employee.nome} - {self.periodo} - R${self.valor}'
