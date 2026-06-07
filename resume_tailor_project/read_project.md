# Resume Tailor Project

This project consists of a browser extension and a Python backend designed to help tailor your resume to specific job descriptions.

## Project Structure

- `resume_tailor_project/browser_extension`: Contains the code for the browser extension.
- `resume_tailor_project/python_backend`: Contains the Flask server responsible for processing job descriptions and generating tailored content.
- `resume_tailor_project/templates`: Stores template files, such as `prompt_template.txt`.
- `resume_tailor_project/data_*.json`: Example data files (e.g., `data_dfas.json`, `data_reddoorz.json`).
- `resume_tailor_project/output`: Directory for generated outputs (e.g., `nasuni_prompt.txt`).

## How it Works

1.  **Browser Extension**:
    *   The `content.js` script runs on web pages, allowing users to select text (e.g., a job description).
    *   `popup.html` and `popup.js` provide the user interface in the browser extension's popup, where the user can input a company name and trigger the process.
    *   The extension sends the selected job description and company name to the local Python backend.

2.  **Python Backend**:
    *   The `server.py` file implements a Flask application.
    *   It exposes a `/generate` endpoint that receives the company name and job description from the browser extension.
    *   This backend is responsible for processing this information (likely using a prompt template from `templates/prompt_template.txt` and potentially other data files) to generate tailored resume content.

## Setup and Usage (Conceptual)

To run this project, you would typically follow these steps:

1.  **Backend Setup**:
    *   Navigate to `resume_tailor_project/python_backend`.
    *   Install Python dependencies (e.g., `Flask`).
    *   Run the Flask server.

2.  **Browser Extension Installation**:
    *   Load the `resume_tailor_project/browser_extension` directory as an unpacked extension in your browser (e.g., Chrome, Firefox).

3.  **Workflow**:
    *   Browse to a job posting.
    *   Use the browser extension to select the job description text.
    *   Enter the company name in the extension's popup.
    *   Click "Generate" (or similar) to send the data to the local server.
    *   The server processes the request and returns tailored content, which the extension then displays or uses.
