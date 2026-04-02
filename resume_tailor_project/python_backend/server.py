from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
# Allow cross-origin requests from the browser extension
CORS(app) 

@app.route('/generate', methods=['POST'])
def generate_prompt():
    data = request.json
    raw_company_name = data.get('company_name', 'Unknown')
    job_description = data.get('job_description', '')

    # Clean the company name for file usage (e.g., "Nasuni Corp" -> "nasuni_corp")
    company_name_safe = raw_company_name.lower().replace(" ", "_")

    # Define paths based on the project structure
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_path = os.path.join(base_dir, 'templates', 'prompt_template.txt')
    output_dir = os.path.join(base_dir, 'output')
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    try:
        with open(template_path, 'r') as file:
            template_content = file.read()
    except FileNotFoundError:
        return jsonify({"error": "prompt_template.txt not found in templates folder."}), 500

    # Inject the Job Description and replace company name variables
    final_prompt = template_content.replace('{{Insert Here}}', job_description)
    final_prompt = final_prompt.replace('{company_name}', company_name_safe)
    final_prompt = final_prompt.replace('Company_name: Nasuni', f'Company_name: {raw_company_name}')

    # Save the final text file
    output_filename = f"{company_name_safe}_prompt.txt"
    output_path = os.path.join(output_dir, output_filename)

    with open(output_path, 'w') as file:
        file.write(final_prompt)

    # Generate the requested terminal commands
    touch_command = f"touch data_{company_name_safe}.json"
    python_command = f"python3 generate.py data_{company_name_safe}.json --out divay_resume_{company_name_safe}.tex"

    return jsonify({
        "message": "Success",
        "output_file": output_filename,
        "touch_command": touch_command,
        "python_command": python_command
    })

if __name__ == '__main__':
    # Run the server on localhost port 5000
    app.run(port=5000, debug=True)