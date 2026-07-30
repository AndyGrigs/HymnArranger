# 🎵 HymnArranger

> AI-powered web app for automatic arrangement of Christian hymn melodies

[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Python-green.svg)](https://fastapi.tiangolo.com/)
[![Hugging Face](https://img.shields.io/badge/🤗-Hugging%20Face-yellow.svg)](https://huggingface.co/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-In%20Development-yellow.svg)]()

---

🌐 **Available in:** [🇺🇦 Українська](README.ua.md) | [🇩🇪 Deutsch](README.de.md)

---

## 📖 About the Project

**HymnArranger** is a full-stack web application that uses an ML model to automatically arrange Christian hymn melodies. The user uploads a melody, selects a style (bayan, piano, strings), and receives a complete arrangement directly in the browser — with the option to download PDF, MIDI, or MusicXML.

---

## 🏗️ Product Architecture

```
┌─────────────────────────────────────┐
│           FRONTEND (UI)             │
│  - Melody upload                    │
│  - Style selection (bayan / piano)  │
│  - Sheet music preview online       │
│  - PDF / MIDI download              │
└────────────────┬────────────────────┘
                 │ REST API
┌────────────────▼────────────────────┐
│           BACKEND (API)             │
│  - MusicXML / MIDI processing       │
│  - ML model inference               │
│  - PDF generation via MuseScore     │
│  - Result storage                   │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│           ML MODEL                  │
│  - Fine-tuned Music Transformer     │
│  - Hugging Face inference           │
└─────────────────────────────────────┘
```

---

## 🎯 Target Audience

- **Church musicians** — quickly create arrangements for worship services
- **ML developers** — a practical example of applying transformers to symbolic music generation
- **Music teachers** — a tool for demonstrating melody harmonization
- **Anyone interested** in the intersection of artificial intelligence and music

---

## ✨ Features

- 🎼 Accepts melody input in MusicXML or MIDI format
- 🪗 Generates arrangements in the selected style (bayan, piano, strings)
- 👁️ Sheet music preview directly in the browser (OpenSheetMusicDisplay)
- 📄 Download results in PDF, MIDI, or MusicXML format
- ☁️ ML model hosted on Hugging Face Spaces

---

## 🛠️ Tech Stack

| Part | Technology | Why |
|------|-----------|-----|
| **Frontend** | Next.js + TypeScript | Fast development, SSR |
| **UI components** | Tailwind + shadcn/ui | Fast and beautiful |
| **Sheet viewer** | OpenSheetMusicDisplay | MusicXML rendering in browser |
| **Backend** | Python FastAPI | Perfect for ML integration |
| **ML model** | Hugging Face + PyTorch | Fine-tuned transformer |
| **Conversion** | music21 + MuseScore CLI | MusicXML → PDF / MIDI |
| **Database** | PostgreSQL | Song and result storage |
| **Model hosting** | Hugging Face Spaces | Free for demo |
| **Deploy** | AWS / Vercel + Railway | Proven stack |

---

## 📁 Project Structure

```
HymnArranger/
├── frontend/                # Next.js app
│   ├── app/
│   │   ├── page.tsx         # Home page
│   │   ├── arrange/         # Arrangement page
│   │   └── results/         # Results viewer
│   └── components/
│       ├── MelodyUploader   # File upload
│       ├── StyleSelector    # Style selection
│       └── SheetViewer      # Sheet music viewer
│
├── backend/                 # FastAPI server
│   ├── main.py              # Entry point
│   ├── routes/
│   │   ├── arrange.py       # POST /arrange
│   │   └── download.py      # GET /download/{id}
│   ├── services/
│   │   ├── ml_service.py    # Model inference
│   │   ├── music_service.py # music21 processing
│   │   └── pdf_service.py   # PDF generation
│   └── models/              # Pydantic schemas
│
├── ml/                      # ML part
│   ├── dataset/
│   ├── notebooks/
│   └── model/
│
└── dataset/                 # Dataset
```

---

## 🚀 User Flow

```
1. User uploads a melody (MusicXML or MIDI)
            ↓
2. Selects a style: 🪗 Bayan / 🎹 Piano / 🎻 Strings
            ↓
3. Clicks "Arrange"
            ↓
4. Sees sheet music directly in the browser (OpenSheetMusicDisplay)
            ↓
5. Downloads PDF / MIDI / MusicXML
```

---

## 🚀 Quick Start

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

---

## 📊 Dataset

The dataset is collected from publicly available sources of Christian choral music (noty-bratstvo.org): bayan arrangements paired with automatically extracted melody lines. All data is unified into MusicXML format.

| Split | Target size | Format |
|-------|-------------|--------|
| train | ~80% of total | MusicXML |
| val   | ~20% of total | MusicXML |

> **Note:** All materials used are publicly available. This project has no commercial purpose.

---

## 📈 Roadmap

- [x] Define project architecture
- [ ] Collect and prepare dataset *(in progress)*
- [ ] Fine-tune ML model
- [ ] Backend API (FastAPI)
- [ ] Frontend (Next.js)
- [ ] OpenSheetMusicDisplay integration
- [ ] Deploy to Vercel + Railway

---

## 🤝 Contributing

Contributions are welcome! Here's how to get involved:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m 'Add my feature'`)
4. Push the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

---

## 👤 Author

**Andrii** — Teacher, Developer, Musician

- Focus areas: Full-Stack Development, ML, Music Data Processing
- Tech stack: Python, TypeScript, Next.js, Node.js, AWS, Hugging Face

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

*Made with ❤️ for musicians and developers*
