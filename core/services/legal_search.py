import re
from typing import List, Dict, Any
from django.db.models import Q
from core.models import LegalDocument
from core.services.rag import retrieve_legal_documents

# Mappings of verified laws (IPC to BNS)
LAW_MAPPINGS = {
    "IPC 120B": "BNS 111",
    "IPC 124A": "BNS 152",
    "IPC 300": "BNS 101",
    "IPC 302": "BNS 103",
    "IPC 354": "BNS 74",
    "IPC 375": "BNS 63",
    "IPC 376": "BNS 64",
    "IPC 378": "BNS 303",
    "IPC 420": "BNS 318",
    "IPC 498A": "BNS 85",
}
REVERSE_LAW_MAPPINGS = {v: k for k, v in LAW_MAPPINGS.items()}

def get_law_mapping(title: str, doc_type: str) -> dict:
    """Check if the given document has a verified new/old law mapping."""
    key = None
    if doc_type == 'Statute':
        # Assumed IPC
        match = re.search(r'Section\s+([0-9A-Z]+)', title, re.IGNORECASE)
        if match:
            key = f"IPC {match.group(1).upper()}"
    elif doc_type in ['BNS', 'BNSS', 'BSA']:
        match = re.search(r'Section\s+([0-9A-Z]+)', title, re.IGNORECASE)
        if match:
            key = f"{doc_type} {match.group(1).upper()}"
            
    if key and key in LAW_MAPPINGS:
        return {"type": "new", "target": LAW_MAPPINGS[key]}
    elif key and key in REVERSE_LAW_MAPPINGS:
        return {"type": "old", "target": REVERSE_LAW_MAPPINGS[key]}
        
    return None

def normalize_query(query: str) -> str:
    """Normalize common legal query formats."""
    q = query.lower().strip()
    q = re.sub(r'\bsec\.?\s*(\d+[a-z]?)\b', r'section \1', q)
    q = re.sub(r'\bs\.?\s*(\d+[a-z]?)\b', r'section \1', q)
    # Ensure space between act and number e.g. ipc420 -> ipc 420
    q = re.sub(r'\b(ipc|bns|bnss|bsa)(\d+[a-z]?)\b', r'\1 \2', q)
    return q

def detect_section_reference(query: str) -> dict:
    """Detect if query refers to a specific section and act."""
    q = normalize_query(query)
    act_match = re.search(r'\b(ipc|bns|bnss|bsa)\b', q)
    sec_match = re.search(r'\b(?:section\s+)?(\d+[a-z]?)\b', q)
    
    act = act_match.group(1).upper() if act_match else None
    sec = sec_match.group(1).upper() if sec_match else None
    
    if not act and sec:
        # If user searches just "420"
        return {"act": None, "section": sec}
        
    return {"act": act, "section": sec}

def hybrid_search(query: str, filters: dict, sort_by: str = 'relevance', limit: int = 100) -> List[Dict[str, Any]]:
    """
    Perform hybrid search (Exact, Keyword, Semantic).
    filters: dict with 'types' (list of doc_types).
    """
    q_norm = normalize_query(query)
    q_lower = q_norm.lower()
    
    doc_types = filters.get('types', [])
    # mapped types
    db_types = []
    for t in doc_types:
        if t == 'IPC': db_types.append('Statute')
        else: db_types.append(t)
        
    if not db_types:
        db_types = ['Statute', 'BNS', 'BNSS', 'BSA', 'Case Law']
        
    base_qs = LegalDocument.objects.filter(doc_type__in=db_types)
    
    results = {}  # doc.id -> dict
    
    def add_result(doc, score, match_type):
        if doc.id not in results:
            results[doc.id] = {
                'document': doc,
                'score': score,
                'match_type': match_type,
                'mapping': get_law_mapping(doc.title, doc.doc_type)
            }
        else:
            # boost score if found multiple ways
            results[doc.id]['score'] = max(results[doc.id]['score'], score)

    # 1. Exact Section Lookup
    ref = detect_section_reference(query)
    if ref['section']:
        sec_str = f"Section {ref['section']}"
        sec_qs = base_qs.filter(title__icontains=sec_str)
        if ref['act']:
            act_type = 'Statute' if ref['act'] == 'IPC' else ref['act']
            sec_qs = sec_qs.filter(doc_type=act_type)
            
        for doc in sec_qs[:10]:
            # very high score for exact reference
            add_result(doc, 100.0, "Exact Match")

    # 2. Exact Title Match
    title_qs = base_qs.filter(title__icontains=query)
    for doc in title_qs[:20]:
        add_result(doc, 80.0, "Title Match")

    # 3. Keyword Match (title, summary, content)
    kw_qs = base_qs.filter(
        Q(title__icontains=query) | Q(summary__icontains=query) | Q(content__icontains=query)
    )
    for doc in kw_qs[:50]:
        # Give higher score if query is small and matches exact word, else basic score
        add_result(doc, 50.0, "Keyword Match")

    # 4. Semantic Search (ChromaDB)
    # Only perform if query isn't just a pure number (e.g., "420")
    if not (ref['section'] and len(q_norm.split()) <= 2):
        try:
            semantic_hits = retrieve_legal_documents(query, top_k=15)
            for hit in semantic_hits:
                doc = hit['document']
                dist = hit['distance']
                if doc and doc.doc_type in db_types:
                    # distance is typically 0.0 to 1.5. lower is better.
                    # Convert to a score: 40 - (dist * 20), capping at 40
                    sem_score = max(10.0, 40.0 - (dist * 20.0))
                    add_result(doc, sem_score, "Semantic Match")
        except Exception:
            pass
            
    # Convert to list and sort
    final_list = list(results.values())
    
    if sort_by == 'relevance':
        final_list.sort(key=lambda x: x['score'], reverse=True)
    elif sort_by == 'section_asc':
        final_list.sort(key=lambda x: x['document'].title)
    elif sort_by == 'section_desc':
        final_list.sort(key=lambda x: x['document'].title, reverse=True)
    elif sort_by == 'title_az':
        final_list.sort(key=lambda x: x['document'].title)
        
    return final_list[:limit]

