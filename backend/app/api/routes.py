from flask import Blueprint, request, jsonify

from app.gloss.rule_based import to_gloss as rule_gloss
from app.pose.sequencer import sequence

bp = Blueprint('api', __name__)

@bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "version": "4.0.0"})

@bp.route("/gemini/status", methods=["GET"])
def gemini_status():
    # Returning offline since the user requested rule-based only, 
    # but we keep the endpoint so frontend doesn't crash.
    return jsonify({"configured": False, "reachable": False})

@bp.route("/translate", methods=["POST"])
def translate():
    data = request.get_json()
    if not data or not data.get("text") or not data["text"].strip():
        return jsonify({"error": "empty text"}), 400
    
    text = data["text"]
    # We ignore data.get("gloss_backend") because the user explicitly said:
    # "keep it rule based and no whisper"
    g = rule_gloss(text)
        
    clip, stats, enriched = sequence(g["tokens"])
    g_out = {**g, "tokens": enriched}
    return jsonify({"gloss": g_out, "pose": clip, "stats": stats})

@bp.route("/lexicon", methods=["GET"])
def list_lexicon():
    from app.pose.lexicon import LEXICON
    stats = LEXICON.stats()
    resp = jsonify({
        "words": stats["known_tokens"],
        "stats": stats
    })
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp

@bp.route("/lexicon/<word>", methods=["GET"])
def get_lexicon_word(word):
    from app.pose.lexicon import LEXICON
    LEXICON._loaded = False
    entry = LEXICON.get(word.upper())
    if not entry:
        return jsonify({"error": f"Word '{word}' not found in lexicon"}), 404
    resp = jsonify(entry)
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp

import os
import tempfile
import json
from werkzeug.utils import secure_filename
from app.process_video import process_video_file

@bp.route("/process-video", methods=["POST"])
def process_video():
    if 'video' not in request.files:
        return jsonify({"error": "No video file provided"}), 400
    if 'word' not in request.form:
        return jsonify({"error": "No word specified"}), 400
        
    video_file = request.files['video']
    word = request.form['word'].strip().upper()
    
    if video_file.filename == '':
        return jsonify({"error": "Empty filename"}), 400
        
    # Save video temporarily
    temp_fd, temp_path = tempfile.mkstemp(suffix='.webm')
    os.close(temp_fd)
    
    try:
        video_file.save(temp_path)
        
        # Process the video to extract heavy landmarks
        frames_data = process_video_file(temp_path)
        
        # Save as JSON
        # Output format has a flag so the frontend knows it's a raw MediaPipe array stream,
        # rather than the old dictionary format.
        output_data = {
            "isHolisticResult": True,
            "frames": frames_data
        }
        
        lexicon_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'lexicon', 'words')
        os.makedirs(lexicon_dir, exist_ok=True)
        
        out_filename = f"{secure_filename(word)}.json"
        out_path = os.path.join(lexicon_dir, out_filename)
        
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f)
            
        return jsonify({
            "status": "success",
            "message": f"Saved {len(frames_data)} frames to {out_filename}",
            "frames": len(frames_data)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@bp.route("/save-sign", methods=["POST"])
def save_sign():
    data = request.get_json()
    if not data or not data.get("word") or not data.get("frames"):
        return jsonify({"error": "Missing word or frames"}), 400

    word = data["word"].strip().upper()
    frames = data["frames"]

    lexicon_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'lexicon', 'words')
    os.makedirs(lexicon_dir, exist_ok=True)
    out_filename = f"{secure_filename(word)}.json"
    out_path = os.path.join(lexicon_dir, out_filename)

    raw_frames = data.get("rawFrames")

    is_mhr_direct = any(isinstance(frame, dict) and frame.get("isMhrDirect") for frame in frames)
    output_data = {
        "name": word,
        "fps": 30,
        "isMhrDirect": is_mhr_direct,
        "isHolisticResult": not is_mhr_direct,
        "frames": frames
    }
    if raw_frames:
        output_data["rawFrames"] = raw_frames

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f)

    # Invalidate lexicon cache so new word is immediately discoverable
    from app.pose.lexicon import LEXICON
    LEXICON._loaded = False

    return jsonify({
        "status": "success",
        "word": word,
        "message": f"Saved {len(frames)} frames to lexicon as {out_filename}",
        "frames": len(frames)
    })
