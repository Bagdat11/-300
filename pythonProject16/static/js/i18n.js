(function () {
  const STORAGE_KEY = "lang";
  const DEFAULT_LANG = "kk";

  const dict = {
    kk: {
      app_title_student: "Студент кіру",
      app_title_admin: "Админ кіру",
      college_name: "Талдықорған жоғары политехникалық колледжі",
      student_subtitle: "Студенттің кіру беті",
      admin_subtitle: "Админ панельге кіру",
      h_student_login: "Кіру",
      h_admin_login: "Админ кіру",
      label_login: "Логин",
      label_password: "Құпиясөз",
      ph_login: "Логин",
      ph_password: "Құпиясөз",
      btn_enter: "КІРУ",
      link_admin: "🔒 Админ кіру",
      link_back_student: "← Студент бетіне қайту",
      lang_label: "Тіл",
    },
    ru: {
      app_title_student: "Вход студента",
      app_title_admin: "Вход админа",
      college_name: "Талдыкорганский высший политехнический колледж",
      student_subtitle: "Страница входа студента",
      admin_subtitle: "Вход в админ-панель",
      h_student_login: "Вход",
      h_admin_login: "Вход администратора",
      label_login: "Логин",
      label_password: "Пароль",
      ph_login: "Логин",
      ph_password: "Пароль",
      btn_enter: "ВОЙТИ",
      link_admin: "🔒 Вход админа",
      link_back_student: "← Назад к студенту",
      lang_label: "Язык",
    },
    en: {
      app_title_student: "Student Login",
      app_title_admin: "Admin Login",
      college_name: "Taldykorgan Higher Polytechnic College",
      student_subtitle: "Student sign-in page",
      admin_subtitle: "Admin panel sign-in",
      h_student_login: "Sign in",
      h_admin_login: "Admin sign in",
      label_login: "Login",
      label_password: "Password",
      ph_login: "Login",
      ph_password: "Password",
      btn_enter: "SIGN IN",
      link_admin: "🔒 Admin login",
      link_back_student: "← Back to student page",
      lang_label: "Language",
    },
  };

  function getLang() {
    return localStorage.getItem(STORAGE_KEY) || DEFAULT_LANG;
  }

  function setLang(lang) {
    localStorage.setItem(STORAGE_KEY, lang);
  }

  function t(lang, key) {
    return (dict[lang] && dict[lang][key]) || (dict[DEFAULT_LANG] && dict[DEFAULT_LANG][key]) || key;
  }

  function applyLang(lang) {
    const titleKey = document.documentElement.getAttribute("data-title-key");
    if (titleKey) document.title = t(lang, titleKey);

    document.documentElement.setAttribute("lang", lang);

    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      el.textContent = t(lang, key);
    });

    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      const key = el.getAttribute("data-i18n-placeholder");
      el.setAttribute("placeholder", t(lang, key));
    });
  }

  function initLanguageUI() {
    const select = document.getElementById("langSelect");
    if (!select) return;

    const current = getLang();
    select.value = current;
    applyLang(current);

    select.addEventListener("change", (e) => {
      const lang = e.target.value;
      setLang(lang);
      applyLang(lang);
    });
  }

  window.i18n = { applyLang, getLang, setLang };
  document.addEventListener("DOMContentLoaded", initLanguageUI);
})();
