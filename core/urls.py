from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    # Autenticação
    path('accounts/', include('django.contrib.auth.urls')),
    path('signup/', views.signup, name='signup'),

    # Admin
  #  path('admin/', admin.site.urls),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Páginas principais
    path('', views.index, name='index'),
    path('Credores/', views.listar_Credores, name='listar_Credores'),
    path('upload/', views.upload_planilha, name='upload_planilha'),
    path('upload_emails/', views.upload_emails, name='upload_emails'),
    path('download-modelo-planilha/', views.download_modelo_planilha, name='download_modelo_planilha'),


    # Credores: Relatórios e ações
    path('relatorio/<int:Credor_id>/', views.gerar_pdf_view, name='gerar_pdf'),
    path('enviar-emails/', views.enviar_emails_view, name='enviar_emails'),
    path('Credors/editar/<int:Credor_id>/', views.editar_Credor, name='editar_Credor'),
    path('Credors/enviar/<int:Credor_id>/', views.enviar_email_individual, name='enviar_email_individual'),
    path('Credors/excluir/<int:Credor_id>/', views.excluir_Credor, name='excluir_Credor'),

    # Seleção em lote
    path('enviar-emails-selecionados/', views.enviar_emails_selecionados, name='enviar_emails_selecionados'),
    path('exportar-Credors/', views.exportar_Credors, name='exportar_Credors'),
    path('exportar-Credors-excel/', views.exportar_Credors_excel, name='exportar_Credors_excel'),
    path('excluir-Credors-selecionados/', views.excluir_Credors_selecionados, name='excluir_Credors_selecionados'),
    path('exportar-pdfs-selecionados/', views.exportar_pdfs_selecionados, name='exportar_pdfs_selecionados'),
    path('alterar-status-selecionados/', views.alterar_status_selecionados, name='alterar_status_selecionados'),

    # CRUD de Rendimento
    path('Credor/<int:Credor_id>/rendimentos/', views.detalhe_rendimentos, name='detalhe_rendimentos'),
    path('Credor/<int:Credor_id>/rendimentos/adicionar/', views.adicionar_rendimento, name='adicionar_rendimento'),
    path('rendimentos/<int:rendimento_id>/editar/', views.editar_rendimento, name='editar_rendimento'),
    path('rendimentos/<int:rendimento_id>/excluir/', views.excluir_rendimento, name='excluir_rendimento'),
]
