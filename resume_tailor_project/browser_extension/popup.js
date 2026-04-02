document.getElementById('generateBtn').addEventListener('click', async () => {
    const companyName = document.getElementById('companyName').value.trim();
    const manualJdBox = document.getElementById('manualJd');
    const manualJdText = manualJdBox.value.trim();
    const outputDiv = document.getElementById('output');
    
    if (!companyName) {
        alert("Please enter a company name.");
        return;
    }

    let finalJobDescription = "";

    // If the user already pasted text into the fallback box, use that immediately
    if (manualJdText) {
        finalJobDescription = manualJdText;
        sendToServer(companyName, finalJobDescription, outputDiv);
        return;
    }

    // Otherwise, try to auto-extract the highlighted text
    let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    chrome.scripting.executeScript({
        target: { tabId: tab.id },
        function: getSelectedText,
    }, (injectionResults) => {
        // Check if extraction worked
        if (injectionResults && injectionResults[0] && injectionResults[0].result) {
            finalJobDescription = injectionResults[0].result;
            sendToServer(companyName, finalJobDescription, outputDiv);
        } else {
            // IF EXTRACTION FAILS: Show the manual paste box and alert the user
            manualJdBox.style.display = "block";
            outputDiv.style.display = "none";
            alert("This website blocks auto-extraction. Please copy the Job Description, paste it into the new text box in this popup, and click Generate again.");
        }
    });
});

// The extraction function
function getSelectedText() {
    return window.getSelection().toString();
}

// The server communication function
async function sendToServer(companyName, jobDescription, outputDiv) {
    outputDiv.style.display = "block";
    outputDiv.innerText = "Sending to local server...";

    try {
        const response = await fetch('http://127.0.0.1:5000/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                company_name: companyName, 
                job_description: jobDescription 
            })
        });
        
        const data = await response.json();

        if (response.ok) {
            outputDiv.innerHTML = `
                <span style="color: green;"><b>Success!</b> File saved.</span><br><br>
                <b>Terminal Commands:</b>
                <code>${data.touch_command}</code>
                <code>${data.python_command}</code>
            `;
            // Hide the manual box again if it was successful
            document.getElementById('manualJd').style.display = "none";
            document.getElementById('manualJd').value = "";
        } else {
            outputDiv.innerText = `Error: ${data.error}`;
        }
    } catch (error) {
        outputDiv.innerText = "Error connecting to backend. Is your Python Flask server running?";
    }
}