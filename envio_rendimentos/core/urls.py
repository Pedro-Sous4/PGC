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
    path('credor/adicionar/', views.adicionar_credor, name='adicionar_credor'),



    # Relatórios e Ações
    path('relatorio/<int:credor_id>/', views.gerar_pdf_view, name='gerar_pdf'),
    path('enviar-emails/', views.enviar_emails_view, name='enviar_emails_view'),
    path('editar-mensagem-email/', views.editar_mensagem_email, name='editar_mensagem_email'),
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
    path('rendimentos/<int:rendimento_id>/pdf/',views.gerar_pdf_individual,name='gerar_pdf_individual'),
    
    # CRUD Histórico PGC
    path('historico-pgc/<int:historico_id>/editar/', views.editar_historico_pgc, name='editar_historico_pgc'),
    path('historico-pgc/<int:historico_id>/excluir/', views.excluir_historico_pgc, name='excluir_historico_pgc'),


    # Admin
    path('admin/', admin.site.urls),
    path('laghetto-sports/', views.laghetto_sports_view, name='laghetto_sports'),
    path('laghetto-sports/status/<str:request_id>/', views.laghetto_pgc_status, name='laghetto_pgc_status'),
    path('laghetto-sports/download/<str:request_id>/', views.laghetto_pgc_download, name='laghetto_pgc_download'),
    #path("pgc/progress/<uuid:request_id>/",views.pgc_progress,name="pgc_progress"),

    # LGM
    path("lgm/", views.lgm_view, name="lgm"),
    path("lgm/status/<str:request_id>/", views.lgm_status, name="lgm_status"),
    path("lgm/errors/<str:request_id>/", views.lgm_errors, name="lgm_errors"),
    path('lgm/credores/<str:request_id>/', views.lgm_credores, name='lgm_credores'),
    path('lgm/reprocess/', views.lgm_reprocess, name='lgm_reprocess'),
    path('lgm/reprocess/status/<str:job_id>/', views.lgm_reprocess_status, name='lgm_reprocess_status'),
    # Chrome DevTools discovery manifest (return 204 to avoid 404 spam)
    path('.well-known/appspecific/com.chrome.devtools.json', views.chrome_devtools_manifest),
    path('lgm/errors/<str:request_id>/resolve/', views.lgm_resolve_errors, name='lgm_resolve_errors'),
   # path('lgm/download/<str:request_id>/', views.lgm_pgc_download, name='lgm_pgc_download'),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)