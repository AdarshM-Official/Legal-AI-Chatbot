import json
import os
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import LegalDocument
from django.db.models import Q
from groq import Groq
from dotenv import load_dotenv

load_dotenv(os.path.join(settings.BASE_DIR, '.env'))

@csrf_exempt
def api_chat(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '').strip()
            
            if not user_message:
                return JsonResponse({'error': 'Message is required'}, status=400)
                
            api_key = os.environ.get("GROQ_API_KEY")
            if not api_key:
                return JsonResponse({'error': 'API key not configured'}, status=500)
                
            client = Groq(api_key=api_key)
            
            system_prompt = "You are a legal information assistant. Your purpose is strictly limited to answering questions related to law and legal matters. Only respond to questions that are genuinely related to legal topics. If a question is unrelated to law, politely refuse to answer and explain that you can only assist with legal and law-related questions. Do not attempt to answer unrelated questions even if they are simple or general. Provide clear, factual, and neutral legal information. Do not claim to be a lawyer, and advise users to consult a qualified legal professional when appropriate. Do not fabricate laws, cases, sections, regulations, or legal precedents. If the jurisdiction is unclear, ask the user to specify the country or jurisdiction."
            
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                model="llama3-70b-8192",
                temperature=0.2,
                max_tokens=1024,
            )
            
            ai_response = chat_completion.choices[0].message.content
            
            return JsonResponse({'response': ai_response})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Invalid request method'}, status=405)

from .models import LegalDocument
from django.db.models import Q

def index(request):
    return render(request, 'core/index.html')

def chat(request):
    return render(request, 'core/chat.html')

def directory(request):
    query = request.GET.get('q', '').strip()
    selected_types = request.GET.getlist('type')
    
    if not selected_types:
        selected_types = ['IPC', 'BNS', 'BNSS', 'BSA', 'Case Law']
        
    db_types = []
    for t in selected_types:
        if t == 'IPC':
            db_types.append('Statute')
        else:
            db_types.append(t)
            
    if query:
        # Standard Database Keyword Search
        legal_documents = LegalDocument.objects.filter(
            Q(title__icontains=query) | Q(summary__icontains=query) | Q(content__icontains=query),
            doc_type__in=db_types
        ).order_by('id')[:50]
    else:
        important_sections = ['Section 120B', 'Section 124A', 'Section 300', 'Section 302', 'Section 354', 'Section 375', 'Section 376', 'Section 378', 'Section 420', 'Section 498A', 'Section 103 (BNS)', 'Section 316 (BNS)', 'Section 318 (BNS)']
        legal_documents = LegalDocument.objects.filter(title__in=important_sections, doc_type__in=db_types).order_by('id')
        
    return render(request, 'core/directory.html', {'legal_documents': legal_documents, 'query': query, 'selected_types': selected_types})
