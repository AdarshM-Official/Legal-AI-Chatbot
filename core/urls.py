from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path('chat/', views.chat, name='chat'),
    path('chat/<int:chat_id>/', views.chat, name='chat_with_id'),
    path('api/chat/', views.api_chat, name='api_chat'),
    path('directory/', views.directory, name='directory'),
]
