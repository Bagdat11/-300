import os
import math
import requests
from pathlib import Path
from datetime import datetime, date
from zoneinfo import ZoneInfo
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from fastapi.templating import Jinja2Templates
from supabase import create_client

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SESSION_SECRET = os.getenv("SESSION_SECRET", "change-me")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# -------------------- БӨЛІМДЕР --------------------
DEPARTMENT_MAP = {
    "IT": [44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73],
    "Радио": [1, 2, 3, 4, 30, 31, 32, 33, 34, 35, 36, 37, 38, 78, 27, 28, 29],
    "Желілік технология": [12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 5, 6, 7, 8, 9, 10, 11],
    "Құрылыс": [39, 40, 41, 42, 43, 74, 75, 76, 77, 79, 80, 81, 82]
}

# -------------------- HELPERS --------------------
def haversine_m(lat1, lng1, lat2, lng2) -> float:
    r = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# -------------------- ROUTES --------------------
@app.post("/bot-webhook")
async def bot_webhook(request: Request):
    data = await request.json()
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "").strip()
        
        if text.startswith("/register "):
            student_name = text.replace("/register ", "").strip()
            res = supabase.table("student").select("studentid").eq("fullname", student_name).single().execute()
            
            if res.data:
                supabase.table("student").update({"parent_telegram_id": str(chat_id)}).eq("studentid", res.data["studentid"]).execute()
                msg = f"Сәтті тіркелдіңіз! {student_name} сабаққа келгенде хабарлама келіп тұрады."
            else:
                msg = "Студент табылмады. Аты-жөнін базадағыдай жазыңыз."
            
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data={"chat_id": chat_id, "text": msg})
    return {"status": "ok"}

@app.post("/attend")
def attend_submit(request: Request, campus_id: int = Form(...), lat: float = Form(...), lng: float = Form(...), device_id: str = Form(...)):
    sid = request.session.get("studentid")
    if not sid: return RedirectResponse("/student-login", status_code=302)

    st = supabase.table("student").select("studentid, device_id, parent_telegram_id, fullname").eq("studentid", sid).single().execute().data
    if not st or st.get("device_id") != device_id: return RedirectResponse("/attend?msg=Қате", status_code=302)
    
    campus = supabase.table("campuses").select("lat, lng, radius_m").eq("id", campus_id).single().execute().data
    if not campus or haversine_m(lat, lng, campus["lat"], campus["lng"]) > campus["radius_m"]:
        return RedirectResponse("/attend?msg=Аймақтан%20тыссыз", status_code=302)

    kz_tz = ZoneInfo("Asia/Almaty")
    now = datetime.now(kz_tz)
    payload = {"studentid": sid, "attend_date": now.date().isoformat(), "attend_time": now.strftime("%H:%M:%S"), "campus_id": campus_id, "present": True}
    
    existing = supabase.table("attendance_daily").select("id").eq("studentid", sid).eq("attend_date", now.date().isoformat()).execute().data
    if existing: supabase.table("attendance_daily").update(payload).eq("id", existing[0]["id"]).execute()
    else: supabase.table("attendance_daily").insert(payload).execute()

    # Telegram хабарлама
    if st.get("parent_telegram_id") and TELEGRAM_BOT_TOKEN:
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", 
                          data={"chat_id": st["parent_telegram_id"], "text": f"Хабарлама: Балаңыз {st['fullname']} сабаққа келді."})
        except: pass

    return RedirectResponse("/attend-result", status_code=302)

@app.get("/")
def home(): return RedirectResponse("/student-login", status_code=302)
