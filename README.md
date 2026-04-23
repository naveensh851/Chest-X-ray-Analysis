# 🩺 AI Chest X-ray Diagnosis System 🚧 *(In Progress)*

![AI](https://img.shields.io/badge/Status-In%20Progress-yellow?style=for-the-badge)
![React](https://img.shields.io/badge/Frontend-React-61DAFB?style=for-the-badge\&logo=react)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge\&logo=fastapi)
![TensorFlow](https://img.shields.io/badge/Model-TensorFlow-FF6F00?style=for-the-badge\&logo=tensorflow)

An AI-powered web application for analyzing chest X-ray images, detecting diseases, and visualizing affected regions using deep learning.

---

## 🚀 Current Status

This project is actively under development.

### ✅ Completed

* Frontend UI (React)
* Backend API (FastAPI)
* Authentication system (JWT)
* Reports storage system
* Heatmap visualization pipeline

### 🚧 In Progress

* Final model integration
* Performance tuning
* Deployment

---

## 🧠 Problem Statement

Chest X-ray interpretation requires expert radiologists and can be time-consuming. This project aims to build an automated system that assists in detecting diseases and highlighting critical regions in X-ray images.

---

## 💡 Solution (Planned)

* AI-based multi-disease classification
* Grad-CAM heatmap visualization
* User-based report management

---

## 🏗️ Tech Stack

### Frontend

* React (Vite)
* Tailwind CSS
* Axios

### Backend

* FastAPI
* SQLite
* JWT Authentication

### AI / ML

* TensorFlow / Keras
* EfficientNetB0
* Grad-CAM (Explainable AI)

---

## 🔄 Pipeline (Planned)

```text id="7kebvr"
Upload → Preprocess → Model → Prediction → Heatmap → Save → Display
```

---

## 📂 Project Structure

```bash id="xg55h6"
xray-app/
├── backend/
│   ├── main.py
│   ├── model/
│   ├── uploads/
│   ├── xray_app.db
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│
├── README.md
```

---

## ⚙️ Setup (Without Model)

### Backend

```bash id="ws2vba"
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend

```bash id="sdc2hm"
cd frontend
npm install
npm run dev
```

---

## ⚠️ Model Not Included

The trained model weights are currently not included in this repository.

👉 As a result:

* The app will run successfully
* But real predictions will not work yet

---

## 👨‍💻 Authors

### 🧑‍💻 Naveen Sharma

[![GitHub](https://img.shields.io/badge/GitHub-naveensh851-181717?style=for-the-badge\&logo=github)](https://github.com/naveensh851)
Frontend, Backend Integration & Deployment

---

### 🧑‍💻 Himanshu Ranglani

[![GitHub](https://img.shields.io/badge/GitHub-himanshu-ranglani-181717?style=for-the-badge\&logo=github)](https://github.com/himanshu-ranglani)
Model Training, Data Preparation & Evaluation

---

## 📌 Future Scope

* Complete model integration
* Multi-label predictions
* Deployment (cloud)
* PDF report export

---

## ⚠️ Disclaimer

This project is for educational purposes only and not intended for clinical use.

---

## ⭐ Support

If you like this project, consider giving it a ⭐ on GitHub!
