import os
from pathlib import Path
import math
from datetime import datetime, date
from zoneinfo import ZoneInfo  # 🌍 Жаңа импорт
from datetime import datetime, date
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

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


# -------------------- БӨЛІМДЕР МЕН ТОПТАР КАРТАСЫ --------------------
# Қай топтың ID-і (group_id) қай бөлімге жататыны осы жерде реттелген.
DEPARTMENT_MAP = {
    "IT": [44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73],
    "Радио": [1, 2, 3, 4, 30, 31, 32, 33, 34, 35, 36, 37, 38, 78, 27, 28, 29],
    "Желілік технология": [12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 5, 6, 7, 8, 9, 10, 11],
    "Құрылыс": [39, 40, 41, 42, 43, 74, 75, 76, 77, 79, 80, 81, 82]
}


# -------------------- БАРЛЫҚ АДМИНДЕР ТІЗІМІ (ЛОГИН/ПАРОЛЬ) --------------------
ADMIN_ACCOUNTS = {
    "global_admin": {"password": "super123", "dept": "ALL"},  # 👑 БАСТЫ АДМИН (Бүкіл колледжді көреді)
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
    sid = request.session.get("studentid")
    return sid


def require_admin(request: Request):
    return bool(request.session.get("is_admin"))


def safe_int(v: Optional[str]) -> Optional[int]:
    if v is None:
        return None
    v = str(v).strip()
    if v == "":
        return None
    if v.isdigit():
        return int(v)
    return None


def fetch_all_students(group_id: Optional[int], q: str, allowed_group_ids: Optional[List[int]] = None, batch_size: int = 500) -> List[Dict[str, Any]]:
    all_rows: List[Dict[str, Any]] = []
    offset = 0

    while True:
        query = supabase.table("student").select("studentid, fullname, loginname, group_id").order("fullname")

        if group_id:
            query = query.eq("group_id", group_id)
        elif allowed_group_ids is not None:
            query = query.in_("group_id", allowed_group_ids)

        if q:
            qq = q.replace("%", "").strip()
            query = query.or_(f"fullname.ilike.%{qq}%,loginname.ilike.%{qq}%")

        res = query.range(offset, offset + batch_size - 1).execute()
        data = res.data or []
        all_rows.extend(data)

        if len(data) < batch_size:
            break

        offset += batch_size

        if offset > 200000:
            break

    return all_rows


# -------------------- ROUTES --------------------

@app.get("/", response_class=HTMLResponse)
def home():
    return RedirectResponse("/student-login", status_code=302)


# -------------------- STUDENT LOGIN --------------------

@app.get("/student-login", response_class=HTMLResponse)
def student_login_page(request: Request, msg: str = ""):
    return templates.TemplateResponse(request=request, name="student_login.html", context={"msg": msg})


@app.post("/student-login")
def student_login(
        request: Request,
        login: str = Form(...),
        password: str = Form(...),
        device_id: str = Form(...)
):
    res = (
        supabase.table("student")
        .select("studentid, fullname, loginname, passwordplain, group_id, device_id")
        .eq("loginname", login)
        .limit(1)
        .execute()
    )

    if not res.data:
        return RedirectResponse("/student-login?msg=Логин%20қате", status_code=302)

    st = res.data[0]

    if st.get("passwordplain") != password:
        return RedirectResponse("/student-login?msg=Пароль%20қате", status_code=302)

    db_device = st.get("device_id")
    if not db_device:
        try:
            supabase.table("student").update({"device_id": device_id}).eq("studentid", st["studentid"]).execute()
        except Exception:
            return RedirectResponse(
                "/student-login?msg=Бұл%20құрылғы%20басқа%20студенттің%20аккаунтына%20байланған!",
                status_code=302
            )
    else:
        if db_device != device_id:
            return RedirectResponse(
                "/student-login?msg=Бұл%20аккаунт%20басқа%20құрылғыға%20байланған",
                status_code=302
            )

    request.session["studentid"] = st["studentid"]
    request.session["student_name"] = st.get("fullname", "")
    request.session["device_id"] = device_id
    return RedirectResponse("/attend", status_code=302)


@app.get("/student-logout")
def student_logout(request: Request):
    request.session.pop("studentid", None)
    request.session.pop("student_name", None)
    request.session.pop("device_id", None)
    return RedirectResponse("/student-login", status_code=302)


@app.get("/attend", response_class=HTMLResponse)
def attend_page(request: Request, msg: str = ""):
    sid = require_student(request)
    if not sid:
        return RedirectResponse("/student-login", status_code=302)

    res = supabase.table("campuses").select("id, name, lat, lng, radius_m").order("id").execute()
    campuses = res.data or []

    return templates.TemplateResponse(
        request=request,
        name="attend.html",
        context={
            "campuses": campuses,
            "msg": msg,
            "student_name": request.session.get("student_name", "")
        }
    )


@app.post("/attend")
def attend_submit(
        request: Request,
        campus_id: int = Form(...),
        lat: float = Form(...),
        lng: float = Form(...),
        device_id: str = Form(...)
):
    sid = require_student(request)
    if not sid:
        return RedirectResponse("/student-login", status_code=302)

    st = (
             supabase.table("student")
             .select("studentid, device_id")
             .eq("studentid", sid)
             .limit(1)
             .execute()
             .data
         ) or []

    if not st:
        return RedirectResponse("/student-login?msg=Студент%20табылмады", status_code=302)

    db_device = st[0].get("device_id")
    if not db_device or db_device != device_id:
        return RedirectResponse("/attend?msg=Device%20сәйкес%20емес", status_code=302)

    c = (
            supabase.table("campuses")
            .select("id, name, lat, lng, radius_m")
            .eq("id", campus_id)
            .limit(1)
            .execute()
            .data
        ) or []

    if not c:
        return RedirectResponse("/attend?msg=Кампус%20табылмады", status_code=302)

    campus = c[0]

    dist_m = haversine_m(lat, lng, float(campus["lat"]), float(campus["lng"]))
    if dist_m > float(campus["radius_m"]):
        return RedirectResponse("/attend?msg=Сіз%20кампус%20аймағынан%20тыссыз", status_code=302)

    today = date.today().isoformat()
    now = datetime.now()

    existing = (
                   supabase.table("attendance_daily")
                   .select("id")
                   .eq("studentid", sid)
                   .eq("attend_date", today)
                   .limit(1)
                   .execute()
                   .data
               ) or []

    payload = {
        "studentid": sid,
        "attend_date": today,
        "attend_time": now.strftime("%H:%M:%S"),
        "campus_id": campus_id,
        "lat": lat,
        "lng": lng,
        "device_id": device_id,
        "present": True
    }

    if existing:
        supabase.table("attendance_daily").update(payload).eq("id", existing[0]["id"]).execute()
    else:
        supabase.table("attendance_daily").insert(payload).execute()

    return RedirectResponse("/attend-result", status_code=302)


@app.get("/attend-result", response_class=HTMLResponse)
def attend_result(request: Request):
    sid = require_student(request)
    if not sid:
        return RedirectResponse("/student-login", status_code=302)

    today = date.today().isoformat()

    att = (
              supabase.table("attendance_daily")
              .select("attend_date, attend_time, campus_id, present")
              .eq("studentid", sid)
              .eq("attend_date", today)
              .limit(1)
              .execute()
              .data
          ) or []

    campus_name = ""
    attend_time = ""
    present = False

    if att:
        attend_time = att[0].get("attend_time", "") or ""
        present = bool(att[0].get("present"))
        cid = att[0].get("campus_id")
        if cid:
            c = supabase.table("campuses").select("name").eq("id", cid).limit(1).execute().data or []
            if c:
                campus_name = c[0]["name"]

    return templates.TemplateResponse(
        request=request,
        name="attend_result.html",
        context={
            "student_name": request.session.get("student_name", ""),
            "attend_time": attend_time,
            "campus_name": campus_name,
            "present": present
        }
    )


# -------------------- ADMIN LOGIC --------------------

@app.get("/admin-login", response_class=HTMLResponse)
def admin_login_page(request: Request, msg: str = ""):
    return templates.TemplateResponse(request=request, name="admin_login.html", context={"msg": msg})


@app.post("/admin-login")
def admin_login(request: Request, login: str = Form(...), password: str = Form(...)):
    if login in ADMIN_ACCOUNTS and ADMIN_ACCOUNTS[login]["password"] == password:
        request.session["is_admin"] = True
        request.session["admin_dept"] = ADMIN_ACCOUNTS[login]["dept"]
        
        # Басты админ бірден Барлық топтарды көру бетіне өтеді
        if ADMIN_ACCOUNTS[login]["dept"] == "ALL":
            return RedirectResponse("/admin-dashboard?dept=БАРЛЫҚ БӨЛІМДЕР", status_code=302)
        
        return RedirectResponse(f"/admin-dashboard?dept={ADMIN_ACCOUNTS[login]['dept']}", status_code=302)
    return RedirectResponse("/admin-login?msg=Қате%20логин/пароль", status_code=302)


@app.get("/admin-logout")
def admin_logout(request: Request):
    request.session.pop("is_admin", None)
    request.session.pop("admin_dept", None)
    return RedirectResponse("/admin-login", status_code=302)


@app.get("/admin-dashboard", response_class=HTMLResponse)
def admin_dashboard(
        request: Request,
        group_id: str = "",
        q: str = "",
        day: str = "",
        dept: Optional[str] = None
):
    if not require_admin(request):
        return RedirectResponse("/admin-login", status_code=302)

    # 1. Сессиядан кім кіргенін анықтау
    session_dept = request.session.get("admin_dept", "IT")
    
    # Егер Басты админ кірсе, ол батырмалар арқылы бөлім таңдай алады. 
    # Кәдімгі админ тек өз бөлімінде құлыптаулы тұрады.
    if session_dept == "ALL":
        current_department = dept if dept else "БАРЛЫҚ БӨЛІМДЕР"
    else:
        current_department = session_dept

    if day and day.strip():
        try:
            selected_date = datetime.strptime(day.strip(), "%Y-%m-%d").date()
        except ValueError:
            selected_date = date.today()
    else:
        selected_date = date.today()

    selected_day = selected_date.isoformat()
    gid = safe_int(group_id)

    # 2. Базадан барлық топтарды оқу
    all_groups = (
                     supabase.table("groups")
                     .select("group_id, group_name")
                     .order("group_name")
                     .execute()
                     .data
                 ) or []

    # 3. Басты админ бе әлде бөлім админі ме — соған қарай сүзгілеу
    if current_department == "БАРЛЫҚ БӨЛІМДЕР":
        allowed_group_ids = None
        groups = all_groups
    else:
        allowed_group_ids = DEPARTMENT_MAP.get(current_department, [])
        groups = [g for g in all_groups if g["group_id"] in allowed_group_ids]
    
    students = fetch_all_students(group_id=gid, q=q, allowed_group_ids=allowed_group_ids, batch_size=500)

    att_day = (
                  supabase.table("attendance_daily")
                  .select("studentid, attend_time, campus_id, present")
                  .eq("attend_date", selected_day)
                  .execute()
                  .data
              ) or []
    attendance_map = {a["studentid"]: a for a in att_day if "studentid" in a}

    campuses = supabase.table("campuses").select("id, name").execute().data or []
    campus_map = {c["id"]: c["name"] for c in campuses if "id" in c}

    rows = []
    present_count = 0
    absent_count = 0

    for s in students:
        sid = s["studentid"]
        a = attendance_map.get(sid)
        present = bool(a.get("present")) if a else False

        if present:
            present_count += 1
        else:
            absent_count += 1

        campus_name = ""
        attend_time = ""
        if a:
            attend_time = a.get("attend_time", "") or ""
            cid = a.get("campus_id")
            if cid in campus_map:
                campus_name = campus_map[cid]

        rows.append({
            "studentid": sid,
            "fullname": s.get("fullname", ""),
            "loginname": s.get("loginname", ""),
            "present": present,
            "campus_name": campus_name,
            "attend_time": attend_time
        })

    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html",
        context={
            "groups": groups,
            "group_id": gid,
            "q": q,
            "day": selected_day,
            "today": selected_day,
            "present_count": present_count,
            "absent_count": absent_count,
            "rows": rows,
            "current_dept": current_department,
            "session_dept": session_dept
        }
    )
