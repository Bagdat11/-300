import os
import math
import requests
from pathlib import Path
from datetime import datetime, date
from zoneinfo import ZoneInfo
from typing import Optional, List, Dict, Any
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

# -------------------- БӨЛІМДЕР МЕН ТОПТАР КАРТАСЫ --------------------
DEPARTMENT_MAP = {
    "IT": [44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73],
    "Радио": [1, 2, 3, 4, 30, 31, 32, 33, 34, 35, 36, 37, 38, 78, 27, 28, 29],
    "Желілік технология": [12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 5, 6, 7, 8, 9, 10, 11],
    "Құрылыс": [39, 40, 41, 42, 43, 74, 75, 76, 77, 79, 80, 81, 82]
}

ADMIN_ACCOUNTS = {
    "global_admin": {"password": "super123", "dept": "ALL"},
    "it_admin": {"password": "it123", "dept": "IT"},
    "radio_admin": {"password": "radio123", "dept": "Радио"},
    "network_admin": {"password": "net123", "dept": "Желілік технология"},
    "const_admin": {"password": "build123", "dept": "Құрылыс"}
}

# -------------------- HELPERS --------------------
def haversine_m(lat1, lng1, lat2, lng2) -> float:
    r = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c

def require_student(request: Request):
    return request.session.get("studentid")

def require_admin(request: Request):
    return bool(request.session.get("is_admin"))

def safe_int(v: Optional[str]) -> Optional[int]:
    if not v or not str(v).strip().isdigit(): return None
    return int(str(v).strip())

def fetch_all_students(group_id, q, allowed_group_ids, batch_size=500):
    all_rows = []
    offset = 0
    while True:
        query = supabase.table("student").select("studentid, fullname, loginname, group_id").order("fullname")
        if group_id: query = query.eq("group_id", group_id)
        elif allowed_group_ids is not None: query = query.in_("group_id", allowed_group_ids)
        if q: query = query.or_(f"fullname.ilike.%{q.strip()}%,loginname.ilike.%{q.strip()}%")
        res = query.range(offset, offset + batch_size - 1).execute()
        data = res.data or []
        all_rows.extend(data)
        if len(data) < batch_size: break
        offset += batch_size
    return all_rows

# -------------------- ROUTES --------------------
@app.get("/", response_class=HTMLResponse)
def home(): return RedirectResponse("/student-login", status_code=302)

@app.get("/student-login", response_class=HTMLResponse)
def student_login_page(request: Request, msg: str = ""):
    return templates.TemplateResponse(request=request, name="student_login.html", context={"msg": msg})

@app.post("/student-login")
def student_login(request: Request, login: str = Form(...), password: str = Form(...), device_id: str = Form(...)):
    res = supabase.table("student").select("studentid, fullname, loginname, passwordplain, group_id, device_id").eq("loginname", login).limit(1).execute()
    if not res.data or res.data[0].get("passwordplain") != password:
        return RedirectResponse("/student-login?msg=Логин%20немесе%20пароль%20қате", status_code=302)
    
    st = res.data[0]
    if not st.get("device_id"):
        supabase.table("student").update({"device_id": device_id}).eq("studentid", st["studentid"]).execute()
    elif st["device_id"] != device_id:
        return RedirectResponse("/student-login?msg=Басқа%20құрылғы", status_code=302)

    request.session.update({"studentid": st["studentid"], "student_name": st.get("fullname", ""), "device_id": device_id})
    return RedirectResponse("/attend", status_code=302)

@app.post("/attend")
def attend_submit(request: Request, campus_id: int = Form(...), lat: float = Form(...), lng: float = Form(...), device_id: str = Form(...)):
    sid = require_student(request)
    if not sid: return RedirectResponse("/student-login", status_code=302)

    # Тексеру және қатысуды тіркеу
    st = supabase.table("student").select("studentid, device_id, parent_telegram_id, fullname").eq("studentid", sid).single().execute().data
    if not st or st.get("device_id") != device_id: return RedirectResponse("/attend?msg=Қате", status_code=302)
    
    campus = supabase.table("campuses").select("lat, lng, radius_m").eq("id", campus_id).single().execute().data
    if not campus or haversine_m(lat, lng, campus["lat"], campus["lng"]) > campus["radius_m"]:
        return RedirectResponse("/attend?msg=Аймақтан%20тыссыз", status_code=302)

    kz_tz = ZoneInfo("Asia/Almaty")
    now = datetime.now(kz_tz)
    today = now.date().isoformat()

    payload = {"studentid": sid, "attend_date": today, "attend_time": now.strftime("%H:%M:%S"), "campus_id": campus_id, "present": True}
    
    existing = supabase.table("attendance_daily").select("id").eq("studentid", sid).eq("attend_date", today).execute().data
    if existing: supabase.table("attendance_daily").update(payload).eq("id", existing[0]["id"]).execute()
    else: supabase.table("attendance_daily").insert(payload).execute()

    # TELEGRAM ХАБАРЛАМА
    parent_id = st.get("parent_telegram_id")
    if parent_id and TELEGRAM_BOT_TOKEN:
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", 
                          data={"chat_id": parent_id, "text": f"Хабарлама: Балаңыз {st['fullname']} сабаққа келді."})
        except: pass

    return RedirectResponse("/attend-result", status_code=302)

@app.get("/admin-dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request, group_id: str = "", q: str = "", day: str = "", dept: Optional[str] = None):
    if not require_admin(request): return RedirectResponse("/admin-login", status_code=302)
    
    session_dept = request.session.get("admin_dept", "IT")
    current_dept = dept if session_dept == "ALL" and dept else session_dept
    
    selected_day = day if day else date.today().isoformat()
    gid = safe_int(group_id)
    
    allowed = None if current_dept == "ALL" or current_dept == "БАРЛЫҚ БӨЛІМДЕР" else DEPARTMENT_MAP.get(current_dept, [])
    students = fetch_all_students(gid, q, allowed)
    
    att_day = supabase.table("attendance_daily").select("studentid, attend_time, campus_id, present").eq("attend_date", selected_day).execute().data or []
    att_map = {a["studentid"]: a for a in att_day}
    
    rows = []
    for s in students:
        a = att_map.get(s["studentid"])
        rows.append({**s, "present": bool(a and a["present"]), "attend_time": a.get("attend_time", "") if a else ""})

    return templates.TemplateResponse(request=request, name="admin_dashboard.html", context={
        "rows": rows, "day": selected_day, "current_dept": current_dept, "groups": [], "group_id": gid, "q": q
    })
