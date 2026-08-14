# 🎵 HymnArranger

> A rule-based, deterministic generator of bayan (button accordion) arrangements from a monophonic melody

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![music21](https://img.shields.io/badge/music21-10.5.0-informational.svg)](https://web.mit.edu/music21/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18%20%2B%20Vite-61DAFB.svg)](https://react.dev/)
[![Status](https://img.shields.io/badge/Status-Active%20Development-yellow.svg)]()

---

🌐 **Available in:** [🇺🇦 Українська](README.ua.md) | [🇩🇪 Deutsch](README.de.md)

---

## 📖 About the Project

**HymnArranger** takes a monophonic melody (MusicXML) and produces a complete two-staff bayan arrangement — a figured right-hand melody line and a Stradella-bass left hand — using a **deterministic, rule-based engine** built on [music21](https://web.mit.edu/music21/), not a black-box neural model.

Christian hymn repertoire is the project's working corpus, and the author's own experience as a bayan player and arranger shaped the musical rules. The engine itself targets any musician or arranger working with melodic material, with bayan as the first implemented instrument style.

A separate, fully-trained neural network was also built and evaluated as a **research baseline** to justify the rule-based approach (see [ML Baseline](#-ml-baseline-research-track) below) — it is not part of the shipped product.

---

## 🏗️ Architecture

```
┌───────────────────────────────────────┐
│      FRONTEND — React + Vite + TS      │
│  - upload a melody or write it in a    │
│    Flat.io embedded editor             │
│  - pick a preset / suite / "all" mode  │
│  - sheet preview (OpenSheetMusicDisplay)│
│  - MIDI playback (GM Accordion)        │
│  - download MusicXML / MIDI            │
└───────────────────┬─────────────────────┘
                     │ REST
┌───────────────────▼─────────────────────┐
│      BACKEND — FastAPI (Python)         │
│  GET  /health                           │
│  POST /presets   — meter + preset list  │
│  POST /arrange    — mode=single|all|suite│
│  POST /midi                             │
└───────────────────┬─────────────────────┘
                     │
┌───────────────────▼─────────────────────┐
│   ARRANGEMENT ENGINE — hymnarranger/     │
│   (music21, rule-based, deterministic)   │
│  - parsing, harmony, figuration          │
│  - Stradella left hand + voice leading   │
│  - textural presets per meter type       │
│  - suite: theme + variations (seeded)    │
└───────────────────────────────────────────┘

   Separate research track (not served in production):
   an encoder-decoder Music Transformer (RPR), trained on
   Google Colab, kept as a documented baseline comparison.
```

> ⚠️ **Known gap:** the frontend API client currently calls `/analyze`, `/suite`, and `/merge`, which are not implemented in the current backend (`hymnarranger/api.py` only exposes `/health`, `/presets`, `/arrange`, `/midi`). This needs to be reconciled before the UI works fully end-to-end — see [Roadmap](#-roadmap).

---

## 🎯 Target Audience

- **Arrangers and musicians** who want a quick, idiomatic starting point for a bayan arrangement
- **Bayan/accordion players** looking for ready-made textural variations on a known melody
- **Church musicians** — the hymn corpus makes this directly useful for worship arrangements
- **ML/software engineers** interested in a documented comparison between a rule-based and a neural approach to symbolic music generation

---

## ✨ Features

- 🎼 Accepts a monophonic melody in MusicXML (`.xml`, `.musicxml`, `.mxl`)
- 🪗 Deterministic rule-based arrangement engine — no model inference required
- 🎹 A dozen-plus textural presets, with separate sets for simple (2/4, 3/4, 4/4) and compound (6/8, 9/8, 12/8) meters
- 🎻 Stradella-bass left hand with voice-leading optimization
- 🧩 Suite mode: theme + a sequence of variations, reproducible via a random seed
- 📚 "All presets" mode: every texture rendered back-to-back in one score, for comparison
- 👁️ In-browser sheet preview (OpenSheetMusicDisplay) and MIDI playback (GM Accordion program)
- ✍️ Write a melody directly in the browser via an embedded Flat.io editor, or upload a file
- 📄 Download the result as MusicXML or MIDI
- 🧪 A documented neural-network baseline for methodological comparison (see below)

---

## 🛠️ Tech Stack

| Part | Technology | Why |
|------|-----------|-----|
| **Frontend** | React 18 + TypeScript + Vite | Fast dev loop, typed API layer |
| **Styling** | Tailwind CSS v4 | Utility-first, no config overhead |
| **Sheet rendering** | OpenSheetMusicDisplay | MusicXML rendering in the browser |
| **MIDI playback** | html-midi-player | Web-component player, GM soundfont |
| **In-browser notation** | Flat.io Embed SDK | Write a melody without leaving the app |
| **Backend** | Python + FastAPI + Uvicorn | Thin HTTP layer over the engine |
| **Arrangement engine** | music21 | Symbolic music parsing & generation |
| **ML baseline (research only)** | PyTorch + Hugging Face Transformers | Encoder-decoder Music Transformer w/ RPR |
| **Dataset prep** | music21, Audiveris | Melody extraction, PDF → MusicXML |
| **Testing** | pytest, httpx | Unit tests, FastAPI test client |

---

## 📁 Project Structure

```
HymnArranger/
├── arranger.py              # CLI entry point
├── commands.md              # quick CLI reference
├── requirements.txt
│
├── hymnarranger/             # core package — the arrangement engine
│   ├── parsing.py           # MusicXML → internal context (absolute offsets)
│   ├── theory.py            # pure diatonic/harmony helpers
│   ├── figuration.py        # right-hand ornamentation engine
│   ├── textures.py          # alternative right-hand textures
│   ├── lefthand.py          # Stradella voicing + voice-leading optimization
│   ├── assembly.py          # score assembly, instrument, MIDI export
│   ├── suite.py             # theme + variations planner (seeded)
│   ├── meters/
│   │   ├── simple.py        # 2/4, 3/4, 4/4 presets
│   │   └── compound.py      # 6/8, 9/8, 12/8 presets
│   └── api.py                # FastAPI app (/health, /presets, /arrange, /midi)
│
├── frontend/                 # React + Vite + TypeScript app
│   └── src/
│       ├── api/              # typed client + types
│       ├── components/       # FileDropzone, SheetViewer, ScoreEditor, ...
│       ├── hooks/             # useAnalysis, useArrangement
│       └── lib/                # music helpers, download utilities
│
├── dataset/                    # 732 melody/arrangement MusicXML pairs (222 songs)
│   ├── melody/
│   └── arrangement/
│
├── helpers/                    # dataset preparation scripts
│   ├── split_variations.py
│   ├── propagate_barlines.py
│   ├── split_dataset.py
│   ├── tokenize_dataset.py
│   ├── check_dataset.py
│   └── music21_fixes.py
│
├── input/                      # CLI scratch folder (drop a file, run arranger.py)
└── output/                     # CLI output folder
```

---

## 🚀 Quick Start

### Backend + CLI

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# CLI usage
python arranger.py melody.musicxml -p mixed -o out.musicxml   # one preset
python arranger.py --all                                       # every preset, separate files
python arranger.py --merge                                     # every preset, one score
python arranger.py --suite --seed 42                            # theme + variations

# HTTP API
uvicorn hymnarranger.api:app --reload
# → http://127.0.0.1:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

> The frontend proxies `/api/*` to the backend during development. As noted above, a few endpoints it expects (`/analyze`, `/suite`, `/merge`) still need to be added to or reconciled with the backend.

---

## 🧠 ML Baseline (research track)

Alongside the rule-based engine, an **encoder-decoder Music Transformer with Relative Position Representation (RPR)** was implemented and trained (REMI-style tokenization with custom `Voice_Melody` / `Voice_Bass` / `Voice_Chord` tokens), trained for 200 epochs on Google Colab (T4 GPU), reaching ~81% token accuracy and a validation loss of ~1.39.

This model is **not served in production**. It is documented as a verified comparison point: cross-entropy loss averages over the many valid arrangements a single melody admits, which is a structurally poor fit for this one-to-many problem — a key finding that motivated committing to the deterministic, rule-based approach instead. Training code and checkpoints live outside this repository (Colab notebooks); only the dataset-preparation scripts used for both tracks are included here.

---

## 📊 Dataset

The dataset is collected from publicly available Christian choral music (**noty-bratstvo.org**): bayan arrangements paired with automatically extracted melody lines, split into musical variations and unified into MusicXML.

| Metric | Value |
|--------|-------|
| Source songs | 222 |
| Melody/arrangement pairs | 732 |
| Train split | 618 |
| Validation split | 114 |
| Format | MusicXML |

> **Note:** All materials used are publicly available. This project has no commercial purpose.

---

## 📈 Roadmap

- [x] Rule-based arrangement engine (`hymnarranger` package) — parsing, figuration, Stradella left hand
- [x] Dataset collected & prepared (732 pairs from 222 source songs)
- [x] Music Transformer trained as a documented research baseline
- [x] FastAPI backend for the rule-based engine
- [x] React + Vite frontend (upload, in-browser editor, sheet + MIDI, download)
- [ ] Reconcile frontend API client with backend endpoints (`/analyze`, `/suite`, `/merge`)
- [ ] Deployment (Docker config drafted for dev, production deploy not yet set up)
- [ ] Add a `LICENSE` file matching the badge above
- [ ] Style parameters for instruments beyond bayan (long-term)

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

**Andrii** — bayan player, arranger, developer

- Focus areas: symbolic music processing, rule-based generation, full-stack development
- Tech stack: Python, music21, TypeScript, React, PyTorch

---

## 📄 License

Intended to be released under the MIT License; the `LICENSE` file has not been added to the repository yet.

---

*Made with ❤️ for musicians and developers*