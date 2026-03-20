# FestCard

![FestCard Logo](frontend/assets/logo.svg)

Generate personalized festival greeting cards with AI-crafted wish text.

[Demo GIF here]

---

## What it does

FestCard lets you create beautiful, personalized greeting cards for any major festival. Pick a festival, enter names, choose a tone, and the app generates a warm, custom message displayed on a styled card matching the festival's colors. Download the finished card as a PNG image.

Works fully offline with built-in fallback messages — no API key required to try it.

---

## Features

- 10 festivals supported: Diwali, Christmas, Eid ul Fitr, Holi, New Year, Ugadi, Pongal, Raksha Bandhan, Birthday, Anniversary
- AI-generated wish text via Groq (llama-3.1-8b-instant) with automatic fallback
- Three tones: Casual, Formal, Heartfelt
- Each festival has a unique color scheme applied to the card
- Download your card as a PNG image
- No CDN dependencies at runtime — all assets served locally
- Full HTTP security headers on every response
- Rate limited API endpoints

---

## Tech Stack

| Layer     | Technology                        |
|-----------|-----------------------------------|
| Backend   | Python FastAPI + uvicorn          |
| Frontend  | Single HTML file, vanilla JS      |
| AI        | Groq API (llama-3.1-8b-instant)   |
| Capture   | html2canvas 1.4.1 (self-hosted)   |
| Rate limit| slowapi                           |

---

## Prerequisites

- Python 3.10 or higher
- A free [Groq API key](https://console.groq.com/) (optional — app works without it)

---

## Setup

```bash
# 1. Clone the repository
git clone https://github.com/SaiVenkataGaneshBandaluppi/FestCard.git
cd FestCard

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your GROQ_API_KEY (optional)

# 5. Run the server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` in your browser.

---

## Usage

1. Select a festival from the dropdown
2. Enter the recipient's name and your name
3. Choose a tone: Casual, Formal, or Heartfelt
4. Click **Generate Card**
5. Read the personalized message on the styled card
6. Click **Download PNG** to save the card as an image

---

## Deployment

### Backend — Render (free tier)

1. Push this repository to GitHub
2. Create a new **Web Service** on [Render](https://render.com)
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables: `GROQ_API_KEY`, `ENVIRONMENT=production`
6. Deploy — Render provides a public URL

### Frontend — GitHub Pages

The frontend is a single `frontend/index.html` file. For production, update the API base URL in the JS to point to your Render backend URL, then enable GitHub Pages from the repository settings pointing to the `frontend/` directory.

> Note: When deployed, the frontend calls the Render backend for API requests. Update the `fetch` URLs in `index.html` from `/api/` to `https://your-render-url.onrender.com/api/` before deploying the frontend to GitHub Pages.

---

## License

MIT — see [LICENSE](LICENSE)
