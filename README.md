# SocialGuard — Social Media Analytics with Modified Content Detection

A full-stack web application for analyzing Instagram post engagement and detecting manipulated content using CNN (image) and BERT/NLP (text) models.

---

## 📁 Project Structure

```
social_media_analytics/
├── app.py                        # Flask application & routes
├── schema.sql                    # MySQL database schema + seed data
├── requirements.txt              # Python dependencies
│
├── ml_modules/
│   ├── __init__.py
│   ├── image_detector.py         # CNN-based image tampering detection (ELA + MobileNetV2)
│   └── text_detector.py          # BERT + rule-based text manipulation detection
│
├── templates/
│   ├── dashboard.html            # Main analytics dashboard
│   ├── analyze.html              # Post submission & analysis form
│   ├── result.html               # Per-post analysis result page
│   ├── posts.html                # All posts with filter tabs
│   └── partials/
│       ├── navbar.html
│       └── sidebar.html
│
└── static/
    ├── css/style.css             # Full custom stylesheet (dark theme)
    ├── js/charts.js              # Chart.js dashboard visualizations
    └── uploads/                  # Uploaded post images (auto-created)
```

---

## ⚙️ Setup Guide

### 1. Prerequisites
- Python 3.10+
- MySQL 8.0+
- pip

### 2. Create & activate virtual environment
```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```
> For CPU-only (no GPU), replace `torch==2.3.0` with:
> `pip install torch --index-url https://download.pytorch.org/whl/cpu`

### 4. Set up MySQL database
```bash
mysql -u root -p < schema.sql
```
Then update credentials in `app.py`:
```python
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'your_password'
```

### 5. Run the application
```bash
python app.py
```
Open: **http://localhost:5000**

---

## 🧠 ML Modules

### Image Tampering Detection (`ml_modules/image_detector.py`)

**Pipeline:**
1. **ELA (Error Level Analysis)** — Re-saves image at lower JPEG quality and computes pixel difference to highlight re-edited regions
2. **MobileNetV2 CNN** — Pre-trained on ImageNet, fine-tuned for tamper vs. authentic classification
3. **Heuristic Fallback** — ELA statistics (mean, std, high-pixel ratio) used when CNN is not loaded

**Training your own model:**
```python
from ml_modules.image_detector import ImageTamperingDetector

detector = ImageTamperingDetector()
detector.train(
    train_dir='data/train',   # folders: authentic/ and tampered/
    val_dir='data/val',
    epochs=30,
    save_path='ml_modules/cnn_weights.h5'
)
```

**Recommended datasets:**
- [CASIA Image Tampering Dataset](https://github.com/namtpham/casia2groundtruth)
- [Columbia Uncompressed Image Splicing Detection](https://www.ee.columbia.edu/ln/dvmm/downloads/AuthSplicedDataSet/)

---

### Text Manipulation Detection (`ml_modules/text_detector.py`)

**Pipeline:**
1. **BERT Fake-News Classifier** — `hamzab/roberta-fake-news-classifier` via HuggingFace
2. **Sentiment Analysis** — Secondary signal using DistilBERT sentiment
3. **Rule-Based Engine** — 15+ pattern rules covering:
   - Urgency/pressure language
   - Sensationalism & clickbait
   - Conspiracy indicators
   - Excessive punctuation / ALL CAPS
   - Fake credibility claims
   - Suspicious hashtags

**Ensemble scoring:**
```
final_score = 0.6 × BERT_score + 0.4 × rule_score + sentiment_penalty
```

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Dashboard |
| GET/POST | `/analyze` | Submit & analyze post |
| GET | `/posts` | All posts (supports `?filter=flagged/clean/image/text`) |
| POST | `/api/analyze-text` | JSON API — quick text check |
| GET | `/api/stats` | JSON API — aggregate stats |
| POST | `/posts/delete/<id>` | Delete a post |

### Example API usage
```bash
curl -X POST http://localhost:5000/api/analyze-text \
  -H "Content-Type: application/json" \
  -d '{"text": "SHARE NOW!! They do not want you to know this!!"}'
```

---

## 📊 Engagement Score Formula

```
engagement_score = ((likes + comments) / followers) × 100
```

| Score | Classification |
|-------|---------------|
| > 10% | Viral |
| 3–10% | Strong |
| 1–3%  | Average |
| < 1%  | Low |

---

## 🔮 Future Improvements

- [ ] Batch CSV import for bulk analysis
- [ ] Export reports to PDF
- [ ] Real Instagram API integration (Graph API)
- [ ] User authentication & multi-tenant support
- [ ] Fine-tuned BERT on social-media-specific fake content dataset
- [ ] Video content detection (deepfake)
- [ ] Email/Slack alerts for suspicious content

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5, CSS3, Bootstrap 5, Chart.js |
| Backend | Python 3, Flask |
| Database | MySQL 8 |
| Image ML | TensorFlow/Keras, MobileNetV2, Pillow |
| Text ML | HuggingFace Transformers, PyTorch, BERT |
