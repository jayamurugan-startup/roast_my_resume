# app.py
import os
import re
import json
from flask import Flask, request, jsonify, render_template_string
from werkzeug.utils import secure_filename
from groq import Groq
import PyPDF2
import docx

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max
app.config['UPLOAD_FOLDER'] = '/tmp'

# Initialize Groq client
client = Groq(api_key=os.environ.get('GROQ_API_KEY'))

# Model config: Primary = Llama 4 Scout, Fallback = Llama 3.3 70B
PRIMARY_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
FALLBACK_MODEL = "llama-3.3-70b-versatile"

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text(file_path, filename):
    ext = filename.rsplit('.', 1)[1].lower()
    text = ""
    
    if ext == 'pdf':
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
    elif ext == 'docx':
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    elif ext == 'txt':
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
    
    return text.strip()

def roast_resume(resume_text):
    """Call Groq API with fallback logic."""
    
    system_prompt = """You are a brutally honest, savage career coach who roasts resumes. 
    Your job is to tear apart resumes line by line with specific, actionable feedback.
    Be funny, savage, but actually helpful. Use emojis. No sugarcoating.
    Format your response as a JSON object with this structure:
    {
        "overall_score": <number 1-10>,
        "headline_roast": "<one savage sentence about the whole resume>",
        "sections": [
            {
                "section_name": "<e.g. Summary, Experience, Skills>",
                "roast": "<savage but specific critique>",
                "severity": "<mild|spicy|nuclear>",
                "fix_it": "<what they should actually do>"
            }
        ],
        "best_line": "<the funniest/most savage one-liner from your roast>",
        "shareable_quote": "<a short, screenshot-worthy quote under 120 chars>"
    }
    
    Rules:
    - Reference SPECIFIC content from their resume, not generic advice
    - If they use buzzwords like "synergy" or "passionate self-starter", DESTROY them
    - If their email is unprofessional, call it out
    - If they list Microsoft Word as a skill, make fun of it
    - If their experience bullets are just responsibilities not results, roast them
    - Keep it entertaining enough that they'd screenshot and share it
    """
    
    user_prompt = f"Here's a resume. Destroy it:\n\n{resume_text[:4000]}"
    
    # Try primary model first
    models_to_try = [PRIMARY_MODEL, FALLBACK_MODEL]
    last_error = None
    
    for model in models_to_try:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.9,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            
            # Parse JSON
            try:
                roast_data = json.loads(content)
            except json.JSONDecodeError:
                # If JSON parse fails, wrap the raw text
                roast_data = {
                    "overall_score": 3,
                    "headline_roast": "Your resume broke our AI. That's how bad it is.",
                    "sections": [{"section_name": "Everything", "roast": content, "severity": "nuclear", "fix_it": "Start over."}],
                    "best_line": "This resume made our AI cry.",
                    "shareable_quote": "My resume broke an AI. 💀",
                    "_model_used": model,
                    "_raw": True
                }
            
            roast_data["_model_used"] = model
            return roast_data
            
        except Exception as e:
            last_error = str(e)
            continue  # Try fallback
    
    # Both failed
    return {
        "overall_score": 1,
        "headline_roast": "Even our AI gave up on your resume. That's a new low.",
        "sections": [{"section_name": "System Error", "roast": f"Primary and fallback models both failed: {last_error}", "severity": "nuclear", "fix_it": "Try again later, or just burn the resume."}],
        "best_line": "Your resume crashed two AI models. Legendary.",
        "shareable_quote": "My resume broke TWO AIs. 🏆",
        "_model_used": "none",
        "_error": last_error
    }

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔥 RoastMyResume — Get Destroyed</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: #0a0a0f;
            color: #e0e0e0;
            min-height: 100vh;
        }
        .container { max-width: 800px; margin: 0 auto; padding: 40px 20px; }
        header { text-align: center; margin-bottom: 40px; }
        h1 { font-size: 3rem; background: linear-gradient(135deg, #ff6b6b, #ffd93d); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 10px; }
        .tagline { color: #888; font-size: 1.1rem; }
        .upload-zone {
            border: 3px dashed #ff6b6b;
            border-radius: 20px;
            padding: 60px 40px;
            text-align: center;
            background: rgba(255,107,107,0.05);
            transition: all 0.3s;
            cursor: pointer;
            margin-bottom: 30px;
        }
        .upload-zone:hover, .upload-zone.dragover {
            background: rgba(255,107,107,0.1);
            border-color: #ffd93d;
            transform: scale(1.02);
        }
        .upload-zone input { display: none; }
        .upload-icon { font-size: 4rem; margin-bottom: 15px; }
        .upload-text { font-size: 1.3rem; color: #ccc; }
        .upload-hint { color: #666; margin-top: 10px; font-size: 0.9rem; }
        .btn {
            background: linear-gradient(135deg, #ff6b6b, #ff8e53);
            border: none;
            padding: 15px 40px;
            border-radius: 50px;
            color: white;
            font-size: 1.1rem;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            margin-top: 20px;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(255,107,107,0.3); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        
        .loading {
            display: none;
            text-align: center;
            padding: 40px;
        }
        .loading.active { display: block; }
        .spinner {
            width: 60px; height: 60px;
            border: 4px solid #333;
            border-top-color: #ff6b6b;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        
        .roast-result {
            display: none;
            animation: fadeIn 0.5s;
        }
        .roast-result.active { display: block; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        
        .score-circle {
            width: 120px; height: 120px;
            border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-size: 3rem; font-weight: bold;
            margin: 0 auto 20px;
            position: relative;
        }
        .score-low { background: linear-gradient(135deg, #ff4444, #cc0000); }
        .score-mid { background: linear-gradient(135deg, #ffaa00, #ff6600); }
        .score-high { background: linear-gradient(135deg, #00cc66, #009944); }
        
        .headline-roast {
            font-size: 1.5rem;
            text-align: center;
            color: #ffd93d;
            margin-bottom: 30px;
            font-style: italic;
        }
        
        .section-card {
            background: rgba(255,255,255,0.03);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            border-left: 4px solid;
        }
        .severity-mild { border-color: #ffd93d; }
        .severity-spicy { border-color: #ff8e53; }
        .severity-nuclear { border-color: #ff4444; background: rgba(255,68,68,0.05); }
        
        .section-header {
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 15px;
        }
        .section-name { font-size: 1.2rem; font-weight: bold; color: #fff; }
        .severity-badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: bold;
            text-transform: uppercase;
        }
        .badge-mild { background: #ffd93d; color: #000; }
        .badge-spicy { background: #ff8e53; color: #000; }
        .badge-nuclear { background: #ff4444; color: #fff; }
        
        .roast-text { font-size: 1.1rem; line-height: 1.6; margin-bottom: 15px; color: #ddd; }
        .fix-box {
            background: rgba(0,200,100,0.1);
            border-radius: 10px;
            padding: 15px;
            border-left: 3px solid #00cc66;
        }
        .fix-label { color: #00cc66; font-weight: bold; font-size: 0.9rem; margin-bottom: 5px; }
        .fix-text { color: #aaa; }
        
        .best-line {
            text-align: center;
            font-size: 1.3rem;
            color: #ff6b6b;
            margin: 30px 0;
            padding: 20px;
            background: rgba(255,107,107,0.05);
            border-radius: 15px;
            font-weight: bold;
        }
        
        .shareable-box {
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            border: 2px solid #333;
        }
        .shareable-quote {
            font-size: 1.4rem;
            color: #fff;
            margin-bottom: 15px;
            font-weight: bold;
        }
        .share-btns {
            display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;
        }
        .share-btn {
            padding: 10px 20px;
            border-radius: 25px;
            border: none;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s;
        }
        .share-twitter { background: #1da1f2; color: white; }
        .share-copy { background: #333; color: white; }
        .share-btn:hover { transform: scale(1.05); }
        
        .error-msg {
            background: rgba(255,68,68,0.1);
            border: 1px solid #ff4444;
            border-radius: 10px;
            padding: 20px;
            color: #ff4444;
            text-align: center;
            margin-bottom: 20px;
        }
        
        .model-badge {
            text-align: center;
            color: #666;
            font-size: 0.8rem;
            margin-top: 20px;
        }
        
        footer {
            text-align: center;
            color: #444;
            margin-top: 50px;
            font-size: 0.9rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔥 RoastMyResume</h1>
            <p class="tagline">Upload your resume. Get destroyed. Share the pain. 💀</p>
        </header>
        
        <div class="upload-zone" id="dropZone">
            <div class="upload-icon">📄</div>
            <div class="upload-text">Drop your resume here or click to browse</div>
            <div class="upload-hint">PDF, DOCX, or TXT (max 5MB)</div>
            <input type="file" id="fileInput" accept=".pdf,.docx,.txt">
            <br>
            <button class="btn" id="roastBtn" disabled>🔥 Roast Me</button>
        </div>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Our AI is reading your resume and questioning its life choices...</p>
        </div>
        
        <div class="roast-result" id="result"></div>
        
        <footer>
            <p>Made for Product Hunt 🚀 | No resumes were harmed (they deserved it)</p>
        </footer>
    </div>

    <script>
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');
        const roastBtn = document.getElementById('roastBtn');
        const loading = document.getElementById('loading');
        const result = document.getElementById('result');
        let selectedFile = null;

        dropZone.addEventListener('click', () => fileInput.click());
        
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });
        
        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('dragover');
        });
        
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length) handleFile(files[0]);
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length) handleFile(e.target.files[0]);
        });

        function handleFile(file) {
            selectedFile = file;
            document.querySelector('.upload-text').textContent = file.name;
            roastBtn.disabled = false;
        }

        roastBtn.addEventListener('click', async () => {
            if (!selectedFile) return;
            
            loading.classList.add('active');
            result.classList.remove('active');
            roastBtn.disabled = true;
            
            const formData = new FormData();
            formData.append('resume', selectedFile);
            
            try {
                const res = await fetch('/roast', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();
                
                if (data.error) {
                    result.innerHTML = `<div class="error-msg">💀 ${data.error}</div>`;
                } else {
                    renderRoast(data);
                }
            } catch (err) {
                result.innerHTML = `<div class="error-msg">💀 Something went wrong. Even our servers couldn't handle your resume.</div>`;
            }
            
            loading.classList.remove('active');
            roastBtn.disabled = false;
            result.classList.add('active');
        });

        function renderRoast(data) {
            const score = data.overall_score || 1;
            const scoreClass = score <= 3 ? 'score-low' : score <= 6 ? 'score-mid' : 'score-high';
            
            let html = `
                <div class="score-circle ${scoreClass}">${score}/10</div>
                <div class="headline-roast">"${data.headline_roast || 'Your resume exists. That\\'s the nicest thing I can say.'}"</div>
            `;
            
            if (data.sections && data.sections.length) {
                html += data.sections.map(sec => `
                    <div class="section-card severity-${sec.severity || 'mild'}">
                        <div class="section-header">
                            <span class="section-name">${sec.section_name || 'Unknown Section'}</span>
                            <span class="severity-badge badge-${sec.severity || 'mild'}">${sec.severity || 'mild'}</span>
                        </div>
                        <div class="roast-text">${sec.roast || 'No roast available. Your resume was too boring to roast.'}</div>
                        <div class="fix-box">
                            <div class="fix-label">✅ How to fix it:</div>
                            <div class="fix-text">${sec.fix_it || 'Burn it and start over.'}</div>
                        </div>
                    </div>
                `).join('');
            }
            
            html += `
                <div class="best-line">💬 "${data.best_line || 'Your resume made me speechless. Not in a good way.'}"</div>
                <div class="shareable-box">
                    <div class="shareable-quote">"${data.shareable_quote || 'My resume got roasted. 💀'}"</div>
                    <div class="share-btns">
                        <button class="share-btn share-twitter" onclick="shareTwitter('${encodeURIComponent(data.shareable_quote || '')}')">🐦 Tweet This</button>
                        <button class="share-btn share-copy" onclick="copyQuote('${encodeURIComponent(data.shareable_quote || '')}')">📋 Copy</button>
                    </div>
                </div>
            `;
            
            if (data._model_used) {
                html += `<div class="model-badge">Roasted by: ${data._model_used}</div>`;
            }
            
            result.innerHTML = html;
        }

        function shareTwitter(text) {
            const url = `https://twitter.com/intent/tweet?text=${text}&url=https://roastmyresume.com`;
            window.open(url, '_blank');
        }

        function copyQuote(text) {
            navigator.clipboard.writeText(decodeURIComponent(text) + ' 🔥 RoastMyResume.com');
            alert('Copied! Now go flex on Twitter. 💀');
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/roast', methods=['POST'])
def roast():
    if 'resume' not in request.files:
        return jsonify({"error": "No file uploaded. Did you forget your resume or your dignity?"}), 400
    
    file = request.files['resume']
    if file.filename == '':
        return jsonify({"error": "Empty filename. Like your achievements section."}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. We only accept PDF, DOCX, or TXT. Not whatever that was."}), 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    try:
        resume_text = extract_text(filepath, filename)
        if not resume_text or len(resume_text) < 50:
            return jsonify({"error": "Your resume is too short or unreadable. Like your job prospects."}), 400
        
        roast_data = roast_resume(resume_text)
        return jsonify(roast_data)
        
    except Exception as e:
        return jsonify({"error": f"Something went wrong: {str(e)}"}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)