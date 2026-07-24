# 🎵 HymnArranger

> AI model for automatic arrangement of Christian hymn melodies in bayan (button accordion) style


🌐 **Available in:** [🇺🇦 Українська](README.ua.md) | [🇩🇪 Deutsch](README.de.md)

---

## 📖 About the Project

**HymnArranger** is a machine learning project that trains a neural network to automatically arrange Christian hymn melodies in the style of a bayan (button accordion). The model takes a simple melodic line as input and generates a complete bayan arrangement — including harmony, left-hand accompaniment, and idiomatic bayan texture.

The project combines symbolic music data processing, fine-tuning of transformer-based models, and automatic generation of sheet music in MusicXML, MIDI, and PDF formats.

---

## 🎯 Target Audience

This project is useful for:

- **Church musicians** — quickly create arrangements for worship services
- **ML developers** — a practical example of applying transformers to symbolic music generation
- **Music teachers** — a tool for demonstrating melody harmonization
- **Anyone interested** in the intersection of artificial intelligence and music

---

## ✨ Features

- 🎼 Accepts melody input in MusicXML or MIDI format
- 🪗 Generates full bayan arrangements (right hand + left hand)
- 🎨 Style parameter support (planned: bayan, piano, accordion)
- 📄 Output in MusicXML, MIDI, and PDF formats
- ☁️ Training and inference in Google Colab (no powerful GPU required)
- 🔧 Fine-tuning on custom dataset

---

## 🏗️ Project Structure

```
HymnArranger/
├── dataset/
│   ├── train/
│   │   ├── melody/          # Melody lines (model input)
│   │   └── arrangement/     # Full arrangements (model target)
│   └── val/
│       ├── melody/
│       └── arrangement/
├── scripts/
│   ├── prepare_dataset.py   # Data conversion and preparation
│   ├── extract_melody.py    # Melody extraction from arrangements (music21)
│   └── convert_to_xml.py    # PDF → MusicXML via Audiveris
├── notebooks/
│   ├── 01_data_preparation.ipynb
│   ├── 02_training.ipynb
│   └── 03_inference.ipynb
├── model/
│   └── config.json
├── output/                  # Generated arrangements
├── requirements.txt
└── README.md
```

---

## 🛠️ Tech Stack

| Technology | Purpose |
|-----------|---------|
| **Python 3.10+** | Core programming language |
| **music21** | Music data processing and analysis (MusicXML, MIDI); automated melody extraction |
| **Audiveris** | Optical Music Recognition — converts source PDF scores to MusicXML |
| **Hugging Face Transformers** | Fine-tuning GPT-2 / Music Transformer |
| **Google Colab** | Cloud-based model training (T4 GPU) |
| **MusicXML / MIDI** | Symbolic music data formats (unified dataset format: MusicXML) |

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/your-username/HymnArranger.git
cd HymnArranger
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Prepare the dataset

```bash
# Convert PDF scores to MusicXML (via Audiveris)
python scripts/convert_to_xml.py --input data/pdf/ --output dataset/train/arrangement/

# Automatically extract melodies
python scripts/extract_melody.py --input dataset/train/arrangement/ --output dataset/train/melody/
```

### 4. Train in Google Colab

Open `notebooks/02_training.ipynb` in Google Colab and run all cells.

### 5. Generate an arrangement *(planned API — not yet implemented)*

```python
from hymn_arranger import HymnArranger

arranger = HymnArranger.load("model/")
arranger.arrange("my_melody.xml", output="arrangement.xml", style="bayan")
```

---

## 📊 Dataset

The dataset is being collected from publicly available sources of Christian choral music (noty-bratstvo.org), covering bayan arrangements paired with their extracted melody lines. All data is unified into MusicXML format. Collection and preparation is currently **in progress**.

| Split  | Target size   | Format   |
|--------|---------------|----------|
| train  | ~80% of total | MusicXML |
| val    | ~20% of total | MusicXML |

> **Note:** All materials used are publicly available. This project has no commercial purpose.

---

## 📈 Roadmap

- [x] Define project architecture
- [ ] Collect and prepare dataset *(in progress)*
- [ ] Data conversion scripts
- [ ] Fine-tune base model
- [ ] Evaluate arrangement quality
- [ ] Web demo interface
- [ ] Support for additional instruments (piano, accordion)

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