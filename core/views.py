import json
import os
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import LegalDocument, ChatSession, ChatMessage
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
            chat_id = data.get('chat_id')
            
            if not user_message:
                return JsonResponse({'error': 'Message is required'}, status=400)
                
            if chat_id:
                try:
                    session = ChatSession.objects.get(id=chat_id)
                    if request.user.is_authenticated:
                        if session.user != request.user:
                            return JsonResponse({'error': 'Unauthorized access to chat'}, status=403)
                    else:
                        if session.user is not None or session.id not in request.session.get('chat_ids', []):
                            return JsonResponse({'error': 'Unauthorized access to chat'}, status=403)
                except ChatSession.DoesNotExist:
                    return JsonResponse({'error': 'Chat session not found'}, status=404)
            else:
                title = user_message[:40] + '...' if len(user_message) > 40 else user_message
                user = request.user if request.user.is_authenticated else None
                session = ChatSession.objects.create(user=user, title=title)
                
                if not request.user.is_authenticated:
                    chat_ids = request.session.get('chat_ids', [])
                    chat_ids.append(session.id)
                    request.session['chat_ids'] = chat_ids
            
            ChatMessage.objects.create(session=session, role='user', content=user_message)
                
            api_key = os.environ.get("GROQ_API_KEY")
            if not api_key:
                return JsonResponse({'error': 'API key not configured'}, status=500)
                
            client = Groq(api_key=api_key)
            
            system_prompt = "You are a friendly legal information assistant. Your purpose is strictly limited to answering questions related to law and legal matters. You may respond politely to basic greetings (like 'hi', 'hello', 'good morning'), but you must immediately steer the conversation toward asking how you can help with legal inquiries. For any actual questions or requests that are unrelated to law, you must politely refuse to answer and explain that you can only assist with legal and law-related questions. Do not attempt to answer unrelated questions even if they are simple or general. Provide clear, factual, and neutral legal information. Do not claim to be a lawyer, and advise users to consult a qualified legal professional when appropriate. Do not fabricate laws, cases, sections, regulations, or legal precedents. If the jurisdiction is unclear, ask the user to specify the country or jurisdiction."
            
            past_messages = list(session.messages.all().order_by('created_at'))
            messages_for_api = [{"role": "system", "content": system_prompt}]
            
            for msg in past_messages[-10:]:
                role = 'assistant' if msg.role == 'ai' else 'user'
                messages_for_api.append({"role": role, "content": msg.content})
            
            chat_completion = client.chat.completions.create(
                messages=messages_for_api,
                model="openai/gpt-oss-20b",
                temperature=0.2,
                max_tokens=1024,
            )
            
            ai_response = chat_completion.choices[0].message.content
            ChatMessage.objects.create(session=session, role='ai', content=ai_response)
            
            return JsonResponse({'response': ai_response, 'chat_id': session.id})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Invalid request method'}, status=405)

def index(request):
    return render(request, 'core/index.html')

def chat(request, chat_id=None):
    current_chat = None
    messages = []
    past_chats = []
    
    if request.user.is_authenticated:
        past_chats = ChatSession.objects.filter(user=request.user).order_by('-updated_at')
        
        if chat_id:
            try:
                current_chat = ChatSession.objects.get(id=chat_id, user=request.user)
                messages = current_chat.messages.all().order_by('created_at')
            except ChatSession.DoesNotExist:
                pass
            
    return render(request, 'core/chat.html', {
        'past_chats': past_chats,
        'current_chat': current_chat,
        'messages': messages,
    })

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
