from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    # Autenticação
    path('accounts/', include('django.contrib.auth.urls')),
    path('signup/', views.signup, name='signup'),

    # Admin
    path('admin/', admin.site.urls),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Páginas principais
    path('', views.index, name='index'),
    path('funcionarios/', views.listar_funcionarios, name='listar_funcionarios'),
    path('upload/', views.upload_planilha, name='upload_planilha'),
    path('download-modelo-planilha/', views.download_modelo_planilha, name='download_modelo_planilha'),


    # Funcionários: Relatórios e ações
    path('relatorio/<int:employee_id>/', views.gerar_pdf_view, name='gerar_pdf'),
    path('enviar-emails/', views.enviar_emails_view, name='enviar_emails'),
    path('funcionarios/editar/<int:employee_id>/', views.editar_funcionario, name='editar_funcionario'),
    path('funcionarios/enviar/<int:employee_id>/', views.enviar_email_individual, name='enviar_email_individual'),
    path('funcionarios/excluir/<int:employee_id>/', views.excluir_funcionario, name='excluir_funcionario'),

    # Seleção em lote
    path('enviar-emails-selecionados/', views.enviar_emails_selecionados, name='enviar_emails_selecionados'),
    path('exportar-funcionarios/', views.exportar_funcionarios, name='exportar_funcionarios'),
    path('exportar-funcionarios-excel/', views.exportar_funcionarios_excel, name='exportar_funcionarios_excel'),
    path('excluir-funcionarios-selecionados/', views.excluir_funcionarios_selecionados, name='excluir_funcionarios_selecionados'),
    path('exportar-pdfs-selecionados/', views.exportar_pdfs_selecionados, name='exportar_pdfs_selecionados'),
    path('alterar-status-selecionados/', views.alterar_status_selecionados, name='alterar_status_selecionados'),

    # CRUD de Rendimento
    path('funcionario/<int:employee_id>/rendimentos/', views.detalhe_rendimentos, name='detalhe_rendimentos'),
    path('funcionario/<int:employee_id>/rendimentos/adicionar/', views.adicionar_rendimento, name='adicionar_rendimento'),
    path('rendimentos/<int:rendimento_id>/editar/', views.editar_rendimento, name='editar_rendimento'),
    path('rendimentos/<int:rendimento_id>/excluir/', views.excluir_rendimento, name='excluir_rendimento'),
]
