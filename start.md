# Resume Tailor — Quick Start

## Prerequisites

- Python 3.7+
- Chrome browser
- A [Groq API key](https://console.groq.com/keys)
- LaTeX engine (optional, for PDF output)

## 1. Set Up the Backend

```bash
cd resume_tailor_project/python_backend

# Create .env with your Groq API key
echo "GROQ_API_KEY=your_key_here" > .env

# Activate virtual environment and start server
source venv/bin/activate
python server.py
```

Server runs at `http://127.0.0.1:5000`.

## 2. Install the Browser Extension

1. Open Chrome → `chrome://extensions`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked** → select:
   ```
   resume_tailor_project/browser_extension
   ```

## 3. Use It

1. Go to a job posting and **highlight** the job description
2. Click the extension icon → enter company name → **Generate**
3. The backend creates `data_{company}.json`

## 4. Generate PDF (Optional)

```bash
cd "Latex_from_Json Engine"
python generate.py ../resume_tailor_project/data_{company}.json
```

## Project Structure

```
resume_tailor_project/
├── browser_extension/   # Chrome extension (popup UI)
├── python_backend/      # Flask server + Groq API
├── templates/           # LLM prompt template
├── data_*.json          # Tailored resume JSONs
└── output/              # Generated prompts

Latex_from_Json Engine/  # Standalone LaTeX generator
├── generate.py          # JSON → .tex → PDF
├── template.tex         # LaTeX template
└── data.json            # Base resume data
```
