# 🎵 HymnArranger

> Regelbasierter, deterministischer Generator für Bajan-(Knopfakkordeon-)Arrangements aus einer einstimmigen Melodie

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![music21](https://img.shields.io/badge/music21-10.5.0-informational.svg)](https://web.mit.edu/music21/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18%20%2B%20Vite-61DAFB.svg)](https://react.dev/)
[![Status](https://img.shields.io/badge/Status-Active%20Development-yellow.svg)]()

---

🌐 **Verfügbar in:** [🇬🇧 English](README.md) | [🇺🇦 Українська](README.ua.md)

📚 **Dokumentation:** [ABC-Notationseditor — vollständige Anleitung](docs/abc-editor.md) (Ukrainisch)

---

## 📖 Projektbeschreibung

**HymnArranger** nimmt eine einstimmige Melodie (MusicXML) entgegen und erzeugt daraus ein vollständiges zweihändiges Bajan-Arrangement — eine figurierte Melodiestimme in der rechten Hand und eine Stradella-Bassbegleitung in der linken — mithilfe einer **deterministischen, regelbasierten Engine** auf Basis von [music21](https://web.mit.edu/music21/), nicht eines Black-Box-Modells.

Das Repertoire christlicher Kirchenlieder dient als Arbeitskorpus, und die musikalischen Regeln beruhen auf der eigenen Erfahrung des Autors als Bajan-Spieler und Arrangeur. Die Engine selbst richtet sich an jeden Musiker bzw. Arrangeur, der mit melodischem Material arbeitet — Bajan ist der erste umgesetzte Instrumentalstil.

Separat wurde ein vollständig trainiertes neuronales Netz als **Forschungs-Baseline** entwickelt und evaluiert, um die Wahl des regelbasierten Ansatzes zu begründen (siehe [ML-Baseline](#-ml-baseline-forschungszweig) unten). Es ist nicht Teil des ausgelieferten Produkts.

---

## 🏗️ Architektur

```
┌─────────────────────────────────────────────┐
│         FRONTEND — React + Vite + TS         │
│  - MusicXML / .abc / .mxl hochladen          │
│  - ABC-Notationseditor mit Toolbar            │
│  - Preset / Suite / "Alle"-Modus wählen       │
│  - Notenvorschau (abcjs)                      │
│  - MIDI-Wiedergabe (GM Accordion)             │
│  - MusicXML / .mxl / MIDI / ABC herunterladen │
│  - Authentifizierung, Werkebibliothek         │
└───────────────────┬───────────────────────────┘
                     │ REST
┌───────────────────▼───────────────────────────┐
│         BACKEND — FastAPI (Python)             │
│                                                │
│  Arrangement-API:                              │
│    GET  /health                                │
│    POST /analyze  — Taktart, Akkorde, Presets  │
│    POST /arrange  — ein Arrangement            │
│    POST /suite    — Thema + Variationen        │
│    POST /merge    — alle Presets in einer      │
│    POST /compress — Packen als .mxl            │
│    POST /midi     — Konvertierung zu MIDI      │
│    POST /export/abc — Konvertierung zu ABC     │
│                                                │
│  Auth-API (/auth/*):                           │
│    register, login, verify-email,              │
│    forgot/reset password                       │
│                                                │
│  Works-API (/works/*):                         │
│    auflisten, abrufen, umbenennen,             │
│    gespeicherte Werke löschen                  │
└───────────────────┬───────────────────────────┘
                     │
┌───────────────────▼───────────────────────────┐
│  ARRANGEMENT-ENGINE — hymnarranger/              │
│  (music21, regelbasiert, deterministisch)        │
│  - Parsing, Harmonik, Figuration                 │
│  - linke Hand Stradella + Voice Leading          │
│  - Textur-Presets je Taktart-Typ                 │
│  - Suite: Thema + Variationen (Seed)             │
└───────────────────────────────────────────────────┘

   Separater Forschungszweig (nicht produktiv im Einsatz):
   ein Encoder-Decoder Music Transformer (RPR), trainiert auf
   Google Colab, dokumentiert als Vergleichs-Baseline.
```

---

## 🎯 Zielgruppe

- **Arrangeure und Musiker**, die einen schnellen, idiomatischen Ausgangspunkt für ein Bajan-Arrangement suchen
- **Bajan-/Akkordeonspieler**, die fertige Textur-Variationen zu einer bekannten Melodie suchen
- **Kirchenmusiker** — der Liederkorpus macht das Tool direkt für Gottesdienste nutzbar
- **ML-/Software-Entwickler**, die sich für einen dokumentierten Vergleich zwischen regelbasiertem und neuronalem Ansatz zur symbolischen Musikgenerierung interessieren

---

## ✨ Funktionen

- 🎼 Nimmt eine einstimmige Melodie im MusicXML-Format entgegen (`.xml`, `.musicxml`, `.mxl`)
- 🪗 Deterministische, regelbasierte Arrangement-Engine — ohne Modellinferenz
- 🎹 Über ein Dutzend Textur-Presets, getrennte Sätze für einfache (2/4, 3/4, 4/4) und zusammengesetzte (6/8, 9/8, 12/8) Taktarten
- 🎻 Linke Hand nach Stradella-System mit Voice-Leading-Optimierung
- 🧩 Suite-Modus: Thema + eine Folge von Variationen, reproduzierbar über einen Zufalls-Seed
- 📚 "Alle Presets"-Modus: jede Textur nacheinander in einer Partitur, zum Vergleich
- 👁️ Notenvorschau im Browser über **abcjs** und MIDI-Wiedergabe (GM-Accordion-Programm)
- 🎵 **ABC-Notationseditor** — Noten per Toolbar-Buttons eingeben (Notenwert, Oktave, Vorzeichen), Akkorde visuell zusammenstellen, Live-Vorschau → [vollständige Anleitung](docs/abc-editor.md)
- 📤 **ABC-Export** — beliebige Arrangements in ABC-Notation konvertieren
- 📄 Ergebnis als MusicXML, komprimiertes .mxl, MIDI oder ABC herunterladen
- 🔐 Benutzerkonten mit E-Mail-Verifizierung, JWT-Authentifizierung und Passwort-Reset per Mail
- 📚 **Meine Werke** — gespeicherte Arrangements mit Volltextsuche und Paginierung
- 🧪 Dokumentierte neuronale Baseline zum methodischen Vergleich (siehe unten)

---

## 🛠️ Technologien

| Teil | Technologie | Warum |
|------|-----------|-----|
| **Frontend** | React 18 + TypeScript + Vite | Schneller Entwicklungszyklus, typisierte API-Schicht |
| **Styling** | Tailwind CSS v4 | Utility-first, kaum Konfigurationsaufwand |
| **ABC-Notation + Notenvorschau** | abcjs 6 | Textbasierter ABC-Editor mit Live-Vorschau, Toolbar und Read-only-Notenansicht |
| **MIDI-Wiedergabe** | html-midi-player | Web-Component-Player, GM-Soundfont |
| **Backend** | Python + FastAPI + Uvicorn | Dünne HTTP-Schicht über der Engine |
| **Arrangement-Engine** | music21 | Parsing & Generierung symbolischer Musik |
| **Datenbank** | PostgreSQL + SQLAlchemy + Alembic | Persistente Benutzerkonten und gespeicherte Werke |
| **Authentifizierung** | PyJWT + bcrypt + Brevo | JWT-Tokens, Passwort-Hashing, transaktionale E-Mails |
| **Rate Limiting** | slowapi | Anfragebegrenzung pro Route |
| **Sicherheit** | defusedxml | Schutz vor XML/Zip-Bomb-Uploads |
| **ML-Baseline (nur Forschung)** | PyTorch + Hugging Face Transformers | Encoder-Decoder Music Transformer mit RPR |
| **Datensatzvorbereitung** | music21, Audiveris | Melodieextraktion, PDF → MusicXML |
| **Tests** | pytest, httpx2 | Unit-Tests, FastAPI-Testclient |

---

## 📁 Projektstruktur

```
HymnArranger/
├── arranger.py               # CLI-Einstiegspunkt
├── commands.md                # Kurzreferenz der CLI-Befehle
├── requirements.txt
│
├── hymnarranger/               # Kernpaket
│   ├── api.py                  # FastAPI-App — Arrangement-Endpunkte + Middleware
│   ├── parsing.py              # MusicXML / ABC → interner Kontext
│   ├── theory.py               # reine diatonische/harmonische Hilfsfunktionen
│   ├── figuration.py           # Figurations-Engine der rechten Hand
│   ├── textures.py             # alternative Texturen der rechten Hand
│   ├── lefthand.py             # Stradella-Voicing + Voice-Leading-Optimierung
│   ├── assembly.py             # Partitur-Zusammenbau, MIDI / MusicXML / ABC-Export
│   ├── abcexport.py            # MusicXML → ABC-Konvertierung
│   ├── suite.py                # Planer für Thema + Variationen (Seed-basiert)
│   ├── styles.py               # benannte Stil-Presets
│   ├── model.py                # Datenmodell des Arrangements
│   ├── sakala.py               # Tonleiter-/Tonart-Hilfsfunktionen
│   ├── meters/
│   │   ├── simple.py           # Presets für 2/4, 3/4, 4/4
│   │   └── compound.py         # Presets für 6/8, 9/8, 12/8
│   │
│   ├── auth/                   # Authentifizierungs-Subsystem
│   │   ├── routes.py           # /auth/*-Endpunkte (register, login, verify-email, reset-password)
│   │   ├── dependencies.py     # get_current_user / get_current_user_optional
│   │   ├── security.py         # JWT, bcrypt, Token-Hilfsfunktionen
│   │   ├── schemas.py          # Pydantic Request-/Response-Modelle
│   │   ├── email.py            # transaktionale E-Mails via Brevo
│   │   └── limiter.py          # slowapi Rate-Limiter-Instanz
│   │
│   ├── works/                  # Subsystem für gespeicherte Arrangements
│   │   ├── routes.py           # /works/*-Endpunkte (auflisten, abrufen, umbenennen, löschen)
│   │   └── schemas.py          # WorkSummary, WorkDetail, WorkRename, WorksPage
│   │
│   └── db/                     # Datenbankschicht
│       ├── models.py           # SQLAlchemy ORM-Modelle (User, Work, Tokens)
│       ├── session.py          # Engine + get_db-Abhängigkeit
│       └── works.py            # CRUD-Hilfsfunktionen für gespeicherte Werke
│
├── frontend/                    # React + Vite + TypeScript
│   └── src/
│       ├── api/                 # typisierter API-Client + Typen
│       ├── components/
│       │   ├── AbcEditor.tsx       # ABC-Notationseditor (Toolbar + abcjs Live-Vorschau)
│       │   ├── AbcPaper.tsx        # Read-only-Notenansicht via abcjs
│       │   ├── AnalysisPanel.tsx
│       │   ├── AuthContext.tsx     # React-Auth-Kontext + Provider
│       │   ├── DownloadBar.tsx
│       │   ├── FileDropzone.tsx
│       │   ├── GeneratePanel.tsx
│       │   ├── MidiPlayer.tsx
│       │   ├── Navbar.tsx
│       │   ├── ProtectedRoute.tsx
│       │   ├── SectionList.tsx
│       │   └── ui/                 # Card, Spinner, ErrorBoundary
│       ├── hooks/
│       │   ├── useAnalysis.ts
│       │   ├── useArrangement.ts
│       │   ├── useAuth.ts
│       │   ├── useInputSource.ts
│       │   └── useMidiPreview.ts
│       ├── pages/
│       │   ├── HomePage.tsx
│       │   ├── HowPage.tsx
│       │   ├── MyWorksPage.tsx         # Werkebibliothek mit Suche + Paginierung
│       │   ├── LoginPage.tsx
│       │   ├── RegisterPage.tsx
│       │   ├── ForgotPasswordPage.tsx
│       │   ├── ResetPasswordPage.tsx
│       │   └── VerifyEmailPage.tsx
│       └── lib/                 # Musik-Hilfsfunktionen, Download-Utilities
│
├── docs/
│   └── abc-editor.md            # Vollständige Anleitung zum ABC-Notationseditor (Ukrainisch)
│
├── dataset/                       # 732 Melodie/Arrangement-Paare (222 Lieder)
│   ├── melody/
│   └── arrangement/
│
├── helpers/                       # Skripte zur Datensatzvorbereitung
│   ├── split_variations.py
│   ├── propagate_barlines.py
│   ├── split_dataset.py
│   ├── tokenize_dataset.py
│   ├── check_dataset.py
│   └── music21_fixes.py
│
├── input/                         # CLI-Arbeitsordner (Datei ablegen, arranger.py starten)
└── output/                        # CLI-Ausgabeordner
```

---

## 🚀 Schnellstart

### Backend + CLI

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# CLI
python arranger.py melody.musicxml -p mixed -o out.musicxml   # ein Preset
python arranger.py --all                                       # alle Presets, einzelne Dateien
python arranger.py --merge                                     # alle Presets, eine Partitur
python arranger.py --suite --seed 42                            # Thema + Variationen

# HTTP-API
uvicorn hymnarranger.api:app --reload
# → http://127.0.0.1:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

> Während der Entwicklung leitet das Frontend `/api/*` an das Backend weiter.

---

## 🧠 ML-Baseline (Forschungszweig)

Parallel zur regelbasierten Engine wurde ein **Encoder-Decoder Music Transformer mit Relative Position Representation (RPR)** implementiert und trainiert (REMI-artige Tokenisierung mit eigenen Tokens `Voice_Melody` / `Voice_Bass` / `Voice_Chord`), 200 Epochen lang auf Google Colab (T4-GPU) trainiert, mit ~81 % Token-Genauigkeit und einem Validierungsverlust von ~1,39.

Dieses Modell wird **nicht produktiv eingesetzt**. Es ist als belegter Vergleichspunkt dokumentiert: Der Cross-Entropy-Verlust mittelt über die vielen gültigen Arrangements, die eine einzelne Melodie zulässt — strukturell eine schlechte Passung für dieses "eins-zu-viele"-Problem. Diese Erkenntnis begründete letztlich die Entscheidung für den deterministischen, regelbasierten Ansatz. Trainingscode und Checkpoints liegen außerhalb dieses Repositorys (Colab-Notebooks); hier enthalten sind nur die für beide Zweige gemeinsamen Datensatz-Vorbereitungsskripte.

---

## 📊 Datensatz

Der Datensatz stammt aus öffentlich zugänglicher christlicher Chormusik (**noty-bratstvo.org**): Bajan-Arrangements zusammen mit automatisch extrahierten Melodiestimmen, aufgeteilt in musikalische Variationen und vereinheitlicht im MusicXML-Format.

| Kennzahl | Wert |
|--------|-------|
| Ausgangslieder | 222 |
| Melodie/Arrangement-Paare | 732 |
| Trainings-Split | 618 |
| Validierungs-Split | 114 |
| Format | MusicXML |

> **Hinweis:** Alle verwendeten Materialien sind öffentlich zugänglich. Das Projekt verfolgt keinen kommerziellen Zweck.

---

## 📈 Aktueller Status

- [x] Regelbasierte Arrangement-Engine (Paket `hymnarranger`) — Parsing, Figuration, linke Hand Stradella
- [x] Datensatz gesammelt und aufbereitet (732 Paare aus 222 Ausgangsliedern)
- [x] Music Transformer als dokumentierte Forschungs-Baseline trainiert
- [x] FastAPI-Backend für die regelbasierte Engine
- [x] Frontend mit React + Vite (Upload, ABC-Editor, Noten + MIDI, Download)
- [x] API-Client des Frontends mit den Backend-Endpunkten abgeglichen
- [x] ABC-Notationseditor mit Live-Vorschau, Noten-/Akkord-Toolbar und `.abc`-Backend-Unterstützung
- [x] ABC-Export — Konvertierung beliebiger Arrangements in ABC-Notation
- [x] Benutzerauthentifizierung (Registrierung, E-Mail-Verifizierung, Login, Passwort-Reset via Brevo)
- [x] Werkebibliothek mit Volltextsuche und Paginierung (Meine Werke)
- [ ] Deployment (Docker-Konfiguration für Entwicklung vorhanden, Produktions-Deployment noch offen)
- [ ] `LICENSE`-Datei passend zum obigen Badge ergänzen
- [ ] Stilparameter für weitere Instrumente über Bajan hinaus (langfristig)

---

## 🤝 Mitwirken

Beiträge sind willkommen! So kannst du mitmachen:

1. Repository forken
2. Feature-Branch erstellen (`git checkout -b feature/my-feature`)
3. Änderungen committen (`git commit -m 'Add my feature'`)
4. Branch pushen (`git push origin feature/my-feature`)
5. Pull Request öffnen

---

## 👤 Autor

**Andrii** — Bajan-Spieler, Arrangeur, Entwickler

- Schwerpunkte: Verarbeitung symbolischer Musik, regelbasierte Generierung, Full-Stack-Entwicklung
- Tech-Stack: Python, music21, TypeScript, React, PyTorch

---

## 📄 Lizenz

Eine Veröffentlichung unter der MIT-Lizenz ist vorgesehen; die Datei `LICENSE` wurde dem Repository noch nicht hinzugefügt.

---

*Mit ❤️ für Musiker und Entwickler gemacht*