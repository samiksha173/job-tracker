
// ── Helpers ──
const SESSION_USER_NAME = document.body.dataset.userName || 'User';
function escHtml(s){ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function safeParseJSON(value, fallback = null){
  try {
    return value === null || value === undefined ? fallback : JSON.parse(value);
  } catch (error) {
    return fallback;
  }
}
const COLORS = ['co-a','co-b','co-c','co-d','co-e','co-f','co-g'];
function colorFor(str){ let h=0; for(let c of str) h=(h<<5)-h+c.charCodeAt(0); return COLORS[Math.abs(h)%COLORS.length]; }
function initials(str){ return String(str||'').trim().split(/\s+/).filter(Boolean).map(w=>w[0]).join('').substring(0,2).toUpperCase() || 'U'; }

// ── Load Dashboard ──
let dashAllApps = [];
let dashVacancyCatalog = [];
let dashAppliedVacancyIds = new Set();
let currentVacancyId = null;
async function loadDashboard() {
  const [stats, apps] = await Promise.all([
    fetch('/api/applications/stats').then(r=>r.json()).catch(()=>({total:0,applied:0,interview:0,offer:0,rejected:0,upcoming_deadlines:0,upcoming_interviews:0})),
    fetch('/api/applications').then(r=>r.json()).catch(()=>[])
  ]);
  dashAllApps = apps;

  document.getElementById('s-total').textContent     = stats.total||0;
  document.getElementById('s-applied').textContent   = stats.applied||0;
  document.getElementById('s-interview').textContent = stats.interview||0;
  document.getElementById('s-offer').textContent     = stats.offer||0;
  document.getElementById('s-rejected').textContent  = stats.rejected||0;
  document.getElementById('s-deadlines').textContent = stats.upcoming_deadlines||0;
  document.getElementById('s-interviews').textContent= stats.upcoming_interviews||0;

  renderHRNotifications(apps);
  renderDashApps(apps);
  updateProgress(apps);
  if (window.refreshNavNotifications) window.refreshNavNotifications();
  loadDashVacancies(apps);
  loadDashReminders();
  loadDashEvents();
}

function renderDashApps(apps){
  const el = document.getElementById('recent-apps');
  if (!apps.length){ el.innerHTML='<p class="empty">No applications yet. <a href="/application" style="color:var(--pk500)">Add one! →</a></p>'; return; }
  const BADGE = {applied:'b-applied',interview:'b-interview',offer:'b-offer',rejected:'b-rejected'};
  el.innerHTML = apps.slice(0,8).map(a=>{
    const sLow = (a.status||'applied').toLowerCase();
    const hrStatus = a.hr_status && a.hr_status!=='Pending' ? a.hr_status : null;
    const hrCls = !hrStatus?'':['Hired','Eligible'].includes(hrStatus)?'b-offer':hrStatus==='Interview'?'b-interview':['Rejected','Not Eligible'].includes(hrStatus)?'b-rejected':'b-pending';
    const hrNote = String(a.hr_notes || '').trim();
    const interviewDate = String(a.interview_datetime || '').trim();
    const hasHRUpdate = !!(hrStatus || hrNote || interviewDate);
    return `<div class="dash-app-row s-${sLow}">
      <div class="app-info">
        <div class="co-avatar ${colorFor(a.company)}">${initials(a.company)}</div>
        <div class="app-info-text">
          <strong>${escHtml(a.company)}</strong>
          <div class="app-meta">${escHtml(a.position)}${a.location?' · '+escHtml(a.location):''}${a.application_date?' · '+escHtml(a.application_date):''}</div>
          ${hasHRUpdate?`<div style="margin-top:4px;font-size:.73rem;color:var(--text3);display:flex;flex-direction:column;gap:3px">
            ${hrStatus?`<div>HR: <span class="badge ${hrCls}" style="font-size:.65rem;padding:2px 8px">${escHtml(hrStatus)}</span></div>`:''}
            ${hrNote?`<div>💬 <em>${escHtml(hrNote)}</em></div>`:''}
            ${interviewDate?`<div>📅 Interview: <strong>${escHtml(interviewDate)}</strong></div>`:''}
          </div>`:''}
        </div>
      </div>
      <span class="badge ${BADGE[sLow]||'b-applied'}">${escHtml(a.status)}</span>
    </div>`;
  }).join('');
}

function filterDashApps(){
  const q = document.getElementById('dash-search').value.toLowerCase();
  const s = document.getElementById('dash-status-filter').value;
  const filtered = dashAllApps.filter(a=>
    (!s||a.status===s)&&(!q||a.company.toLowerCase().includes(q)||a.position.toLowerCase().includes(q))
  );
  renderDashApps(filtered);
  document.getElementById('dash-app-empty').classList.toggle('hidden', filtered.length>0);
}

function renderHRNotifications(apps){
  const updates = apps.filter(a=>['Hired','Eligible','Interview','Rejected','Not Eligible'].includes(a.hr_status) || String(a.hr_notes || '').trim());
  const el = document.getElementById('hr-notifications');
  if (!updates.length){ el.innerHTML=''; return; }
  el.innerHTML = `<div style="background:linear-gradient(120deg,#fff0f8,#fce7f3,#ffd6e7);border:1.5px solid var(--pk200);border-radius:18px;padding:20px 24px;margin-bottom:26px;display:flex;align-items:center;gap:18px;position:relative;overflow:hidden">
    <div style="position:absolute;right:24px;bottom:-10px;font-size:5rem;opacity:.1;pointer-events:none;transform:rotate(-15deg)">🌸</div>
    <div style="width:48px;height:48px;flex-shrink:0;background:linear-gradient(135deg,var(--pk300),var(--pk500));border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:1.4rem;box-shadow:0 4px 12px rgba(219,39,119,.25)">✨</div>
    <div style="flex:1">
      <div style="font-size:1rem;font-weight:700;color:var(--pk700);margin-bottom:3px">You have ${updates.length} new HR update${updates.length>1?'s':''} today</div>
      <div style="font-size:.82rem;color:var(--text2);line-height:1.5">${updates.slice(0,2).map(a=>`${escHtml(a.company)}${a.hr_status && a.hr_status!=='Pending' ? ` → ${escHtml(a.hr_status)}` : ''}`).join(' · ')}</div>
    </div>
    <button class="wb-btn" onclick="document.getElementById('hr-notif-card').scrollIntoView({behavior:'smooth'})" style="background:linear-gradient(135deg,var(--pk400),var(--pk600));color:#fff;border:none;padding:9px 22px;border-radius:20px;font-size:.83rem;font-weight:600;box-shadow:0 3px 12px rgba(219,39,119,.28);transition:all .2s;white-space:nowrap;flex-shrink:0;cursor:pointer">View Updates</button>
  </div>`;

  const notifCard = document.getElementById('hr-notif-card');
  notifCard.style.display = 'block';
  const BADGE = {applied:'b-applied',interview:'b-interview',offer:'b-offer',rejected:'b-rejected'};
  document.getElementById('hr-notif-list').innerHTML = updates.slice(0,4).map(a=>{
    const hrStatus = a.hr_status && a.hr_status!=='Pending' ? a.hr_status : null;
    const isGood=['Hired','Eligible'].includes(hrStatus);
    const isInt=hrStatus==='Interview';
    const cls=isGood?'hr-selected':isInt?'hr-interview':hrStatus?'hr-rejected':'hr-selected';
    const icon=isGood?'🎉':isInt?'📅':hrStatus?'📋':'💬';
    const message = String(a.hr_notes || '').trim();
    const interviewDate = String(a.interview_datetime || '').trim();
    const detailParts = [];
    if (message) detailParts.push(`HR says: "<em>${escHtml(message)}</em>"`);
    if (hrStatus) detailParts.push(`Status updated to <strong>${escHtml(hrStatus)}</strong>.`);
    if (interviewDate) detailParts.push(`📅 Interview scheduled: <strong>${escHtml(interviewDate)}</strong>`);

    return `<div class="hr-banner ${cls}">
      <div class="hr-icon">${icon}</div>
      <div>
        <div class="hr-title">${hrStatus? (isGood?'Selected':isInt?'Interview':'Update') : 'HR Message'} — ${escHtml(a.company)}</div>
        <div class="hr-msg">${detailParts.join(' ')}</div>
        <span class="hr-pill ${isGood?'green':isInt?'yellow':'red'}">${escHtml(a.position)}</span>
      </div>
    </div>`;
  }).join('');
}

function updateProgress(apps){
  const total = apps.length || 1;
  const responses = apps.filter(a=>a.status!=='Applied').length;
  const interviews = apps.filter(a=>a.status==='Interview'||a.status==='Offer').length;
  const offers = apps.filter(a=>a.status==='Offer').length;
  const resp = Math.round(responses/total*100);
  const intv = Math.round(interviews/total*100);
  const offr = Math.round(offers/total*100);
  document.getElementById('d-resp-pct').textContent = resp+'%';
  document.getElementById('d-intv-pct').textContent = intv+'%';
  document.getElementById('d-offr-pct').textContent = offr+'%';
  setTimeout(()=>{
    document.getElementById('d-resp-bar').style.width = resp+'%';
    document.getElementById('d-intv-bar').style.width = intv+'%';
    document.getElementById('d-offr-bar').style.width = offr+'%';
  }, 400);
}

async function loadDashVacancies(apps = []){
  const el = document.getElementById('dash-vacancies');
  const countEl = document.getElementById('dash-vac-count');
  try{
    const vacs = await fetch('/api/vacancies').then(r=>r.json());
    dashVacancyCatalog = vacs;
    countEl.textContent = `${vacs.length} opening${vacs.length!==1?'s':''}`;
    if(!vacs.length){
      el.innerHTML = '<p class="empty">No vacancies posted by HR yet.</p>';
      return;
    }
    dashAppliedVacancyIds = new Set();
    apps.forEach(a=>{
      const match = vacs.find(v=>v.title===a.position && v.company===a.company);
      if(match) dashAppliedVacancyIds.add(match.id);
    });
    el.innerHTML = `<div class="dash-vac-grid">${vacs.map(v=>dashVacancyCard(v, dashAppliedVacancyIds.has(v.id))).join('')}</div>`;
  }catch(e){
    countEl.textContent = 'Unavailable';
    el.innerHTML = '<p class="empty">Failed to load vacancies.</p>';
  }
}

function normalizeVacancySkills(v){
  if(Array.isArray(v.skills)) return v.skills.map(s=>String(s).trim()).filter(Boolean).slice(0,6);
  if(typeof v.skills === 'string') return v.skills.split(',').map(s=>s.trim()).filter(Boolean).slice(0,6);
  return [];
}

function openVacancyModal(id){
  const v = dashVacancyCatalog.find(item => item.id === id);
  if(!v) return;
  currentVacancyId = id;

  document.getElementById('vacancy-modal-title').textContent = v.title || 'Job Opportunity';
  document.getElementById('vacancy-modal-company').textContent = v.company || 'Company';
  document.getElementById('vacancy-modal-location').textContent = v.location || 'Location TBD';
  document.getElementById('vacancy-modal-type').textContent = v.job_type || 'Full-time';
  document.getElementById('vacancy-modal-salary').textContent = v.salary || 'Not specified';
  document.getElementById('vacancy-modal-deadline').textContent = v.deadline || 'No deadline set';
  document.getElementById('vacancy-modal-experience').textContent = v.experience || 'Experience not specified';
  document.getElementById('vacancy-modal-description').textContent = v.description || 'No description provided.';

  const requirementsEl = document.getElementById('vacancy-modal-requirements');
  const requirementsWrap = document.getElementById('vacancy-modal-requirements-wrap');
  if(v.requirements){
    requirementsEl.textContent = v.requirements;
    requirementsWrap.style.display = 'block';
  } else {
    requirementsEl.textContent = 'No specific requirements listed.';
    requirementsWrap.style.display = 'block';
  }

  const skillsEl = document.getElementById('vacancy-modal-skills');
  const skills = normalizeVacancySkills(v);
  skillsEl.innerHTML = skills.length ? skills.map(s=>`<span class="vacancy-skill-chip">${escHtml(s)}</span>`).join('') : '<span class="vacancy-skill-chip">Skills not listed</span>';

  const applyBtn = document.getElementById('vacancy-modal-apply');
  const applied = dashAppliedVacancyIds.has(id);
  applyBtn.disabled = applied;
  applyBtn.textContent = applied ? 'Applied' : 'Apply Now';

  openModal('vacancy-modal');
}

function dashVacancyCard(v, isApplied){
  const logo = (v.company||'?').split(' ').map(w=>w[0]).join('').substring(0,2).toUpperCase();
  const summary = v.description || v.requirements || '';
  const experience = v.experience ? `Experience: ${escHtml(v.experience)}` : '';
  const skills = normalizeVacancySkills(v);
  return `<div class="dash-vac-card vacancy-clickable" onclick="openVacancyModal(${v.id})" role="button" tabindex="0" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();openVacancyModal(${v.id});}">
    <div class="dash-vac-top">
      <div class="dash-vac-logo">${escHtml(logo)}</div>
      <div>
        <div class="dash-vac-title">${escHtml(v.title)}</div>
        <div class="dash-vac-company">${escHtml(v.company)}</div>
      </div>
    </div>
    <div class="dash-vac-meta">
      ${v.location?`<span class="dash-vac-chip blue">${escHtml(v.location)}</span>`:''}
      ${v.job_type?`<span class="dash-vac-chip green">${escHtml(v.job_type)}</span>`:''}
      ${v.salary?`<span class="dash-vac-chip amber">${escHtml(v.salary)}</span>`:''}
      ${v.deadline?`<span class="dash-vac-chip">Deadline: ${escHtml(v.deadline)}</span>`:''}
      ${v.experience?`<span class="dash-vac-chip purple">${escHtml(v.experience)}</span>`:''}
    </div>
    ${experience?`<div class="dash-vac-experience">${experience}</div>`:''}
    ${summary?`<div class="dash-vac-desc">${escHtml(summary)}</div>`:''}
    ${skills.length?`<div class="dash-vac-note">Skills: ${skills.map(s=>escHtml(s)).join(' • ')}</div>`:''}
    <div class="dash-vac-footer">
      <span class="dash-vac-date">Posted ${escHtml((v.created_at||'').substring(0,10))}</span>
      ${isApplied
        ? '<span class="dash-vac-applied">Applied</span>'
        : `<button class="dash-vac-apply" onclick="event.stopPropagation(); applyDashVacancy(${v.id}, this)">Apply Now</button>`}
    </div>
  </div>`;
}

async function applyDashVacancy(id, btn){
  btn.disabled = true;
  btn.textContent = 'Applying...';
  try{
    const res = await fetch(`/api/vacancies/${id}/apply`, {method:'POST'});
    const data = await res.json();
    if(data.success){
      dashAppliedVacancyIds.add(id);
      btn.outerHTML = '<span class="dash-vac-applied">Applied</span>';
      showToast('Application submitted!', 'success');
      if(currentVacancyId===id){
        const modalBtn = document.getElementById('vacancy-modal-apply');
        if(modalBtn){
          modalBtn.disabled = true;
          modalBtn.textContent = 'Applied';
        }
      }
      loadDashboard();
    }else{
      showToast(data.message || data.error || 'Could not apply.', 'error');
      btn.disabled = false;
      btn.textContent = 'Apply Now';
    }
  }catch(e){
    showToast('Network error. Please try again.', 'error');
    btn.disabled = false;
    btn.textContent = 'Apply Now';
  }
}

async function loadDashReminders(){
  try{
    const res = await fetch('/api/reminders');
    const rems = await res.json();
    const el = document.getElementById('dash-reminders');
    if (!rems.length){ el.innerHTML='<p class="empty">No reminders. <a href="/reminders" style="color:var(--pk500)">Add one →</a></p>'; return; }
    const today=new Date(); today.setHours(0,0,0,0);
    el.innerHTML = rems.slice(0,3).map(r=>{
      const d=new Date(r.remind_date);
      const diff=Math.ceil((d-today)/86400000);
      const urgCls=diff<=2?'urg-urgent':diff<=7?'urg-week':'urg-soon';
      return `<div class="rem-card rem-${r.reminder_type}">
        <div class="rem-header">
          <span class="rem-type-badge">${r.reminder_type}</span>
          <span class="rem-date">${r.remind_date}</span>
          <span class="urgency ${urgCls}">${diff<=0?'TODAY':diff+'d'}</span>
        </div>
        <div class="rem-text">${escHtml(r.title)}</div>
        ${r.note?`<div class="rem-note">${escHtml(r.note)}</div>`:''}
      </div>`;
    }).join('')+`<a href="/reminders" style="display:block;text-align:center;font-size:.8rem;color:var(--pk500);font-weight:600;margin-top:8px;padding:6px">View all reminders →</a>`;
  }catch(e){}
}

async function loadDashEvents(){
  try{
    const now=new Date();
    const ym=`${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}`;
    const res=await fetch(`/api/events?month=${ym}`);
    const events=await res.json();
    const el=document.getElementById('dash-events');
    const upcoming=events.filter(e=>e.event_date>=ym).slice(0,4);
    if(!upcoming.length){ el.innerHTML='<p class="empty">No upcoming events. <a href="/calendar" style="color:var(--pk500)">Add one →</a></p>'; return; }
    const dotMap={interview:'dot-green',deadline:'dot-pink',offer:'dot-blue',reminder:'dot-red'};
    el.innerHTML=upcoming.map(e=>{
      const d=new Date(e.event_date+'T00:00');
      return `<div class="dash-ev-item">
        <div class="dash-ev-date"><div class="dash-ev-day">${d.getDate()}</div><div class="dash-ev-mon">${d.toLocaleString('default',{month:'short'})}</div></div>
        <div style="flex:1;min-width:0">
          <div style="font-size:.84rem;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${escHtml(e.title)}</div>
          <div style="font-size:.74rem;color:var(--text3)">${e.event_time?e.event_time+' · ':''}${e.note||''}</div>
        </div>
        <div class="event-type-dot" style="width:8px;height:8px;border-radius:50%;flex-shrink:0;background:${e.event_type==='interview'?'#10b981':e.event_type==='deadline'?'var(--pk400)':e.event_type==='offer'?'#3b82f6':'#ef4444'}"></div>
      </div>`;
    }).join('');
  }catch(er){}
}

// ── Mini Calendar ──
const MONTHS=['January','February','March','April','May','June','July','August','September','October','November','December'];
const DAYS=['Su','Mo','Tu','We','Th','Fr','Sa'];
const CAL_EVENTS={'2026-5-14':'pink','2026-5-16':'green','2026-5-18':'green','2026-5-20':'blue','2026-5-19':'red'};
let calYear=new Date().getFullYear(), calMonth=new Date().getMonth();
function renderCalendar(){
  const grid=document.getElementById('cal-grid');
  document.getElementById('cal-month-label').textContent=MONTHS[calMonth]+' '+calYear;
  grid.innerHTML='';
  DAYS.forEach(d=>{const el=document.createElement('div');el.className='cal-day-name';el.textContent=d;grid.appendChild(el)});
  const firstDay=new Date(calYear,calMonth,1).getDay();
  const daysInMonth=new Date(calYear,calMonth+1,0).getDate();
  const today=new Date();
  for(let i=0;i<firstDay;i++){const el=document.createElement('div');el.className='cal-cell';grid.appendChild(el)}
  for(let d=1;d<=daysInMonth;d++){
    const el=document.createElement('div');el.className='cal-cell';el.textContent=d;
    const isToday=d===today.getDate()&&calMonth===today.getMonth()&&calYear===today.getFullYear();
    if(isToday) el.classList.add('today');
    const key=`${calYear}-${calMonth+1}-${d}`;
    if(CAL_EVENTS[key]){const dot=document.createElement('div');dot.className=`event-dot dot-${CAL_EVENTS[key]}`;el.style.position='relative';el.appendChild(dot);}
    el.addEventListener('click',()=>{document.querySelectorAll('.cal-cell.selected').forEach(c=>c.classList.remove('selected'));if(!isToday)el.classList.add('selected');});
    grid.appendChild(el);
  }
}
function prevMonth(){if(calMonth===0){calMonth=11;calYear--;}else calMonth--;renderCalendar();}
function nextMonth(){if(calMonth===11){calMonth=0;calYear++;}else calMonth++;renderCalendar();}

// ── Modals ──
function openModal(id){document.getElementById(id).classList.remove('hidden')}
function closeModal(id){document.getElementById(id).classList.add('hidden')}
document.querySelectorAll('.modal').forEach(m=>{m.addEventListener('click',e=>{if(e.target===m)m.classList.add('hidden')})});

// ── Add Application (modal) ──
async function addApplication(){
  const company=document.getElementById('m-company').value.trim();
  const role=document.getElementById('m-role').value.trim();
  if(!company||!role){showToast('Please fill in company and role.','error');return;}
  const statusValue=document.getElementById('m-status').value;
  const date=document.getElementById('m-date').value;
  const statusLabel={applied:'Applied',interview:'Interview',offer:'Offer',rejected:'Rejected'};
  const payload = {
    company,
    position: role,
    location: document.getElementById('m-location').value.trim(),
    status: statusLabel[statusValue] || 'Applied',
    application_date: date,
    notes: document.getElementById('m-notes').value.trim()
  };
  try{
    const res = await fetch('/api/applications', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if(!res.ok){ showToast(data.error || 'Error adding application', 'error'); return; }
    ['m-company','m-role','m-location','m-notes'].forEach(id=>document.getElementById(id).value='');
    document.getElementById('m-date').value='';
    closeModal('add-app-modal');
    showToast('Application added for '+company+' 🌸','success');
    await loadDashboard();
    if (window.refreshNavNotifications) window.refreshNavNotifications();
  }catch(e){
    showToast('Network error. Please try again.', 'error');
  }
}

// ── Add Reminder (modal) ──
function addReminder(){
  const title=document.getElementById('r-title').value.trim();
  if(!title){showToast('Please enter a reminder title.','error');return;}
  const type=document.getElementById('r-type').value;
  const date=document.getElementById('r-date').value;
  const note=document.getElementById('r-note').value.trim();
  const typeColor={Interview:'rc-green',Deadline:'rc-red','Follow-up':'','Offer Deadline':'rc-blue',Other:''};
  const dateStr=date?new Date(date).toLocaleDateString('en-IN',{day:'numeric',month:'long',year:'numeric'}):'No date set';
  const card=document.createElement('div');
  card.className='rem-card '+(typeColor[type]||'');
  card.innerHTML=`<div class="rem-header"><span class="rem-type-badge">${type}</span><span class="rem-date">${dateStr}</span></div><div class="rem-text">${escHtml(title)}</div>${note?`<div class="rem-note">${escHtml(note)}</div>`:''}`;
  const el=document.getElementById('dash-reminders');
  if(el.querySelector('.empty'))el.innerHTML='';
  el.prepend(card);
  ['r-title','r-date','r-note'].forEach(id=>document.getElementById(id).value='');
  closeModal('add-reminder-modal');
  showToast('Reminder set! 📌','success');
}

// ── Profile ──
let profileData = safeParseJSON(localStorage.getItem('hirebloom-profile'), {});

async function loadProfileUI(){
  try {
    const response = await fetch('/api/profile');
    if (response.ok) {
      const serverProfile = await response.json();
      if (serverProfile && Object.keys(serverProfile).length) {
        profileData = { ...profileData, ...serverProfile };
        localStorage.setItem('hirebloom-profile', JSON.stringify(profileData));
      }
    }
  } catch (error) {
    // Fall back to locally cached data if the server is unavailable.
  }

  const displayName = (profileData.name || SESSION_USER_NAME || 'User').trim();
  const avatarInitials = initials(displayName);
  const dashProfileName = document.getElementById('dash-profile-name');
  if (dashProfileName) dashProfileName.textContent = displayName;
  const dashAvatarInitials = document.getElementById('dash-avatar-initials');
  if (dashAvatarInitials) dashAvatarInitials.textContent = avatarInitials;
  const profilePreviewInitials = document.getElementById('profile-preview-initials');
  if (profilePreviewInitials) profilePreviewInitials.textContent = avatarInitials;
  const pName = document.getElementById('p-name');
  if (pName) pName.value = displayName;
  const role = (profileData.role || 'Open to new opportunities').trim();
  const dashProfileRole = document.getElementById('dash-profile-role');
  if (dashProfileRole) dashProfileRole.textContent = role;
  const av = document.getElementById('dash-avatar-display');
  const prev = document.getElementById('profile-preview');
  if (profileData.photo && av && prev) {
    av.style.background = 'transparent';
    av.innerHTML = `<img src="${profileData.photo}" style="width:100%;height:100%;object-fit:cover"/>`;
    prev.style.background = 'transparent';
    prev.innerHTML = `<img src="${profileData.photo}" style="width:100%;height:100%;object-fit:cover;border-radius:50%"/>`;
    if (profilePreviewInitials) profilePreviewInitials.textContent = '';
  } else if (av && prev) {
    av.style.background = 'linear-gradient(135deg, var(--pk300), var(--pk600))';
    av.innerHTML = `<span id="dash-avatar-initials">${avatarInitials}</span>`;
    prev.style.background = 'linear-gradient(135deg, var(--pk300), var(--pk600))';
    prev.innerHTML = `<span id="profile-preview-initials">${avatarInitials}</span>`;
  }
  if (profileData.skills) {
    const tags = profileData.skills.split(',').map(s => s.trim()).filter(Boolean).slice(0, 4);
    const row = document.getElementById('dash-tags-row');
    if (row) row.innerHTML = tags.map(t => `<span class="tag">${escHtml(t)}</span>`).join('') + '<span class="tag-gray">Open to work</span>';
  }
  const fields = ['role', 'email', 'phone', 'location', 'bio', 'skills', 'linkedin', 'portfolio'];
  fields.forEach(f => {
    const el = document.getElementById('p-' + f);
    if (el && profileData[f]) el.value = profileData[f];
  });
  const progressKeys = ['name', 'role', 'email', 'phone', 'location', 'bio', 'skills', 'linkedin', 'portfolio'];
  const filled = progressKeys.filter(k => profileData[k] && String(profileData[k]).trim()).length + (profileData.photo ? 1 : 0);
  const fullPct = Math.min(Math.round(filled / (progressKeys.length + 1) * 100), 100);
  const dashProfileBar = document.getElementById('dash-profile-bar');
  if (dashProfileBar) dashProfileBar.style.width = fullPct + '%';
  const dashProfilePct = document.getElementById('dash-profile-pct');
  if (dashProfilePct) dashProfilePct.textContent = fullPct + '%';
}

function updateProfilePreview(){
  const name=(document.getElementById('p-name').value||SESSION_USER_NAME||'User').trim();
  const initialsText=initials(name);
  const previewInitials=document.getElementById('profile-preview-initials');
  if(previewInitials) previewInitials.textContent=initialsText;
}

function previewPhoto(evt){
  const file=evt.target.files[0];
  if(!file) return;
  const reader=new FileReader();
  reader.onload=e=>{
    const src=e.target.result;
    const prev=document.getElementById('profile-preview');
    prev.style.background='transparent';
    prev.innerHTML=`<img src="${src}" style="width:100%;height:100%;object-fit:cover;border-radius:50%"/>`;
    document.getElementById('profile-preview-initials').textContent='';
    profileData.photo=src;
  };
  reader.readAsDataURL(file);
}

async function saveProfile(){
  const name=document.getElementById('p-name').value.trim();
  if(!name){
    showToast('Please enter your name before saving your profile.','error');
    return;
  }
  const fields=['name','role','email','phone','location','bio','skills','linkedin','portfolio'];
  fields.forEach(f=>{ const el=document.getElementById('p-'+f); if(el) profileData[f]=el.value.trim(); });

  try {
    const response = await fetch('/api/profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profileData)
    });

    if(!response.ok){
      const error = await response.json().catch(()=>({error:'Failed to save profile'}));
      throw new Error(error.error || 'Failed to save profile');
    }

    const savedProfile = await response.json();
    profileData = { ...profileData, ...savedProfile };
    localStorage.setItem('hirebloom-profile',JSON.stringify(profileData));
    await loadProfileUI();
    closeModal('profile-modal');
    showToast('Profile updated! ✨','success');
  } catch (error) {
    showToast(error.message || 'Could not save profile right now.', 'error');
  }
}

const RESUME_STEP_IDS = ['resume-step-1','resume-step-2','resume-step-3','resume-step-4'];
let currentResumeStep = 1;
let resumeExperienceEntries = [];

function openResumeBuilderModal(){
  const savedResumeDraft = JSON.parse(localStorage.getItem('hirebloom-resume-builder') || 'null');
  const profile = JSON.parse(localStorage.getItem('hirebloom-profile') || '{}');

  document.getElementById('resume-name').value = profile.name || SESSION_USER_NAME || 'Your Name';
  document.getElementById('resume-role').value = profile.role || 'Professional';
  document.getElementById('resume-email').value = profile.email || '';
  document.getElementById('resume-phone').value = profile.phone || '';
  document.getElementById('resume-location').value = profile.location || '';
  document.getElementById('resume-target-role').value = profile.targetRole || (profile.role || 'Product Designer');
  document.getElementById('resume-experience-level').value = profile.experienceLevel || '5+ years';
  document.getElementById('resume-summary').value = profile.bio || 'Results-driven professional focused on delivering user-friendly experiences and measurable business impact.';

  if(savedResumeDraft){
    Object.assign(profile, savedResumeDraft);
    document.getElementById('resume-name').value = savedResumeDraft.name || document.getElementById('resume-name').value;
    document.getElementById('resume-role').value = savedResumeDraft.role || document.getElementById('resume-role').value;
    document.getElementById('resume-target-role').value = savedResumeDraft.targetRole || document.getElementById('resume-target-role').value;
    document.getElementById('resume-summary').value = savedResumeDraft.summary || document.getElementById('resume-summary').value;
    document.getElementById('resume-experience-level').value = savedResumeDraft.experienceLevel || document.getElementById('resume-experience-level').value;
    resumeExperienceEntries = Array.isArray(savedResumeDraft.experienceEntries) && savedResumeDraft.experienceEntries.length ? savedResumeDraft.experienceEntries : getDefaultResumeExperienceEntries();
  } else {
    resumeExperienceEntries = getDefaultResumeExperienceEntries();
  }

  const skillValue = profile.skills || '';
  document.getElementById('resume-skill-input').value = '';
  updateResumeSkillTags(skillValue);
  renderResumeExperienceEntries();
  currentResumeStep = 1;
  showResumeBuilderStep(currentResumeStep);
  document.getElementById('resume-generated-state').hidden = true;
  document.getElementById('resume-download-btn').hidden = true;
  document.getElementById('resume-preview-area').innerHTML = '';
  openModal('resume-builder-modal');
}

function getDefaultResumeExperienceEntries(){
  return [
    {
      company: 'Previous Company',
      title: 'Senior Product Designer',
      duration: '2022 - Present',
      summary: 'Led product redesigns, improved user engagement metrics, and collaborated cross-functionally to launch high-impact features.'
    }
  ];
}

function showResumeBuilderStep(step){
  currentResumeStep = step;
  RESUME_STEP_IDS.forEach((id, index)=>{
    const isActive = index === step-1;
    document.getElementById(id).hidden = !isActive;
  });
  document.getElementById('resume-step-current').textContent = step;
  document.getElementById('resume-step-total').textContent = RESUME_STEP_IDS.length;
  document.getElementById('resume-progress-fill').style.width = `${Math.round((step/RESUME_STEP_IDS.length)*100)}%`;
  document.getElementById('resume-step-label').textContent = [
    'Profile basics',
    'Target role & summary',
    'Professional experience',
    'Key skills'
  ][step-1];

  document.getElementById('resume-back-btn').hidden = step === 1;
  document.getElementById('resume-next-btn').hidden = step === RESUME_STEP_IDS.length;
  document.getElementById('resume-generate-btn').hidden = step !== RESUME_STEP_IDS.length;

  if(step === RESUME_STEP_IDS.length){
    generateResumePreview();
  }
}

function resumeBuilderChangeStep(delta){
  const nextStep = Math.min(Math.max(currentResumeStep + delta, 1), RESUME_STEP_IDS.length);
  showResumeBuilderStep(nextStep);
}

function addResumeExperienceEntry(){
  resumeExperienceEntries.push({company:'', title:'', duration:'', summary:''});
  renderResumeExperienceEntries();
}

function removeResumeExperience(index){
  resumeExperienceEntries.splice(index,1);
  renderResumeExperienceEntries();
}

function renderResumeExperienceEntries(){
  const container = document.getElementById('resume-experience-list');
  if(!container) return;

  container.innerHTML = resumeExperienceEntries.map((entry, index)=>`
    <div class="resume-experience-entry" data-index="${index}">
      <div class="resume-experience-header">
        <div class="resume-experience-title">${escHtml(entry.company || `Experience ${index + 1}`)}</div>
        <button class="resume-experience-remove" type="button" onclick="removeResumeExperience(${index})">Remove</button>
      </div>
      <div class="resume-form-grid">
        <label class="resume-field">Company
          <input class="form-input" type="text" data-field="company" value="${escHtml(entry.company)}" placeholder="Company name"/>
        </label>
        <label class="resume-field">Role
          <input class="form-input" type="text" data-field="title" value="${escHtml(entry.title)}" placeholder="Senior Product Designer"/>
        </label>
        <label class="resume-field">Duration
          <input class="form-input" type="text" data-field="duration" value="${escHtml(entry.duration)}" placeholder="2021 - 2024"/>
        </label>
        <label class="resume-field resume-full-span">Achievement / impact
          <textarea class="form-input" rows="3" data-field="summary" placeholder="Improved conversion by 18% through a redesigned onboarding flow.">${escHtml(entry.summary)}</textarea>
        </label>
      </div>
    </div>
  `).join('');

  container.querySelectorAll('[data-field]').forEach(field=>{
    field.addEventListener('input', (event)=>{
      const index = Number(event.target.closest('.resume-experience-entry').dataset.index);
      const fieldName = event.target.dataset.field;
      resumeExperienceEntries[index][fieldName] = event.target.value;
      const title = document.querySelector(`.resume-experience-entry[data-index="${index}"] .resume-experience-title`);
      if(title && fieldName === 'company') title.textContent = event.target.value || `Experience ${index + 1}`;
    });
  });
}

function updateResumeSkillTags(skillText){
  const input = document.getElementById('resume-skill-input');
  const container = document.getElementById('resume-skill-tags');
  if(!container) return;

  const skills = Array.from(new Set((skillText || (input ? input.value : '')).split(',').map(skill=>skill.trim()).filter(Boolean)));
  container.innerHTML = skills.length ? skills.map(skill=>`<span class="resume-tag-chip">${escHtml(skill)} <button class="resume-tag-remove" type="button" onclick="removeResumeSkill('${skill.replace(/'/g, "\\'")}')">×</button></span>`).join('') : '<div class="resume-modal-note">No skills added yet. Add a few keywords to tailor the draft.</div>';
}

function addResumeSkillFromInput(){
  const input = document.getElementById('resume-skill-input');
  if(!input) return;
  const value = input.value.trim();
  if(!value){
    showToast('Enter a skill first.', 'error');
    return;
  }
  const existing = (document.getElementById('resume-skill-tags').querySelectorAll('.resume-tag-chip') || []);
  const label = value.split(',').map(item=>item.trim()).filter(Boolean);
  const skills = [];
  existing.forEach(el=>skills.push(el.textContent.replace('×','').trim()));
  label.forEach(skill=>{
    if(!skills.includes(skill)) skills.push(skill);
  });
  updateResumeSkillTags(skills.join(', '));
  input.value = '';
}

function removeResumeSkill(skill){
  const currentSkills = Array.from(document.getElementById('resume-skill-tags').querySelectorAll('.resume-tag-chip')).map(el=>el.textContent.replace('×','').trim());
  const nextSkills = currentSkills.filter(item=>item !== skill);
  updateResumeSkillTags(nextSkills.join(', '));
}

function generateResumePreview(){
  const preview = document.getElementById('resume-preview-area');
  const loading = document.getElementById('resume-generated-state');
  const downloadBtn = document.getElementById('resume-download-btn');
  if(!preview || !loading || !downloadBtn) return;

  loading.hidden = false;
  preview.innerHTML = '';

  const name = document.getElementById('resume-name').value.trim() || 'Your Name';
  const role = document.getElementById('resume-role').value.trim() || 'Professional';
  const targetRole = document.getElementById('resume-target-role').value.trim() || 'Target Role';
  const experienceLevel = document.getElementById('resume-experience-level').value.trim() || 'Experience';
  const summary = document.getElementById('resume-summary').value.trim() || 'Results-focused professional delivering measurable value.';
  const skills = Array.from(new Set(Array.from(document.getElementById('resume-skill-tags').querySelectorAll('.resume-tag-chip')).map(el=>el.textContent.replace('×','').trim()).filter(Boolean)));

  const experiences = resumeExperienceEntries.map(entry=>`
    <li>
      <strong>${escHtml(entry.title || 'Role')}</strong> — ${escHtml(entry.company || 'Company')}<br/>
      <span>${escHtml(entry.duration || 'Duration')}</span><br/>
      ${escHtml(entry.summary || 'Key achievement highlight.')}
    </li>
  `).join('');

  const skillList = skills.length ? skills.map(skill=>`<li>${escHtml(skill)}</li>`).join('') : '<li>Skills will appear here.</li>';

  preview.innerHTML = `
    <div class="resume-preview-root">
      <h1>${escHtml(name)}</h1>
      <div class="resume-subtitle">${escHtml(role)} • ${escHtml(document.getElementById('resume-location').value.trim() || 'Location available')}</div>
      <div class="resume-meta">
        <span>Target role: ${escHtml(targetRole)}</span>
        <span>Experience: ${escHtml(experienceLevel)}</span>
        <span>${escHtml(document.getElementById('resume-email').value.trim() || 'Email available')}</span>
      </div>
      <div class="resume-section">
        <h2>Professional Summary</h2>
        <p>${escHtml(summary)}</p>
      </div>
      <div class="resume-section">
        <h2>Core Skills</h2>
        <ul class="resume-list">${skillList}</ul>
      </div>
      <div class="resume-section">
        <h2>Professional Experience</h2>
        <ul class="resume-list">${experiences}</ul>
      </div>
    </div>
  `;

  loading.hidden = true;
  downloadBtn.hidden = false;

  localStorage.setItem('hirebloom-resume-builder', JSON.stringify({
    name: document.getElementById('resume-name').value.trim(),
    role: document.getElementById('resume-role').value.trim(),
    targetRole: document.getElementById('resume-target-role').value.trim(),
    summary: document.getElementById('resume-summary').value.trim(),
    experienceLevel: document.getElementById('resume-experience-level').value.trim(),
    experienceEntries: resumeExperienceEntries,
    skills: skills.join(', ')
  }));
}

function downloadResume(){
  const preview = document.getElementById('resume-preview-area');
  if(!preview) return;

  const printWindow = window.open('', '_blank', 'width=900,height=700');
  if(!printWindow){
    showToast('Popup blocked. Please allow popups to print your resume as PDF.', 'error');
    return;
  }

  const printTitle = (document.getElementById('resume-name').value.trim() || 'Resume') + ' Resume';
  const previewMarkup = preview.innerHTML;

  printWindow.document.write(`
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8" />
        <title>${escHtml(printTitle)}</title>
        <style>
          body { margin: 0; padding: 28px; font-family: Inter, system-ui, sans-serif; color: #1f2937; background: #fff; }
          .resume-preview-root { max-width: 800px; margin: 0 auto; }
          .resume-preview-root h1 { margin: 0; font-size: 30px; color: #1f2937; }
          .resume-subtitle { margin-top: 6px; font-size: 14px; color: #6b7280; font-weight: 600; }
          .resume-meta { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 12px; font-size: 12px; color: #4b5563; }
          .resume-meta span { background: #f3f4f6; border-radius:999px; padding: 5px 10px; }
          .resume-section { margin-top: 20px; border-top: 1px solid #e5e7eb; padding-top: 14px; }
          .resume-section h2 { margin: 0 0 8px; font-size: 16px; color: #111827; }
          .resume-section p { margin: 0; line-height: 1.55; font-size: 13px; color: #374151; }
          .resume-list { margin: 0; padding-left: 18px; }
          .resume-list li { margin-bottom: 8px; font-size: 13px; line-height: 1.45; color: #374151; }
          @media print { body { padding: 18px; } }
        </style>
      </head>
      <body>
        ${previewMarkup}
      </body>
    </html>
  `);
  printWindow.document.close();
  printWindow.focus();
  setTimeout(()=>{
    printWindow.print();
    printWindow.close();
  }, 250);

  showToast('Print dialog opened. Choose Save as PDF.', 'success');
}

const interviewPrompts = [
  'Tell me about a project where you solved a real user problem and measured the outcome.',
  'How would you prioritize competing deadlines while keeping product quality high?',
  'Describe a time you received feedback and turned it into a meaningful improvement.',
  'What motivates you to stay engaged in fast-changing product environments?'
];

function refreshInterviewQuestions(){
  const container = document.getElementById('interview-question-list');
  if(!container) return;

  const shuffled = [...interviewPrompts].sort(()=>Math.random()-0.5).slice(0,4);
  container.innerHTML = shuffled.map((prompt, index)=>`<div class="interview-question-item">${index + 1}. ${escHtml(prompt)}</div>`).join('');
}

function analyzeMockAnswer(){
  const answerInput = document.getElementById('mock-answer-input');
  const feedbackBox = document.getElementById('mock-feedback-box');
  if(!answerInput || !feedbackBox) return;

  const answer = answerInput.value.trim();
  if(!answer){
    feedbackBox.innerHTML = '<div class="interview-empty-state">Type a sample answer first to receive coaching feedback.</div>';
    showToast('Add an answer before analyzing it.', 'error');
    return;
  }

  const length = answer.length;
  const hasConcrete = /(metric|number|improved|increased|reduced|used|launched|built)/i.test(answer);
  const hasStructure = /(first|then|next|finally|because)/i.test(answer);

  let score = 'Strong';
  let tips = [];

  if(length < 120){
    score = 'Needs more detail';
    tips.push('Add a concrete example and one measurable outcome.');
  } else if(length < 220){
    score = 'Good structure';
    tips.push('Add one metric or result to strengthen impact.');
  } else {
    score = 'Excellent depth';
    tips.push('Keep your answer concise while maintaining impact.');
  }

  if(!hasConcrete){
    tips.push('Include a number, metric, or specific result to make the answer memorable.');
  }

  if(!hasStructure){
    tips.push('Use a clear structure like: situation, action, result.');
  } else {
    tips.push('Your answer already follows a logical flow.');
  }

  feedbackBox.innerHTML = `
    <div style="display:flex;flex-direction:column;gap:8px">
      <div style="font-weight:800;color:var(--pk700)">Coaching summary: ${score}</div>
      <div>Here’s what stood out:</div>
      <ul style="margin:0;padding-left:18px;display:flex;flex-direction:column;gap:6px">
        ${tips.map(item=>`<li>${escHtml(item)}</li>`).join('')}
      </ul>
    </div>
  `;
}

function openInterviewPrepModal(){
  const profile = safeParseJSON(localStorage.getItem('hirebloom-profile'), {});
  const roleEl = document.getElementById('interview-prep-role');
  const answerInput = document.getElementById('mock-answer-input');
  const feedbackBox = document.getElementById('mock-feedback-box');

  if (roleEl) roleEl.textContent = profile && profile.role ? profile.role : 'Product Designer';
  refreshInterviewQuestions();
  if (answerInput) answerInput.value = '';
  if (feedbackBox) feedbackBox.innerHTML = '<div class="interview-empty-state">Your coaching feedback will appear here after you draft an answer.</div>';
  if (typeof openModal === 'function') openModal('interview-prep-modal');
}

// ── Init ──
renderCalendar();
loadDashboard();
loadProfileUI();
refreshInterviewQuestions();
showResumeBuilderStep(1);
