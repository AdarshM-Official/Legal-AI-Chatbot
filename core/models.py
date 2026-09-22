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

class DocumentAnalysis(models.Model):
    STATUS_CHOICES = (
        ('uploaded', 'Uploaded'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    original_filename = models.CharField(max_length=255)
    uploaded_file = models.FileField(upload_to='legal_documents/')
    document_type = models.CharField(max_length=50, blank=True, null=True)
    extracted_text = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_owned_by(self, request):
        if self.user:
            return request.user == self.user
        if self.session_key:
            return request.session.session_key == self.session_key
        return False

class DocumentAnalysisResult(models.Model):
    analysis = models.OneToOneField(DocumentAnalysis, related_name='result', on_delete=models.CASCADE)
    summary = models.TextField(blank=True, null=True)
    parties = models.JSONField(blank=True, null=True, default=list)
    important_dates = models.JSONField(blank=True, null=True, default=list)
    legal_references = models.JSONField(blank=True, null=True, default=list)
    key_facts = models.JSONField(blank=True, null=True, default=list)
    obligations = models.JSONField(blank=True, null=True, default=list)
    clauses = models.JSONField(blank=True, null=True, default=list)
    deadlines = models.JSONField(blank=True, null=True, default=list)
    risks = models.JSONField(blank=True, null=True, default=list)
    review_points = models.JSONField(blank=True, null=True, default=list)
    rag_provisions = models.JSONField(blank=True, null=True, default=list)
    matched_db_docs = models.JSONField(blank=True, null=True, default=list)
    raw_ai_output = models.TextField(blank=True, null=True)

class SavedLegalDocument(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_documents')
    legal_document = models.ForeignKey(LegalDocument, on_delete=models.CASCADE, related_name='saved_by_users')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'legal_document')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} saved {self.legal_document.title}"
