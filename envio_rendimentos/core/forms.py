from django import forms
from .models import Credor, Rendimento

class CredorForm(forms.ModelForm):
    class Meta:
        model = Credor
        fields = '__all__'

class RendimentoForm(forms.ModelForm):
    class Meta:
        model = Rendimento
        fields = '__all__'
        
class UploadFileForm(forms.Form):
    file = forms.FileField(label='Selecione a planilha (.csv ou .xlsx)')

class UploadPGCForm(forms.Form):
    file = forms.FileField()
    numero_pgc = forms.IntegerField(label="Número do PGC", min_value=1)