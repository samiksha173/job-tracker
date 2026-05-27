// Hamburger menu
const ham = document.getElementById('hamburger');
const menu = document.getElementById('mobileMenu');
if (ham) ham.addEventListener('click', () => menu.classList.toggle('open'));

// Toast helper
function showToast(msg, type='info') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `toast toast-${type}`;
  setTimeout(() => t.className = 'toast hidden', 3000);
}

// Load user info for avatar
fetch('/api/me').then(r=>r.json()).then(u=>{
  const av = document.getElementById('avatarBtn');
  if (av && u.name) av.textContent = u.name.split(' ').map(w=>w[0]).join('').toUpperCase().slice(0,2);
}).catch(()=>{});