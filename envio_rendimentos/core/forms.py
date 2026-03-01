from django import forms
from .models import Credor, Rendimento

class CredorForm(forms.ModelForm):
    class Meta:
        model = Credor
        fields = '__all__'

class RendimentoForm(forms.ModelForm):
    # Accept valor as text so we can parse formatted currency (e.g. "R$ 1.234,56")
    valor = forms.CharField(label='Valor', widget=forms.TextInput())
    numero_pgc = forms.IntegerField(label='Número do PGC', required=False, min_value=0)

    class Meta:
        model = Rendimento
        # Excluir o FK Credor do formulário; será atribuído na view
        fields = ['periodo', 'valor']

    def clean_valor(self):
        from decimal import Decimal, InvalidOperation
        v = self.cleaned_data.get('valor', '')
        if v is None:
            raise forms.ValidationError('Valor é obrigatório.')
        v = str(v).strip()
        # remover símbolo de moeda e espaços
        v = v.replace('R$', '').replace('r$', '').replace(' ', '')
        # Se usar vírgula como separador decimal (ex: 1.234,56), converte para ponto
        if ',' in v:
            # remover separadores de milhares (pontos)
            v = v.replace('.', '')
            v = v.replace(',', '.')
        else:
            # caso não tenha vírgula, apenas remover quaisquer separadores inválidos
            v = v.replace(',', '')
        try:
            return Decimal(v)
        except InvalidOperation:
            raise forms.ValidationError('Valor inválido.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # placeholder para período
        if 'periodo' in self.fields:
            self.fields['periodo'].widget.attrs.update({'placeholder': 'MM/YYYY'})

        # Quando estiver editando, mostra o valor formatado em BR
        if getattr(self, 'instance', None) and getattr(self.instance, 'valor', None) is not None:
            try:
                v = float(self.instance.valor)
                formatted = f"R$ {v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                self.fields['valor'].initial = formatted
            except Exception:
                # fallback: deixar o valor decimal bruto
                self.fields['valor'].initial = str(self.instance.valor)
        
class UploadFileForm(forms.Form):
    file = forms.FileField(label='Selecione a planilha (.csv ou .xlsx)')

class UploadPGCForm(forms.Form):
    file = forms.FileField()
    numero_pgc = forms.IntegerField(label="Número do PGC", min_value=1)