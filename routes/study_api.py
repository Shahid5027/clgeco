import json
import os
import re
import uuid

import google.generativeai as genai
from PyPDF2 import PdfReader
from flask import Blueprint, current_app, jsonify, render_template, request
from youtube_transcript_api import YouTubeTranscriptApi

study_bp = Blueprint("study", __name__, template_folder="../templates")

GENAI_API_KEY = os.environ.get("GENAI_API_KEY", "")
if GENAI_API_KEY:
    genai.configure(api_key=GENAI_API_KEY)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

CONTENT_CACHE = {}


def extract_video_id(url: str) -> str | None:
    if not url:
        return None
    if "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    if "/embed/" in url:
        return url.split("/embed/")[1].split("?")[0]
    match = re.search(r"([a-zA-Z0-9_-]{11})", url)
    return match.group(1) if match else None


def get_transcript_data(video_id: str):
    api = YouTubeTranscriptApi()
    return api.fetch(video_id, languages=("en", "en-US", "en-IN", "hi")).to_raw_data()


def extract_pdf_text(filepath: str) -> str:
    reader = PdfReader(filepath)
    return "\n".join([(page.extract_text() or "").strip() for page in reader.pages])


def parse_gemini_json(text: str):
    cleaned = text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            return json.loads(cleaned[start : end + 1])
        raise ValueError("The AI generated invalid JSON. Try generating again.")


def get_gemini_model(json_mode=True):
    config = {"response_mime_type": "application/json"} if json_mode else {}
    return genai.GenerativeModel(model_name="gemini-2.5-flash", generation_config=config)


def build_prompt(raw_text: str, persona: str, q_count: int, difficulty: str, mode: str) -> str:
    if mode == "layered":
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
            "Task: Break content into a 4-layer learning structure.\n"
            "Output Requirement: VALID JSON only. Do NOT use markdown formatting. Escape all quotes inside strings.\n"
            f"Content:\n{raw_text[:40000]}\n\n"
            f"Use this Schema:\n{schema}"
        )

    schema = """
    {
      "summary": ["Bullet 1", "Bullet 2"],
      "analogy_title": "Title",
      "analogy_content": "Content...",
      "mind_map": "graph TD; A[\\"Node\\"] --> B[\\"Node\\"];",
      "quiz": [
        { "type": "mcq", "question": "...", "options": ["A","B"], "answer_index": 0, "feedback": "..." },
        { "type": "cloze", "question": "...", "sentence_with_blank": "The ____ is power.", "answer": "knowledge", "feedback": "..." }
      ]
    }
    """
    return (
        f"Persona: {persona}\n"
        "Task: Create study material.\n"
        "Output Requirement: VALID JSON only. No markdown. Escape inner quotes.\n"
        f"Quiz: {q_count} questions ({difficulty}). Mix 'mcq' and 'cloze'.\n"
        "Mind Map: Mermaid JS. Wrap all node text in double quotes.\n"
        f"Content:\n{raw_text[:40000]}\n\n"
        f"Use this Schema:\n{schema}"
    )


@study_bp.route("/", methods=["GET"])
def index():
    return render_template("study_index.html")


@study_bp.route("/generate", methods=["POST"])
def generate():
    if not GENAI_API_KEY:
        return jsonify({"status": "error", "message": "GENAI_API_KEY is not configured."}), 400

    try:
        source_type = request.form.get("source_type", "").strip().lower()
        style = request.form.get("style", "Standard")
        q_count = int(request.form.get("q_count", "5"))
        gen_mode = request.form.get("gen_mode", "standard")

        raw_text_full = ""
        video_id = None

        if source_type == "youtube":
            url = request.form.get("url", "")
            video_id = extract_video_id(url)
            transcript_data = get_transcript_data(video_id)
            raw_text_full = " ".join([item["text"] for item in transcript_data])
        elif source_type == "pdf":
            if "file" not in request.files:
                raise ValueError("No file part")
            file_obj = request.files["file"]
            if file_obj.filename == "":
                raise ValueError("No selected file")
            save_path = os.path.join(UPLOAD_DIR, file_obj.filename)
            file_obj.save(save_path)
            raw_text_full = extract_pdf_text(save_path)
        elif source_type in ["text", "gemini"]:
            raw_text_full = request.form.get("text_content", "").strip()
            if source_type == "gemini":
                raw_text_full = f"CONTEXT: Chat Log. Focus on concepts.\nLOG:\n{raw_text_full}"
            if len(raw_text_full) < 500 and gen_mode == "standard":
                q_count = 1
                style = "Strict Professor"

        if not raw_text_full:
            raise ValueError("No text could be extracted.")

        session_id = str(uuid.uuid4())
        CONTENT_CACHE[session_id] = {
            "text": raw_text_full,
            "meta": {"source": source_type, "style": style},
        }

        model = get_gemini_model(json_mode=True)
        prompt = build_prompt(raw_text_full, style, q_count, "Hard", gen_mode)
        response = model.generate_content(prompt)
        if not response.candidates:
            raise ValueError("The AI refused to generate content (Safety Filter).")

        data = parse_gemini_json(response.text)
        return jsonify(
            {
                "status": "success",
                "data": data,
                "video_id": video_id,
                "session_id": session_id,
                "mode": gen_mode,
            }
        )
    except Exception as exc:
        current_app.logger.exception("Study generate failed")
        return jsonify({"status": "error", "message": str(exc)}), 400


@study_bp.route("/chat", methods=["POST"])
def chat():
    if not GENAI_API_KEY:
        return jsonify({"reply": "GENAI_API_KEY is not configured."}), 400

    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    user_msg = data.get("message")
    mode = data.get("mode", "tutor")

    if not session_id or session_id not in CONTENT_CACHE:
        return jsonify({"reply": "Session expired."}), 400

    context_str = CONTENT_CACHE[session_id]["text"][:30000]
    instructions = (
        "You are a Strict Examiner. Test the user using Active Recall. Ask questions. Do not lecture."
        if mode == "examiner"
        else "You are a helpful Tutor. Explain clearly using the context."
    )

    try:
        model = get_gemini_model(json_mode=False)
        chat_prompt = f"{instructions}\n\nContext:\n{context_str}\n\nUser: {user_msg}"
        response = model.generate_content(chat_prompt)
        return jsonify({"reply": response.text})
    except Exception:
        current_app.logger.exception("Study chat failed")
        return jsonify({"reply": "Error."}), 500
