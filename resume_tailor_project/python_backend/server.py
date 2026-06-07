from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from openai import OpenAI
from dotenv import load_dotenv
import os, sys, json, subprocess, base64, re, tempfile, shutil, logging, uuid
from logging.handlers import RotatingFileHandler
from datetime import datetime

load_dotenv()

# ── App ──────────────────────────────────────────────────────
app = Flask(__name__)

# ── Logging ──────────────────────────────────────────────────
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

log_formatter = logging.Formatter(
    "[%(asctime)s] %(levelname)s %(name)s - %(message)s"
)

access_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, "access.log"), maxBytes=10_485_760, backupCount=5
)
access_handler.setFormatter(log_formatter)

error_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, "error.log"), maxBytes=10_485_760, backupCount=5
)
error_handler.setFormatter(log_formatter)
error_handler.setLevel(logging.WARNING)

app.logger.addHandler(access_handler)
app.logger.addHandler(error_handler)
app.logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
app.logger.addHandler(console_handler)

# ── Config ───────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    app.logger.error("GROQ_API_KEY not set in .env")
    raise SystemExit("GROQ_API_KEY is required")

AUTH_TOKEN = os.getenv("AUTH_TOKEN")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "chrome-extension://*,http://127.0.0.1:5000")
MAX_JD_LENGTH = int(os.getenv("MAX_JD_LENGTH", "15000"))
MAX_BODY_SIZE = int(os.getenv("MAX_BODY_SIZE", "5_242_880"))
RATE_LIMIT = os.getenv("RATE_LIMIT", "10 per minute")

app.config["MAX_CONTENT_LENGTH"] = MAX_BODY_SIZE

CORS(app, origins=[o.strip() for o in ALLOWED_ORIGINS.split(",")])

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[RATE_LIMIT],
    storage_uri="memory://",
)

client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
TEMPLATE_PATH = os.path.join(BASE_DIR, "templates", "prompt_template.txt")
LATEX_DIR = os.path.join(PROJECT_ROOT, "Latex_from_Json Engine")

# ── Helpers ──────────────────────────────────────────────────

def validate_input(company_name, job_description):
    errors = []
    if not company_name or not company_name.strip():
        errors.append("company_name is required")
    elif len(company_name) > 100:
        errors.append("company_name must be under 100 characters")
    elif not re.match(r'^[\w\s\-\.]+$', company_name):
        errors.append("company_name contains invalid characters")

    if not job_description or not job_description.strip():
        errors.append("job_description is required")
    elif len(job_description) > MAX_JD_LENGTH:
        errors.append(f"job_description must be under {MAX_JD_LENGTH} characters ({len(job_description)} given)")

    return errors


def require_auth():
    if not AUTH_TOKEN:
        return None
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {AUTH_TOKEN}":
        return jsonify({"error": "Unauthorized"}), 401
    return None


def sanitize_filename(name):
    return re.sub(r'[^a-zA-Z0-9_]', '', name.lower().replace(" ", "_")) or "resume"


def generate_files(json_data, safe_name):
    pdf_b64 = None
    tex_b64 = None
    pdf_name = f"resume_{safe_name}.pdf"
    tex_name = f"resume_{safe_name}.tex"

    if not os.path.exists(LATEX_DIR):
        app.logger.warning("LaTeX engine directory not found at %s", LATEX_DIR)
        return pdf_b64, tex_b64, pdf_name, tex_name

    tmpdir = tempfile.mkdtemp(prefix="resume_")
    try:
        json_path = os.path.join(tmpdir, f"data_{safe_name}.json")
        with open(json_path, "w") as f:
            json.dump(json_data, f, indent=4)

        # Copy template + any needed files
        tex_template = os.path.join(LATEX_DIR, "template.tex")
        if os.path.exists(tex_template):
            shutil.copy2(tex_template, tmpdir)

        result = subprocess.run(
            [sys.executable, os.path.join(LATEX_DIR, "generate.py"),
             "build", json_path, "--out", tex_name],
            cwd=tmpdir, capture_output=True, text=True, timeout=120
        )

        if result.returncode != 0:
            app.logger.error("LaTeX build failed:\n%s", result.stderr[-2000:])

        pdf_path = os.path.join(tmpdir, "output", pdf_name)
        tex_path = os.path.join(tmpdir, "output", tex_name)

        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                pdf_b64 = base64.b64encode(f.read()).decode()
        if os.path.exists(tex_path):
            with open(tex_path, "rb") as f:
                tex_b64 = base64.b64encode(f.read()).decode()
    except subprocess.TimeoutExpired:
        app.logger.error("LaTeX compilation timed out")
    except Exception as e:
        app.logger.error("LaTeX generation error: %s", str(e), exc_info=True)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    return pdf_b64, tex_b64, pdf_name, tex_name


# ── Routes ───────────────────────────────────────────────────

@app.route("/generate", methods=["POST"])
@limiter.limit(RATE_LIMIT)
def generate_resume():
    auth_err = require_auth()
    if auth_err:
        return auth_err

    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON body"}), 400

    if not data:
        return jsonify({"error": "Request body is required"}), 400

    raw_company = data.get("company_name", "").strip()
    job_description = data.get("job_description", "").strip()
    safe_name = sanitize_filename(raw_company)

    # Validate
    validation_errors = validate_input(raw_company, job_description)
    if validation_errors:
        return jsonify({"error": "; ".join(validation_errors)}), 400

    request_id = uuid.uuid4().hex[:8]
    app.logger.info("[%s] Generate for '%s' (%s)", request_id, raw_company, safe_name)

    # Read template
    if not os.path.exists(TEMPLATE_PATH):
        app.logger.error("Template not found at %s", TEMPLATE_PATH)
        return jsonify({"error": "Server configuration error: template missing"}), 500

    with open(TEMPLATE_PATH, "r") as f:
        template_content = f.read()

    # Build prompt
    final_prompt = (
        template_content
        .replace("{{Insert Here}}", job_description)
        .replace("{company_name}", safe_name)
    )
    final_prompt += (
        "\n\nCRITICAL INSTRUCTION: "
        "Return ONLY a valid JSON object matching the template above. "
        "Do not include any other text, markdown, or explanations."
    )

    # Call LLM
    try:
        app.logger.info("[%s] Calling Groq API (%s)...", request_id, MODEL)
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a JSON generator. Return ONLY valid JSON."},
                {"role": "user", "content": final_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            timeout=60,
        )
        resume_data = json.loads(response.choices[0].message.content)
        app.logger.info("[%s] LLM response parsed successfully", request_id)
    except json.JSONDecodeError:
        app.logger.warning("[%s] LLM returned invalid JSON", request_id)
        return jsonify({"error": "LLM did not return valid JSON. Try again."}), 502
    except Exception as e:
        app.logger.error("[%s] Groq API error: %s", request_id, str(e), exc_info=True)
        return jsonify({"error": "AI service error. Please try again later."}), 502

    # Generate PDF & TEX
    app.logger.info("[%s] Generating PDF/TEX...", request_id)
    pdf_b64, tex_b64, pdf_name, tex_name = generate_files(resume_data, safe_name)

    resp = {
        "message": "Success",
        "json_file": f"data_{safe_name}.json",
    }
    if pdf_b64:
        resp["pdf_base64"] = pdf_b64
        resp["pdf_filename"] = pdf_name
    if tex_b64:
        resp["tex_base64"] = tex_b64
        resp["tex_filename"] = tex_name

    app.logger.info(
        "[%s] Done — pdf=%s tex=%s",
        request_id, "yes" if pdf_b64 else "no", "yes" if tex_b64 else "no"
    )
    return jsonify(resp)


@app.route("/health", methods=["GET"])
def health():
    latex_ok = os.path.exists(LATEX_DIR)
    groq_ok = bool(GROQ_API_KEY)
    template_ok = os.path.exists(TEMPLATE_PATH)
    status = 200 if (groq_ok and template_ok) else 503
    return jsonify({
        "status": "ok" if status == 200 else "degraded",
        "groq_api": groq_ok,
        "latex_engine": latex_ok,
        "template": template_ok,
    }), status


@app.errorhandler(413)
def payload_too_large(e):
    return jsonify({"error": "Request body too large"}), 413


@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": "Rate limit exceeded. Try again later."}), 429


@app.errorhandler(500)
def internal_error(e):
    app.logger.error("Unhandled error: %s", str(e), exc_info=True)
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.logger.info("Starting server on port %d (debug=%s)", port, debug)
    app.run(host="0.0.0.0", port=port, debug=debug)
