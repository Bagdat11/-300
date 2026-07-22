import os
import requests
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, Body
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from fastapi.templating import Jinja2Templates
from supabase import create_client
from typing import Optional
from datetime import date

load_dotenv()

# main.py файлы орналасқан папканың толық жолын анықтау (Render үшін 100% қатесіз)
BASE_DIR = Path(__file__).resolve().parent

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SESSION_SECRET = os.getenv("SESSION_SECRET", "change-me")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

# Динамикалық абсолютті жолдарды қосу
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

DEPARTMENT_MAP = {
    "IT": [44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73],
    "Радио": [1, 2, 3, 4, 30, 31, 32, 33, 34, 35, 36, 37, 38, 78, 27, 28, 29],
    "Желілік технология": [12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 5, 6, 7, 8, 9, 10, 11],
    "Құрылыс": [39, 40, 41, 42, 43, 74, 75, 76, 77, 79, 80, 81, 82]
}

def fetch_all_students(group_id, q, allowed_group_ids, batch_size=500):
    if not supabase: return []
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

@app.get("/")
def home(): 
    return RedirectResponse("/student-login", status_code=302)

@app.get("/student-login")
def login_page(request: Request): 
    return templates.TemplateResponse(request=request, name="student_login.html")

@app.post("/student-login")
def student_login(request: Request, login: str = Form(...), password: str = Form(...), device_id: str = Form("")):
    if supabase:
        res = supabase.table("student").select("*").eq("loginname", login).execute()
        if res.data and len(res.data) > 0:
            student = res.data[0]
            request.session["studentid"] = student["studentid"]
            return RedirectResponse("/attend", status_code=302)
    return templates.TemplateResponse(request=request, name="student_login.html", context={"msg": "Логин немесе құпиясөз қате!"})

@app.get("/attend")
def attend_page(request: Request):
    sid = request.session.get("studentid")
    if not sid: return RedirectResponse("/student-login", status_code=302)
    
    student_name = ""
    campuses = []
    if supabase:
        st_res = supabase.table("student").select("fullname").eq("studentid", sid).single().execute()
        if st_res.data: student_name = st_res.data.get("fullname", "")
        campuses = supabase.table("campus").select("*").execute().data or []
    
    return templates.TemplateResponse(request=request, name="attend.html", context={
        "student_name": student_name,
        "campuses": campuses
    })

@app.post("/attend")
def attend_submit(request: Request, campus_id: int = Form(...), lat: float = Form(...), lng: float = Form(...), device_id: str = Form(...)):
    sid = request.session.get("studentid")
    if not sid: return RedirectResponse("/student-login", status_code=302)
    
    if supabase and TELEGRAM_BOT_TOKEN:
        st = supabase.table("student").select("studentid, device_id, fullname, parent_telegram_id").eq("studentid", sid).single().execute().data
        if st and st.get("parent_telegram_id"):
            try:
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", 
                              data={"chat_id": st["parent_telegram_id"], "text": f"Балаңыз {st['fullname']} сабаққа келді."})
            except: pass
    return RedirectResponse("/attend-result", status_code=302)

@app.get("/attend-result")
def attend_result(request: Request):
    sid = request.session.get("studentid")
    if not sid: return RedirectResponse("/student-login", status_code=302)
    
    student_name = ""
    if supabase:
        st_res = supabase.table("student").select("fullname").eq("studentid", sid).single().execute()
        if st_res.data: student_name = st_res.data.get("fullname", "")
        
    return templates.TemplateResponse(request=request, name="result.html", context={
        "student_name": student_name,
        "present": True,
        "campus_name": "Негізгі корпус",
        "attend_time": "Бүгін"
    })

@app.get("/student-logout")
def student_logout(request: Request):
    request.session.clear()
    return RedirectResponse("/student-login", status_code=302)

@app.get("/admin-login")
def admin_login_page(request: Request):
    return templates.TemplateResponse(request=request, name="admin_login.html")

@app.post("/admin-login")
def admin_login(request: Request, login: str = Form(...), password: str = Form(...)):
    if login == "admin" and password == "admin123":
        request.session["is_admin"] = True
        request.session["admin_dept"] = "ALL"
        return RedirectResponse("/admin-dashboard", status_code=302)
    return templates.TemplateResponse(request=request, name="admin_login.html", context={"msg": "Админ логині немесе құпиясөзі қате!"})

@app.get("/admin-dashboard")
def admin_dashboard(request: Request, group_id: str = "", q: str = "", dept: Optional[str] = None, day: Optional[str] = None):
    if not request.session.get("is_admin"): return RedirectResponse("/admin-login", status_code=302)
    session_dept = request.session.get("admin_dept", "ALL")
    current_dept = dept if session_dept == "ALL" and dept else session_dept
    allowed_groups = None if current_dept == "ALL" else DEPARTMENT_MAP.get(current_dept, [])
    
    students = fetch_all_students(group_id, q, allowed_groups)
    groups = supabase.table("study_group").select("group_id, group_name").execute().data or [] if supabase else []
    
    return templates.TemplateResponse(request=request, name="admin_dashboard.html", context={
        "rows": students, 
        "current_dept": current_dept,
        "session_dept": session_dept,
        "groups": groups,
        "group_id": group_id,
        "q": q,
        "today": day or str(date.today()),
        "present_count": len(students),
        "absent_count": 0
    })

@app.post("/admin/mark-attendance")
def mark_attendance(data: dict = Body(...)):
    return JSONResponse({"success": True})

@app.get("/admin-logout")
def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin-login", status_code=302)

@app.post("/bot-webhook")
async def bot_webhook(request: Request):
    data = await request.json()
    if "message" in data and supabase and TELEGRAM_BOT_TOKEN:
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
