# RxScribe — AI Handwritten Prescription Reader

A local web app that helps a **human reviewer** transcribe a photographed medical prescription.

It is **not** a doctor, pharmacist, or dispensing system. Unreadable text stays marked as `unclear`. Spelling suggestions are shown for review and are **never** applied automatically.

## What it does

1. You upload a photo of a prescription.
2. OpenCV gently improves contrast and straightens the page.
3. Google Gemini reads the handwriting and returns structured JSON.
4. RapidFuzz compares medicine names with a small medical dictionary.
5. You correct the table, confirm verification, and download JSON or PDF.

## Project folders

```
prescription-reader/
  app.py                 Streamlit dashboard
  requirements.txt       Python packages
  .env.example           API key template
  src/
    preprocessing.py     Grayscale, CLAHE, deskew, threshold preview
    gemini_client.py     Gemini vision extraction
    validation.py        Dictionary + RapidFuzz + missing-field checks
    export.py            JSON and PDF download
    models.py            Data shapes
  data/medicines.json    Common medicines, routes, frequencies
  tests/                 Automated checks
```

## Beginner setup (Windows)

### 1. Install Python 3.10 or newer

From [python.org](https://www.python.org/downloads/). During setup, tick **Add Python to PATH**.

If Windows opens the Microsoft Store when you type `python`, the real interpreter is not on PATH yet. Install from python.org, or run:

```powershell
winget install Python.Python3.12
```

Then close and reopen the terminal.

### 2. Open a terminal in this folder

```powershell
cd C:\Users\LENOVO\Desktop\ai\prescription-reader
```

### 3. Create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If Windows blocks the activate script, run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate again.

### 4. Install packages

```powershell
pip install -r requirements.txt
```

### 5. Add your Gemini API key

1. Create a key at [Google AI Studio](https://aistudio.google.com/apikey).
2. Copy the example env file:

```powershell
copy .env.example .env
```

3. Open `.env` in a text editor and replace `your_gemini_api_key_here` with your real key.

Never commit `.env` or share the key.

### 6. Run the app

```powershell
streamlit run app.py
```

Your browser should open a dashboard. Upload a prescription image and click **Process prescription**.

A practice image is included at `data/sample_prescription.png`. It is a typed sample, not a real patient record. Use it to learn the screens before you try a real photo.

## How to use it safely

- Treat every extracted dose as **unverified** until a qualified person checks the original paper or photo.
- If a field says `unclear`, leave it unclear. Do not guess.
- Dictionary suggestions (for example `Amoxcilin` → `Amoxicillin`) are hints only.
- Tick the verification checkbox only after you compared the table with the image.

## Tests

```powershell
pytest -q
```

These tests cover image preprocessing, fuzzy matching, missing-field flags, and file export. They do not call Gemini, so they work without an API key.

## Troubleshooting

| Problem | What to try |
| --- | --- |
| `GEMINI_API_KEY is missing` | Create `.env` from `.env.example` and restart Streamlit. You can also paste a key in the sidebar. |
| Gemini request failed | Check the key, internet connection, and that the model name in `.env` is available to your account. Try `gemini-2.5-flash` or `gemini-flash-latest`. |
| Handwriting looks washed out | Use a clearer photo. The app avoids harsh filters on purpose so thin strokes survive. |
| `streamlit` is not recognized | Activate `.venv` first, then `pip install -r requirements.txt`. |

## Privacy

Images and extracted text are sent to Google Gemini when you click **Process prescription**. Do not upload prescriptions unless you have the right to process that data.
