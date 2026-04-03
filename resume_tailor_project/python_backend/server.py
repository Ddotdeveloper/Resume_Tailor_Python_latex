from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import os
import json
from dotenv import load_dotenv
load_dotenv()
app = Flask(__name__)
CORS(app)

# ==========================================
# 1. SETUP YOUR LLM API
# ==========================================
# IMPORTANT: Generate a NEW key and paste it here!
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# We use Gemini 2.5 Flash because it's fast, cheap, and excellent at JSON.
model = genai.GenerativeModel(
    'gemini-2.5-flash',
    generation_config={"response_mime_type": "application/json"}
)

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
        print(f"Sending request to Gemini for {raw_company_name}...")
        response = model.generate_content(final_prompt)
        
        # Parse the response to ensure it's valid JSON
        resume_data = json.loads(response.text)

        # ==========================================
        # 4. SAVE THE JSON FILE
        # ==========================================
        with open(json_filepath, 'w') as json_file:
            json.dump(resume_data, json_file, indent=4)
        print(f"Successfully saved {json_filename}")

        return jsonify({
            "message": "Success",
            "json_file": json_filename
        })

    except json.JSONDecodeError:
         return jsonify({"error": "LLM did not return valid JSON. Try again."}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(port=5000, debug=True)