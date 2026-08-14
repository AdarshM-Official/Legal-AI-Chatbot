from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path('chat/', views.chat, name='chat'),
    path('api/chat/', views.api_chat, name='api_chat'),
    path('directory/', views.directory, name='directory'),
]
