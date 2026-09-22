# LegalAI ⚖️

LegalAI is an advanced AI-powered legal research assistant and document intelligence engine designed specifically for the Indian legal system (IPC, BNS, BNSS, BSA, and Case Law). 

Built with Django and powered by high-speed LLM inference via the Groq API, LegalAI helps legal professionals and individuals extract facts, analyze risks, and research legal provisions using RAG (Retrieval-Augmented Generation).

## 🌟 Key Features

*   **💬 Contextual Legal Chatbot**: Ask complex legal questions and get answers grounded in real Indian penal codes and statutes. Features inline citations, interactive chips, and contextual conversation memory.
*   **📄 Document Intelligence Engine**: Drag and drop legal documents (FIRs, Agreements, Legal Notices) to instantly extract key facts, involved parties, critical dates, and hidden liabilities.
*   **🛡️ Strict Legal Validation**: The analyzer engine automatically screens uploads and rejects non-legal documents (e.g., recipes, random texts) to prevent hallucinations.
*   **📚 Cases & Directory**: A fully searchable directory of important Indian legal provisions, statutes, and case laws.
*   **🖥️ Professional Workspace**: A dedicated dashboard to manage your past consultations, recent document analyses, and bookmarked provisions.
*   **📝 Rich Markdown Support**: AI responses render beautifully formatted tables, code blocks, and structured lists natively in the UI.

## 🛠️ Tech Stack

*   **Backend**: Python, Django
*   **Frontend**: HTML5, Vanilla JavaScript, Custom CSS (Modern UI)
*   **AI/LLM**: Groq API 
*   **Architecture**: RAG (Retrieval-Augmented Generation) for precise, hallucination-free legal citations

## 🚀 Installation & Setup

### Prerequisites
*   Python 3.8+
*   A [Groq API Key](https://console.groq.com/) for AI inference

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/illegalai.git
cd illegalai
```

### 2. Set up a Virtual Environment
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install django groq python-dotenv
# If a requirements.txt exists: pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the project root directory and add your Groq API key:
```env
GROQ_API_KEY=your_groq_api_key_here
```

### 5. Run Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Start the Development Server
```bash
python manage.py runserver
```

### 7. Access the Application
Open your browser and navigate to `http://127.0.0.1:8000`.

## 🔒 Disclaimer
LegalAI provides legal information and AI-assisted research. It is **not** a replacement for professional legal advice. Always consult a qualified legal professional for your specific situation.
