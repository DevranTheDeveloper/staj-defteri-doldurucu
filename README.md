# 📑 Staj Defteri Doldurucu (Internship Notebook PDF Filler)

> **Mühendislik Staj Defterleri için Dinamik PDF Form ve Rapor Doldurma Uygulaması**  
> Dynamic PDF Form & Report Ingestion Engine for Engineering Internship Notebooks.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![PyMuPDF](https://img.shields.io/badge/PyMuPDF-fitz-orange)
![Flask](https://img.shields.io/badge/Flask-Web%20Studio-green)
![License](https://img.shields.io/badge/License-MIT-purple)

---

## 🌟 Öne Çıkan Özellikler (Key Features)

1. **Dinamik Şablon İnceleme Motoru (Dynamic Template Inspector)**:
   - Sayfa numaraları sabit kodlanmaz (`hardcoded` değildir).
   - Yüklenen PDF şablonunu otomatik tarar; **Staj Devam Çizelgesi (Attendance Sheet)** ve **Günlük Rapor Sayfaları**nı vektörel çizgileri, anahtar kelimeleri ve imza alanlarını inceleyerek tespit eder.
   - Sayfa düzeni varyasyonlarını (örneğin 1. gün ile sonraki günlerin farklı başlık koordinatları) dinamik olarak ayarlar.

2. **Otomatik İş Günü ve Tarih Hesaplama**:
   - Belirtilen başlangıç tarihinden (örn. 10 Ağustos 2026 Pazartesi) itibaren haftasonlarını (Cumartesi-Pazar) atlayarak geçerli staj iş günlerini hesaplar.
   - Tarihler hem günlük sayfalara hem de **Devam Çizelgesi (Page 12)** tablosundaki nokta yer tutucuların (`..../..../........`) üzerine milimetrik basılır.

3. **Akademik Tipografi (Times New Roman & Auto-Scaling)**:
   - Rapor standartlarına uygun **Times New Roman** (`tiro` regular, `tibo` bold).
   - Tipografik tire (`–`, `—`) ve tırnak işaretleri PDF Type 1 fontlarında soru işareti (`?`) oluşturmayacak şekilde otomatik temizlenir.
   - Metin uzunluğuna göre font boyutu dinamik olarak ölçeklenir; kutudan taşma veya metin kesilmesi yaşanmaz.

4. **Kullanıcı Dostu Web Stüdyosu (Flask Web App)**:
   - Sürükle-bırak JSON ve PDF yükleme.
   - Canlı analiz konsolu ve anında PDF indirme.
   - CLI üzerinden tek komutla çalışabilme imkanı.

---

## 🚀 Hızlı Başlangıç (Quick Start)

### 1. Kurulum
```bash
# Depoyu klonlayın
git clone https://github.com/DevranTheDeveloper/staj-defteri-doldurucu.git
cd staj-defteri-doldurucu

# Sanal ortam oluşturup paketleri yükleyin
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Web Uygulamasını Başlatma
```bash
python app.py
```
Tarayıcınızda `http://127.0.0.1:5001` adresine giderek arayüzü kullanabilirsiniz.

### 3. Komut Satırından (CLI) Çalıştırma
```bash
python fill_notebook.py --input "EEE-Internship Notebook.pdf" --output "Doldurulmus_Staj_Defteri.pdf" --data "entries.json" --start-date "2026-08-10"
```

---

## 📋 Veri Şeması (`entries.json`)

```json
[
  {
    "day": 1,
    "department": "IT Operations & Maintenance Workshop",
    "date": "10/08/2026",
    "topic": "Orientation, Workshop Safety, and Inventorying Decommissioned Systems",
    "content": "Today was my first day as an intern in the department. In the morning, I met with my internship mentor..."
  }
]
```

---

## 🛠 Mimari ve Rol Dağılımı

- **`TemplateInspector`**: PDF sayfalarındaki metin bloklarını (`Date:`, `Department`, `Tasks Accomplished`) ve çizim çizgilerini inceleyerek hedef koordinatları çıkartır.
- **`process_internship_notebook`**: Verileri bellek üstünde vektörel nesnelere zarar vermeden enjekte eder.
- **`app.py`**: Flask tabanlı web sunucusu ve reaktif arayüz.

---

## 📄 Lisans
Bu proje [MIT](LICENSE) lisansı ile lisanslanmıştır. Geliştirici: [Devran Sever](https://github.com/DevranTheDeveloper).
