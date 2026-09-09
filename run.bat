@echo off
cd /d %~dp0
if not exist .env (echo .env fehlt - bitte .env.example kopieren und LLM_API_KEY setzen & exit /b 1)
python -m pip install -r requirements.txt -q
python -m uvicorn app.main:app --port 8040
