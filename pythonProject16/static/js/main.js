function getOrCreateDeviceId() {
  let id = localStorage.getItem("device_id");
  if (!id) {
    // UUID v4 simple
    id = "dev-" + ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
      (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
    localStorage.setItem("device_id", id);
  }
  return id;
}

function submitAttend() {
  const form = document.getElementById("attendForm");
  const latEl = document.getElementById("lat");
  const lngEl = document.getElementById("lng");

  if (!navigator.geolocation) {
    alert("Геолокация қолдамайды");
    return;
  }

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      latEl.value = pos.coords.latitude;
      lngEl.value = pos.coords.longitude;
      form.submit();
    },
    (err) => {
      alert("Геолокацияға рұқсат беріңіз. Error: " + err.message);
    },
    { enableHighAccuracy: true, timeout: 10000 }
  );
}
// ===== i18n (3 languages) =====
const I18N = {
  kk: {
    student_title: "Студент кіру",
    student_heading: "Студент кіру",
    admin_title: "Админ кіру",
    admin_heading: "Админ кіру",
    login_ph: "Логин",
    password_ph: "Құпиясөз",
    login_btn: "Кіру",
    admin_link: "Админ кіру",
    back_to_student: "← Студент бетіне қайту",
  },
  ru: {
    student_title: "Вход студента",
    student_heading: "Вход студента",
    admin_title: "Вход администратора",
    admin_heading: "Вход администратора",
    login_ph: "Логин",
    password_ph: "Пароль",
    login_btn: "Войти",
    admin_link: "Вход админа",
    back_to_student: "← Вернуться к студенту",
  },
  en: {
    student_title: "Student Login",
    student_heading: "Student Login",
    admin_title: "Admin Login",
    admin_heading: "Admin Login",
    login_ph: "Login",
    password_ph: "Password",
    login_btn: "Sign in",
    admin_link: "Admin",
    back_to_student: "← Back to student",
  }
};

function applyLanguage(lang) {
  const dict = I18N[lang] || I18N.kk;

  // set html lang attribute
  document.documentElement.setAttribute("lang", lang);

  // translate text nodes
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.getAttribute("data-i18n");
    if (dict[key]) el.textContent = dict[key];
  });

  // translate placeholders
  document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
    const key = el.getAttribute("data-i18n-placeholder");
    if (dict[key]) el.setAttribute("placeholder", dict[key]);
  });

  // translate title
  const titleEl = document.querySelector("title[data-i18n]");
  if (titleEl) {
    const key = titleEl.getAttribute("data-i18n");
    if (dict[key]) document.title = dict[key];
  }
}

function initLanguageUI() {
  const select = document.getElementById("langSelect");
  const saved = localStorage.getItem("lang") || "kk";

  if (select) {
    select.value = saved;
    select.addEventListener("change", () => {
      localStorage.setItem("lang", select.value);
      applyLanguage(select.value);
    });
  }

  applyLanguage(saved);
}
function markAttendance(studentId, status) {
  const params = new URLSearchParams(window.location.search);
  const day = params.get('day');

  fetch('/admin/mark-attendance', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      student_id: studentId,
      day: day,
      status: status
    })
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      location.reload();
    } else {
      alert('Қате: ' + (data.error || 'сақталмады'));
    }
  })
  .catch(err => {
    console.error(err);
    alert('Сервермен байланыс жоқ');
  });
}