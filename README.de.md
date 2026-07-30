# 🎵 HymnArranger

> KI-gestützte Web-App zur automatischen Harmonisierung christlicher Kirchenlieder

[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Python-green.svg)](https://fastapi.tiangolo.com/)
[![Hugging Face](https://img.shields.io/badge/🤗-Hugging%20Face-yellow.svg)](https://huggingface.co/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-In%20Entwicklung-yellow.svg)]()

---

🌐 **Verfügbar in:** [🇬🇧 English](README.md) | [🇺🇦 Українська](README.ua.md)

---

## Projektbeschreibung

**HymnArranger** ist eine vollständige Web-Anwendung, die ein ML-Modell verwendet, um Melodien christlicher Kirchenlieder automatisch zu arrangieren. Der Nutzer lädt eine Melodie hoch, wählt einen Stil (Bajan, Klavier, Streicher) und erhält ein fertiges Arrangement direkt im Browser — mit der Möglichkeit, PDF, MIDI oder MusicXML herunterzuladen.

---

## 🏗️ Produktarchitektur

```
┌─────────────────────────────────────┐
│           FRONTEND (UI)             │
│  - Melodie hochladen                │
│  - Stil wählen (Bajan / Klavier)    │
│  - Noten online ansehen             │
│  - PDF / MIDI herunterladen         │
└────────────────┬────────────────────┘
                 │ REST API
┌────────────────▼────────────────────┐
│           BACKEND (API)             │
│  - MusicXML / MIDI verarbeiten      │
│  - ML-Modell aufrufen               │
│  - PDF-Erzeugung via MuseScore      │
│  - Ergebnisse speichern             │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│           ML-MODELL                 │
│  - Fine-tuned Music Transformer     │
│  - Hugging Face Inferenz            │
└─────────────────────────────────────┘
```

---

## Zielgruppe

- **Musiker in Kirchengemeinden** — schnelle Erstellung von Arrangements für Gottesdienste
- **ML-Entwickler** — Beispiel für den Einsatz von Transformern zur symbolischen Musikgenerierung
- **Musiklehrer** — Werkzeug zur Veranschaulichung von Melodieharmonisierung
- **Alle Interessierten** an der Schnittstelle von Künstlicher Intelligenz und Musik

---

## Funktionen

- 🎼 Eingabe einer Melodie im Format MusicXML oder MIDI
- 🪗 Generierung eines Arrangements im gewählten Stil (Bajan, Klavier, Streicher)
- 👁️ Notenansicht direkt im Browser (OpenSheetMusicDisplay)
- 📄 Download des Ergebnisses als PDF, MIDI oder MusicXML
- ☁️ ML-Modell gehostet auf Hugging Face Spaces

---

## Technologien

| Teil | Technologie | Warum |
|------|------------|-------|
| **Frontend** | Next.js + TypeScript | Schnelle Entwicklung, SSR |
| **UI-Komponenten** | Tailwind + shadcn/ui | Schnell und schön |
| **Notenansicht** | OpenSheetMusicDisplay | MusicXML-Rendering im Browser |
| **Backend** | Python FastAPI | Ideal für ML-Integration |
| **ML-Modell** | Hugging Face + PyTorch | Fine-tuned Transformer |
| **Konvertierung** | music21 + MuseScore CLI | MusicXML → PDF / MIDI |
| **Datenbank** | PostgreSQL | Speicherung von Songs und Ergebnissen |
| **Modell-Hosting** | Hugging Face Spaces | Kostenlos für Demo |
| **Deployment** | AWS / Vercel + Railway | Bewährter Stack |

---

## Projektstruktur

```
HymnArranger/
├── frontend/                # Next.js App
│   ├── app/
│   │   ├── page.tsx         # Startseite
│   │   ├── arrange/         # Arrangierseite
│   │   └── results/         # Ergebnisansicht
│   └── components/
│       ├── MelodyUploader   # Datei-Upload
│       ├── StyleSelector    # Stil-Auswahl
│       └── SheetViewer      # Notenansicht
│
├── backend/                 # FastAPI-Server
│   ├── main.py              # Einstiegspunkt
│   ├── routes/
│   │   ├── arrange.py       # POST /arrange
│   │   └── download.py      # GET /download/{id}
│   ├── services/
│   │   ├── ml_service.py    # Modellaufruf
│   │   ├── music_service.py # music21-Verarbeitung
│   │   └── pdf_service.py   # PDF-Erzeugung
│   └── models/              # Pydantic-Schemas
│
├── ml/                      # ML-Teil
│   ├── dataset/
│   ├── notebooks/
│   └── model/
│
└── dataset/                 # Datensatz
```

---

## Nutzerablauf

```
1. Nutzer lädt eine Melodie hoch (MusicXML oder MIDI)
            ↓
2. Wählt einen Stil: 🪗 Bajan / 🎹 Klavier / 🎻 Streicher
            ↓
3. Klickt auf „Arrangieren"
            ↓
4. Sieht die Noten direkt im Browser (OpenSheetMusicDisplay)
            ↓
5. Lädt PDF / MIDI / MusicXML herunter
```

---

## Schnellstart

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

## Datensatz

Der Datensatz wird aus frei zugänglichen Quellen christlicher Chormusik (noty-bratstvo.org) zusammengestellt: Bajan-Arrangements zusammen mit den daraus automatisch extrahierten Melodielinien. Alle Daten werden im Format MusicXML vereinheitlicht.

| Teilmenge | Zielanzahl | Format |
|-----------|--------------|--------|
| train     | ~80% gesamt  | MusicXML |
| val       | ~20% gesamt  | MusicXML |

> **Hinweis:** Alle verwendeten Materialien sind frei zugänglich. Das Projekt verfolgt keine kommerziellen Zwecke.

---

## Aktueller Status

- [x] Projektarchitektur festgelegt
- [ ] Datensatz gesammelt und vorbereitet *(in Bearbeitung)*
- [ ] ML-Modell fine-tunen
- [ ] Backend API (FastAPI)
- [ ] Frontend (Next.js)
- [ ] OpenSheetMusicDisplay Integration
- [ ] Deployment auf Vercel + Railway

---

## Mitwirken

Beiträge sind willkommen! So kannst du mitmachen:

1. Repository forken
2. Feature-Branch erstellen (`git checkout -b feature/mein-feature`)
3. Änderungen committen (`git commit -m 'Add mein-feature'`)
4. Branch pushen (`git push origin feature/mein-feature`)
5. Pull Request öffnen

---

## 👤 Autor

**Andrii** — Lehrer, Entwickler, Musiker

- Schwerpunkte: Full-Stack-Entwicklung, ML, Verarbeitung von Musikdaten
- Tech-Stack: Python, TypeScript, Next.js, Node.js, AWS, Hugging Face

---

## Lizenz

Dieses Projekt steht unter der MIT-Lizenz. Details siehe [LICENSE](LICENSE).

---

*Mit ❤️ für Musiker und Entwickler erstellt*
