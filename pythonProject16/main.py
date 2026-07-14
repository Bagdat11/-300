import os
import math
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from fastapi.templating import Jinja2Templates
from supabase import create_client
from typing import Optional

load_dotenv()

# Supabase және басқа конфигурациялар
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SESSION_SECRET = os.getenv("SESSION_SECRET", "change-me")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

# ПАПКАЛАРДЫ ДҰРЫС БАЙЛАУ (Root Directory -> pythonProject16 ішінде болғандықтан)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- БӨЛІМДЕР ЖӘНЕ АДМИНДЕР ---
DEPARTMENT_MAP = {
    "IT": [44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73],
    "Радио": [1, 2, 3, 4, 30, 31, 32, 33, 34, 35, 36, 37, 38, 78, 27, 28, 29],
    "Желілік технология": [12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 5, 6, 7, 8, 9, 10, 11],
    "Құрылыс": [39, 40, 41, 42, 43, 74, 75, 76, 77, 79, 80, 81, 82]
}

# --- ФУНКЦИЯЛАР ---
def fetch_all_students(group_id, q, allowed_group_ids, batch_size=500):
    all_rows = []
    offset = 0
    while True:
        query = supabase.table("student").select("studentid, fullname, loginname, group_id").order("fullname")
        if group_id: query = query.eq("group_id", group_id)
        elif allowed_group_ids is not None: query = query.in_("group_id", allowed_group_ids)
        if q: query = query.or_(f"fullname.ilike.%{q}%,loginname.ilike.%{q}%")
        res = query.range(offset, offset + batch_size - 1).execute()
        data = res.data or []
        all_rows.extend(data)
        if len(data) < batch_size: break
        offset += batch_size
    return all_rows

# --- TELEGRAM WEBHOOK ---
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
                msg = "Сәтті тіркелдіңіз!"
            else:
                msg = "Студент табылмады."
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data={"chat_id": chat_id, "text": msg})
    return {"status": "ok"}

# --- ATTENDANCE ---
@app.post("/attend")
def attend_submit(request: Request, campus_id: int = Form(...), lat: float = Form(...), lng: float = Form(...), device_id: str = Form(...)):
    sid = request.session.get("studentid")
    if not sid: return RedirectResponse("/student-login", status_code=302)

    st = supabase.table("student").select("studentid, device_id, fullname, parent_telegram_id").eq("studentid", sid).single().execute().data
    
    # Хабарлама жіберу
    if st and st.get("parent_telegram_id") and TELEGRAM_BOT_TOKEN:
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", 
                          data={"chat_id": st["parent_telegram_id"], "text": f"Балаңыз {st['fullname']} сабаққа келді."})
        except: pass
    
    return RedirectResponse("/attend-result", status_code=302)

# --- ROUTES ---
@app.get("/student-login")
def login_page(request: Request): return templates.TemplateResponse("student_login.html", {"request": request})

@app.get("/admin-dashboard")
def admin_dashboard(request: Request, group_id: str = "", q: str = "", dept: Optional[str] = None):
    if not request.session.get("is_admin"): return RedirectResponse("/admin-login", status_code=302)
    session_dept = request.session.get("admin_dept", "IT")
    current_dept = dept if session_dept == "ALL" and dept else session_dept
    allowed_groups = None if current_dept == "ALL" else DEPARTMENT_MAP.get(current_dept, [])
    students = fetch_all_students(group_id, q, allowed_groups)
    return templates.TemplateResponse("admin_dashboard.html", {"request": request, "rows": students, "current_dept": current_dept})

@app.get("/")
def home(): return RedirectResponse("/student-login", status_code=302)
