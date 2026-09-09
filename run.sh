#!/usr/bin/env sh
cd "$(dirname "$0")"
[ -f .env ] || { echo ".env fehlt - bitte .env.example kopieren und LLM_API_KEY setzen"; exit 1; }
python -m pip install -r requirements.txt -q
python -m uvicorn app.main:app --port 8040
