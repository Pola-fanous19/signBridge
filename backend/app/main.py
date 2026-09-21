from flask import Flask, jsonify
from flask_cors import CORS
from app.api.routes import bp as api_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(api_bp, url_prefix="/api")

@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "name": "SignBridge",
        "version": "4.0.0",
        "endpoints": ["/api/health", "/api/translate", "/api/gemini/status"],
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
