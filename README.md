# Resume Generator — LaTeX from JSON

A minimal, production-ready Python tool that fills a LaTeX resume template
from structured JSON data, with automatic one-page fitting.

---

## Folder Structure

```
resume_tool/
├── generate.py        ← Main script (run this)
├── template.tex       ← LaTeX template with {{PLACEHOLDERS}}
├── data.json          ← Your resume content
├── data_backend.json  ← (Optional) another role-specific JSON
└── output/
    ├── resume.tex     ← Generated LaTeX
    └── resume.pdf     ← Generated PDF (if --pdf flag used)
```

---

## Step 1 — Install Requirements

You need Python 3.7+ (no third-party packages required).

For PDF compilation, install pdflatex:
- **Ubuntu/Debian**: `sudo apt install texlive-full`
- **macOS**: Install MacTeX from https://tug.org/mactex/
- **Windows**: Install MiKTeX from https://miktex.org/

---

## Step 2 — Run the Generator

```bash
# Basic: generate output/resume.tex
python generate.py data.json

# Generate + compile to PDF
python generate.py data.json --pdf

# Custom output filename
python generate.py data.json --out divay_resume.tex --pdf

# Skip one-page fitting (use default layout)
python generate.py data.json --no-fit

# Multiple roles — just swap the JSON!
python generate.py data_backend.json --out backend_resume.tex --pdf
python generate.py data_frontend.json --out frontend_resume.tex --pdf
```

---

## How One-Page Fitting Works

The script tries progressively tighter layouts until the content fits on one page:

| Level | Font Size | Item Spacing | Margins |
|-------|-----------|--------------|---------|
| 1     | 10pt      | 3pt          | default |
| 2     | 10pt      | 2pt          | slightly tighter |
| 3     | 10pt      | 1pt          | tighter |
| 4     | 9.5pt     | 2pt          | tighter |
| 5     | 9pt       | 2pt          | tighter |
| 6     | 9pt       | 1pt          | tightest |
| 7     | 8.5pt     | 1pt          | last resort |

If `pdflatex` is not installed, it generates the .tex with default settings.

---

## How to Add a New Role (Multiple JSON Files)

Copy `data.json` to `data_backend.json` and edit the content:
- Change `SUMMARY` to highlight relevant skills
- Reorder or remove `experience` / `projects` entries
- Keep only the most relevant `skills` rows

```bash
python generate.py data_backend.json --out backend_resume.tex --pdf
```

---

## Placeholder Reference

### Simple string placeholders (in template.tex)
| Placeholder | Description |
|---|---|
| `{{NAME}}` | Full name |
| `{{PHONE}}` | Phone number |
| `{{EMAIL}}` | Email address |
| `{{LINKEDIN_URL}}` | LinkedIn profile URL |
| `{{GITHUB_URL}}` | GitHub profile URL |
| `{{LEETCODE_URL}}` | LeetCode profile URL |
| `{{EDU_INSTITUTION}}` | University name |
| `{{EDU_DATES}}` | Enrollment dates |
| `{{EDU_DEGREE}}` | Degree and specialization |
| `{{EDU_CGPA}}` | CGPA |
| `{{EDU_LOCATION}}` | City, Country |
| `{{SUMMARY}}` | Professional summary paragraph |

### Structured JSON keys (auto-converted to LaTeX)
| JSON key | Description |
|---|---|
| `experience` | Array of job objects |
| `projects` | Array of project objects |
| `skills` | Array of `{label, value}` objects |
| `achievements` | Array of strings |

### Auto-injected by fitting engine (do not put in JSON)
`{{FONT_SIZE}}`, `{{ITEM_SEP}}`, `{{MARGIN_SIDE}}`, `{{MARGIN_TOP}}`,
`{{MARGIN_TEXT_WIDTH}}`, `{{MARGIN_TEXT_HEIGHT}}`

---

## Customizing the Template

To add a new section, put `{{MY_BLOCK}}` anywhere in `template.tex`,
then add `"MY_BLOCK": "your LaTeX content here"` in `data.json`.

For lists, add a JSON array and the script will auto-convert to `\item` format.
How to run the project 

python generate.py data.json              # Generate output/resume.tex
python generate.py data.json --pdf        # Also compile to PDF
python generate.py data.json --no-fit     # Skip one-page auto-fitting
python generate.py data_backend.json --out backend.tex --pdf  # Role-specific
