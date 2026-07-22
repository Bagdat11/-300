function getOrCreateDeviceId() {
  let id = localStorage.getItem("device_id");
  if (!id) {
    id = "dev-" + Math.random().toString(36).substring(2) + Date.now().toString(36);
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

function markAttendance(studentId, status) {
  const params = new URLSearchParams(window.location.search);
  const day = params.get('day');

  fetch('/admin/mark-attendance', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ student_id: studentId, day: day, status: status })
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
