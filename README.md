<div align="center">

# AuthentiScan

### AI-Powered Product Authenticity & Review Verification System

<p align="center">
Detect counterfeit products and misleading reviews using Machine Learning and Artificial Intelligence.
</p>

<p align="center">

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![TensorFlow](https://img.shields.io/badge/TensorFlow-FF6F00?style=flat-square&logo=tensorflow&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)
![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)

</p>

---

<img src="screenshots/banner.gif" width="900"/>

*A secure AI-powered platform for verifying product authenticity and detecting fake reviews.*

</div>

---

# Overview

AuthentiScan is a web application that combines Artificial Intelligence and Machine Learning to help users identify counterfeit products and detect fake or manipulated customer reviews before making purchasing decisions.

The platform provides an intuitive interface where users can analyze products, verify authenticity, and receive AI-generated insights within seconds.

---

# Key Features

| Feature | Description |
|----------|-------------|
| Product Verification | Detects counterfeit products using a trained deep learning model. |
| Fake Review Detection | Identifies suspicious and AI-generated reviews using NLP. |
| Secure Authentication | User login and authentication system. |
| FastAPI Backend | Lightweight REST API for efficient processing. |
| Interactive Interface | Clean and responsive frontend built using HTML, CSS and JavaScript. |
| Machine Learning Models | TensorFlow and Scikit-Learn powered prediction models. |

---

# Technology Stack

| Layer | Technologies |
|--------|--------------|
| Frontend | HTML5, CSS3, JavaScript |
| Backend | Python, FastAPI |
| Machine Learning | TensorFlow, Scikit-Learn |
| Database | SQLite |
| Development | VS Code, Git, GitHub |

---

# Repository Structure

```text
AuthentiScan
│
├── app.js
├── database.py
├── fake_product_detector.keras
├── index.html
├── login.css
├── login.js
├── model_db.py
├── review_model.pkl
├── server.py
├── styles.css
├── vectorizer.pkl
├── README.md
└── LICENSE
```

---

# Getting Started

## Clone the Repository

```bash
git clone https://github.com/vex-codex/Authentiscan.git
```

Move into the project directory.

```bash
cd Authentiscan
```

Create a virtual environment.

```bash
python -m venv .venv
```

Activate the environment.

### Windows

```powershell
.\.venv\Scripts\Activate.ps1
```

### Linux / macOS

```bash
source .venv/bin/activate
```

Install dependencies.

```bash
pip install -r requirements.txt
```

Run the application.

```bash
python server.py
```

Open your browser.

```
http://127.0.0.1:8000
```

---

# Machine Learning Models

| Model | Purpose |
|--------|---------|
| fake_product_detector.keras | Product authenticity detection |
| review_model.pkl | Fake review classification |
| vectorizer.pkl | Text preprocessing and vectorization |

---

# Application Preview

<div align="center">

| Home | Login |
|------|-------|
| <img src="screenshots/home.png" width="420"> | <img src="screenshots/login.png" width="420"> |

| Result Dashboard |
|------------------|
| <img src="screenshots/result.png" width="850"> |

</div>

---

# Future Scope

- QR Code Verification
- Barcode Scanner
- OCR-based Product Analysis
- Cloud Database
- User Dashboard
- Admin Dashboard
- Analytics and Reporting

---

# Author

**Sakshi Patel**

Computer Engineering Student

GitHub: https://github.com/vex-codex

---

# License

Distributed under the MIT License.
