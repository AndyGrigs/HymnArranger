# HymnArranger

> KI-Modell zur automatischen Harmonisierung christlicher Kirchenlieder im Bajan-Stil

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Hugging Face](https://img.shields.io/badge/🤗-Hugging%20Face-yellow.svg)](https://huggingface.co/)
[![Google Colab](https://img.shields.io/badge/Google-Colab-orange.svg)](https://colab.research.google.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-In%20Entwicklung-yellow.svg)]()

---

## Projektbeschreibung

**HymnArranger** ist ein ML-Projekt, das ein neuronales Netz darauf trainiert, Melodien christlicher Kirchenlieder automatisch im Bajan-Stil zu arrangieren. Das Modell nimmt eine einfache Melodielinie entgegen und generiert daraus ein vollständiges Arrangement für Bajan — mit Harmonie, Begleitung für die linke Hand und charakteristischer Bajan-Faktur.

Das Projekt verbindet die Verarbeitung musikalischer Daten, das Fine-Tuning von Transformer-Modellen und die automatische Erzeugung von Notenfiles in den Formaten MusicXML, MIDI und PDF.

---

## Zielgruppe

Dieses Projekt richtet sich an:

- **Musiker in Kirchengemeinden** — schnelle Erstellung von Arrangements für Gottesdienste
- **ML-Entwickler** — Beispiel für den Einsatz von Transformern zur symbolischen Musikgenerierung
- **Musiklehrer** — Werkzeug zur Veranschaulichung von Melodieharmonisierung
- **Alle Interessierten** an der Schnittstelle von Künstlicher Intelligenz und Musik

---

## Funktionen

- 🎼 Eingabe einer Melodie im Format MusicXML oder MIDI
- 🪗 Generierung eines Arrangements im Bajan-Stil (rechte + linke Hand)
- 🎨 Unterstützung verschiedener Stile (geplant: Bajan, Klavier, Akkordeon)
- 📄 Ausgabe in den Formaten MusicXML, MIDI und PDF
- ☁️ Training und Inferenz in Google Colab (ohne leistungsstarke GPU)
- 🔧 Fine-Tuning auf eigenem Datensatz

---

## Projektstruktur

```
HymnArranger/
├── dataset/
│   ├── train/
│   │   ├── melody/          # Melodielinien (Eingabe)
│   │   └── arrangement/     # Vollständige Arrangements (Ziel)
│   └── val/
│       ├── melody/
│       └── arrangement/
├── scripts/
│   ├── prepare_dataset.py   # Konvertierung und Datenvorbereitung
│   ├── extract_melody.py    # Melodieextraktion aus Arrangements (music21)
│   └── convert_to_xml.py    # PDF → MusicXML via Audiveris
├── notebooks/
│   ├── 01_data_preparation.ipynb
│   ├── 02_training.ipynb
│   └── 03_inference.ipynb
├── model/
│   └── config.json
├── output/                  # Generierte Arrangements
├── requirements.txt
└── README.md
```

---

## Technologien

| Technologie | Verwendungszweck |
|------------|-----------------|
| **Python 3.10+** | Hauptprogrammiersprache |
| **music21** | Verarbeitung und Analyse von Musikdaten (MusicXML, MIDI); automatisierte Melodieextraktion |
| **Audiveris** | Optische Notenerkennung (OMR) — konvertiert PDF-Notenvorlagen in MusicXML |
| **Hugging Face Transformers** | Fine-Tuning von GPT-2 / Music Transformer |
| **Google Colab** | Cloud-basiertes Modelltraining (GPU T4) |
| **MusicXML / MIDI** | Formate für Musikdaten (einheitliches Datensatzformat: MusicXML) |

---

## Schnellstart

### 1. Repository klonen

```bash
git clone https://github.com/your-username/HymnArranger.git
cd HymnArranger
```

### 2. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

### 3. Datensatz vorbereiten

```bash
# PDF-Noten in MusicXML konvertieren (via Audiveris)
python scripts/convert_to_xml.py --input data/pdf/ --output dataset/train/arrangement/

# Melodien automatisch extrahieren
python scripts/extract_melody.py --input dataset/train/arrangement/ --output dataset/train/melody/
```

### 4. Training in Google Colab

Öffne `notebooks/02_training.ipynb` in Google Colab und führe alle Zellen aus.

### 5. Arrangement generieren *(geplante API — noch nicht implementiert)*

```python
from hymn_arranger import HymnArranger

arranger = HymnArranger.load("model/")
arranger.arrange("my_melody.xml", output="arrangement.xml", style="bayan")
```

---

## Datensatz

Der Datensatz wird aus frei zugänglichen Quellen christlicher Chormusik (noty-bratstvo.org) zusammengestellt: Bajan-Arrangements zusammen mit den daraus automatisch extrahierten Melodielinien. Alle Daten werden im Format MusicXML vereinheitlicht. Sammlung und Aufbereitung befinden sich derzeit **in Bearbeitung**.

| Teilmenge | Zielanzahl | Format |
|-----------|--------------|--------|
| train     | ~80% gesamt  | MusicXML |
| val       | ~20% gesamt  | MusicXML |

> **Hinweis:** Alle verwendeten Materialien sind frei zugänglich. Das Projekt verfolgt keine kommerziellen Zwecke.

---

## Aktueller Status

- [x] Projektarchitektur festgelegt
- [ ] Datensatz gesammelt und vorbereitet *(in Bearbeitung)*
- [ ] Skripte zur Datenkonvertierung
- [ ] Fine-Tuning des Basismodells
- [ ] Qualitätsbewertung der Arrangements
- [ ] Web-Interface zur Demonstration
- [ ] Unterstützung weiterer Instrumente (Klavier, Akkordeon)

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