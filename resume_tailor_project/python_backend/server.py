from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from openai import OpenAI
import os, sys, json, subprocess, base64
from dotenv import load_dotenv
load_dotenv()
app = Flask(__name__)
CORS(app)

# ==========================================
# 1. SETUP YOUR LLM API
# ==========================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

MODEL = "llama-3.3-70b-versatile"

@app.route('/generate', methods=['POST'])
def generate_resume():
    data = request.json
    raw_company_name = data.get('company_name', 'Unknown')
    job_description = data.get('job_description', '')
    company_name_safe = raw_company_name.lower().replace(" ", "_")

    # Define paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_path = os.path.join(base_dir, 'templates', 'prompt_template.txt')
    
    # We will save the JSON in the base directory
    json_filename = f"data_{company_name_safe}.json"
    json_filepath = os.path.join(base_dir, json_filename)
    
    try:
        # ==========================================
        # 2. PREPARE THE PROMPT
        # ==========================================
        with open(template_path, 'r') as file:
            template_content = file.read()

        # Inject the JD into your template
        final_prompt = template_content.replace('{{Insert Here}}', job_description)
        final_prompt = final_prompt.replace('{company_name}', company_name_safe)
        final_prompt += "\n\nCRITICAL INSTRUCTION: Return ONLY a valid JSON object matching the template above. Do not include any other text, markdown, or explanations."

        # ==========================================
        # 3. CALL THE LLM
        # ==========================================
        print(f"Sending request to Groq ({MODEL}) for {raw_company_name}...")
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a JSON generator. Return ONLY valid JSON."},
                {"role": "user", "content": final_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        # Parse the response to ensure it's valid JSON
        resume_data = json.loads(response.choices[0].message.content)

        # ==========================================
        # 4. SAVE THE JSON FILE
        # ==========================================
        with open(json_filepath, 'w') as json_file:
            json.dump(resume_data, json_file, indent=4)
        print(f"Successfully saved {json_filename}")

        # ==========================================
        # 5. GENERATE PDF & TEX FROM JSON
        # ==========================================
        project_root = os.path.dirname(base_dir)
        latex_dir = os.path.join(project_root, "Latex_from_Json Engine")
        tex_name = f"resume_{company_name_safe}"
        pdf_base64 = None
        tex_base64 = None

        if os.path.exists(latex_dir):
            try:
                subprocess.run(
                    [sys.executable, "generate.py", "build", json_filepath,
                     "--out", f"{tex_name}.tex"],
                    cwd=latex_dir, capture_output=True, text=True, timeout=120
                )
                pdf_path = os.path.join(latex_dir, "output", f"{tex_name}.pdf")
                tex_path = os.path.join(latex_dir, "output", f"{tex_name}.tex")
                if os.path.exists(pdf_path):
                    with open(pdf_path, "rb") as f:
                        pdf_base64 = base64.b64encode(f.read()).decode()
                    print(f"PDF generated: {tex_name}.pdf")
                if os.path.exists(tex_path):
                    with open(tex_path, "rb") as f:
                        tex_base64 = base64.b64encode(f.read()).decode()
                    print(f"TEX generated: {tex_name}.tex")
            except Exception as e:
                print(f"PDF/TEX generation skipped: {e}")

        resp = {"message": "Success", "json_file": json_filename}
        if pdf_base64:
            resp["pdf_base64"] = pdf_base64
            resp["pdf_filename"] = f"{tex_name}.pdf"
        if tex_base64:
            resp["tex_base64"] = tex_base64
            resp["tex_filename"] = f"{tex_name}.tex"
        return jsonify(resp)

    except json.JSONDecodeError:
         return jsonify({"error": "LLM did not return valid JSON. Try again."}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(port=5000, debug=True)