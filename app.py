# app.py
import os
import json
from flask import Flask, request, jsonify, render_template_string
from werkzeug.utils import secure_filename
from groq import Groq
import PyPDF2
import docx

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

client = Groq(api_key=os.environ.get('GROQ_API_KEY'))
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
            for page in PyPDF2.PdfReader(f).pages:
                text += page.extract_text() or ""
    elif ext == 'docx':
        for para in docx.Document(file_path).paragraphs:
            text += para.text + "\n"
    elif ext == 'txt':
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
    return text.strip()

def roast_resume(resume_text):
    system_prompt = """You are a brutally honest, savage career coach who roasts resumes. Format response as JSON: {"overall_score": 1-10, "headline_roast": "...", "sections": [{"section_name": "...", "roast": "...", "severity": "mild|spicy|nuclear", "fix_it": "..."}], "best_line": "...", "shareable_quote": "..."}. Be specific, funny, savage but helpful. Use emojis. Reference actual resume content. No sugarcoating."""
    user_prompt = f"Roast this resume:\n\n{resume_text[:4000]}"
    
    for model in [PRIMARY_MODEL, FALLBACK_MODEL]:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.9,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )
            data = json.loads(response.choices[0].message.content)
            data["_model_used"] = model
            return data
        except:
            continue
    
    return {"overall_score": 1, "headline_roast": "Even AI gave up on your resume.", "sections": [{"section_name": "Everything", "roast": "Both AI models crashed. Legendary.", "severity": "nuclear", "fix_it": "Burn it."}], "best_line": "Your resume broke two AIs. 🏆", "shareable_quote": "My resume broke TWO AIs. 💀", "_model_used": "none"}

HTML = '''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🔥 RoastMyResume</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#0a0a0f;color:#e0e0e0;min-height:100vh}
.container{max-width:800px;margin:0 auto;padding:40px 20px}
header{text-align:center;margin-bottom:40px}
h1{font-size:3rem;background:linear-gradient(135deg,#ff6b6b,#ffd93d);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.tagline{color:#888;margin-top:10px}
.upload-zone{border:3px dashed #ff6b6b;border-radius:20px;padding:60px 40px;text-align:center;background:rgba(255,107,107,0.05);cursor:pointer;transition:all .3s}
.upload-zone:hover{border-color:#ffd93d;transform:scale(1.02)}
.upload-zone input{display:none}
.upload-icon{font-size:4rem}
.upload-text{font-size:1.3rem;color:#ccc;margin:15px 0}
.upload-hint{color:#666;font-size:.9rem}
.btn{background:linear-gradient(135deg,#ff6b6b,#ff8e53);border:none;padding:15px 40px;border-radius:50px;color:#fff;font-size:1.1rem;font-weight:bold;cursor:pointer;margin-top:20px;transition:all .3s}
.btn:hover{transform:translateY(-2px);box-shadow:0 10px 30px rgba(255,107,107,0.3)}
.btn:disabled{opacity:.5;cursor:not-allowed}
.loading{display:none;text-align:center;padding:40px}
.loading.active{display:block}
.spinner{width:60px;height:60px;border:4px solid #333;border-top-color:#ff6b6b;border-radius:50%;animation:spin 1s linear infinite;margin:0 auto 20px}
@keyframes spin{to{transform:rotate(360deg)}}
.result{display:none}
.result.active{display:block;animation:fadeIn .5s}
@keyframes fadeIn{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
.score{width:120px;height:120px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:3rem;font-weight:bold;margin:0 auto 20px}
.s1{background:linear-gradient(135deg,#ff4444,#cc0000)}
.s2{background:linear-gradient(135deg,#ffaa00,#ff6600)}
.s3{background:linear-gradient(135deg,#00cc66,#009944)}
.headline{text-align:center;font-size:1.5rem;color:#ffd93d;margin-bottom:30px;font-style:italic}
.card{background:rgba(255,255,255,0.03);border-radius:15px;padding:25px;margin-bottom:20px;border-left:4px solid}
.mild{border-color:#ffd93d}
.spicy{border-color:#ff8e53}
.nuclear{border-color:#ff4444;background:rgba(255,68,68,0.05)}
.card-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:15px}
.card-title{font-size:1.2rem;font-weight:bold;color:#fff}
.badge{padding:4px 12px;border-radius:20px;font-size:.8rem;font-weight:bold;text-transform:uppercase}
.b1{background:#ffd93d;color:#000}
.b2{background:#ff8e53;color:#000}
.b3{background:#ff4444;color:#fff}
.roast-text{font-size:1.1rem;line-height:1.6;margin-bottom:15px;color:#ddd}
.fix{background:rgba(0,200,100,0.1);border-radius:10px;padding:15px;border-left:3px solid #00cc66}
.fix-label{color:#00cc66;font-weight:bold;font-size:.9rem}
.fix-text{color:#aaa;margin-top:5px}
.best-line{text-align:center;font-size:1.3rem;color:#ff6b6b;margin:30px 0;padding:20px;background:rgba(255,107,107,0.05);border-radius:15px;font-weight:bold}
.share-box{background:linear-gradient(135deg,#1a1a2e,#16213e);border-radius:15px;padding:25px;text-align:center;border:2px solid #333}
.share-quote{font-size:1.4rem;color:#fff;margin-bottom:15px;font-weight:bold}
.share-btns{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}
.share-btn{padding:10px 20px;border-radius:25px;border:none;cursor:pointer;font-weight:bold;color:#fff}
.tw{background:#1da1f2}
.cp{background:#333}
.error{background:rgba(255,68,68,0.1);border:1px solid #ff4444;border-radius:10px;padding:20px;color:#ff4444;text-align:center;margin-bottom:20px}
.model-info{text-align:center;color:#666;font-size:.8rem;margin-top:20px}
footer{text-align:center;color:#444;margin-top:50px;font-size:.9rem}
</style>
</head>
<body>
<div class="container">
<header><h1>🔥 RoastMyResume</h1><p class="tagline">Upload your resume. Get destroyed. Share the pain. 💀</p></header>
<div class="upload-zone" id="dz"><div class="upload-icon">📄</div><div class="upload-text" id="ut">Drop your resume or click to browse</div><div class="upload-hint">PDF, DOCX, or TXT (max 5MB)</div><input type="file" id="fi" accept=".pdf,.docx,.txt"><br><button class="btn" id="rb" disabled>🔥 Roast Me</button></div>
<div class="loading" id="ld"><div class="spinner"></div><p>Our AI is reading your resume and questioning its life choices...</p></div>
<div class="result" id="rs"></div>
<footer><p>Made for Product Hunt 🚀 | No resumes were harmed (they deserved it)</p></footer>
</div>
<script>
const dz=document.getElementById('dz'),fi=document.getElementById('fi'),rb=document.getElementById('rb'),ld=document.getElementById('ld'),rs=document.getElementById('rs'),ut=document.getElementById('ut');
let sf=null;
dz.onclick=()=>fi.click();
dz.ondragover=e=>{e.preventDefault();dz.style.borderColor='#ffd93d'};
dz.ondragleave=()=>{dz.style.borderColor='#ff6b6b'};
dz.ondrop=e=>{e.preventDefault();dz.style.borderColor='#ff6b6b';if(e.dataTransfer.files.length)hf(e.dataTransfer.files[0])};
fi.onchange=e=>{if(e.target.files.length)hf(e.target.files[0])};
function hf(f){sf=f;ut.textContent=f.name;rb.disabled=false}
rb.onclick=async()=>{if(!sf)return;ld.classList.add('active');rs.classList.remove('active');rb.disabled=true;const fd=new FormData();fd.append('resume',sf);try{const r=await fetch('/roast',{method:'POST',body:fd});const d=await r.json();rs.innerHTML=d.error?`<div class="error">💀 ${d.error}</div>`:render(d)}catch(e){rs.innerHTML='<div class="error">💀 Something went wrong. Even our servers couldn\'t handle your resume.</div>'}ld.classList.remove('active');rb.disabled=false;rs.classList.add('active')};
function render(d){const s=d.overall_score||1,sc=s<=3?'s1':s<=6?'s2':'s3';let h=`<div class="score ${sc}">${s}/10</div><div class="headline">"${d.headline_roast||'Your resume exists. That\'s the nicest thing I can say.'}"</div>`;if(d.sections&&d.sections.length)h+=d.sections.map(x=>`<div class="card ${x.severity||'mild'}"><div class="card-header"><span class="card-title">${x.section_name||'Unknown'}</span><span class="badge b${(x.severity==='spicy'?2:x.severity==='nuclear'?3:1)}">${x.severity||'mild'}</span></div><div class="roast-text">${x.roast||'Too boring to roast.'}</div><div class="fix"><div class="fix-label">✅ How to fix it:</div><div class="fix-text">${x.fix_it||'Burn it and start over.'}</div></div></div>`).join('');h+=`<div class="best-line">💬 "${d.best_line||'Your resume made me speechless. Not in a good way.'}"</div><div class="share-box"><div class="share-quote">"${d.shareable_quote||'My resume got roasted. 💀'}"</div><div class="share-btns"><button class="share-btn tw" onclick="window.open('https://twitter.com/intent/tweet?text=${encodeURIComponent(d.shareable_quote||'')}&url=https://roastmyresume.com','_blank')">🐦 Tweet</button><button class="share-btn cp" onclick="navigator.clipboard.writeText('${(d.shareable_quote||'').replace(/'/g,"\\'")} 🔥 RoastMyResume.com');alert('Copied! 💀')">📋 Copy</button></div></div>`;if(d._model_used)h+=`<div class="model-info">Roasted by: ${d._model_used}</div>`;return h}
</script>
</body>
</html>'''

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/roast', methods=['POST'])
def roast():
    if 'resume' not in request.files:
        return jsonify({"error": "No file uploaded. Did you forget your resume or your dignity?"}), 400
    file = request.files['resume']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file. We only accept PDF, DOCX, or TXT."}), 400
    fn = secure_filename(file.filename)
    fp = '/tmp/' + fn
    file.save(fp)
    try:
        text = extract_text(fp, fn)
        if not text or len(text) < 50:
            return jsonify({"error": "Resume too short or unreadable. Like your job prospects."}), 400
        return jsonify(roast_resume(text))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(fp):
            os.remove(fp)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)