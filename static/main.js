// helper
async function api(url, opts){
  opts = opts || {};
  opts.headers = opts.headers || {};
  if(!opts.headers['Content-Type']) opts.headers['Content-Type'] = 'application/json';
  const resp = await fetch(url, opts);
  return resp.json();
}

// Register
const registerForm = document.getElementById('registerForm');
if(registerForm){
  registerForm.addEventListener('submit', async (e)=>{
    e.preventDefault();
    const fd = Object.fromEntries(new FormData(e.target).entries());
    const res = await api('/api/register', {method:'POST', body: JSON.stringify({
      username: fd.username, display_name: fd.display_name, password: fd.password, confirm: fd.confirm
    })});
    const msg = document.getElementById('registerMsg');
    if(res.error) msg.innerText = res.error;
    else { msg.innerText = res.message; setTimeout(()=>location.href='/login',1200); }
  });
}

// Login
const loginForm = document.getElementById('loginForm');
if(loginForm){
  loginForm.addEventListener('submit', async (e)=>{
    e.preventDefault();
    const fd = Object.fromEntries(new FormData(e.target).entries());
    const res = await api('/api/login', {method:'POST', body: JSON.stringify({username:fd.username, password: fd.password})});
    const msg = document.getElementById('loginMsg');
    if(res.error) msg.innerText = res.error;
    else { msg.innerText = 'Berhasil masuk'; setTimeout(()=>location.href='/quiz',800); }
  });
}

// Logout button in base template
const logoutBtn = document.getElementById('logoutBtn');
if(logoutBtn){
  logoutBtn.addEventListener('click', async ()=>{
    await api('/api/logout', {method:'POST'});
    location.href = '/';
  });
}

// Weather
const getWeatherBtn = document.getElementById('getWeatherBtn');
if(getWeatherBtn){
  getWeatherBtn.addEventListener('click', async ()=>{
    const city = document.getElementById('cityInput').value || 'Jakarta';
    const res = await api(`/api/weather?city=${encodeURIComponent(city)}`);
    const container = document.getElementById('weatherResult');
    if(res.error){
      container.innerText = res.error;
      if (res.detail) container.innerText += ' ' + res.detail;
      return;
    }
    let html = `<h3>${res.city}</h3><table><tr><th>Tanggal</th><th>Hari</th><th>Suhu Siang (°C)</th><th>Suhu Malam (°C)</th><th>Cuaca</th></tr>`;
    for(const d of res.forecast){
      html += `<tr><td>${d.date}</td><td>${d.day}</td><td>${d.temp_day}</td><td>${d.temp_night}</td><td>${d.weather}</td></tr>`;
    }
    html += `</table>`;
    container.innerHTML = html;
  });
}

// Quiz logic
const nextQBtn = document.getElementById('nextQBtn');
const questionText = document.getElementById('questionText');
const choicesDiv = document.getElementById('choices');
const resultDiv = document.getElementById('result');
const scoreVal = document.getElementById('scoreVal');

async function loadScore(){
  const r = await api('/api/score');
  if(r.total_score != undefined) scoreVal.innerText = r.total_score;
}

if(nextQBtn){
  nextQBtn.addEventListener('click', async ()=>{
    resultDiv.innerText = '';
    const data = await api('/api/question');
    if(data.error){ questionText.innerText = data.error; return; }
    questionText.innerText = data.question.text;
    choicesDiv.innerHTML = '';
    for(const c of data.choices){
      const btn = document.createElement('button');
      btn.innerText = c.text;
      btn.onclick = async ()=>{
        const res = await api('/api/submit', {method:'POST', body: JSON.stringify({question_id: data.question.id, choice_id: c.id})});
        if(res.error) resultDiv.innerText = res.error;
        else {
          resultDiv.innerText = res.correct ? 'Jawaban benar!' : 'Salah :(';
          scoreVal.innerText = res.new_total;
        }
      };
      choicesDiv.appendChild(btn);
    }
  });
  loadScore();
}

// leaderboard page
async function loadLeaderboard(){
  const table = document.getElementById('leaderboardTable');
  if(!table) return;
  const data = await api('/api/leaderboard');
  const tbody = table.querySelector('tbody');
  tbody.innerHTML = '';
  data.forEach((u,i)=>{
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${i+1}</td><td>${u.display_name}</td><td>${u.username}</td><td>${u.score}</td>`;
    tbody.appendChild(tr);
  });
}
loadLeaderboard();
