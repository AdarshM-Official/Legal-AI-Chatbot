from django.db import models
from django.contrib.auth.models import User

class LegalDocument(models.Model):
    DOC_TYPES = (
        ('Statute', 'Statute'),
        ('Case Law', 'Case Law'),
        ('Rule', 'Rule'),
        ('Other', 'Other'),
    )
    title = models.CharField(max_length=500)
    doc_type = models.CharField(max_length=50, choices=DOC_TYPES)
    summary = models.TextField()
    content = models.TextField()
    vector_id = models.CharField(max_length=255, blank=True, null=True, help_text="Reference to FAISS/ChromaDB embedding")
    source_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.doc_type}: {self.title}"

class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Session: {self.title} ({self.created_at.date()})"

class ChatMessage(models.Model):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('ai', 'AI'),
    )
    session = models.ForeignKey(ChatSession, related_name='messages', on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message ({self.role}) in {self.session.title}"

class MessageCitation(models.Model):
    message = models.ForeignKey(ChatMessage, related_name='citations', on_delete=models.CASCADE)
    document = models.ForeignKey(LegalDocument, on_delete=models.CASCADE)

    def __str__(self):
        return f"Citation: {self.document.title} in {self.message.id}"
