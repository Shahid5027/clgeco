import os
import json
import uuid
import re
from flask import Flask, render_template, request, jsonify

# AI & Content Tools
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from PyPDF2 import PdfReader

# -------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------
# ⚠️ PASTE YOUR API KEY HERE
GENAI_API_KEY = "AIzaSyAgvlA3B41QoqqF2eBbcAfWhVM3P6tlv94" 

try:
    genai.configure(api_key=GENAI_API_KEY)
except Exception as e:
    print(f"Error configuring Gemini: {e}")

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory storage (Resets when you stop the script)
CONTENT_CACHE = {}

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# -------------------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------------------

def extract_video_id(url: str) -> str:
    if not url: return None
    if "youtu.be/" in url: return url.split("youtu.be/")[1].split("?")[0]
    if "v=" in url: return url.split("v=")[1].split("&")[0]
    if "/embed/" in url: return url.split("/embed/")[1].split("?")[0]
    match = re.search(r"([a-zA-Z0-9_-]{11})", url)
    return match.group(1) if match else None

def get_transcript_data(video_id: str):
    try:
        api = YouTubeTranscriptApi()
        return api.fetch(video_id, languages=("en", "en-US", "en-IN", "hi")).to_raw_data()
    except Exception as e:
        raise ValueError(f"No captions found. Error: {str(e)}")

def extract_pdf_text(filepath: str) -> str:
    try:
        reader = PdfReader(filepath)
        text = "\n".join([(page.extract_text() or "").strip() for page in reader.pages])
        return text
    except Exception as e:
        raise ValueError(f"PDF Error: {str(e)}")

def parse_gemini_json(text: str):
    """
    Robust JSON parser that attempts to fix common AI errors.
    """
    try:
        # 1. Basic Cleanup
        text = text.replace("```json", "").replace("```", "").strip()
        
        # 2. Try parsing directly
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {e}")
        print(f"Bad JSON Content: {text[:500]}...") # Print first 500 chars for debugging
        
        # 3. Fallback: Try to find the outermost brackets
        try:
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                json_str = text[start:end+1]
                # Common Fix: Remove newlines inside strings if that's the issue
                # (This is a simplified fix, complex cases might still fail)
                return json.loads(json_str)
        except:
            pass
            
        raise ValueError("The AI generated invalid data. Please try again (sometimes just clicking Generate again works).")

# -------------------------------------------------------------
# AI LOGIC
# -------------------------------------------------------------

def get_gemini_model(json_mode=True):
    # We force JSON mode in the config
    config = {"response_mime_type": "application/json"} if json_mode else {}
    return genai.GenerativeModel(model_name="gemini-2.5-flash", generation_config=config)

def build_prompt(raw_text: str, persona: str, q_count: int, difficulty: str, mode: str) -> str:
    
    # --- MODE 1: X-RAY (SCAFFOLDING) ---
    if mode == 'layered':
        schema = """
        [
          {
            "heading": "Main Heading",
            "subsections": [
              {
                "subheading": "Sub-point",
                "layer_3_concept": "One sentence core logic.",
                "layer_4_detail": "Full detailed explanation."
              }
            ]
          }
        ]
        """
        return (
            f"Persona: {persona}\n"
            f"Task: Break content into a 4-layer learning structure.\n"
            f"Output Requirement: VALID JSON only. Do NOT use markdown formatting. Escape all quotes inside strings.\n"
            f"Content:\n{raw_text[:40000]}\n\n"
            f"Use this Schema:\n{schema}"
        )

    # --- MODE 2: STANDARD MIX (QUIZ + MAP) ---
    schema = """
    {
      "summary": ["Bullet 1", "Bullet 2"],
      "analogy_title": "Title",
      "analogy_content": "Content...",
      "mind_map": "graph TD; A[Node] --> B[Node];", 
      "quiz": [
        { "type": "mcq", "question": "...", "options": ["A","B"], "answer_index": 0, "feedback": "..." },
        { "type": "cloze", "question": "...", "sentence_with_blank": "The ____ is power.", "answer": "knowledge", "feedback": "..." }
      ]
    }
    """
    return (
        f"Persona: {persona}\n"
        f"Task: Create study material.\n"
        f"Output Requirement: VALID JSON only. No markdown. Escape inner quotes.\n"
        f"Quiz: {q_count} questions ({difficulty}). Mix 'mcq' and 'cloze'.\n"
        f"Mind Map: Mermaid JS. Wrap ALL node text in double quotes (e.g. A[\"Text\"]).\n"
        f"Content:\n{raw_text[:40000]}\n\n"
        f"Use this Schema:\n{schema}"
    )

# -------------------------------------------------------------
# ROUTES
# -------------------------------------------------------------

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    try:
        source_type = request.form.get('source_type', '').strip().lower()
        style = request.form.get('style', 'Standard')
        q_count = int(request.form.get('q_count', '5'))
        gen_mode = request.form.get('gen_mode', 'standard') 
        
        raw_text_full = ""
        video_id = None
        transcript_data = None

        # Source Handling
        if source_type == 'youtube':
            url = request.form.get('url', '')
            video_id = extract_video_id(url)
            transcript_data = get_transcript_data(video_id)
            raw_text_full = " ".join([item['text'] for item in transcript_data])
        elif source_type == 'pdf':
            if 'file' not in request.files: raise ValueError("No file part")
            f = request.files['file']
            if f.filename == '': raise ValueError("No selected file")
            save_path = os.path.join(UPLOAD_DIR, f.filename)
            f.save(save_path)
            raw_text_full = extract_pdf_text(save_path)
        elif source_type in ['text', 'gemini']:
            raw_text_full = request.form.get('text_content', '').strip()
            if source_type == 'gemini':
                raw_text_full = f"CONTEXT: Chat Log. Focus on concepts.\nLOG:\n{raw_text_full}"
            
            # Micro-Concept Logic
            if len(raw_text_full) < 500 and gen_mode == 'standard':
                q_count = 1
                style = "Strict Professor"
        
        if not raw_text_full:
            raise ValueError("No text could be extracted.")

        # Cache
        session_id = str(uuid.uuid4())
        CONTENT_CACHE[session_id] = {
            "text": raw_text_full, 
            "meta": {"source": source_type, "style": style}
        }

        # Generate
        model = get_gemini_model(json_mode=True)
        prompt = build_prompt(raw_text_full, style, q_count, "Hard", gen_mode)
        resp = model.generate_content(prompt)
        
        # Check if response was blocked
        if not resp.candidates:
             raise ValueError("The AI refused to generate content (Safety Filter). Try different content.")
             
        data = parse_gemini_json(resp.text)

        return jsonify({
            "status": "success", "data": data, 
            "video_id": video_id, "session_id": session_id, "mode": gen_mode
        })

    except Exception as e:
        print(f"SERVER ERROR: {e}") # This will show in your terminal
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    session_id = data.get('session_id')
    user_msg = data.get('message')
    mode = data.get('mode', 'tutor')

    if not session_id or session_id not in CONTENT_CACHE:
        return jsonify({"reply": "Session expired."})

    context_str = CONTENT_CACHE[session_id]['text'][:30000]

    if mode == 'examiner':
        instructions = "You are a Strict Examiner. Test the user using Active Recall. Ask questions. Do not lecture."
    else:
        instructions = "You are a helpful Tutor. Explain clearly using the context."

    try:
        model = get_gemini_model(json_mode=False)
        chat_prompt = f"{instructions}\n\nContext:\n{context_str}\n\nUser: {user_msg}"
        resp = model.generate_content(chat_prompt)
        return jsonify({"reply": resp.text})
    except Exception:
        return jsonify({"reply": "Error."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)