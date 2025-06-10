from django.contrib import admin
from django.urls import path, include
from core import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Autenticação padrão do Django (login, logout, etc)
    path('accounts/', include('django.contrib.auth.urls')),

    # Cadastro de novos usuários
    path('signup/', views.signup, name='signup'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Página inicial
    path('', views.index, name='index'),

    # CRUD Credores
    path('credores/', views.listar_Credores, name='listar_Credores'),
    path('upload/', views.upload_planilha, name='upload_planilha'),
    path('upload-emails/', views.upload_emails, name='upload_emails'),
    path('abrir-pasta/<int:credor_id>/<int:numero_pgc>/', views.abrir_pasta_explorer, name='abrir_pasta'),


    # Relatórios e Ações
    path('relatorio/<int:credor_id>/', views.gerar_pdf_view, name='gerar_pdf'),
    path('enviar-emails/', views.enviar_emails_view, name='enviar_emails_view'),
    path('credores/editar/<int:credor_id>/', views.editar_Credor, name='editar_Credor'),
    path('credores/enviar/<int:credor_id>/', views.enviar_email_individual, name='enviar_email_individual'),
    path('credores/excluir/<int:credor_id>/', views.excluir_Credor, name='excluir_Credor'),

    # Seleção em lote
    path('enviar-emails-selecionados/', views.enviar_emails_selecionados, name='enviar_emails_selecionados'),
    path('exportar-credores/', views.exportar_Credores, name='exportar_Credores'),
    path('exportar-credores-excel/', views.exportar_Credores_excel, name='exportar_Credores_excel'),
    path('excluir-credores-selecionados/', views.excluir_Credores_selecionados, name='excluir_Credores_selecionados'),
    path('exportar-pdfs-selecionados/', views.exportar_pdfs_selecionados, name='exportar_pdfs_selecionados'),
    path('alterar-status-selecionados/', views.alterar_status_selecionados, name='alterar_status_selecionados'),

    # CRUD Rendimento
    path('credor/<int:credor_id>/rendimentos/', views.detalhe_rendimentos, name='detalhe_rendimentos'),
    path('credor/<int:credor_id>/rendimentos/adicionar/', views.adicionar_rendimento, name='adicionar_rendimento'),
    path('rendimentos/<int:rendimento_id>/editar/', views.editar_rendimento, name='editar_rendimento'),
    path('rendimentos/<int:rendimento_id>/excluir/', views.excluir_rendimento, name='excluir_rendimento'),

    # Admin
    path('admin/', admin.site.urls),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)