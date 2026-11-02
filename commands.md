# python arranger_v11.py                          # один пресет (за замовчуванням "Мікс")
# python arranger_v11.py -p sixteenths_nb         # конкретний пресет
# python arranger_v11.py --all                    # 13 окремих файлів
# python arranger_v11.py --merge                  # усі 13 в одній партитурі

"C"C4 "G"D4 | "C"E4 "F"F4| "C"G4 "F"A4 | "G7"B4  "C"c4 | "Am"c4 "Em"B4 | "F"A4 "C"G4 | "Dm"F4 "C"E4 | "G7"D4 "C"C4|]  



X:3
T:The Wellerman
M:4/4
L:1/8
K:Amin
E2 |"Am"A2 A2 A2 B2 | c3 d e4 | "E7"d2 d2 B2 c2 | d3 e B2 E2 |
"Am"A2 A2 A2 B2 | c3 d e4 | "E7"d2 c2 B2 ^G2 | "Am"A6 ||
e2 | "Am"a3 g e4 | "Dm"f3 e d4 | "Am"e2 e2 c2 d2 | "E7"e3 d B2 E2 |
"Am"A2 A2 A2 B2 | c3 d e4 | "E7"d2 c2 B2 ^G2 | "Am"A6 |]



X:3
T:Bruder Jakob
M:4/4
L:1/4
K:C
"C"C D E C | C D E C | "C"E F G2 | E F G2 |
"C"G/A/G/F/ E C | "C"G/A/G/F/ E C | "G"C G, "C"C2 | "G"C G, "C"C2 |]

Потрібні два термінали: бекенд (порт 8000) і фронтенд (порт 5173). Залежності в проєкті вже встановлені: є `.venv`, `frontend/node_modules` і `.env` із `DATABASE_URL`.

**Термінал 1 — бекенд** (з кореня проєкту):
```powershell
.venv\Scripts\activate
uvicorn hymnarranger.api:app --reload
```
API буде на `http://127.0.0.1:8000`, документація на `/docs`.

**Термінал 2 — фронтенд:**
```powershell
cd frontend
npm run dev
```
Відкрийте `http://localhost:5173`. Vite сам проксіює `/api` на бекенд (див. [vite.config.ts](frontend/vite.config.ts)), тож нічого налаштовувати не треба.

**Що перевірити, якщо не стартує:**
- **База:** `hymnarranger/db/session.py` кидає помилку, якщо `DATABASE_URL` порожній. Postgres має бути запущений. Для нової бази один раз виконайте `alembic upgrade head`.
- **`ALLOWED_HOSTS`:** у `.env` цієї змінної немає. Без неї діє `localhost,127.0.0.1`, що для локального запуску достатньо.
- **Листи (підтвердження пошти, скидання пароля):** вони потребують `BREVO_API_KEY` і `SENDER_EMAIL`, без них реєстрація не надішле лист.

**Без бази й акаунтів** можна запускати лише тести: `.venv\Scripts\python -m pytest`. Вони йдуть на SQLite у пам'яті.

Щоб спробувати новий мікс: завантажте мелодію, у «Налаштуваннях» оберіть «Мікс фактур» і натисніть «Аранжувати». N6 (відхилення в ре-бемоль) поки доступний тільки з Python-коду, у інтерфейс його ще не виведено.