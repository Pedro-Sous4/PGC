from django.contrib import admin
from .models import Credor, Grupo, EmpresaPagadora

@admin.register(Credor)
class CredorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'email', 'grupo', 'periodo', 'enviado', 'data_envio')
    search_fields = ('nome', 'email')
    list_filter = ( 'grupo','enviado', 'periodo')

@admin.register(Grupo)
class GrupoAdmin(admin.ModelAdmin):
    list_display = ['nome']

@admin.register(EmpresaPagadora)
class EmpresaPagadoraAdmin(admin.ModelAdmin):
    list_display = ('nome_completo', 'nome_curto', 'cnpj')
    search_fields = ('nome_completo', 'nome_curto', 'cnpj')
