from django.contrib import admin
from .models import LegalDocument, ChatSession, ChatMessage, MessageCitation

@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'doc_type')
    search_fields = ('title', 'summary')
    list_filter = ('doc_type',)

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'created_at')

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'role', 'created_at')

admin.site.register(MessageCitation)
