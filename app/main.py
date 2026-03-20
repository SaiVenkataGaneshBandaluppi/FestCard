# MIT License - Copyright (c) 2026 Sai Venkata Ganesh Bandaluppi

import logging
import os
import random
import re
from contextlib import asynccontextmanager

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler("festcard.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

SUPPORTED_FESTIVALS = {
    "Diwali": {"primary": "#4B0082", "secondary": "#FFD700", "accent": "#FF8C00"},
    "Christmas": {"primary": "#1A5C2A", "secondary": "#CC0000", "accent": "#FFFFFF"},
    "Eid ul Fitr": {"primary": "#008080", "secondary": "#C0C0C0", "accent": "#FFFFFF"},
    "Holi": {"primary": "#FF6B6B", "secondary": "#4ECDC4", "accent": "#FFE66D"},
    "New Year": {"primary": "#0D1B4B", "secondary": "#FFD700", "accent": "#FFFFFF"},
    "Ugadi": {"primary": "#FF8C00", "secondary": "#228B22", "accent": "#FFD700"},
    "Pongal": {"primary": "#DAA520", "secondary": "#8B4513", "accent": "#FFF8DC"},
    "Raksha Bandhan": {"primary": "#FF69B4", "secondary": "#FF6600", "accent": "#FFFFFF"},
    "Birthday": {"primary": "#1E90FF", "secondary": "#FFD700", "accent": "#FFFFFF"},
    "Anniversary": {"primary": "#C2185B", "secondary": "#F5CBA7", "accent": "#FFFFFF"},
}

SUPPORTED_TONES = {"casual", "formal", "heartfelt"}

FALLBACK_WISHES = {
    "Diwali": [
        "May the light of a thousand diyas fill your home with joy, prosperity, and endless warmth this Diwali. Wishing you and your loved ones a celebration as radiant as your spirit.",
        "This Diwali, may every lamp you light bring peace to your heart and abundance to your life. May this festival of lights chase away every shadow from your path.",
        "Sending you the warmest Diwali wishes — may this celebration bring your family together, fill your days with laughter, and your home with golden light.",
    ],
    "Christmas": [
        "May the magic of Christmas fill every corner of your home with warmth, laughter, and the company of those you cherish most. Wishing you a truly blessed holiday season.",
        "Christmas is a time for joy, reflection, and gratitude. Hoping this season brings you everything you have wished for and more — and that the new year ahead is bright and full of promise.",
        "Wishing you a Christmas filled with quiet moments of peace, big moments of laughter, and all the love your heart can hold. May this holiday be everything you deserve.",
    ],
    "Eid ul Fitr": [
        "Eid Mubarak! May this joyous occasion bring peace, blessings, and happiness into your life and the lives of all you hold dear. May Allah accept your prayers and grant you all that your heart desires.",
        "On this blessed occasion of Eid ul Fitr, may your home be filled with laughter, your table with abundance, and your heart with gratitude. Wishing you a beautiful celebration.",
        "May the spirit of Eid fill your days with grace and your heart with contentment. Wishing you and your family a blessed, joyful, and peaceful celebration.",
    ],
    "Holi": [
        "May the vibrant colors of Holi paint your life with happiness, friendship, and new beginnings. Wishing you a celebration as bright and beautiful as you are.",
        "Happy Holi! May every color you play with today represent a new joy coming your way — may your year be as full and vivid as the festival itself.",
        "Wishing you a Holi filled with laughter, the company of good friends, and all the colors of happiness. May this festival wash away the old and welcome the bright and new.",
    ],
    "New Year": [
        "As one chapter closes and another begins, may the new year bring you clarity, courage, and countless reasons to smile. Wishing you a year of growth and genuine happiness.",
        "Here is to a new year full of fresh starts and exciting possibilities. May every day bring you closer to your dreams and further from your worries.",
        "Wishing you a New Year filled with everything that matters most — good health, warm connections, and moments of real joy that stay with you long after they have passed.",
    ],
    "Ugadi": [
        "Happy Ugadi! As the new year dawns, may it bring you the sweetness of new beginnings, the strength to face challenges, and the wisdom to cherish every moment.",
        "May this Ugadi mark the start of a year filled with prosperity, happiness, and all the things that make your heart full. Wishing you a wonderful new beginning.",
        "On this auspicious Ugadi, may your life bloom like a new season — full of color, possibility, and the quiet joy of fresh starts.",
    ],
    "Pongal": [
        "Happy Pongal! May this harvest festival bring your home abundant joy, warm togetherness, and the sweetness of all your hard work paying off in the year ahead.",
        "Wishing you a Pongal filled with the warmth of family, the richness of tradition, and the promise of a fruitful and happy year. May your harvest be plentiful in every way.",
        "May the spirit of Pongal remind us of the beauty in gratitude and the strength found in community. Wishing you and your family a truly joyful and blessed celebration.",
    ],
    "Raksha Bandhan": [
        "Happy Raksha Bandhan! May the bond you share always be a source of strength, comfort, and endless love — a thread that holds through every season of life.",
        "This Raksha Bandhan, celebrating the beautiful and unbreakable bond that ties us together. May you always find in each other a safe place to land.",
        "Wishing you a Raksha Bandhan filled with warmth, laughter, and the deep joy that only family can bring. May your bond grow stronger with every passing year.",
    ],
    "Birthday": [
        "Happy Birthday! May this year bring you adventures worth remembering, quiet moments worth savoring, and all the happiness you so richly deserve.",
        "Wishing you a birthday as wonderful as you are — filled with joy, surrounded by people who love you, and followed by a year that exceeds your every expectation.",
        "On your special day, may you feel celebrated, cherished, and deeply loved. Here is to another year of being exactly, brilliantly you.",
    ],
    "Anniversary": [
        "Happy Anniversary! May every year you have built together be a reminder of the love that brought you here, and may every year ahead be even more beautiful than the last.",
        "Congratulations on another year of choosing each other. May your love continue to grow deeper, your partnership stronger, and your joy more abundant with every passing day.",
        "Wishing you a wonderful anniversary filled with gratitude for the journey you have shared and excitement for everything still to come. Here is to your beautiful story continuing.",
    ],
}


class RequestSizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 1_048_576:
            return JSONResponse(status_code=413, content={"detail": "Request too large"})
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
        )
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store"
        for key in ("server", "Server"):
            if key in response.headers:
                del response.headers[key]
        if ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(docs_url=None, redoc_url=None, debug=False)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def strip_html(value: str) -> str:
    return re.sub(r"<[^>]*>", "", value)


def contains_suspicious_patterns(value: str) -> bool:
    patterns = [
        r"<script",
        r"javascript:",
        r"on\w+\s*=",
        r"(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|--|;)\s",
        r"\.\./",
        r"ignore\s+previous\s+instructions",
        r"forget\s+everything",
        r"you\s+are\s+now",
    ]
    lower = value.lower()
    for pattern in patterns:
        if re.search(pattern, lower, re.IGNORECASE):
            return True
    return False


class WishRequest(BaseModel):
    festival: str
    recipient_name: str
    sender_name: str
    tone: str

    @field_validator("festival")
    @classmethod
    def validate_festival(cls, v: str) -> str:
        if v not in SUPPORTED_FESTIVALS:
            raise ValueError("Invalid festival")
        return v

    @field_validator("tone")
    @classmethod
    def validate_tone(cls, v: str) -> str:
        if v not in SUPPORTED_TONES:
            raise ValueError("Invalid tone")
        return v

    @field_validator("recipient_name", "sender_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        v = strip_html(v)
        if len(v) > 50:
            raise ValueError("Name too long")
        if contains_suspicious_patterns(v):
            raise ValueError("Invalid input")
        return v


@app.get("/api/festivals")
@limiter.limit("60/minute")
async def get_festivals(request: Request):
    festivals = [
        {"name": name, "colors": colors}
        for name, colors in SUPPORTED_FESTIVALS.items()
    ]
    return {"festivals": festivals}


@app.post("/api/generate-wish")
@limiter.limit("10/minute")
async def generate_wish(request: Request, body: WishRequest):
    fallback = random.choice(FALLBACK_WISHES[body.festival])

    if not GROQ_API_KEY or GROQ_API_KEY == "paste_your_key_here":
        return {"wish_text": fallback, "source": "fallback"}

    system_prompt = (
        "You are a greeting card message writer. Write warm, genuine, personalized messages. "
        "Never use emojis. Keep messages to 2 to 3 sentences maximum. "
        "Do not add any preamble or explanation."
    )
    user_prompt = (
        f"Write a {body.tone} {body.festival} greeting card message "
        f"for {body.recipient_name} from {body.sender_name}."
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": 150,
                    "temperature": 0.8,
                },
            )
        resp.raise_for_status()
        data = resp.json()
        wish_text = data["choices"][0]["message"]["content"].strip()
        if not wish_text:
            raise ValueError("Empty response from API")
        return {"wish_text": wish_text, "source": "groq"}
    except Exception as exc:
        logger.error("Groq API error: %s", str(exc))
        return {"wish_text": fallback, "source": "fallback"}


app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
