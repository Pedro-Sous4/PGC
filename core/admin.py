from django.contrib import admin
from .models import Credor, Rendimento

@admin.register(Credor)
class CredorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'email', 'periodo', 'enviado', 'data_envio')

@admin.register(Rendimento)
class RendimentoAdmin(admin.ModelAdmin):
    list_display = ('Credor', 'periodo', 'valor')
