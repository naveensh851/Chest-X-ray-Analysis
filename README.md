# AI Chest X-ray Diagnosis System

![Status](https://img.shields.io/badge/Status-Live-brightgreen?style=for-the-badge)
![React](https://img.shields.io/badge/Frontend-React-61DAFB?style=for-the-badge&logo=react)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi)
![TensorFlow](https://img.shields.io/badge/Model-TensorFlow-FF6F00?style=for-the-badge&logo=tensorflow)
![EfficientNet](https://img.shields.io/badge/Architecture-EfficientNetB0-blue?style=for-the-badge)
![GradCAM](https://img.shields.io/badge/XAI-Grad--CAM-purple?style=for-the-badge)

An AI-powered web application for analyzing chest X-ray images, detecting diseases, and visualizing affected regions using deep learning and explainable AI.

---

## Features

| Feature | Status |
|---|---|
| React Frontend (Vite + Tailwind) | Complete |
| FastAPI Backend | Complete |
| JWT Authentication (register / login) | Complete |
| EfficientNetB0 ML Model | Integrated |
| 5-Class Disease Classification | Live |
| Grad-CAM Heatmap Visualization | Live |
| Per-user Report Storage (SQLite) | Complete |
| REST API for predictions & reports | Complete |

---

## Problem Statement

Chest X-ray interpretation requires expert radiologists and can be time-consuming and error-prone. This project builds an automated AI assistant that:

- Classifies chest X-rays into 5 disease categories
- Highlights the regions of the image that influenced the prediction using Grad-CAM
- Stores per-user diagnostic reports for review

> **Disclaimer:** This project is for educational purposes only and is not intended for clinical or diagnostic use.

---

## How It Works

```
Upload X-ray
    |
Grayscale -> Resize (224x224) -> Stack x3 -> EfficientNet preprocess_input
    |
EfficientNetB0 (5-class sigmoid) -> Prediction + Confidence
    |
Grad-CAM (top_conv layer) -> Heatmap overlay on original image
    |
Save report + heatmap -> Return JSON response -> Display in UI
```

---

## ML Model

### Architecture

```
EfficientNetB0 (weights=None, include_top=False, input_shape=(224,224,3))
    -> GlobalAveragePooling2D
    -> BatchNormalization
    -> Dense(256, relu)
    -> Dropout(0.5)
    -> Dense(5, sigmoid)
```

### Output Classes

| Index | Disease |
|---|---|
| 0 | Infiltration |
| 1 | Effusion |
| 2 | Atelectasis |
| 3 | Nodule |
| 4 | Mass |

### Preprocessing Pipeline

1. Convert image to grayscale (X-rays are monochrome)
2. Resize to 224 x 224
3. Convert to float32 array
4. Stack x3 to create 3-channel input (H, W, 3)
5. Apply `preprocess_input` — EfficientNet-specific normalization
6. Expand batch dimension — final shape `(1, 224, 224, 3)`

### Weights

```
backend/model/model_5class_balanced_weights.h5   (~18 MB, class-balanced training)
```

---

## Grad-CAM — Explainable AI

The system uses **Gradient-weighted Class Activation Mapping (Grad-CAM)** to identify which regions of the X-ray influenced the model's prediction.

- **Target layer:** `top_conv` — final convolutional layer of EfficientNetB0, feature map size 7x7
- **Algorithm:** `tf.GradientTape` computes gradients of the predicted class score with respect to the `top_conv` feature maps. Gradients are globally average-pooled, used to weight the feature maps, summed, passed through ReLU, and normalized.
- **Overlay:** JET colormap blended at 45% opacity onto the original X-ray
- **Fallback:** Pure-NumPy JET colormap if OpenCV is not installed
- **Output path:** `backend/uploads/heatmaps/<uuid>.png`

---

## Tech Stack

### Frontend
- React (Vite)
- Tailwind CSS
- Axios with JWT interceptors

### Backend
- FastAPI (Python)
- SQLite with SQLAlchemy ORM
- JWT Authentication via python-jose
- Pillow for image processing
- python-multipart for file uploads

### AI / ML
- TensorFlow / Keras >= 2.13
- EfficientNetB0 (custom-trained, no ImageNet weights)
- NumPy >= 1.24
- Grad-CAM via `tf.GradientTape`

---

## Project Structure

```
xray-app/
├── backend/
│   ├── main.py                               # FastAPI application — auth, predict, reports
│   ├── requirements.txt
│   ├── model/
│   │   ├── model_5class_balanced_weights.h5  # Trained model weights
│   │   ├── inference_5class.py               # Standalone inference module
│   │   └── model_5class.py
│   ├── uploads/
│   │   └── heatmaps/                         # Grad-CAM heatmap output images
│   └── xray_app.db                           # SQLite database
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

## Setup and Running

### Prerequisites
- Python 3.9 or higher
- Node.js 18 or higher
- Approximately 500 MB disk space (TensorFlow + model weights)

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux / macOS

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn main:app --reload
```

Server runs at: `http://127.0.0.1:8000`

Expected startup output:
```
INFO  Building EfficientNetB0 architecture (balanced) ...
INFO  EfficientNetB0 model loaded successfully (4383912 params).
INFO  Application startup complete.
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: `http://localhost:5173`

---

## API Reference

| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `POST` | `/auth/register` | No | Register a new user |
| `POST` | `/auth/login` | No | Login and receive a JWT token |
| `POST` | `/predict` | Yes | Upload an X-ray image, returns prediction and heatmap |
| `GET` | `/reports` | Yes | List all reports for the authenticated user |
| `GET` | `/reports/{id}` | Yes | Retrieve a single report by ID |
| `GET` | `/uploads/heatmaps/{file}` | No | Serve a generated heatmap image |

### Prediction Response Example

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

## Authors

**Naveen Sharma**
[![GitHub](https://img.shields.io/badge/GitHub-naveensh851-181717?style=for-the-badge&logo=github)](https://github.com/naveensh851)

Frontend, Backend Integration, ML Integration & Deployment

---

**Himanshu Ranglani**
[![GitHub](https://img.shields.io/badge/GitHub-himanshu--ranglani-181717?style=for-the-badge&logo=github)](https://github.com/himanshu-ranglani)

Model Training, Data Preparation & Evaluation

---

## Future Scope

- Multi-label prediction — detecting multiple diseases per scan
- PDF report export
- Cloud deployment (Render / Railway / GCP)
- DICOM file format support
- Doctor review and annotation layer
- Mobile-responsive UI improvements

---

## Support

If you find this project useful, consider giving it a star on GitHub.
