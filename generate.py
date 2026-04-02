#!/usr/bin/env python3
"""
Resume Generator — Fills a LaTeX template from JSON, auto-fits to one page.
Supports both Tectonic and pdflatex as compile engines.

SUBCOMMANDS
-----------
  generate   Fill template from JSON  →  output/resume.tex
  compile    Compile a .tex file      →  output/resume.pdf
  build      generate + compile in one shot (default when no subcommand given)

USAGE EXAMPLES
--------------
  python generate.py data.json                         # build (gen + compile)
  python generate.py data.json --no-pdf                # generate .tex only
  python generate.py data.json --engine pdflatex       # use pdflatex instead
  python generate.py data.json --out divay.tex         # custom output name

  python generate.py generate data.json                # explicit generate
  python generate.py generate data.json --no-fit       # skip 1-page fitting
  python generate.py generate data.json --out role.tex

  python generate.py compile output/resume.tex         # compile existing .tex
  python generate.py compile output/resume.tex --engine pdflatex

  python generate.py build data.json                   # explicit build
  python generate.py build data_backend.json --out backend.tex
"""

import json
import os
import re
import sys
import shutil
import argparse
import subprocess
import tempfile


# ──────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────

OUTPUT_DIR    = "output"
TEMPLATE_FILE = "template.tex"

# Progressively tighter layouts — tried in order until content fits 1 page.
# (font_size, item_sep, margin_side, margin_top, text_width_add, text_height_add)
FIT_LEVELS = [
    (10,  3, "-0.5", "-0.5", "1.0", "1.0"),
    (10,  2, "-0.6", "-0.6", "1.2", "1.2"),
    (10,  1, "-0.7", "-0.7", "1.4", "1.4"),
    (9.5, 2, "-0.7", "-0.7", "1.4", "1.4"),
    (9,   2, "-0.7", "-0.7", "1.4", "1.4"),
    (9,   1, "-0.8", "-0.8", "1.6", "1.6"),
    (8.5, 1, "-0.8", "-0.8", "1.6", "1.6"),
]


# ──────────────────────────────────────────────────────────────
# ENGINE DETECTION
# ──────────────────────────────────────────────────────────────

def detect_engine(preferred: str = "tectonic") -> str:
    """Return available engine. Tries preferred first, then fallbacks."""
    if preferred and shutil.which(preferred):
        return preferred
    for eng in ["tectonic", "pdflatex"]:
        if shutil.which(eng):
            return eng
    return None


# ──────────────────────────────────────────────────────────────
# LATEX BLOCK BUILDERS
# ──────────────────────────────────────────────────────────────

def build_experience_block(experience):
    lines = []
    for job in experience:
        lines.append(
            f"    \\resumeSubheading\n"
            f"      {{{job['title']}}}{{{job['dates']}}}\n"
            f"      {{{job['company']}}}{{{job['location']}}}\n"
            f"      \\resumeItemListStart"
        )
        for bullet in job.get("bullets", []):
            lines.append(f"        \\resumeItem{{{bullet}}}")
        lines.append("      \\resumeItemListEnd\n")
    return "\n".join(lines)


def build_projects_block(projects):
    lines = []
    for proj in projects:
        lines.append(
            f"    \\resumeProjectHeading\n"
            f"      {{\\textbf{{{proj['title']}}} $|$ \\emph{{{proj['tech']}}}}}{{}}\n"
            f"      \\resumeItemListStart"
        )
        for bullet in proj.get("bullets", []):
            lines.append(f"        \\resumeItem{{{bullet}}}")
        lines.append("      \\resumeItemListEnd\n")
    return "\n".join(lines)


def build_skills_block(skills):
    parts = []
    for i, skill in enumerate(skills):
        suffix = " \\\\" if i < len(skills) - 1 else ""
        parts.append(f"     \\textbf{{{skill['label']}}}{{: {skill['value']}}}{suffix}")
    return "\n".join(parts)


def build_achievements_block(achievements):
    return "\n".join(f"    \\resumeItem{{{a}}}" for a in achievements)


# ──────────────────────────────────────────────────────────────
# TEMPLATE RENDERER
# ──────────────────────────────────────────────────────────────

def render_template(template, data, fit_params):
    font_size, item_sep, margin_side, margin_top, tw_add, th_add = fit_params

    ctx = dict(data)
    ctx["FONT_SIZE"] = str(font_size)
    ctx["ITEM_SEP"]  = str(item_sep)
    ctx["MARGIN_LINES"] = (
        f"\\addtolength{{\\oddsidemargin}}{{{margin_side}in}}\n"
        f"\\addtolength{{\\evensidemargin}}{{{margin_side}in}}\n"
        f"\\addtolength{{\\textwidth}}{{{tw_add}in}}\n"
        f"\\addtolength{{\\topmargin}}{{{margin_top}in}}\n"
        f"\\addtolength{{\\textheight}}{{{th_add}in}}"
    )
    ctx["EXPERIENCE_BLOCK"]   = build_experience_block(data.get("experience", []))
    ctx["PROJECTS_BLOCK"]     = build_projects_block(data.get("projects", []))
    ctx["SKILLS_BLOCK"]       = build_skills_block(data.get("skills", []))
    ctx["ACHIEVEMENTS_BLOCK"] = build_achievements_block(data.get("achievements", []))

    def replacer(match):
        key = match.group(1)
        if key in ctx:
            val = ctx[key]
            if isinstance(val, list):
                return "\n".join(f"  \\item {v}" for v in val)
            return str(val)
        print(f"  [WARN] Placeholder '{{{{{key}}}}}' not in JSON — leaving blank.")
        return ""

    return re.sub(r"\{\{([A-Z0-9_]+)\}\}", replacer, template)


# ──────────────────────────────────────────────────────────────
# LOW-LEVEL ENGINE RUNNER
# ──────────────────────────────────────────────────────────────

def _run_engine(engine, tex_file, out_dir):
    """Run engine silently. Returns (returncode, log_string)."""
    tex_dir  = os.path.dirname(os.path.abspath(tex_file))
    tex_name = os.path.basename(tex_file)

    if engine == "tectonic":
        cmd = ["tectonic", "--outdir", out_dir, "--keep-logs", tex_name]
    else:
        cmd = ["pdflatex", "-interaction=nonstopmode",
               f"-output-directory={out_dir}", tex_name]

    try:
        r = subprocess.run(cmd, cwd=tex_dir,
                           capture_output=True, text=True, timeout=90)
        return r.returncode, r.stdout + r.stderr
    except FileNotFoundError:
        return -10, f"Engine '{engine}' not found."
    except subprocess.TimeoutExpired:
        return -11, "Timed out."


def count_pages(tex_file, engine):
    """
    Compile into a temp dir, return page count.
    -1 = error,  -2 = engine missing,  -3 = timeout
    """
    with tempfile.TemporaryDirectory() as tmpout:
        rc, log = _run_engine(engine, tex_file, tmpout)

        if rc == -10: return -2
        if rc == -11: return -3

        if engine == "tectonic":
            pdfs = [f for f in os.listdir(tmpout) if f.endswith(".pdf")]
            if pdfs:
                try:
                    from pypdf import PdfReader
                    return len(PdfReader(os.path.join(tmpout, pdfs[0])).pages)
                except ImportError:
                    pass
                m = re.search(r"(\d+) page", log)
                return int(m.group(1)) if m else (1 if rc == 0 else -1)
            return -1
        else:
            m = re.search(r"Output written on .+? \((\d+) page", log)
            if m:
                return int(m.group(1))
            if rc != 0 or "! " in log:
                print("  [ERROR] pdflatex failed. Last lines:")
                for line in log.splitlines()[-15:]:
                    print("   ", line)
                return -1
            return 1


# ──────────────────────────────────────────────────────────────
# COMPILE  (public command)
# ──────────────────────────────────────────────────────────────

def compile_tex(tex_path, engine_pref="tectonic"):
    """Compile tex_path → PDF next to it. Returns True on success."""
    engine = detect_engine(engine_pref)
    if not engine:
        print("[ERROR] No LaTeX engine found on PATH.")
        print("  Tectonic : https://tectonic-typesetting.github.io")
        print("  pdflatex : sudo apt install texlive-full")
        return False

    tex_abs  = os.path.abspath(tex_path)
    tex_dir  = os.path.dirname(tex_abs)
    tex_name = os.path.basename(tex_abs)
    basename = os.path.splitext(tex_name)[0]

    print(f"[*] Compiling with {engine}: {tex_path}")

    if engine == "tectonic":
        rc, log = _run_engine("tectonic", tex_abs, tex_dir)
        if rc != 0:
            print("[ERROR] Tectonic failed:")
            for line in log.splitlines()[-20:]:
                print("   ", line)
            return False
    else:
        for run in range(2):          # pdflatex needs 2 passes
            rc, log = _run_engine("pdflatex", tex_abs, tex_dir)
            if rc != 0:
                print(f"[ERROR] pdflatex failed (pass {run+1}):")
                for line in log.splitlines()[-15:]:
                    print("   ", line)
                return False
        for ext in [".aux", ".log", ".out", ".fls", ".fdb_latexmk"]:
            aux = os.path.join(tex_dir, basename + ext)
            if os.path.exists(aux):
                os.remove(aux)

    pdf = os.path.join(tex_dir, basename + ".pdf")
    if os.path.exists(pdf):
        print(f"[+] PDF ready: {pdf}")
        return True
    print("[WARN] Compilation finished but no PDF found.")
    return False


# ──────────────────────────────────────────────────────────────
# GENERATE  (public command)
# ──────────────────────────────────────────────────────────────

def cmd_generate(json_path, output_name, skip_fit, engine_pref="tectonic"):
    """Fill template → write .tex file. Returns output path."""
    if not os.path.exists(TEMPLATE_FILE):
        print(f"[ERROR] '{TEMPLATE_FILE}' not found in current directory.")
        sys.exit(1)
    if not os.path.exists(json_path):
        print(f"[ERROR] '{json_path}' not found.")
        sys.exit(1)

    with open(TEMPLATE_FILE, encoding="utf-8") as f:
        template = f.read()
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    print(f"[+] Loaded: {json_path}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_tex = os.path.join(OUTPUT_DIR, output_name)

    if skip_fit:
        content = render_template(template, data, FIT_LEVELS[0])
        with open(out_tex, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[+] Generated (no-fit): {out_tex}")
        return out_tex

    engine = detect_engine(engine_pref)
    if not engine:
        print("[WARN] No engine found — skipping fit check, using default layout.")
        content = render_template(template, data, FIT_LEVELS[0])
        with open(out_tex, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[+] Generated: {out_tex}")
        return out_tex

    print(f"[*] Fitting to 1 page  (engine: {engine}) ...")
    chosen = None

    with tempfile.TemporaryDirectory() as tmpdir:
        for fname in os.listdir("."):
            if fname.endswith((".sty", ".cls", ".bst")):
                shutil.copy(fname, tmpdir)

        for i, params in enumerate(FIT_LEVELS):
            content = render_template(template, data, params)
            tmp_tex = os.path.join(tmpdir, "probe.tex")
            with open(tmp_tex, "w", encoding="utf-8") as f:
                f.write(content)

            pages = count_pages(tmp_tex, engine)

            if pages == -2:
                print(f"  Engine gone — using level {i+1}."); chosen = content; break
            elif pages == -3:
                print(f"  Timeout — using level {i+1}."); chosen = content; break
            elif pages == -1:
                print(f"  Level {i+1}: compile error — stopping.")
                if chosen is None: chosen = content
                break
            elif pages == 1:
                print(f"  Level {i+1} ✓  font={params[0]}pt  itemsep={params[1]}pt  → 1 page")
                chosen = content; break
            else:
                print(f"  Level {i+1}    font={params[0]}pt  itemsep={params[1]}pt  → {pages} pages, tightening...")
                chosen = content

    if chosen is None:
        print("[WARN] Using tightest settings as fallback.")
        chosen = render_template(template, data, FIT_LEVELS[-1])

    with open(out_tex, "w", encoding="utf-8") as f:
        f.write(chosen)
    print(f"[+] Generated: {out_tex}")
    return out_tex


# ──────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────

def _add_engine(p):
    p.add_argument("--engine", default="tectonic",
                   choices=["tectonic", "pdflatex"],
                   help="LaTeX engine (default: tectonic)")

def _add_out(p):
    p.add_argument("--out", default="resume.tex",
                   help="Output .tex filename (default: resume.tex)")


def main():
    # Allow shorthand: `python generate.py data.json` → treated as `build`
    known = {"generate", "gen", "compile", "cmp", "build"}
    if len(sys.argv) > 1 and sys.argv[1] not in known and not sys.argv[1].startswith("-"):
        sys.argv.insert(1, "build")

    parser = argparse.ArgumentParser(
        prog="generate.py",
        description="LaTeX resume generator  |  JSON → .tex → PDF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="cmd")

    # ── generate
    p_gen = sub.add_parser("generate", aliases=["gen"],
                            help="Fill template from JSON → .tex")
    p_gen.add_argument("json_file")
    p_gen.add_argument("--no-fit", dest="nofit", action="store_true",
                       help="Skip one-page auto-fitting")
    _add_out(p_gen); _add_engine(p_gen)

    # ── compile
    p_cmp = sub.add_parser("compile", aliases=["cmp"],
                            help="Compile an existing .tex → PDF")
    p_cmp.add_argument("tex_file", help="Path to .tex file")
    _add_engine(p_cmp)

    # ── build
    p_bld = sub.add_parser("build",
                            help="generate + compile in one shot (default)")
    p_bld.add_argument("json_file")
    p_bld.add_argument("--no-fit", dest="nofit", action="store_true",
                       help="Skip one-page auto-fitting")
    p_bld.add_argument("--no-pdf", dest="nopdf", action="store_true",
                       help="Generate .tex only, skip compilation")
    _add_out(p_bld); _add_engine(p_bld)

    args = parser.parse_args()

    if args.cmd in ("generate", "gen"):
        cmd_generate(args.json_file, args.out, args.nofit, args.engine)

    elif args.cmd in ("compile", "cmp"):
        ok = compile_tex(args.tex_file, args.engine)
        sys.exit(0 if ok else 1)

    elif args.cmd == "build":
        tex = cmd_generate(args.json_file, args.out, args.nofit, args.engine)
        if not args.nopdf:
            ok = compile_tex(tex, args.engine)
            sys.exit(0 if ok else 1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()