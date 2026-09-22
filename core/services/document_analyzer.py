import os
import json
import logging
from django.conf import settings
from groq import Groq

from .rag import retrieve_legal_documents

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are LegalAI, an expert Indian legal document analyzer.
Your task is to analyze the provided text. First, you must determine if the document is actually a legal document (such as a contract, FIR, notice, court order, affidavit, terms of service, etc.) or just non-legal text (like a recipe, a greeting, a random story).

If it is NOT a legal document, you must return your response EXCLUSIVELY as a JSON object with EXACTLY these keys:
{
    "is_legal": false,
    "rejection_reason": "Provide a concise reason why this is not a legal document."
}

If it IS a legal document, you must analyze it and return your response EXCLUSIVELY as a JSON object with EXACTLY these keys:
{
    "is_legal": true,
    "summary": "A concise 2-4 sentence summary of the document",
    "parties": [{"role": "Plaintiff/Defendant/Applicant/etc", "name": "Name"}],
    "important_dates": [{"date": "YYYY-MM-DD or text", "description": "What happened"}],
    "legal_references": [{"law": "Act/Code Name", "section": "Section Number"}],
    "key_facts": ["Fact 1", "Fact 2"],
    "obligations": ["Obligation 1", "Obligation 2"],
    "clauses": ["Important clause 1"],
    "deadlines": ["Deadline 1"],
    "risks": ["Risk 1", "Risk 2"],
    "review_points": ["Review point 1"]
}
If a field is not applicable or not found, return an empty list or string as appropriate.
Do not include any markdown formatting around the JSON object.
"""

def _safe_parse_json(response_text: str) -> dict:
    text = response_text.strip()
    if text.startswith("```json"):
        text = text.replace("```json", "", 1)
    if text.startswith("```"):
        text = text.replace("```", "", 1)
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from AI response: {e}\nResponse: {text}")
        return {
            "summary": "Failed to parse AI response into structured data.",
            "raw_error": str(e),
            "raw_text": text
        }

def run_analysis(text: str, doc_type: str = "auto") -> dict:
    """Analyze the text using Groq and then fetch RAG provisions."""
    api_key = getattr(settings, 'GROQ_API_KEY', os.environ.get('GROQ_API_KEY'))
    if not api_key:
        return {"summary": "Error: Groq API Key not found."}
        
    client = Groq(api_key=api_key)
    
    # Optional truncation if document is too large (using basic char limit for 8k context)
    max_chars = 15000
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n...[DOCUMENT TRUNCATED]..."

    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",  # or settings.GROQ_MODEL if defined
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Document Type: {doc_type}\n\nDocument Text:\n{text}"}
            ],
            temperature=0.1,
        )
        
        raw_output = completion.choices[0].message.content
        result = _safe_parse_json(raw_output)
        result['raw_ai_output'] = raw_output
        
        # Now, gather context using RAG
        # We can construct a query from the summary and legal references
        rag_query_parts = []
        if result.get("summary"):
            rag_query_parts.append(result["summary"])
        for ref in result.get("legal_references", []):
            rag_query_parts.append(f"{ref.get('law', '')} {ref.get('section', '')}")
            
        rag_query = " ".join(rag_query_parts)
        
        rag_provisions = []
        matched_db_docs = []
        
        if rag_query.strip():
            hits = retrieve_legal_documents(rag_query, top_k=3)
            for hit in hits:
                doc = hit['document']
                if doc:
                    rag_provisions.append({
                        "title": doc.title,
                        "law_type": doc.doc_type,
                        "summary": doc.summary,
                    })
                    matched_db_docs.append(doc.id)
                    
        result['rag_provisions'] = rag_provisions
        result['matched_db_docs'] = matched_db_docs
        
        return result
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        return {"summary": f"Analysis failed due to internal error: {e}"}

