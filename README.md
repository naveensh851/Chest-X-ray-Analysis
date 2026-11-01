# 🩺 AI Chest X-ray Diagnosis System

![Status](https://img.shields.io/badge/Status-Live-brightgreen?style=for-the-badge)
![React](https://img.shields.io/badge/Frontend-React-61DAFB?style=for-the-badge&logo=react)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi)
![TensorFlow](https://img.shields.io/badge/Model-TensorFlow-FF6F00?style=for-the-badge&logo=tensorflow)
![EfficientNet](https://img.shields.io/badge/Architecture-EfficientNetB0-blue?style=for-the-badge)
![GradCAM](https://img.shields.io/badge/XAI-Grad--CAM-purple?style=for-the-badge)

An AI-powered web application for analyzing chest X-ray images, detecting diseases, and visualizing affected regions using deep learning and explainable AI.

---

## ✅ What's Working

| Feature | Status |
|---|---|
| React Frontend (Vite + Tailwind) | ✅ Complete |
| FastAPI Backend | ✅ Complete |
| JWT Authentication (register / login) | ✅ Complete |
| Real EfficientNetB0 ML Model | ✅ Integrated |
| 5-Class Disease Classification | ✅ Live |
| Grad-CAM Heatmap Visualization | ✅ Live |
| Per-user Report Storage (SQLite) | ✅ Complete |
| REST API for predictions & reports | ✅ Complete |

---

## 🧠 Problem Statement

Chest X-ray interpretation requires expert radiologists and can be time-consuming and error-prone. This project builds an automated AI assistant that:

- Classifies chest X-rays into 5 disease categories
- Highlights the regions of the image that influenced the prediction (Grad-CAM)
- Stores per-user diagnostic reports for review

> ⚠️ **Disclaimer:** This project is for educational purposes only and is **not** intended for clinical or diagnostic use.

---

## 💡 How It Works

```
Upload X-ray
    ↓
Grayscale → Resize (224×224) → Stack ×3 → EfficientNet preprocess_input
    ↓
EfficientNetB0 (5-class sigmoid) → Prediction + Confidence
    ↓
Grad-CAM (top_conv layer) → Heatmap overlay on original image
    ↓
Save report + heatmap → Return JSON response → Display in UI
```

---

## 🤖 ML Model

### Architecture

```
EfficientNetB0 (weights=None, include_top=False, input_shape=(224,224,3))
    → GlobalAveragePooling2D
    → BatchNormalization
    → Dense(256, relu)
    → Dropout(0.5)
    → Dense(5, sigmoid)          ← multi-label output
```

### Classes

| Index | Disease |
|---|---|
| 0 | Infiltration |
| 1 | Effusion |
| 2 | Atelectasis |
| 3 | Nodule |
| 4 | Mass |

### Preprocessing Pipeline

1. Convert image to **grayscale** (X-rays are monochrome)
2. Resize to **224 × 224**
3. Convert to float32 array
4. **Stack × 3** to create 3-channel input (H, W, 3)
5. Apply `preprocess_input` (EfficientNet-specific normalization)
6. Expand batch dimension → shape `(1, 224, 224, 3)`

### Weights

```
backend/model/model_5class_balanced_weights.h5   (~18 MB, class-balanced training)
```

---

## 🔥 Grad-CAM (Explainable AI)

The system uses **Gradient-weighted Class Activation Mapping (Grad-CAM)** to show *which regions of the X-ray influenced the prediction*.

- **Target layer:** `top_conv` (final convolutional layer of EfficientNetB0, output 7×7)
- **Algorithm:** `tf.GradientTape` → gradients of predicted class score w.r.t. `top_conv` feature maps → global average pool → weighted sum → ReLU → normalize
- **Overlay:** JET colormap blended at 45% opacity onto the original X-ray
- **Fallback:** Pure-NumPy JET colormap if OpenCV is not installed
- **Saved to:** `backend/uploads/heatmaps/<uuid>.png`

---

## 🏗️ Tech Stack

### Frontend
- **React** (Vite)
- **Tailwind CSS**
- **Axios** (with JWT interceptors)

### Backend
- **FastAPI** (Python)
- **SQLite** + SQLAlchemy ORM
- **JWT** Authentication (python-jose)
- **Pillow** for image handling
- **python-multipart** for file uploads

### AI / ML
- **TensorFlow / Keras** ≥ 2.13
- **EfficientNetB0** (custom-trained, no ImageNet weights)
- **NumPy** ≥ 1.24
- **Grad-CAM** via `tf.GradientTape`

---

## 📂 Project Structure

```
xray-app/
├── backend/
│   ├── main.py                          # FastAPI app — auth, predict, reports
│   ├── requirements.txt
│   ├── model/
│   │   ├── model_5class_balanced_weights.h5   # Trained weights
│   │   ├── inference_5class.py                # Standalone inference module
│   │   └── model_5class.py
│   ├── uploads/
│   │   └── heatmaps/                    # Generated Grad-CAM heatmap images
│   └── xray_app.db                      # SQLite database
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.jsx
│   │   │   ├── Loader.jsx
│   │   │   ├── ResultCard.jsx
│   │   │   ├── ReportModal.jsx
│   │   │   ├── UploadSection.jsx
│   │   │   └── PrivateRoute.jsx
│   │   ├── pages/
│   │   │   ├── Home.jsx
│   │   │   ├── Login.jsx
│   │   │   └── Reports.jsx
│   │   ├── services/api.js
│   │   ├── context/AuthContext.jsx
│   │   └── main.jsx
│   ├── index.html
│   ├── vite.config.js
│   └── tailwind.config.js
│
└── README.md
```

---

## ⚙️ Setup & Running

### Prerequisites
- Python 3.9+
- Node.js 18+
- ~500 MB disk space (TensorFlow + model weights)

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn main:app --reload
```

Server runs at: **http://127.0.0.1:8000**

On startup you'll see:
```
INFO  Building EfficientNetB0 architecture (balanced) …
INFO  EfficientNetB0 model loaded successfully (4383912 params).
INFO  Application startup complete.
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: **http://localhost:5173**

---

## 🔌 API Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | ❌ | Register new user |
| `POST` | `/auth/login` | ❌ | Login, returns JWT |
| `POST` | `/predict` | ✅ | Upload X-ray → get prediction + heatmap |
| `GET` | `/reports` | ✅ | List all reports for current user |
| `GET` | `/reports/{id}` | ✅ | Get single report |
| `GET` | `/uploads/heatmaps/{file}` | ❌ | Serve heatmap image |

### Predict Response Example

```json
{
  "disease": "Effusion",
  "confidence": 0.87,
  "report": "The X-ray suggests signs of Effusion with confidence 0.87",
  "heatmap_url": "http://localhost:8000/uploads/heatmaps/abc123.png",
  "report_id": 42
}
```

---

## 👨‍💻 Authors

### 🧑‍💻 Naveen Sharma
[![GitHub](https://img.shields.io/badge/GitHub-naveensh851-181717?style=for-the-badge&logo=github)](https://github.com/naveensh851)

Frontend, Backend Integration, ML Integration & Deployment

---

### 🧑‍💻 Himanshu Ranglani
[![GitHub](https://img.shields.io/badge/GitHub-himanshu--ranglani-181717?style=for-the-badge&logo=github)](https://github.com/himanshu-ranglani)

Model Training, Data Preparation & Evaluation

---

## 📌 Future Scope

- [ ] Multi-label prediction (multiple diseases per scan)
- [ ] PDF report export
- [ ] Cloud deployment (Render / Railway / GCP)
- [ ] DICOM file support
- [ ] Doctor review / annotation layer
- [ ] Mobile responsive improvements

---

## ⭐ Support

If you like this project, consider giving it a ⭐ on GitHub!
