# 🎵 HymnArranger

> ШІ-модель для автоматичного аранжування християнських гімнів у стилі баяна

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Hugging Face](https://img.shields.io/badge/🤗-Hugging%20Face-yellow.svg)](https://huggingface.co/)
[![Google Colab](https://img.shields.io/badge/Google-Colab-orange.svg)](https://colab.research.google.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-In%20Development-yellow.svg)]()

---

## 📖 Опис проєкту

**HymnArranger** — це ML-проєкт, який навчає нейронну мережу автоматично аранжувати мелодії християнських гімнів у стилі баяна. Модель приймає просту мелодичну лінію і генерує повноцінне аранжування для баяна — з гармонією, акомпанементом лівою рукою та характерною баянною фактурою.

Проєкт поєднує обробку музичних даних, fine-tuning трансформерних моделей та автоматичну генерацію нотних файлів у форматах MusicXML, MIDI та PDF.

---

## 🎯 Цільова аудиторія

Цей проєкт буде корисним для:

- **Музикантів церковних громад** — швидке створення аранжувань для богослужінь
- **ML-розробників** — приклад застосування трансформерів для символьної музичної генерації
- **Викладачів музики** — інструмент для демонстрації гармонізації мелодій
- **Всіх, хто цікавиться** перетином штучного інтелекту та музики

---

## ✨ Можливості

- 🎼 Приймає мелодію у форматі MusicXML або MIDI
- 🪗 Генерує аранжування у стилі баяна (права + ліва рука)
- 🎨 Підтримка різних стилів (планується: баян, фортепіано, акордеон)
- 📄 Вивід у форматах MusicXML, MIDI та PDF
- ☁️ Тренування та інференс у Google Colab (без потужного GPU)
- 🔧 Fine-tuning на власному датасеті

---

## 🏗️ Архітектура проєкту

```
HymnArranger/
├── dataset/
│   ├── train/
│   │   ├── melody/          # Мелодичні лінії (вхід)
│   │   └── arrangement/     # Повні аранжування (ціль)
│   └── val/
│       ├── melody/
│       └── arrangement/
├── scripts/
│   ├── prepare_dataset.py   # Конвертація та підготовка даних
│   ├── extract_melody.py    # Витягування мелодії з аранжування (music21)
│   └── convert_to_xml.py    # PDF → MusicXML через Audiveris
├── notebooks/
│   ├── 01_data_preparation.ipynb
│   ├── 02_training.ipynb
│   └── 03_inference.ipynb
├── model/
│   └── config.json
├── output/                  # Згенеровані аранжування
├── requirements.txt
└── README.md
```

---

## 🛠️ Технології

| Технологія | Призначення |
|-----------|-------------|
| **Python 3.10+** | Основна мова розробки |
| **music21** | Обробка та аналіз музичних даних (MusicXML, MIDI); автоматичне витягування мелодії |
| **Audiveris** | Оптичне розпізнавання нот (OMR) — конвертація вихідних PDF-партитур у MusicXML |
| **Hugging Face Transformers** | Fine-tuning GPT-2 / Music Transformer |
| **Google Colab** | Хмарне тренування моделі (GPU T4) |
| **MusicXML / MIDI** | Формати музичних даних (єдиний формат датасету: MusicXML) |

---

## 🚀 Швидкий старт

### 1. Клонування репозиторію

```bash
git clone https://github.com/your-username/HymnArranger.git
cd HymnArranger
```

### 2. Встановлення залежностей

```bash
pip install -r requirements.txt
```

### 3. Підготовка датасету

```bash
# Конвертація PDF-нот у MusicXML (через Audiveris)
python scripts/convert_to_xml.py --input data/pdf/ --output dataset/train/arrangement/

# Автоматичне витягування мелодій
python scripts/extract_melody.py --input dataset/train/arrangement/ --output dataset/train/melody/
```

### 4. Тренування в Google Colab

Відкрий `notebooks/02_training.ipynb` у Google Colab і запусти всі комірки.

### 5. Генерація аранжування *(планований API — ще не реалізований)*

```python
from hymn_arranger import HymnArranger

arranger = HymnArranger.load("model/")
arranger.arrange("my_melody.xml", output="arrangement.xml", style="bayan")
```

---

## 📊 Датасет

Датасет збирається з відкритих джерел християнської хорової музики (noty-bratstvo.org): аранжування для баяна разом з автоматично витягнутими з них мелодичними лініями. Усі дані уніфікуються у форматі MusicXML. Збір та підготовка наразі **в процесі**.

| Розділ | Цільова кількість | Формат |
|--------|-----------------|--------|
| train  | ~80% від загального | MusicXML |
| val    | ~20% від загального | MusicXML |

> **Примітка:** Всі використані матеріали є у відкритому доступі. Проєкт не переслідує комерційної мети.

---

## 📈 Поточний статус

- [x] Визначення архітектури проєкту
- [ ] Збір та підготовка датасету *(в процесі)*
- [ ] Скрипти конвертації даних
- [ ] Fine-tuning базової моделі
- [ ] Оцінка якості аранжувань
- [ ] Веб-інтерфейс для демонстрації
- [ ] Підтримка інших інструментів (фортепіано, акордеон)

---

## 🤝 Внесок у проєкт

Внески вітаються! Якщо ти хочеш допомогти:

1. Зроби Fork репозиторію
2. Створи гілку для своєї функції (`git checkout -b feature/my-feature`)
3. Зроби Commit (`git commit -m 'Add my feature'`)
4. Зроби Push (`git push origin feature/my-feature`)
5. Відкрий Pull Request

---

## 👤 Автор

**Andrii** — вчитель, розробник, музикант

- Спеціалізація: Full-Stack розробка, ML, обробка музичних даних
- Стек: Python, TypeScript, Next.js, Node.js, AWS, Hugging Face

---

## 📄 Ліцензія

Цей проєкт розповсюджується під ліцензією MIT. Дивись файл [LICENSE](LICENSE) для деталей.

---

*Зроблено з ❤️ для музикантів і розробників*