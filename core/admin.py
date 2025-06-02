from django.contrib import admin
from .models import Employee

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('nome', 'email', 'cpf', 'matricula')
    search_fields = ('nome', 'email', 'cpf', 'matricula')
