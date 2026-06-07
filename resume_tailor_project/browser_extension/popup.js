const companyInput = document.getElementById('companyName');
const manualJdBox = document.getElementById('manualJd');
const outputDiv = document.getElementById('output');
const generateBtn = document.getElementById('generateBtn');
const statusDot = document.getElementById('statusDot');
const configBtn = document.getElementById('configBtn');
const configPanel = document.getElementById('configPanel');
const authTokenInput = document.getElementById('authToken');
const saveTokenBtn = document.getElementById('saveTokenBtn');
const tokenStatus = document.getElementById('tokenStatus');

let isLoading = false;
let authToken = '';

chrome.storage.local.get('authToken', (result) => {
    authToken = result.authToken || '';
    if (authToken) {
        authTokenInput.value = authToken;
    }
});

function setLoading(state) {
    isLoading = state;
    generateBtn.disabled = state;
    generateBtn.innerHTML = state
        ? '<span class="spinner"></span> Generating...'
        : 'Extract JD &amp; Generate';
}

function showOutput(message, type) {
    outputDiv.className = type;
    outputDiv.innerHTML = message;
}

function downloadBase64(b64, filename, mimeType) {
    try {
        const byteChars = atob(b64);
        const bytes = new Uint8Array(byteChars.length);
        for (let i = 0; i < byteChars.length; i++) bytes[i] = byteChars.charCodeAt(i);
        const blob = new Blob([bytes], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    } catch (e) {
        showOutput('Error downloading file. Please try again.', 'error');
    }
}

checkServer();

async function checkServer() {
    try {
        const resp = await fetch('http://127.0.0.1:5001/health');
        if (resp.ok) {
            statusDot.className = 'status-dot online';
            statusDot.title = 'Server is running';
        } else {
            statusDot.className = 'status-dot';
            statusDot.title = 'Server is degraded';
        }
    } catch {
        statusDot.className = 'status-dot';
        statusDot.title = 'Server is offline';
    }
}

configBtn.addEventListener('click', () => {
    configPanel.style.display = configPanel.style.display === 'none' ? 'block' : 'none';
});

saveTokenBtn.addEventListener('click', () => {
    const token = authTokenInput.value.trim();
    chrome.storage.local.set({ authToken: token }, () => {
        authToken = token;
        tokenStatus.textContent = 'Token saved';
        tokenStatus.style.color = '#2b8a3e';
        setTimeout(() => { tokenStatus.textContent = ''; }, 2000);
    });
});

generateBtn.addEventListener('click', async () => {
    const companyName = companyInput.value.trim();
    const manualJdText = manualJdBox.value.trim();

    if (!companyName) {
        showOutput('Please enter a company name.', 'error');
        companyInput.focus();
        return;
    }

    if (isLoading) return;
    setLoading(true);
    showOutput('', '');
    manualJdBox.style.display = 'none';

    let finalJobDescription = '';

    if (manualJdText) {
        finalJobDescription = manualJdText;
        await sendToServer(companyName, finalJobDescription);
        setLoading(false);
        return;
    }

    try {
        let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

        chrome.scripting.executeScript({
            target: { tabId: tab.id },
            function: getSelectedText,
        }, async (injectionResults) => {
            if (injectionResults && injectionResults[0] && injectionResults[0].result) {
                finalJobDescription = injectionResults[0].result;
                await sendToServer(companyName, finalJobDescription);
            } else {
                manualJdBox.style.display = 'block';
                manualJdBox.focus();
                showOutput(
                    'Auto-extraction blocked on this page. Paste the job description above and click Generate again.',
                    'info'
                );
            }
            setLoading(false);
        });
    } catch (err) {
        showOutput('Could not access the active tab. Try pasting the JD manually.', 'error');
        manualJdBox.style.display = 'block';
        setLoading(false);
    }
});

function getSelectedText() {
    return window.getSelection().toString();
}

async function sendToServer(companyName, jobDescription) {
    showOutput('Sending to server...', 'info');

    const headers = { 'Content-Type': 'application/json' };
    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }

    try {
        const response = await fetch('http://127.0.0.1:5001/generate', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({
                company_name: companyName,
                job_description: jobDescription
            })
        });

        const data = await response.json();

        if (response.ok) {
            let html = `<strong style="color:#2b8a3e">&#10003; Success!</strong> Resume tailored for <strong>${companyName}</strong>.`;

            if (data.pdf_base64) {
                html += `<br><br><button class="btn btn-primary" id="downloadPdfBtn" style="font-size:13px;padding:8px;">&#11015; Download PDF</button>`;
                html += `<div style="font-size:11px;color:#6c757d;margin-top:4px;">${data.pdf_filename}</div>`;
            }
            if (data.tex_base64) {
                html += `<br><button class="btn btn-primary" id="downloadTexBtn" style="font-size:13px;padding:8px;margin-top:4px;">&#11015; Download LaTeX (.tex)</button>`;
                html += `<div style="font-size:11px;color:#6c757d;margin-top:4px;">${data.tex_filename}</div>`;
            }
            if (!data.pdf_base64) {
                html += `<br><span style="font-size:12px;color:#6c757d;">JSON saved as <code>${data.json_file}</code></span>`;
            }

            showOutput(html, 'success');

            if (data.pdf_base64) {
                document.getElementById('downloadPdfBtn').addEventListener('click', () => downloadBase64(data.pdf_base64, data.pdf_filename, 'application/pdf'));
            }
            if (data.tex_base64) {
                document.getElementById('downloadTexBtn').addEventListener('click', () => downloadBase64(data.tex_base64, data.tex_filename, 'text/plain'));
            }

            manualJdBox.style.display = 'none';
            manualJdBox.value = '';
        } else if (response.status === 401) {
            showOutput(
                'Server requires authentication. Add your auth token in settings (gear icon).',
                'error'
            );
            configPanel.style.display = 'block';
            authTokenInput.focus();
        } else if (response.status === 429) {
            showOutput('Too many requests. Please wait a moment and try again.', 'error');
        } else {
            showOutput(`Error: ${data.error || 'Something went wrong'}`, 'error');
        }
    } catch {
        showOutput(
            'Could not reach the backend. Make sure your Flask server is running (<code>python server.py</code>).',
            'error'
        );
    }
}
