from django import forms
from .models import Employee

from .models import Rendimento

class RendimentoForm(forms.ModelForm):
    class Meta:
        model = Rendimento
        fields = ['periodo', 'valor']

class UploadFileForm(forms.Form):
    arquivo = forms.FileField(label="Selecione a planilha (.csv ou .xlsx)")

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['nome', 'email', 'cpf', 'matricula', 'enviado', 'periodo']