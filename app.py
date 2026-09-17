"""
app.py - Web Application for Dynamic Internship Notebook PDF Filling
"""

import os
import io
import json
from datetime import datetime
from flask import Flask, request, send_file, render_template_string, jsonify
from fill_notebook import process_internship_notebook, TemplateInspector
import fitz

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB limit

DEFAULT_PDF_PATH = os.path.join(os.path.dirname(__file__), "EEE-Internship Notebook.pdf")
DEFAULT_JSON_PATH = os.path.join(os.path.dirname(__file__), "entries.json")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Staj Defteri Doldurucu | AI Supported Dynamic PDF Filler</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #0b0f19;
            --surface: #131b2e;
            --surface-card: #182238;
            --border: #233252;
            --primary: #4f46e5;
            --primary-hover: #6366f1;
            --primary-glow: rgba(99, 102, 241, 0.25);
            --accent: #06b6d4;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --success: #10b981;
            --warning: #f59e0b;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: var(--bg);
            color: var(--text);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            background-image: 
                radial-gradient(at 0% 0%, rgba(79, 70, 229, 0.15) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(6, 182, 212, 0.1) 0px, transparent 50%);
        }

        header {
            padding: 2.5rem 1.5rem 1.5rem;
            text-align: center;
        }

        .badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.35rem 0.85rem;
            border-radius: 9999px;
            background: rgba(99, 102, 241, 0.12);
            border: 1px solid rgba(99, 102, 241, 0.3);
            color: #818cf8;
            font-size: 0.825rem;
            font-weight: 600;
            margin-bottom: 1rem;
            letter-spacing: 0.02em;
        }

        h1 {
            font-size: 2.5rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            background: linear-gradient(135deg, #ffffff 40%, #94a3b8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.75rem;
        }

        p.subtitle {
            color: var(--text-muted);
            font-size: 1.05rem;
            max-width: 620px;
            margin: 0 auto;
            line-height: 1.6;
        }

        main {
            max-width: 960px;
            width: 100%;
            margin: 0 auto 3rem;
            padding: 0 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 1.75rem;
        }

        .glass-panel {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 1.25rem;
            padding: 2rem;
            box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(12px);
        }

        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
        }

        @media (max-width: 768px) {
            .grid-2 {
                grid-template-columns: 1fr;
            }
        }

        .upload-card {
            background: var(--surface-card);
            border: 2px dashed var(--border);
            border-radius: 1rem;
            padding: 1.75rem;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s ease;
            position: relative;
        }

        .upload-card:hover, .upload-card.dragover {
            border-color: var(--primary);
            background: rgba(99, 102, 241, 0.05);
            box-shadow: 0 0 25px var(--primary-glow);
        }

        .upload-card input[type="file"] {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            opacity: 0;
            cursor: pointer;
        }

        .icon-circle {
            width: 52px;
            height: 52px;
            border-radius: 1rem;
            background: rgba(99, 102, 241, 0.15);
            color: #818cf8;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 1rem;
        }

        .card-title {
            font-size: 1.05rem;
            font-weight: 700;
            margin-bottom: 0.35rem;
        }

        .card-desc {
            font-size: 0.825rem;
            color: var(--text-muted);
            line-height: 1.4;
        }

        .file-status {
            margin-top: 0.85rem;
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--accent);
            display: none;
            word-break: break-all;
        }

        .config-bar {
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
            align-items: center;
            justify-content: space-between;
            padding-top: 1.5rem;
            border-top: 1px solid var(--border);
            margin-top: 1.5rem;
        }

        .field-group {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        label {
            font-size: 0.875rem;
            font-weight: 600;
            color: var(--text-muted);
        }

        input[type="date"] {
            background: var(--surface-card);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 0.6rem 0.9rem;
            border-radius: 0.6rem;
            font-family: inherit;
            font-size: 0.9rem;
            outline: none;
        }

        input[type="date"]:focus {
            border-color: var(--primary);
        }

        .btn {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.75rem 1.75rem;
            border-radius: 0.75rem;
            font-size: 0.95rem;
            font-weight: 700;
            cursor: pointer;
            border: none;
            transition: all 0.2s ease;
            text-decoration: none;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--primary) 0%, #4338ca 100%);
            color: white;
            box-shadow: 0 10px 25px -5px var(--primary-glow);
        }

        .btn-primary:hover {
            background: linear-gradient(135deg, var(--primary-hover) 0%, var(--primary) 100%);
            transform: translateY(-1px);
        }

        .btn-secondary {
            background: var(--surface-card);
            border: 1px solid var(--border);
            color: var(--text-muted);
            font-size: 0.85rem;
            padding: 0.5rem 1rem;
        }

        .btn-secondary:hover {
            color: var(--text);
            border-color: var(--text-muted);
        }

        .terminal-panel {
            background: #060911;
            border: 1px solid var(--border);
            border-radius: 1rem;
            padding: 1.25rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.825rem;
            color: #38bdf8;
            min-height: 180px;
            max-height: 280px;
            overflow-y: auto;
            line-height: 1.6;
        }

        .terminal-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.75rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .log-entry {
            margin-bottom: 0.25rem;
            white-space: pre-wrap;
        }

        .log-entry.success { color: #34d399; }
        .log-entry.warning { color: #fbbf24; }
        .log-entry.info { color: #93c5fd; }

        footer {
            text-align: center;
            padding: 2rem;
            color: var(--text-muted);
            font-size: 0.825rem;
            margin-top: auto;
        }

        footer a {
            color: var(--text);
            text-decoration: none;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <header>
        <div class="badge">
            <span>✨</span> Dinamik PDF Analiz & Enjeksiyon Motoru
        </div>
        <h1>Staj Defteri Doldurucu</h1>
        <p class="subtitle">
            Şablon sayfaları otomatik incelenir. İster varsayılan şablonu kullanın, ister kendi üniversite defterinizi yükleyin; tarihler, devam çizelgesi ve günlük raporlar sıfır taşma ile doldurulur.
        </p>
    </header>

    <main>
        <div class="glass-panel">
            <form id="fillForm">
                <div class="grid-2">
                    <!-- JSON Upload -->
                    <div class="upload-card" id="jsonCard">
                        <input type="file" id="jsonInput" name="json_file" accept=".json">
                        <div class="icon-circle">📄</div>
                        <div class="card-title">1. Staj Günlükleri (JSON)</div>
                        <div class="card-desc">Gerekli 30 günlük içerikleri içeren <code>entries.json</code> dosyasını seçin veya sürükleyin.</div>
                        <div class="file-status" id="jsonStatus"></div>
                        <div style="margin-top: 1rem;">
                            <button type="button" class="btn btn-secondary" id="useDefaultJsonBtn">Örnek JSON'ı Kullan</button>
                        </div>
                    </div>

                    <!-- PDF Template Upload -->
                    <div class="upload-card" id="pdfCard">
                        <input type="file" id="pdfInput" name="pdf_file" accept=".pdf">
                        <div class="icon-circle">📑</div>
                        <div class="card-title">2. Şablon Defter (PDF)</div>
                        <div class="card-desc">Doldurulacak boş staj defteri PDF'ini yükleyin (Boş bırakılırsa varsayılan EEE şablonu kullanılır).</div>
                        <div class="file-status" id="pdfStatus"></div>
                        <div style="margin-top: 1rem;">
                            <button type="button" class="btn btn-secondary" id="useDefaultPdfBtn">Varsayılan Şablonu Kullan</button>
                        </div>
                    </div>
                </div>

                <div class="config-bar">
                    <div class="field-group">
                        <label for="startDate">Başlangıç Tarihi (Pzt):</label>
                        <input type="date" id="startDate" name="start_date" value="2026-08-10">
                    </div>

                    <div style="display: flex; gap: 0.75rem;">
                        <a href="/api/sample-json" class="btn btn-secondary" download="entries.example.json">📥 Örnek JSON İndir</a>
                        <button type="submit" class="btn btn-primary" id="submitBtn">
                            <span>🚀</span> Defteri Doldur ve İndir
                        </button>
                    </div>
                </div>
            </form>
        </div>

        <div class="glass-panel" style="padding: 1.5rem;">
            <div class="terminal-header">
                <span>Dinamik Analiz & İşlem Konsolu</span>
                <span id="logStatus">Hazır</span>
            </div>
            <div class="terminal-panel" id="terminal">
                <div class="log-entry info">[Sistem] Dinamik Şablon İnceleme Motoru aktif.</div>
                <div class="log-entry info">[Bilgi] JSON ve PDF yükleyip "Defteri Doldur" butonuna tıklayınız.</div>
            </div>
        </div>
    </main>

    <footer>
        Geliştirici: <a href="https://github.com/DevranTheDeveloper" target="_blank">Devran Sever</a> • PyMuPDF & Times New Roman ile hazırlanmıştır.
    </footer>

    <script>
        const jsonInput = document.getElementById('jsonInput');
        const pdfInput = document.getElementById('pdfInput');
        const jsonStatus = document.getElementById('jsonStatus');
        const pdfStatus = document.getElementById('pdfStatus');
        const terminal = document.getElementById('terminal');
        const logStatus = document.getElementById('logStatus');
        const submitBtn = document.getElementById('submitBtn');

        let useDefaultJson = false;
        let useDefaultPdf = true;

        jsonInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                jsonStatus.style.display = 'block';
                jsonStatus.textContent = `✓ Seçildi: ${e.target.files[0].name}`;
                useDefaultJson = false;
            }
        });

        pdfInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                pdfStatus.style.display = 'block';
                pdfStatus.textContent = `✓ Seçildi: ${e.target.files[0].name}`;
                useDefaultPdf = false;
            }
        });

        document.getElementById('useDefaultJsonBtn').addEventListener('click', () => {
            useDefaultJson = true;
            jsonInput.value = '';
            jsonStatus.style.display = 'block';
            jsonStatus.textContent = '✓ Yerleşik örnek entries.json seçildi.';
        });

        document.getElementById('useDefaultPdfBtn').addEventListener('click', () => {
            useDefaultPdf = true;
            pdfInput.value = '';
            pdfStatus.style.display = 'block';
            pdfStatus.textContent = '✓ Yerleşik EEE-Internship Notebook.pdf seçildi.';
        });

        function addLog(msg, type='info') {
            const div = document.createElement('div');
            div.className = `log-entry ${type}`;
            div.textContent = msg;
            terminal.appendChild(div);
            terminal.scrollTop = terminal.scrollHeight;
        }

        document.getElementById('fillForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            if (!jsonInput.files.length && !useDefaultJson) {
                alert('Lütfen bir entries.json dosyası seçin veya "Örnek JSON\'ı Kullan" butonuna basın.');
                return;
            }

            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span>⏳</span> İşleniyor...';
            logStatus.textContent = 'İşleniyor...';

            terminal.innerHTML = '';
            addLog('[+] İstek sunucuya gönderiliyor...', 'info');

            const formData = new FormData();
            if (jsonInput.files.length > 0) {
                formData.append('json_file', jsonInput.files[0]);
            } else {
                formData.append('use_default_json', 'true');
            }

            if (pdfInput.files.length > 0) {
                formData.append('pdf_file', pdfInput.files[0]);
            } else {
                formData.append('use_default_pdf', 'true');
            }

            formData.append('start_date', document.getElementById('startDate').value);

            try {
                const response = await fetch('/api/fill', {
                    method: 'POST',
                    body: formData
                });

                const logsHeader = response.headers.get('X-Process-Logs');
                if (logsHeader) {
                    const logs = JSON.parse(decodeURIComponent(escape(atob(logsHeader))));
                    logs.forEach(l => addLog(l, l.includes('[!]') ? 'warning' : 'success'));
                }

                if (!response.ok) {
                    const err = await response.json();
                    addLog(`[HATA] ${err.error || 'İşlem başarısız'}`, 'warning');
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<span>🚀</span> Defteri Doldur ve İndir';
                    logStatus.textContent = 'Hata';
                    return;
                }

                const blob = await response.blob();
                const downloadUrl = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = downloadUrl;
                a.download = 'Doldurulmus_Staj_Defteri.pdf';
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(downloadUrl);

                addLog('[✓] PDF başarıyla üretildi ve indirme başlatıldı!', 'success');
                logStatus.textContent = 'Tamamlandı';
            } catch (err) {
                addLog(`[Bağlantı Hatası] ${err.message}`, 'warning');
                logStatus.textContent = 'Hata';
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<span>🚀</span> Defteri Doldur ve İndir';
            }
        });
    </script>
</body>
</html>
"""

import base64

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/sample-json")
def sample_json():
    if os.path.isfile(DEFAULT_JSON_PATH):
        return send_file(DEFAULT_JSON_PATH, as_attachment=True, download_name="entries.json", mimetype="application/json")
    return jsonify({"error": "Sample JSON not found"}), 404

@app.route("/api/sample-pdf")
def sample_pdf():
    if os.path.isfile(DEFAULT_PDF_PATH):
        return send_file(DEFAULT_PDF_PATH, as_attachment=True, download_name="EEE-Internship Notebook.pdf", mimetype="application/pdf")
    return jsonify({"error": "Sample PDF not found"}), 404

@app.route("/api/fill", methods=["POST"])
def fill_pdf_endpoint():
    try:
        # 1. Resolve JSON
        if request.form.get("use_default_json") == "true" or "json_file" not in request.files:
            if not os.path.isfile(DEFAULT_JSON_PATH):
                return jsonify({"error": "Default entries.json not found on server."}), 400
            with open(DEFAULT_JSON_PATH, "r", encoding="utf-8") as f:
                entries = json.load(f)
        else:
            json_file = request.files["json_file"]
            content = json_file.read().decode("utf-8")
            entries = json.loads(content)

        # 2. Resolve PDF
        if request.form.get("use_default_pdf") == "true" or "pdf_file" not in request.files:
            if not os.path.isfile(DEFAULT_PDF_PATH):
                return jsonify({"error": "Default template PDF not found on server."}), 400
            with open(DEFAULT_PDF_PATH, "rb") as f:
                pdf_bytes = f.read()
        else:
            pdf_file = request.files["pdf_file"]
            pdf_bytes = pdf_file.read()

        start_date_str = request.form.get("start_date", "2026-08-10")

        # Process with dynamic inspection engine
        output_bytes, logs = process_internship_notebook(pdf_bytes, entries, start_date_str)

        # Encode logs safely into header
        logs_b64 = base64.b64encode(json.dumps(logs).encode('utf-8')).decode('utf-8')

        response = send_file(
            io.BytesIO(output_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name="Doldurulmus_Staj_Defteri.pdf"
        )
        response.headers["X-Process-Logs"] = logs_b64
        response.headers["Access-Control-Expose-Headers"] = "X-Process-Logs"
        return response

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"Starting Internship Notebook Filler Web Studio on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
