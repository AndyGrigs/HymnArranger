# 🎵 HymnArranger

> Веб-додаток з ШІ для автоматичного аранжування християнських гімнів

[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Python-green.svg)](https://fastapi.tiangolo.com/)
[![Hugging Face](https://img.shields.io/badge/🤗-Hugging%20Face-yellow.svg)](https://huggingface.co/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-In%20Development-yellow.svg)]()

---

🌐 **Доступно мовами:** [🇬🇧 English](README.md) | [🇩🇪 Deutsch](README.de.md)

---

## 📖 Опис проєкту

**HymnArranger** — це повноцінний веб-додаток, який використовує ML-модель для автоматичного аранжування мелодій християнських гімнів. Користувач завантажує мелодію, обирає стиль (баян, фортепіано, струнні), і отримує готове аранжування прямо в браузері — з можливістю завантажити PDF, MIDI або MusicXML.

---

## 🏗️ Загальна архітектура

```
┌─────────────────────────────────────┐
│           FRONTEND (UI)             │
│  - Завантаження мелодії             │
│  - Вибір стилю (баян / піаніно)     │
│  - Перегляд нот онлайн              │
│  - Завантаження PDF / MIDI          │
└────────────────┬────────────────────┘
                 │ REST API
┌────────────────▼────────────────────┐
│           BACKEND (API)             │
│  - Обробка MusicXML / MIDI          │
│  - Виклик ML моделі                 │
│  - Генерація PDF через MuseScore    │
│  - Зберігання результатів           │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│           ML МОДЕЛЬ                 │
│  - Fine-tuned Music Transformer     │
│  - Hugging Face інференс            │
└─────────────────────────────────────┘
```

---

## 🎯 Цільова аудиторія

- **Музиканти церковних громад** — швидке створення аранжувань для богослужінь
- **ML-розробники** — приклад застосування трансформерів для символьної музичної генерації
- **Викладачі музики** — інструмент для демонстрації гармонізації мелодій
- **Всі, хто цікавиться** перетином штучного інтелекту та музики

---

## ✨ Можливості

- 🎼 Приймає мелодію у форматі MusicXML або MIDI
- 🪗 Генерує аранжування в обраному стилі (баян, фортепіано, струнні)
- 👁️ Перегляд нот прямо в браузері (OpenSheetMusicDisplay)
- 📄 Завантаження результату у форматах PDF, MIDI, MusicXML
- ☁️ Хостинг ML-моделі на Hugging Face Spaces

---

## 🛠️ Технологічний стек

| Частина | Технологія | Чому |
|---------|-----------|------|
| **Frontend** | Next.js + TypeScript | Швидка розробка, SSR |
| **UI компоненти** | Tailwind + shadcn/ui | Швидко і красиво |
| **Перегляд нот** | OpenSheetMusicDisplay | Рендер MusicXML в браузері |
| **Backend** | Python FastAPI | Ідеально для ML інтеграції |
| **ML модель** | Hugging Face + PyTorch | Fine-tuned трансформер |
| **Конвертація** | music21 + MuseScore CLI | MusicXML → PDF / MIDI |
| **База даних** | PostgreSQL | Зберігання пісень і результатів |
| **Хостинг моделі** | Hugging Face Spaces | Безкоштовно для демо |
| **Деплой** | AWS / Vercel + Railway | Перевірений стек |

---

## 📁 Структура проєкту

```
HymnArranger/
├── frontend/                # Next.js додаток
│   ├── app/
│   │   ├── page.tsx         # Головна сторінка
│   │   ├── arrange/         # Сторінка аранжування
│   │   └── results/         # Перегляд результатів
│   └── components/
│       ├── MelodyUploader   # Завантаження файлу
│       ├── StyleSelector    # Вибір стилю
│       └── SheetViewer      # Перегляд нот
│
├── backend/                 # FastAPI сервер
│   ├── main.py              # Точка входу
│   ├── routes/
│   │   ├── arrange.py       # POST /arrange
│   │   └── download.py      # GET /download/{id}
│   ├── services/
│   │   ├── ml_service.py    # Виклик моделі
│   │   ├── music_service.py # music21 обробка
│   │   └── pdf_service.py   # Генерація PDF
│   └── models/              # Pydantic схеми
│
├── ml/                      # ML частина
│   ├── dataset/
│   ├── notebooks/
│   └── model/
│
└── dataset/                 # Датасет
```

---

## 🚀 Як це працює для користувача

```
1. Користувач завантажує мелодію (MusicXML або MIDI)
            ↓
2. Обирає стиль: 🪗 Баян / 🎹 Піаніно / 🎻 Струнні
            ↓
3. Натискає "Аранжувати"
            ↓
4. Бачить ноти прямо в браузері (OpenSheetMusicDisplay)
            ↓
5. Завантажує PDF / MIDI / MusicXML
```

---

## 🚀 Швидкий старт

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

## 📊 Датасет

Датасет збирається з відкритих джерел християнської хорової музики (noty-bratstvo.org): аранжування для баяна разом з автоматично витягнутими мелодичними лініями. Усі дані уніфікуються у форматі MusicXML.

| Розділ | Цільова кількість | Формат |
|--------|-----------------|--------|
| train  | ~80% від загального | MusicXML |
| val    | ~20% від загального | MusicXML |

> **Примітка:** Всі використані матеріали є у відкритому доступі. Проєкт не переслідує комерційної мети.

---

## 📈 Поточний статус

- [x] Визначення архітектури проєкту
- [ ] Збір та підготовка датасету *(в процесі)*
- [ ] Fine-tuning ML-моделі
- [ ] Backend API (FastAPI)
- [ ] Frontend (Next.js)
- [ ] Інтеграція OpenSheetMusicDisplay
- [ ] Деплой на Vercel + Railway

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
