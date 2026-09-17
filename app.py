"""
app.py - Web Application for Dynamic Internship Notebook PDF Filling
"""

import os
import io
import time
import json
import uuid
import threading
from datetime import datetime
from flask import Flask, request, send_file, render_template_string, jsonify
from fill_notebook import process_internship_notebook, TemplateInspector

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB limit

DEFAULT_PDF_PATH = os.path.join(os.path.dirname(__file__), "EEE-Internship Notebook.pdf")
DEFAULT_JSON_PATH = os.path.join(os.path.dirname(__file__), "entries.json")

# In-memory store for generated PDF files: { token: { 'bytes': b'...', 'filename': '...', 'created_at': timestamp } }
GENERATED_CACHE = {}
CACHE_LOCK = threading.Lock()

def cleanup_old_cache():
    """Removes cached PDFs older than 1 hour."""
    now = time.time()
    with CACHE_LOCK:
        expired = [token for token, data in GENERATED_CACHE.items() if now - data.get('created_at', 0) > 3600]
        for token in expired:
            GENERATED_CACHE.pop(token, None)


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Staj Defteri Doldurucu | Dinamik PDF İşleme Stüdyosu</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #0b0f19;
            --surface: #131b2e;
            --surface-card: #182238;
            --surface-hover: #1e2b45;
            --border: #233252;
            --border-active: #4f46e5;
            --primary: #4f46e5;
            --primary-hover: #6366f1;
            --primary-glow: rgba(99, 102, 241, 0.28);
            --accent: #06b6d4;
            --success: #10b981;
            --success-glow: rgba(16, 185, 129, 0.25);
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --warning: #f59e0b;
            --danger: #ef4444;
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
                radial-gradient(at 0% 0%, rgba(79, 70, 229, 0.16) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(6, 182, 212, 0.12) 0px, transparent 50%);
        }

        header {
            padding: 2.2rem 1.5rem 1.2rem;
            text-align: center;
        }

        .badge-brand {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.35rem 0.9rem;
            border-radius: 9999px;
            background: rgba(99, 102, 241, 0.12);
            border: 1px solid rgba(99, 102, 241, 0.3);
            color: #818cf8;
            font-size: 0.825rem;
            font-weight: 600;
            margin-bottom: 0.85rem;
        }

        h1 {
            font-size: 2.3rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            background: linear-gradient(135deg, #ffffff 30%, #cbd5e1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }

        p.subtitle {
            color: var(--text-muted);
            font-size: 0.98rem;
            max-width: 680px;
            margin: 0 auto;
            line-height: 1.55;
        }

        main {
            max-width: 980px;
            width: 100%;
            margin: 0 auto 3rem;
            padding: 0 1.25rem;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        .glass-panel {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 1.25rem;
            padding: 1.75rem;
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

        /* Upload Cards */
        .upload-card {
            background: var(--surface-card);
            border: 2px dashed var(--border);
            border-radius: 1rem;
            padding: 1.4rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: all 0.25s ease;
            position: relative;
            min-height: 220px;
        }

        .upload-card:hover {
            border-color: rgba(99, 102, 241, 0.5);
            background: var(--surface-hover);
        }

        .upload-card.loaded {
            border-color: var(--success);
            border-style: solid;
            background: rgba(16, 185, 129, 0.05);
            box-shadow: 0 0 20px rgba(16, 185, 129, 0.1);
        }

        .upload-card.dragover {
            border-color: var(--accent);
            background: rgba(6, 182, 212, 0.08);
            transform: scale(1.01);
        }

        .card-header {
            display: flex;
            align-items: center;
            gap: 0.85rem;
            margin-bottom: 0.85rem;
        }

        .icon-box {
            width: 42px;
            height: 42px;
            border-radius: 0.75rem;
            background: rgba(99, 102, 241, 0.15);
            color: #818cf8;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
            flex-shrink: 0;
        }

        .upload-card.loaded .icon-box {
            background: rgba(16, 185, 129, 0.18);
            color: #34d399;
        }

        .card-title {
            font-size: 1.05rem;
            font-weight: 700;
        }

        .card-sub {
            font-size: 0.8rem;
            color: var(--text-muted);
        }

        /* Dropzone */
        .dropzone {
            border: 1px dashed rgba(255, 255, 255, 0.12);
            border-radius: 0.75rem;
            padding: 1rem;
            text-align: center;
            margin-bottom: 0.85rem;
            cursor: pointer;
            transition: all 0.2s;
            background: rgba(0, 0, 0, 0.2);
        }

        .dropzone:hover {
            border-color: var(--accent);
            background: rgba(6, 182, 212, 0.05);
        }

        .dropzone-text {
            font-size: 0.825rem;
            color: var(--text-muted);
        }

        .dropzone-text strong {
            color: #38bdf8;
        }

        /* File Loaded Box */
        .file-info-box {
            display: none;
            background: #090f1d;
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-radius: 0.75rem;
            padding: 0.75rem 0.9rem;
            margin-bottom: 0.85rem;
        }

        .file-info-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.35rem;
        }

        .file-name {
            font-weight: 700;
            font-size: 0.875rem;
            color: #f8fafc;
            display: flex;
            align-items: center;
            gap: 0.4rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 210px;
        }

        .file-size {
            font-size: 0.75rem;
            color: var(--text-muted);
            font-family: 'JetBrains Mono', monospace;
        }

        .file-stat-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.2rem 0.6rem;
            border-radius: 9999px;
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            font-size: 0.75rem;
            font-weight: 600;
        }

        .card-actions {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }

        /* Student & Internship Details Form Section */
        .section-title-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1.25rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid var(--border);
        }

        .section-title {
            font-size: 1.15rem;
            font-weight: 700;
            color: #f8fafc;
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }

        .section-sub {
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 0.25rem;
        }

        .form-group-title {
            font-size: 0.875rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #818cf8;
            margin-bottom: 0.85rem;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }

        .input-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.25rem;
        }

        @media (max-width: 900px) {
            .input-grid {
                grid-template-columns: 1fr;
            }
        }

        .field-group-card {
            background: rgba(19, 27, 46, 0.7);
            border: 1px solid var(--border);
            border-radius: 0.85rem;
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            gap: 0.85rem;
            transition: border-color 0.2s, box-shadow 0.2s;
        }

        .field-group-card:hover {
            border-color: rgba(99, 102, 241, 0.4);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        }

        .field-col {
            display: flex;
            flex-direction: column;
            gap: 0.85rem;
        }

        .form-row-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.75rem;
        }

        @media (max-width: 600px) {
            .form-row-2 {
                grid-template-columns: 1fr;
            }
        }

        .form-field {
            display: flex;
            flex-direction: column;
            gap: 0.35rem;
        }

        .form-field label {
            font-size: 0.8rem;
            font-weight: 600;
            color: #cbd5e1;
        }

        .form-field input,
        .form-field textarea {
            background: var(--surface-card);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 0.65rem 0.85rem;
            border-radius: 0.6rem;
            font-family: inherit;
            font-size: 0.875rem;
            outline: none;
            transition: all 0.2s;
        }

        .form-field textarea {
            resize: vertical;
            min-height: 52px;
            line-height: 1.35;
        }

        .form-field input:focus,
        .form-field textarea:focus {
            border-color: var(--primary);
            box-shadow: 0 0 10px var(--primary-glow);
            background: #19253d;
        }

        .form-field .field-hint {
            font-size: 0.725rem;
            color: #64748b;
        }

        /* Buttons */
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            padding: 0.65rem 1.25rem;
            border-radius: 0.65rem;
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
            border: none;
            transition: all 0.2s ease;
            text-decoration: none;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--primary) 0%, #4338ca 100%);
            color: white;
            box-shadow: 0 10px 20px -5px var(--primary-glow);
            padding: 0.8rem 2rem;
            font-size: 1rem;
            font-weight: 700;
        }

        .btn-primary:hover:not(:disabled) {
            background: linear-gradient(135deg, var(--primary-hover) 0%, var(--primary) 100%);
            transform: translateY(-1px);
        }

        .btn-secondary {
            background: var(--surface-card);
            border: 1px solid var(--border);
            color: var(--text-muted);
            font-size: 0.8rem;
            padding: 0.45rem 0.8rem;
        }

        .btn-secondary:hover {
            color: var(--text);
            border-color: var(--text-muted);
            background: rgba(255, 255, 255, 0.05);
        }

        .btn-success {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            font-weight: 700;
            padding: 0.85rem 2rem;
            font-size: 1.05rem;
            box-shadow: 0 10px 25px -5px var(--success-glow);
        }

        .btn-success:hover {
            background: linear-gradient(135deg, #34d399 0%, #10b981 100%);
            transform: translateY(-2px);
            box-shadow: 0 12px 30px -5px var(--success-glow);
        }

        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none !important;
        }

        /* Action Footer Bar */
        .action-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            padding-top: 1.5rem;
            border-top: 1px solid var(--border);
            margin-top: 1.5rem;
            flex-wrap: wrap;
        }

        /* Step 2: Result & Download Card */
        #resultContainer {
            display: none;
            background: linear-gradient(145deg, #102436 0%, #0f1d33 100%);
            border: 2px solid #10b981;
            border-radius: 1.25rem;
            padding: 2rem;
            text-align: center;
            box-shadow: 0 25px 50px -12px rgba(16, 185, 129, 0.25);
            animation: slideDown 0.35s ease;
        }

        @keyframes slideDown {
            from { opacity: 0; transform: translateY(-15px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .result-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.35rem 0.9rem;
            border-radius: 9999px;
            background: rgba(16, 185, 129, 0.2);
            color: #34d399;
            font-size: 0.85rem;
            font-weight: 700;
            margin-bottom: 0.75rem;
        }

        .result-title {
            font-size: 1.6rem;
            font-weight: 800;
            margin-bottom: 0.5rem;
            color: #ffffff;
        }

        .result-desc {
            font-size: 0.95rem;
            color: #94a3b8;
            max-width: 600px;
            margin: 0 auto 1.5rem;
            line-height: 1.5;
        }

        .result-stats {
            display: flex;
            justify-content: center;
            gap: 1.25rem;
            margin-bottom: 1.75rem;
            flex-wrap: wrap;
        }

        .stat-pill {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 0.5rem 1rem;
            border-radius: 0.75rem;
            font-size: 0.85rem;
            color: #e2e8f0;
        }

        .result-buttons {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 1rem;
            flex-wrap: wrap;
        }

        /* Terminal Panel */
        .terminal-panel {
            background: #060911;
            border: 1px solid var(--border);
            border-radius: 1rem;
            padding: 1.25rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.825rem;
            color: #38bdf8;
            min-height: 160px;
            max-height: 260px;
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
        .log-entry.danger { color: #f87171; }

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
        <div class="badge-brand">
            <span>✨</span> Dinamik PDF Analiz & Enjeksiyon Motoru
        </div>
        <h1>Staj Defteri Doldurucu</h1>
        <p class="subtitle">
            Tüm idari kapak ve onay sayfaları, devam çizelgesi ve 30 günlük raporlar girdiğiniz bilgilerle Times New Roman fontu ile milimetrik doldurulur.
        </p>
    </header>

    <main>
        <!-- Step 1: Input Setup -->
        <div class="glass-panel" id="inputPanel">
            <!-- 1. File Uploads -->
            <div class="grid-2" style="margin-bottom: 1.75rem;">
                <!-- JSON Upload Card -->
                <div class="upload-card" id="jsonCard">
                    <div>
                        <div class="card-header">
                            <div class="icon-box" id="jsonIcon">📄</div>
                            <div>
                                <div class="card-title">1. Staj Günlükleri (JSON)</div>
                                <div class="card-sub" id="jsonSub">30 günlük rapor verisi</div>
                            </div>
                        </div>

                        <div class="dropzone" id="jsonDropzone">
                            <div class="dropzone-text">
                                <div>📁 <strong>JSON Dosyası Seç</strong> veya sürükle</div>
                                <div style="font-size: 0.75rem; margin-top: 0.25rem; color: #64748b;">(Örnek: entries.json)</div>
                            </div>
                        </div>

                        <div class="file-info-box" id="jsonInfoBox">
                            <div class="file-info-row">
                                <span class="file-name" id="jsonFileName">dosya.json</span>
                                <span class="file-size" id="jsonFileSize">0 KB</span>
                            </div>
                            <div class="file-stat-pill" id="jsonDaysPill">✓ 30 Günlük Veri Hazır</div>
                        </div>
                    </div>

                    <div class="card-actions">
                        <input type="file" id="jsonFileInput" accept=".json" style="display: none;">
                        <button type="button" class="btn btn-secondary" id="chooseJsonBtn">📂 Dosya Seç</button>
                        <button type="button" class="btn btn-secondary" id="useDefaultJsonBtn">⚡ Örnek 30 Günü Yükle</button>
                        <button type="button" class="btn btn-secondary" id="clearJsonBtn" style="display: none; color: #f87171;">✕ Kaldır</button>
                    </div>
                </div>

                <!-- PDF Template Card -->
                <div class="upload-card loaded" id="pdfCard">
                    <div>
                        <div class="card-header">
                            <div class="icon-box" id="pdfIcon">📑</div>
                            <div>
                                <div class="card-title">2. Defter Şablonu (PDF)</div>
                                <div class="card-sub" id="pdfSub">Doldurulacak boş defter</div>
                            </div>
                        </div>

                        <div class="file-info-box" id="pdfInfoBox" style="display: block;">
                            <div class="file-info-row">
                                <span class="file-name" id="pdfFileName">EEE-Internship Notebook.pdf</span>
                                <span class="file-size" id="pdfFileSize">Varsayılan Şablon</span>
                            </div>
                            <div class="file-stat-pill" id="pdfPagesPill" style="background: rgba(6, 182, 212, 0.15); color: #22d3ee;">
                                📑 47 Sayfa (Dinamik İnceleme)
                            </div>
                        </div>

                        <div class="dropzone" id="pdfDropzone" style="display: none;">
                            <div class="dropzone-text">
                                <div>📑 <strong>Kendi PDF Şablonunu Seç</strong> veya sürükle</div>
                                <div style="font-size: 0.75rem; margin-top: 0.25rem; color: #64748b;">(Üniversitenizin boş staj defteri)</div>
                            </div>
                        </div>
                    </div>

                    <div class="card-actions">
                        <input type="file" id="pdfFileInput" accept=".pdf" style="display: none;">
                        <button type="button" class="btn btn-secondary" id="choosePdfBtn">📑 Kendi Şablonunu Yükle</button>
                        <button type="button" class="btn btn-secondary" id="useDefaultPdfBtn" style="display: none;">🔄 Varsayılan Şablona Dön</button>
                    </div>
                </div>
            </div>

            <!-- 2. Student & Internship Details Form -->
            <div class="section-title-bar">
                <div>
                    <div class="section-title">
                        <span>📝</span> Öğrenci ve Staj Bilgileri
                    </div>
                    <div class="section-sub">
                        PDF'teki Kapak, Kabul Formu, Devam Çizelgesi ve Değerlendirme sayfalarına basılacak alanlar.
                    </div>
                </div>
                <div style="display: flex; gap: 0.5rem;">
                    <button type="button" class="btn btn-secondary" id="resetDefaultsBtn" title="Varsayılan bilgileri geri yükle">
                        <span>↺</span> Varsayılanları Yükle
                    </button>
                    <button type="button" class="btn btn-secondary" id="clearFieldsBtn" title="Tüm alanları temizle">
                        <span>🧹</span> Temizle
                    </button>
                </div>
            </div>

            <div class="input-grid">
                <!-- Card 1: Student Information -->
                <div class="field-group-card">
                    <div class="form-group-title">
                        <span>🎓</span> Öğrenci Kişisel & Akademik Bilgileri
                    </div>

                    <div class="form-row-2">
                        <div class="form-field">
                            <label for="studentName">Öğrenci Adı Soyadı</label>
                            <input type="text" id="studentName" value="Devran Sever" placeholder="Örn: Devran Sever">
                            <span class="field-hint">Kapak, Kabul, Devam, Komisyon</span>
                        </div>
                        <div class="form-field">
                            <label for="studentTc">T.C. Kimlik No</label>
                            <input type="text" id="studentTc" value="12345678901" maxlength="11" placeholder="11 haneli T.C. Kimlik No">
                            <span class="field-hint">Zorunlu staj formu kimlik tablosu</span>
                        </div>
                    </div>

                    <div class="form-row-2">
                        <div class="form-field">
                            <label for="studentId">Öğrenci Numarası</label>
                            <input type="text" id="studentId" value="23091400016" placeholder="Örn: 23091400016">
                        </div>
                        <div class="form-field">
                            <label for="studentYear">Sınıf / Yıl</label>
                            <input type="text" id="studentYear" value="3rd" placeholder="Örn: 3rd veya 3">
                        </div>
                    </div>

                    <div class="form-row-2">
                        <div class="form-field">
                            <label for="studentDept">Üniversite Bölümü</label>
                            <input type="text" id="studentDept" value="Electrical and Electronics Engineering" placeholder="Bölüm Adı">
                        </div>
                        <div class="form-field">
                            <label for="courseCode">Staj Dersi Kodu</label>
                            <input type="text" id="courseCode" value="EEE 299" placeholder="Örn: EEE 299">
                        </div>
                    </div>

                    <div class="form-row-2">
                        <div class="form-field">
                            <label for="birthPlace">Doğum Yeri</label>
                            <input type="text" id="birthPlace" value="Istanbul" placeholder="Örn: Istanbul">
                        </div>
                        <div class="form-field">
                            <label for="birthDate">Doğum Tarihi</label>
                            <input type="text" id="birthDate" value="15/04/2003" placeholder="GG/AA/YYYY">
                        </div>
                    </div>

                    <div class="form-row-2">
                        <div class="form-field">
                            <label for="fatherName">Baba Adı</label>
                            <input type="text" id="fatherName" value="Ahmet" placeholder="Baba Adı">
                        </div>
                        <div class="form-field">
                            <label for="motherName">Anne Adı</label>
                            <input type="text" id="motherName" value="Fatma" placeholder="Anne Adı">
                        </div>
                    </div>

                    <div class="form-row-2">
                        <div class="form-field">
                            <label for="studentEmail">Öğrenci E-posta</label>
                            <input type="email" id="studentEmail" value="devransever@ogr.halic.edu.tr" placeholder="E-posta">
                        </div>
                        <div class="form-field">
                            <label for="studentPhone">Öğrenci Telefon</label>
                            <input type="tel" id="studentPhone" value="+90 555 123 4567" placeholder="Telefon">
                        </div>
                    </div>

                    <div class="form-row-2">
                        <div class="form-field">
                            <label for="academicYear">Öğretim Yılı</label>
                            <input type="text" id="academicYear" value="2025 - 2026" placeholder="Örn: 2025 - 2026">
                        </div>
                        <div class="form-field">
                            <label for="studentSignDate">Başvuru / Beyan Tarihi</label>
                            <input type="text" id="studentSignDate" value="25/07/2026" placeholder="GG/AA/YYYY">
                        </div>
                    </div>

                    <div class="form-field">
                        <label for="residenceAddress">İkametgah / Ev Adresi</label>
                        <input type="text" id="residenceAddress" value="Ornek Mah. Ataturk Cad. No:14 D:5 Kadikoy / Istanbul" placeholder="Açık ikametgah adresi">
                        <span class="field-hint">Zorunlu staj formu beyan adresi satırı</span>
                    </div>
                </div>

                <!-- Card 2: Company Details -->
                <div class="field-group-card">
                    <div class="form-group-title">
                        <span>🏢</span> Kurum / Şirket Bilgileri
                    </div>

                    <div class="form-field">
                        <label for="companyName">Kurum / Şirket Tam Adı</label>
                        <input type="text" id="companyName" value="Teknoloji ve Yazilim Cozumleri A.S." placeholder="Kurumun resmi unvanı">
                        <span class="field-hint">Kabul, devam çizelgesi ve değerlendirme sayfaları</span>
                    </div>

                    <div class="form-field">
                        <label for="companyAddress">Kurum Açık Adresi</label>
                        <input type="text" id="companyAddress" value="Buyukdere Cad. No:122 Levent / Besiktas / Istanbul" placeholder="Şirket resmi açık adresi">
                        <span class="field-hint">Zorunlu staj formu ve staj yeri değerlendirme formu</span>
                    </div>

                    <div class="form-row-2">
                        <div class="form-field">
                            <label for="internshipDept">Staj Yapılan Departman</label>
                            <input type="text" id="internshipDept" value="IT Operations & Software Engineering" placeholder="Örn: IT Operations">
                        </div>
                        <div class="form-field">
                            <label for="companyField">Faaliyet Alanı / Sektör</label>
                            <input type="text" id="companyField" value="Information Technology & Software Development" placeholder="Örn: Information Technology">
                        </div>
                    </div>

                    <div class="form-row-2">
                        <div class="form-field">
                            <label for="productionServiceArea">Üretim / Hizmet Alanı</label>
                            <input type="text" id="productionServiceArea" value="Yazilim & Bilisim Cozumleri" placeholder="Örn: Yazilim & Bilisim">
                        </div>
                        <div class="form-field">
                            <label for="riskRange">Tehlike Sınıfı</label>
                            <input type="text" id="riskRange" value="Az Tehlikeli (Low Risk)" placeholder="Örn: Az Tehlikeli">
                        </div>
                    </div>

                    <div class="form-row-2">
                        <div class="form-field">
                            <label for="companyWeb">Web Sitesi</label>
                            <input type="text" id="companyWeb" value="www.teknolojias.com.tr" placeholder="www.sirket.com">
                        </div>
                        <div class="form-field">
                            <label for="companyPhone">Şirket Telefonu</label>
                            <input type="tel" id="companyPhone" value="(0212) 555 0100" placeholder="(0212) ...">
                        </div>
                    </div>

                    <div class="form-row-2">
                        <div class="form-field">
                            <label for="companyFax">Faks Numarası</label>
                            <input type="text" id="companyFax" value="(0212) 555 0101" placeholder="(0212) ...">
                        </div>
                        <div class="form-field">
                            <label for="companyEmail">Şirket Kurumsal E-posta</label>
                            <input type="email" id="companyEmail" value="staj@teknoloji.com.tr" placeholder="staj@sirket.com">
                        </div>
                    </div>
                </div>

                <!-- Card 3: Employer & Authorized Personnel -->
                <div class="field-group-card">
                    <div class="form-group-title">
                        <span>👔</span> Yetkili / Amir Bilgileri & Onaylar
                    </div>

                    <div class="form-row-2">
                        <div class="form-field">
                            <label for="employerName">Yetkili Adı Soyadı</label>
                            <input type="text" id="employerName" value="Mehmet Yilmaz" placeholder="Yetkili Mühendis / Yönetici">
                            <span class="field-hint">Kabul formu ve işyeri değerlendirme formu yetkilisi</span>
                        </div>
                        <div class="form-field">
                            <label for="employerTitle">Yetkili Görev / Unvanı</label>
                            <input type="text" id="employerTitle" value="Engineering Manager" placeholder="Örn: Engineering Manager">
                        </div>
                    </div>

                    <div class="form-row-2">
                        <div class="form-field">
                            <label for="employerEmail">Yetkili E-posta Adresi</label>
                            <input type="email" id="employerEmail" value="mehmet.yilmaz@teknoloji.com.tr" placeholder="yetkili@sirket.com">
                        </div>
                        <div class="form-field">
                            <label for="departmentEmployees">Departmandaki Personel Sayısı</label>
                            <input type="text" id="departmentEmployees" value="12 Employees" placeholder="Örn: 12 Employees">
                        </div>
                    </div>

                    <div class="form-row-2">
                        <div class="form-field">
                            <label for="acceptanceDate">Kabul Formu Onay Tarihi</label>
                            <input type="text" id="acceptanceDate" value="28/07/2026" placeholder="GG/AA/YYYY">
                            <span class="field-hint">Sayfa 11 Kabul Formu üst sağ tarihi</span>
                        </div>
                        <div class="form-field">
                            <label for="evaluationDate">Değerlendirme Formu Tarihi</label>
                            <input type="text" id="evaluationDate" value="18/09/2026" placeholder="GG/AA/YYYY">
                            <span class="field-hint">Sayfa 13 Staj bitiş onay tarihi</span>
                        </div>
                    </div>

                    <div style="background: rgba(255,255,255,0.03); border: 1px dashed rgba(255,255,255,0.15); border-radius: 0.6rem; padding: 0.75rem; font-size: 0.775rem; color: #94a3b8; line-height: 1.4;">
                        ℹ️ <strong>İmza & Kaşe Alanları:</strong> Resmi imza, mühür ve kaşe alanları üniversite yönergesi gereği ıslak imza için otomatik olarak boş bırakılır.
                    </div>
                </div>

                <!-- Card 4: Internship Metrics, Engineer Statistics & Survey -->
                <div class="field-group-card">
                    <div class="form-group-title">
                        <span>📊</span> Staj Takvimi, Mühendis İstatistikleri & Anket
                    </div>

                    <div class="form-row-2">
                        <div class="form-field">
                            <label for="durationWorkdays">Staj Süresi</label>
                            <input type="text" id="durationWorkdays" value="30 Workdays" placeholder="Örn: 30 Workdays">
                            <span class="field-hint">Kabul ve devam formları süresi</span>
                        </div>
                        <div class="form-field">
                            <label for="startDateInput">Staj Başlangıç Tarihi (Pazartesi)</label>
                            <input type="date" id="startDateInput" value="2026-08-10">
                            <span class="field-hint">30 iş günü (Pzt-Cum) hesaplanır</span>
                        </div>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0.5rem;">
                        <div class="form-field">
                            <label for="totalEngineers">Toplam Mühendis</label>
                            <input type="text" id="totalEngineers" value="18" placeholder="Örn: 18">
                            <span class="field-hint">İşyeri anketi S.1</span>
                        </div>
                        <div class="form-field">
                            <label for="eeeEngineers">EEE Mühendisi</label>
                            <input type="text" id="eeeEngineers" value="4" placeholder="Örn: 4">
                            <span class="field-hint">Bölüm mezunu</span>
                        </div>
                        <div class="form-field">
                            <label for="totalEmployees">Toplam Çalışan</label>
                            <input type="text" id="totalEmployees" value="45" placeholder="Örn: 45">
                            <span class="field-hint">Tüm personel</span>
                        </div>
                    </div>

                    <div class="form-field">
                        <label for="eeeNeedExplanation">EEE Mühendisi İhtiyacı Gerekçesi (Sayfa 14 - Soru 2)</label>
                        <textarea id="eeeNeedExplanation" rows="2" placeholder="Gerekçe açıklaması">Hardware-software integration, system testing and network infrastructure projects.</textarea>
                    </div>

                    <div class="form-field">
                        <label for="surveyExplanation">İşyeri Değerlendirme & Ar-Ge Açıklaması (Sayfa 15 - Soru 4)</label>
                        <textarea id="surveyExplanation" rows="2" placeholder="Ar-Ge ve altyapı açıklaması">N/A - The enterprise provided strong technical mentorship, well-equipped hardware labs, and advanced database infrastructure.</textarea>
                    </div>
                </div>
            </div>

            <!-- Action Bar -->
            <div class="action-bar">
                <a href="/api/sample-json" class="btn btn-secondary" download="entries.example.json">
                    <span>📥</span> Örnek JSON Şablonunu İndir
                </a>

                <button type="button" class="btn btn-primary" id="processBtn">
                    <span>⚡</span> Defteri Doldur ve Düzenle
                </button>
            </div>
        </div>

        <!-- Step 2: Result & Download Card (Displayed after successful processing) -->
        <div id="resultContainer">
            <div class="result-badge">✓ Düzenleme Başarıyla Tamamlandı</div>
            <div class="result-title">🎉 Staj Defteriniz Hazır!</div>
            <div class="result-desc">
                Öğrenci ve staj bilgileri kapak ve idari sayfalara işlendi, 30 iş günü devam çizelgesine yerleştirildi ve 30 günlük rapor sayfaları sıfır taşma ile dolduruldu.
            </div>

            <div class="result-stats">
                <div class="stat-pill" id="resDaysStat">📅 30 İş Günü İşlendi</div>
                <div class="stat-pill" id="resAttendanceStat">📋 Devam Çizelgesi Dolduruldu</div>
                <div class="stat-pill" id="resSizeStat">💾 Boyut: Hesaplanıyor</div>
            </div>

            <div class="result-buttons">
                <a href="#" class="btn btn-success" id="downloadBtn" download="Doldurulmus_Staj_Defteri.pdf">
                    <span>📥</span> Doldurulmuş PDF'i İndir
                </a>
                <a href="#" class="btn btn-secondary" id="previewBtn" target="_blank" style="padding: 0.85rem 1.4rem; font-size: 0.95rem;">
                    <span>👁️</span> Tarayıcıda Önizle
                </a>
                <button type="button" class="btn btn-secondary" id="reconfigureBtn" style="padding: 0.85rem 1.2rem; font-size: 0.95rem;">
                    <span>↺</span> Yeniden Düzenle
                </button>
            </div>
        </div>

        <!-- Terminal & Real-Time Inspection Console -->
        <div class="glass-panel" style="padding: 1.25rem 1.5rem;">
            <div class="terminal-header">
                <span>Dinamik Analiz & Süreç Konsolu</span>
                <span id="terminalStatus" style="color: #94a3b8;">Hazır</span>
            </div>
            <div class="terminal-panel" id="terminal">
                <div class="log-entry info">[Sistem] Dinamik Şablon İnceleme & Form Doldurma Motoru aktif.</div>
                <div class="log-entry info">[Adım 1] Bilgilerinizi kontrol ediniz veya kendi öğrenci bilgilerinizi yazınız.</div>
                <div class="log-entry info">[Adım 2] JSON dosyasını seçip 'Defteri Doldur ve Düzenle' butonuna tıklayınız.</div>
            </div>
        </div>
    </main>

    <footer>
        Geliştirici: <a href="https://github.com/DevranTheDeveloper" target="_blank">Devran Sever</a> • PyMuPDF & Times New Roman ile hazırlandı.
    </footer>

    <script>
        // DOM Elements - Uploads
        const jsonCard = document.getElementById('jsonCard');
        const jsonDropzone = document.getElementById('jsonDropzone');
        const jsonFileInput = document.getElementById('jsonFileInput');
        const chooseJsonBtn = document.getElementById('chooseJsonBtn');
        const useDefaultJsonBtn = document.getElementById('useDefaultJsonBtn');
        const clearJsonBtn = document.getElementById('clearJsonBtn');
        const jsonInfoBox = document.getElementById('jsonInfoBox');
        const jsonFileName = document.getElementById('jsonFileName');
        const jsonFileSize = document.getElementById('jsonFileSize');
        const jsonDaysPill = document.getElementById('jsonDaysPill');
        const jsonSub = document.getElementById('jsonSub');

        const pdfCard = document.getElementById('pdfCard');
        const pdfDropzone = document.getElementById('pdfDropzone');
        const pdfFileInput = document.getElementById('pdfFileInput');
        const choosePdfBtn = document.getElementById('choosePdfBtn');
        const useDefaultPdfBtn = document.getElementById('useDefaultPdfBtn');
        const pdfInfoBox = document.getElementById('pdfInfoBox');
        const pdfFileName = document.getElementById('pdfFileName');
        const pdfFileSize = document.getElementById('pdfFileSize');
        const pdfPagesPill = document.getElementById('pdfPagesPill');
        const pdfSub = document.getElementById('pdfSub');

        // Form Fields - Student
        const studentName = document.getElementById('studentName');
        const studentTc = document.getElementById('studentTc');
        const studentId = document.getElementById('studentId');
        const studentYear = document.getElementById('studentYear');
        const studentDept = document.getElementById('studentDept');
        const courseCode = document.getElementById('courseCode');
        const birthPlace = document.getElementById('birthPlace');
        const birthDate = document.getElementById('birthDate');
        const fatherName = document.getElementById('fatherName');
        const motherName = document.getElementById('motherName');
        const studentEmail = document.getElementById('studentEmail');
        const studentPhone = document.getElementById('studentPhone');
        const academicYear = document.getElementById('academicYear');
        const studentSignDate = document.getElementById('studentSignDate');
        const residenceAddress = document.getElementById('residenceAddress');

        // Form Fields - Company
        const companyName = document.getElementById('companyName');
        const companyAddress = document.getElementById('companyAddress');
        const internshipDept = document.getElementById('internshipDept');
        const companyField = document.getElementById('companyField');
        const productionServiceArea = document.getElementById('productionServiceArea');
        const riskRange = document.getElementById('riskRange');
        const companyWeb = document.getElementById('companyWeb');
        const companyPhone = document.getElementById('companyPhone');
        const companyFax = document.getElementById('companyFax');
        const companyEmail = document.getElementById('companyEmail');

        // Form Fields - Employer
        const employerName = document.getElementById('employerName');
        const employerTitle = document.getElementById('employerTitle');
        const employerEmail = document.getElementById('employerEmail');
        const departmentEmployees = document.getElementById('departmentEmployees');
        const acceptanceDate = document.getElementById('acceptanceDate');
        const evaluationDate = document.getElementById('evaluationDate');

        // Form Fields - Metrics & Survey
        const durationWorkdays = document.getElementById('durationWorkdays');
        const startDateInput = document.getElementById('startDateInput');
        const totalEngineers = document.getElementById('totalEngineers');
        const eeeEngineers = document.getElementById('eeeEngineers');
        const totalEmployees = document.getElementById('totalEmployees');
        const eeeNeedExplanation = document.getElementById('eeeNeedExplanation');
        const surveyExplanation = document.getElementById('surveyExplanation');

        const resetDefaultsBtn = document.getElementById('resetDefaultsBtn');
        const clearFieldsBtn = document.getElementById('clearFieldsBtn');

        // Actions & Results
        const processBtn = document.getElementById('processBtn');
        const resultContainer = document.getElementById('resultContainer');
        const downloadBtn = document.getElementById('downloadBtn');
        const previewBtn = document.getElementById('previewBtn');
        const reconfigureBtn = document.getElementById('reconfigureBtn');
        const terminal = document.getElementById('terminal');
        const terminalStatus = document.getElementById('terminalStatus');

        // State variables
        let selectedJsonFile = null;
        let useDefaultJson = true; // start with default enabled for frictionless UX
        let selectedPdfFile = null;
        let useDefaultPdf = true;

        // Automatically configure initial UI state for default JSON
        window.addEventListener('DOMContentLoaded', () => {
            setJsonLoaded('entries.json (Varsayılan)', '39.8 KB', 30);
        });

        // Helper Defaults
        const DEFAULTS = {
            name: "Devran Sever",
            tc_no: "12345678901",
            student_id: "23091400016",
            year: "3rd",
            department: "Electrical and Electronics Engineering",
            course_code: "EEE 299",
            birth_place: "Istanbul",
            birth_date: "15/04/2003",
            father_name: "Ahmet",
            mother_name: "Fatma",
            student_email: "devransever@ogr.halic.edu.tr",
            student_phone: "+90 555 123 4567",
            academic_year: "2025 - 2026",
            student_sign_date: "25/07/2026",
            residence_address: "Ornek Mah. Ataturk Cad. No:14 D:5 Kadikoy / Istanbul",

            company_name: "Teknoloji ve Yazilim Cozumleri A.S.",
            company_address: "Buyukdere Cad. No:122 Levent / Besiktas / Istanbul",
            internship_department: "IT Operations & Software Engineering",
            company_field: "Information Technology & Software Development",
            production_service_area: "Yazilim & Bilisim Cozumleri",
            risk_range: "Az Tehlikeli (Low Risk)",
            company_web: "www.teknolojias.com.tr",
            company_phone: "(0212) 555 0100",
            company_fax: "(0212) 555 0101",
            company_email: "staj@teknoloji.com.tr",

            employer_name: "Mehmet Yilmaz",
            employer_title: "Engineering Manager",
            employer_email: "mehmet.yilmaz@teknoloji.com.tr",
            department_employees: "12 Employees",
            acceptance_date: "28/07/2026",
            evaluation_date: "18/09/2026",

            duration_workdays: "30 Workdays",
            start_date: "2026-08-10",
            total_engineers: "18",
            eee_engineers: "4",
            total_employees: "45",
            eee_need_explanation: "Hardware-software integration, system testing and network infrastructure projects.",
            survey_explanation: "N/A - The enterprise provided strong technical mentorship, well-equipped hardware labs, and advanced database infrastructure."
        };

        resetDefaultsBtn.addEventListener('click', () => {
            studentName.value = DEFAULTS.name;
            studentTc.value = DEFAULTS.tc_no;
            studentId.value = DEFAULTS.student_id;
            studentYear.value = DEFAULTS.year;
            studentDept.value = DEFAULTS.department;
            courseCode.value = DEFAULTS.course_code;
            birthPlace.value = DEFAULTS.birth_place;
            birthDate.value = DEFAULTS.birth_date;
            fatherName.value = DEFAULTS.father_name;
            motherName.value = DEFAULTS.mother_name;
            studentEmail.value = DEFAULTS.student_email;
            studentPhone.value = DEFAULTS.student_phone;
            academicYear.value = DEFAULTS.academic_year;
            studentSignDate.value = DEFAULTS.student_sign_date;
            residenceAddress.value = DEFAULTS.residence_address;

            companyName.value = DEFAULTS.company_name;
            companyAddress.value = DEFAULTS.company_address;
            internshipDept.value = DEFAULTS.internship_department;
            companyField.value = DEFAULTS.company_field;
            productionServiceArea.value = DEFAULTS.production_service_area;
            riskRange.value = DEFAULTS.risk_range;
            companyWeb.value = DEFAULTS.company_web;
            companyPhone.value = DEFAULTS.company_phone;
            companyFax.value = DEFAULTS.company_fax;
            companyEmail.value = DEFAULTS.company_email;

            employerName.value = DEFAULTS.employer_name;
            employerTitle.value = DEFAULTS.employer_title;
            employerEmail.value = DEFAULTS.employer_email;
            departmentEmployees.value = DEFAULTS.department_employees;
            acceptanceDate.value = DEFAULTS.acceptance_date;
            evaluationDate.value = DEFAULTS.evaluation_date;

            durationWorkdays.value = DEFAULTS.duration_workdays;
            startDateInput.value = DEFAULTS.start_date;
            totalEngineers.value = DEFAULTS.total_engineers;
            eeeEngineers.value = DEFAULTS.eee_engineers;
            totalEmployees.value = DEFAULTS.total_employees;
            eeeNeedExplanation.value = DEFAULTS.eee_need_explanation;
            surveyExplanation.value = DEFAULTS.survey_explanation;

            log('[i] Form alanları varsayılan öğrenci ve staj bilgileri ile dolduruldu.', 'info');
        });

        clearFieldsBtn.addEventListener('click', () => {
            const allInputs = [
                studentName, studentTc, studentId, studentYear, studentDept, courseCode,
                birthPlace, birthDate, fatherName, motherName, studentEmail, studentPhone,
                academicYear, studentSignDate, residenceAddress, companyName, companyAddress,
                internshipDept, companyField, productionServiceArea, riskRange, companyWeb,
                companyPhone, companyFax, companyEmail, employerName, employerTitle,
                employerEmail, departmentEmployees, acceptanceDate, evaluationDate,
                durationWorkdays, totalEngineers, eeeEngineers, totalEmployees,
                eeeNeedExplanation, surveyExplanation
            ];
            allInputs.forEach(el => { if (el) el.value = ''; });
            log('[i] Tüm form alanları temizlendi.', 'info');
        });

        // Terminal Log Helper
        function log(msg, type='info') {
            const div = document.createElement('div');
            div.className = `log-entry ${type}`;
            div.textContent = msg;
            terminal.appendChild(div);
            terminal.scrollTop = terminal.scrollHeight;
        }

        function formatBytes(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
        }

        // ================= JSON Management =================
        function setJsonLoaded(name, sizeStr, daysCount) {
            jsonCard.classList.add('loaded');
            jsonDropzone.style.display = 'none';
            jsonInfoBox.style.display = 'block';
            jsonFileName.textContent = name;
            jsonFileSize.textContent = sizeStr;
            jsonDaysPill.textContent = `✓ ${daysCount} Günlük Veri Hazır`;
            jsonSub.textContent = `✓ ${daysCount} gün yüklendi`;
            clearJsonBtn.style.display = 'inline-flex';
            chooseJsonBtn.textContent = '🔄 Değiştir';
        }

        function resetJson() {
            selectedJsonFile = null;
            useDefaultJson = false;
            jsonFileInput.value = '';
            jsonCard.classList.remove('loaded');
            jsonDropzone.style.display = 'block';
            jsonInfoBox.style.display = 'none';
            jsonSub.textContent = '30 günlük rapor verisi';
            clearJsonBtn.style.display = 'none';
            chooseJsonBtn.textContent = '📂 Dosya Seç';
        }

        chooseJsonBtn.addEventListener('click', () => jsonFileInput.click());
        jsonDropzone.addEventListener('click', () => jsonFileInput.click());

        jsonFileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                const file = e.target.files[0];
                handleJsonFile(file);
            }
        });

        function handleJsonFile(file) {
            const reader = new FileReader();
            reader.onload = (event) => {
                try {
                    const parsed = JSON.parse(event.target.result);
                    if (!Array.isArray(parsed)) {
                        alert('Hata: JSON dosyası günlüklerin bir listesini (array) içermelidir.');
                        return;
                    }
                    selectedJsonFile = file;
                    useDefaultJson = false;
                    setJsonLoaded(file.name, formatBytes(file.size), parsed.length);
                    log(`[✓] JSON yüklendi: ${file.name} (${parsed.length} gün tespit edildi)`, 'success');
                } catch (err) {
                    alert('Geçersiz JSON dosyası! Lütfen geçerli bir JSON seçin.');
                }
            };
            reader.readAsText(file);
        }

        useDefaultJsonBtn.addEventListener('click', async () => {
            try {
                useDefaultJsonBtn.disabled = true;
                useDefaultJsonBtn.textContent = '⏳ Yükleniyor...';
                const res = await fetch('/api/sample-json');
                if (!res.ok) throw new Error('Örnek JSON alınamadı.');
                const data = await res.json();
                useDefaultJson = true;
                selectedJsonFile = null;
                setJsonLoaded('entries.json (Örnek)', '39.8 KB', data.length);
                log(`[✓] Yerleşik 30 günlük örnek entries.json seçildi.`, 'success');
            } catch (err) {
                alert('Örnek JSON yüklenemedi: ' + err.message);
            } finally {
                useDefaultJsonBtn.disabled = false;
                useDefaultJsonBtn.textContent = '⚡ Örnek 30 Günü Yükle';
            }
        });

        clearJsonBtn.addEventListener('click', () => {
            resetJson();
            log(`[i] JSON seçimi kaldırıldı.`, 'info');
        });

        // JSON Drag & Drop
        jsonCard.addEventListener('dragover', (e) => { e.preventDefault(); jsonCard.classList.add('dragover'); });
        jsonCard.addEventListener('dragleave', () => jsonCard.classList.remove('dragover'));
        jsonCard.addEventListener('drop', (e) => {
            e.preventDefault();
            jsonCard.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                handleJsonFile(e.dataTransfer.files[0]);
            }
        });

        // ================= PDF Template Management =================
        function setPdfLoaded(name, sizeStr, isDefault=false) {
            pdfCard.classList.add('loaded');
            pdfDropzone.style.display = 'none';
            pdfInfoBox.style.display = 'block';
            pdfFileName.textContent = name;
            pdfFileSize.textContent = sizeStr;
            if (isDefault) {
                pdfPagesPill.textContent = '📑 47 Sayfa (Varsayılan EEE Şablonu)';
                pdfPagesPill.style.background = 'rgba(6, 182, 212, 0.15)';
                pdfPagesPill.style.color = '#22d3ee';
                useDefaultPdfBtn.style.display = 'none';
                choosePdfBtn.textContent = '📑 Kendi Şablonunu Yükle';
            } else {
                pdfPagesPill.textContent = '📑 Özel Şablon (Dinamik Taranacak)';
                pdfPagesPill.style.background = 'rgba(16, 185, 129, 0.15)';
                pdfPagesPill.style.color = '#34d399';
                useDefaultPdfBtn.style.display = 'inline-flex';
                choosePdfBtn.textContent = '🔄 Başka PDF Seç';
            }
        }

        choosePdfBtn.addEventListener('click', () => pdfFileInput.click());
        pdfDropzone.addEventListener('click', () => pdfFileInput.click());

        pdfFileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                const file = e.target.files[0];
                selectedPdfFile = file;
                useDefaultPdf = false;
                setPdfLoaded(file.name, formatBytes(file.size), false);
                log(`[✓] Özel PDF şablonu yüklendi: ${file.name}`, 'success');
            }
        });

        useDefaultPdfBtn.addEventListener('click', () => {
            selectedPdfFile = null;
            useDefaultPdf = true;
            pdfFileInput.value = '';
            setPdfLoaded('EEE-Internship Notebook.pdf', 'Varsayılan Şablon', true);
            log(`[✓] Varsayılan EEE staj defteri şablonuna dönüldü.`, 'info');
        });

        // PDF Drag & Drop
        pdfCard.addEventListener('dragover', (e) => { e.preventDefault(); pdfCard.classList.add('dragover'); });
        pdfCard.addEventListener('dragleave', () => pdfCard.classList.remove('dragover'));
        pdfCard.addEventListener('drop', (e) => {
            e.preventDefault();
            pdfCard.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                const file = e.dataTransfer.files[0];
                if (file.name.endsWith('.pdf')) {
                    selectedPdfFile = file;
                    useDefaultPdf = false;
                    setPdfLoaded(file.name, formatBytes(file.size), false);
                    log(`[✓] Özel PDF şablonu yüklendi: ${file.name}`, 'success');
                } else {
                    alert('Lütfen geçerli bir .pdf dosyası bırakın.');
                }
            }
        });

        // ================= STEP 1: Process Internship Notebook =================
        processBtn.addEventListener('click', async () => {
            if (!selectedJsonFile && !useDefaultJson) {
                alert('Lütfen önce staj günlüklerinizi içeren JSON dosyasını yükleyin veya "Örnek 30 Günü Yükle"ye tıklayın.');
                return;
            }

            processBtn.disabled = true;
            processBtn.innerHTML = '<span>⏳</span> İnceleniyor ve Dolduruluyor...';
            terminalStatus.textContent = 'İşleniyor...';
            terminalStatus.style.color = '#f59e0b';

            terminal.innerHTML = '';
            log('[1/4] Dinamik Şablon Analiz Motoru başlatıldı...', 'info');
            log(`[2/4] Öğrenci: ${studentName.value} (No: ${studentId.value})`, 'info');
            log(`[3/4] Başlangıç Tarihi: ${startDateInput.value} (30 iş günü hesaplanıyor)...`, 'info');

            const formData = new FormData();
            if (selectedJsonFile) {
                formData.append('json_file', selectedJsonFile);
            } else {
                formData.append('use_default_json', 'true');
            }

            if (selectedPdfFile) {
                formData.append('pdf_file', selectedPdfFile);
            } else {
                formData.append('use_default_pdf', 'true');
            }

            formData.append('start_date', startDateInput.value);

            // Collect all student & internship administrative fields
            const studentInfo = {
                // Student
                name: studentName ? studentName.value.trim() : "",
                tc_no: studentTc ? studentTc.value.trim() : "",
                student_id: studentId ? studentId.value.trim() : "",
                year: studentYear ? studentYear.value.trim() : "",
                year_num: studentYear ? (studentYear.value.replace(/[^0-9]/g, '') || "3") : "3",
                department: studentDept ? studentDept.value.trim() : "",
                course_code: courseCode ? courseCode.value.trim() : "",
                birth_place: birthPlace ? birthPlace.value.trim() : "",
                birth_date: birthDate ? birthDate.value.trim() : "",
                father_name: fatherName ? fatherName.value.trim() : "",
                mother_name: motherName ? motherName.value.trim() : "",
                email: studentEmail ? studentEmail.value.trim() : "",
                phone: studentPhone ? studentPhone.value.trim() : "",
                academic_year: academicYear ? academicYear.value.trim() : "",
                student_sign_date: studentSignDate ? studentSignDate.value.trim() : "",
                residence_address: residenceAddress ? residenceAddress.value.trim() : "",

                // Company
                company_name: companyName ? companyName.value.trim() : "",
                company_address: companyAddress ? companyAddress.value.trim() : "",
                internship_department: internshipDept ? internshipDept.value.trim() : "",
                company_field: companyField ? companyField.value.trim() : "",
                production_service_area: productionServiceArea ? productionServiceArea.value.trim() : "",
                risk_range: riskRange ? riskRange.value.trim() : "",
                company_web: companyWeb ? companyWeb.value.trim() : "",
                company_phone: companyPhone ? companyPhone.value.trim() : "",
                company_fax: companyFax ? companyFax.value.trim() : "",
                company_email: companyEmail ? companyEmail.value.trim() : "",

                // Employer
                employer_name: employerName ? employerName.value.trim() : "",
                employer_title: employerTitle ? employerTitle.value.trim() : "",
                employer_email: employerEmail ? employerEmail.value.trim() : "",
                department_employees: departmentEmployees ? departmentEmployees.value.trim() : "",
                acceptance_date: acceptanceDate ? acceptanceDate.value.trim() : "",
                evaluation_date: evaluationDate ? evaluationDate.value.trim() : "",

                // Metrics & Survey
                duration_workdays: durationWorkdays ? durationWorkdays.value.trim() : "30 Workdays",
                total_engineers: totalEngineers ? totalEngineers.value.trim() : "18",
                eee_engineers: eeeEngineers ? eeeEngineers.value.trim() : "4",
                total_employees: totalEmployees ? totalEmployees.value.trim() : "45",
                eee_need_explanation: eeeNeedExplanation ? eeeNeedExplanation.value.trim() : "",
                survey_explanation: surveyExplanation ? surveyExplanation.value.trim() : ""
            };
            formData.append('student_info', JSON.stringify(studentInfo));

            try {
                const response = await fetch('/api/process', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (!response.ok || !data.success) {
                    throw new Error(data.error || 'İşlem sırasında bir hata oluştu.');
                }

                // Render logs from server
                if (data.logs && Array.isArray(data.logs)) {
                    data.logs.forEach(l => {
                        let type = 'info';
                        if (l.includes('Successfully') || l.includes('Injected') || l.includes('Detected') || l.includes('Populated')) type = 'success';
                        if (l.includes('[!]') || l.includes('Warning')) type = 'warning';
                        log(l, type);
                    });
                }

                log(`[✓] Defter başarıyla oluşturuldu! Boyut: ${data.file_size}`, 'success');
                terminalStatus.textContent = 'Tamamlandı';
                terminalStatus.style.color = '#10b981';

                // Setup Step 2: Download Card
                document.getElementById('resDaysStat').textContent = `📅 ${data.days_count || 30} İş Günü Dolduruldu`;
                document.getElementById('resSizeStat').textContent = `💾 Boyut: ${data.file_size}`;
                downloadBtn.href = `/api/download/${data.token}`;
                downloadBtn.innerHTML = `<span>📥</span> Doldurulmuş PDF'i İndir (${data.file_size})`;
                previewBtn.href = `/api/preview/${data.token}`;

                resultContainer.style.display = 'block';
                resultContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });

            } catch (err) {
                log(`[HATA] ${err.message}`, 'danger');
                terminalStatus.textContent = 'Hata Oluştu';
                terminalStatus.style.color = '#ef4444';
                alert('İşlem Hatası: ' + err.message);
            } finally {
                processBtn.disabled = false;
                processBtn.innerHTML = '<span>⚡</span> Defteri Doldur ve Düzenle';
            }
        });

        reconfigureBtn.addEventListener('click', () => {
            resultContainer.style.display = 'none';
            document.getElementById('inputPanel').scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/sample-json")
def sample_json():
    target_path = DEFAULT_JSON_PATH if os.path.isfile(DEFAULT_JSON_PATH) else os.path.join(os.path.dirname(__file__), "entries.example.json")
    if os.path.isfile(target_path):
        return send_file(target_path, as_attachment=True, download_name="entries.json", mimetype="application/json")
    return jsonify({"error": "Sample JSON not found"}), 404


@app.route("/api/sample-pdf")
def sample_pdf():
    if os.path.isfile(DEFAULT_PDF_PATH):
        return send_file(DEFAULT_PDF_PATH, as_attachment=True, download_name="EEE-Internship Notebook.pdf", mimetype="application/pdf")
    return jsonify({"error": "Sample PDF not found"}), 404


@app.route("/api/process", methods=["POST"])
def process_endpoint():
    """
    Step 1: Analyzes and fills the PDF, caches the output, and returns
    process status, metrics, and download token without forcing an immediate download.
    """
    try:
        cleanup_old_cache()

        # 1. Resolve JSON
        if request.form.get("use_default_json") == "true" or "json_file" not in request.files:
            if not os.path.isfile(DEFAULT_JSON_PATH):
                return jsonify({"success": False, "error": "Sunucuda varsayılan entries.json bulunamadı."}), 400
            with open(DEFAULT_JSON_PATH, "r", encoding="utf-8") as f:
                entries = json.load(f)
        else:
            json_file = request.files["json_file"]
            content = json_file.read().decode("utf-8")
            entries = json.loads(content)

        if not isinstance(entries, list) or len(entries) == 0:
            return jsonify({"success": False, "error": "JSON dosyası boş veya bir liste formatında değil."}), 400

        # 2. Resolve PDF template
        if request.form.get("use_default_pdf") == "true" or "pdf_file" not in request.files:
            if not os.path.isfile(DEFAULT_PDF_PATH):
                return jsonify({"success": False, "error": "Sunucuda varsayılan EEE-Internship Notebook.pdf bulunamadı."}), 400
            with open(DEFAULT_PDF_PATH, "rb") as f:
                pdf_bytes = f.read()
        else:
            pdf_file = request.files["pdf_file"]
            pdf_bytes = pdf_file.read()

        start_date_str = request.form.get("start_date", "2026-08-10")

        # 3. Parse Student Information
        student_info = {}
        student_info_raw = request.form.get("student_info")
        if student_info_raw:
            try:
                student_info = json.loads(student_info_raw)
            except Exception:
                student_info = {}

        # Fallback to direct parameters if provided
        for field in [
            "name", "student_id", "year", "department", "course_code", "company_name",
            "internship_department", "company_field", "duration_workdays", "student_sign_date",
            "acceptance_date", "department_employees", "evaluation_date", "total_engineers",
            "eee_engineers", "total_employees", "survey_explanation"
        ]:
            val = request.form.get(field)
            if val and field not in student_info:
                student_info[field] = val

        # 4. Process with Dynamic Inspection Engine
        output_bytes, logs = process_internship_notebook(
            pdf_bytes,
            entries,
            start_date_str,
            student_info=student_info
        )

        # 5. Cache generated PDF with unique token
        token = uuid.uuid4().hex[:16]
        with CACHE_LOCK:
            GENERATED_CACHE[token] = {
                "bytes": output_bytes,
                "filename": "Doldurulmus_Staj_Defteri.pdf",
                "created_at": time.time(),
                "days_count": len(entries),
            }

        size_kb = len(output_bytes) / 1024
        size_str = f"{size_kb / 1024:.2f} MB" if size_kb > 1024 else f"{size_kb:.1f} KB"

        return jsonify({
            "success": True,
            "token": token,
            "file_size": size_str,
            "days_count": len(entries),
            "logs": logs
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/download/<token>", methods=["GET"])
def download_pdf(token):
    """Step 2: Serves the processed PDF for direct download."""
    with CACHE_LOCK:
        file_data = GENERATED_CACHE.get(token)

    if not file_data:
        return "Dosya bulunamadı veya oturum süresi doldu. Lütfen tekrar düzenleme yapın.", 404

    return send_file(
        io.BytesIO(file_data["bytes"]),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=file_data.get("filename", "Doldurulmus_Staj_Defteri.pdf")
    )


@app.route("/api/preview/<token>", methods=["GET"])
def preview_pdf(token):
    """Step 2 (Alternate): Allows viewing the filled PDF directly in the browser tab."""
    with CACHE_LOCK:
        file_data = GENERATED_CACHE.get(token)

    if not file_data:
        return "Dosya bulunamadı veya oturum süresi doldu.", 404

    return send_file(
        io.BytesIO(file_data["bytes"]),
        mimetype="application/pdf",
        as_attachment=False
    )


# Backward compatibility endpoint
@app.route("/api/fill", methods=["POST"])
def fill_pdf_endpoint_legacy():
    return process_endpoint()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"Starting Internship Notebook Filler Web Studio on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
