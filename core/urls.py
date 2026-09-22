from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path('chat/', views.chat, name='chat'),
    path('chat/<int:chat_id>/', views.chat, name='chat_with_id'),
    path('api/chat/', views.api_chat, name='api_chat'),
    path('directory/', views.directory, name='directory'),
    path('api/directory/<int:doc_id>/preview/', views.api_document_preview, name='api_document_preview'),
    path('api/directory/<int:doc_id>/explain/', views.api_document_explain, name='api_document_explain'),
    path('api/directory/<int:doc_id>/save/', views.api_document_save, name='api_document_save'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Document Analyzer
    path('analyze-document/', views.analyze_document, name='analyze_document'),
    path('analyze-document/<int:analysis_id>/', views.analyze_document_detail, name='analyze_document_detail'),
    path('api/analyze-document/', views.api_analyze_document, name='api_analyze_document'),
]
