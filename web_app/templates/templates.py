# web_app/templates/templates.py

HTML_TEMPLATE = r"""
<!doctype html>
<html lang="hu">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Futár</title>
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <style>
    body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:#fff;color:#111;margin:16px}
    .container{max-width:720px;margin:0 auto}
    .tabs{display:flex;gap:8px;margin-bottom:10px;flex-wrap:wrap}
    .tab{padding:8px 12px;border:1px solid #bbb;border-radius:999px;background:#fafafa;cursor:pointer}
    .tab.active{background:#1a73e8;color:#fff;border-color:#1a73e8}
    .card{border:1px solid #ddd;border-radius:12px;padding:12px;margin:10px 0;background:#fafafa}
    .row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
    .pill{padding:2px 8px;border-radius:999px;background:#eee;font-size:12px}
    .time-buttons{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:10px 0}
    .time-btn{border:1px solid #1a73e8;border-radius:10px;padding:10px;background:#fff;cursor:pointer;font-size:12px}
    .time-btn.selected{background:#1a73e8;color:#fff}
    .accept-btn{border:0;border-radius:10px;padding:12px;width:100%;background:#1a73e8;color:#fff;cursor:pointer}
    .muted{color:#666;font-size:12px}
    
    /* Navigációs gombok stílusai */
    .nav-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin:8px 0}
    .nav{display:block;text-decoration:none;border:1px solid #1a73e8;border-radius:8px;padding:8px;background:#fff;text-align:center;font-size:11px;color:#1a73e8}
    .nav.apple{border-color:#000;color:#000;background:#f5f5f7}
    .nav.waze{border-color:#33ccff;color:#33ccff;background:#f0f8ff}
    .nav:hover{opacity:0.8}
    
    .ok{display:none;background:#d4edda;color:#155724;border-radius:8px;padding:10px;margin:8px 0}
    .err{display:none;background:#f8d7da;color:#721c24;border-radius:8px;padding:10px;margin:8px 0}
    
    /* Útvonal optimalizáló gombok */
    .routebar{display:none;gap:6px;margin:8px 0;flex-wrap:wrap}
    .routebtn{border:0;border-radius:10px;padding:10px 12px;background:#1a73e8;color:#fff;cursor:pointer;font-size:12px}
    .routebtn.apple{background:#000}
    .routebtn.waze{background:#33ccff}
    .routebtn:hover{opacity:0.9}
  </style>
</head>
<body>
  <div class="container">

  <div id="admin-btn" style="display:none; margin-bottom:10px;">
    <button onclick="openAdmin()" class="accept-btn">⚙️ Admin</button>
  </div>

<script>
  function openAdmin(){
    const initData = window.Telegram?.WebApp?.initData || '';
    window.open(`${window.location.origin}/admin?init_data=${encodeURIComponent(initData)}`, '_blank');
  }

  async function checkAdmin(){
    try{
      const r = await fetch(`${window.location.origin}/api/is_admin`, {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ initData: window.Telegram?.WebApp?.initData || '' })
      });
      const j = await r.json();
      if(j.ok && j.admin){
        document.getElementById('admin-btn').style.display = 'block';
      }
    }catch(e){
      console.error('Admin check error:', e);
    }
  }
  checkAdmin();
</script>

    <h2>🍕 Futár felület</h2>

    <div class="tabs">
      <button class="tab" id="tab-av" onclick="setTab('available')">Elérhető</button>
      <button class="tab" id="tab-ac" onclick="setTab('accepted')">Elfogadott</button>
      <button class="tab" id="tab-pk" onclick="setTab('picked_up')">Felvett</button>
      <button class="tab" id="tab-dv" onclick="setTab('delivered')">Kiszállított</button>
    </div>

    <!-- Navigációs gombok - csak Felvett menüben -->
    <div class="routebar" id="routebar" style="display:none;">
      <button class="routebtn" onclick="openOptimizedRoute('google')">🗺️ Google Maps - Optimalizált útvonal</button>
      <button class="routebtn apple" onclick="openOptimizedRoute('apple')">🍎 Apple Maps - Optimalizált útvonal</button>
      <button class="routebtn waze" onclick="openOptimizedRoute('waze')">🚗 Waze - Optimalizált útvonal</button>
    </div>

    <div class="ok" id="ok"></div>
    <div class="err" id="err"></div>
    <div id="list">Betöltés…</div>
  </div>

<script>
  const tg = window.Telegram?.WebApp; 
  if(tg) tg.expand();
  
  const API = window.location.origin;
  let selectedETA = {}; // order_id -> 10/20/30
  let TAB = (new URLSearchParams(location.search).get('tab')) || 'available';

  function ok(m){ 
    const d=document.getElementById('ok'); 
    d.textContent=m; 
    d.style.display='block'; 
    setTimeout(()=>d.style.display='none', 3000); 
  }
  
  function err(m){ 
    const d=document.getElementById('err'); 
    d.textContent=m; 
    d.style.display='block'; 
    setTimeout(()=>d.style.display='none', 5000); 
  }

  // Navigációs függvények
  // HELPERS: cím tisztítása / dekódolása, hibabiztos
    function normalizeAddress(addr){
      if(!addr && addr !== 0) return '';
      try {
    // ha %-kódolt részeket találunk, próbáljuk dekódolni (pl. 'Danko%20Pista' -> 'Danko Pista')
        if (/%[0-9A-Fa-f]{2}/.test(addr)) {
            addr = decodeURIComponent(addr);
        }
      } catch(e) {
    // ha a dekódolás hibát dob (hibás %xx), hagyjuk az eredetit
      }
  // pluszokból szóköz, többszörös whitespace normalizálás, trim
      addr = String(addr).replace(/\+/g, ' ').replace(/\s+/g, ' ').trim();
      return addr;
    }

  function googleMapsLink(addr){
    // eltávolítjuk a sorszám előtagot, majd normalizálunk/dekódolunk
    const withoutIndex = String(addr).replace(/^\d{1,2}\.\s+/, '');
    const cleanAddr = normalizeAddress(withoutIndex);
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(cleanAddr)}`;
  }
  
  function appleMapsLink(addr){
    const cleanAddr = addr.replace(/^\d{1,2}\.\s+/, ''); // Sorszám eltávolítás
    return `https://maps.apple.com/?daddr=${encodeURIComponent(cleanAddr)}&dirflg=d`;
  }
  
  function wazeLink(addr){
    const cleanAddr = addr.replace(/^\d{1,2}\.\s+/, ''); // Sorszám eltávolítás
    return `https://waze.com/ul?q=${encodeURIComponent(cleanAddr)}&navigate=yes`;
  }

  function render(order){
    // Navigációs gombok - csak Felvett menüben
    const nav = (TAB === 'picked_up') ? `
      <div class="nav-grid">
        <a class="nav" href="${googleMapsLink(order.restaurant_address)}" target="_blank">🗺️ Google</a>
        <a class="nav apple" href="${appleMapsLink(order.restaurant_address)}" target="_blank">🍎 Apple</a>
        <a class="nav waze" href="${wazeLink(order.restaurant_address)}" target="_blank">🚗 Waze</a>
      </div>
    ` : '';
    
    const timeBtns = `
      <div class="time-buttons" style="${order.status==='pending'?'':'display:none'}">
        <button class="time-btn" data-oid="${order.id}" data-eta="10">⏱️ 10 perc</button>
        <button class="time-btn" data-oid="${order.id}" data-eta="20">⏱️ 20 perc</button>
        <button class="time-btn" data-oid="${order.id}" data-eta="30">⏱️ 30 perc</button>
      </div>
    `;
    
    let btnLabel = '🚚 Rendelés elfogadása';
    if(order.status==='accepted') btnLabel = '✅ Felvettem';
    if(order.status==='picked_up') btnLabel = '✅ Kiszállítva / Leadva';

    const showBtn = order.status !== 'delivered';
    
    return `
      <div class="card" id="card-${order.id}">
        <div class="row">
          <b>${order.group_name || order.restaurant_name}</b>
          <span class="pill">${order.status}</span>
        </div>
        <div>📍 <b>Cím:</b> ${order.restaurant_address}</div>
        ${order.phone_number ? `<div>📞 <b>Telefon:</b> ${order.phone_number}</div>` : ''}
        ${order.order_details ? `<div>📝 <b>Megjegyzés:</b> ${order.order_details}</div>` : ''}
        <div class="muted">ID: #${order.id} • ${order.created_at}</div>
        ${nav}
        ${timeBtns}
        ${showBtn ? `<button class="accept-btn" id="btn-${order.id}" onclick="doAction(${order.id}, '${order.status}')">${btnLabel}</button>` : ''}
      </div>
    `;
  }

  function wireTimeButtons(){
    document.querySelectorAll('.time-btn').forEach(b=>{
      b.addEventListener('click', ()=>{
        const oid = b.dataset.oid, eta = b.dataset.eta;
        document.querySelectorAll(`[data-oid="${oid}"]`).forEach(x=>x.classList.remove('selected'));
        b.classList.add('selected');
        selectedETA[oid] = eta;
        if(tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('light');
      });
    });
  }

  async function load(){
    // tab aktív állapot
    document.getElementById('tab-av').classList.toggle('active', TAB==='available');
    document.getElementById('tab-ac').classList.toggle('active', TAB==='accepted');
    document.getElementById('tab-pk').classList.toggle('active', TAB==='picked_up');
    document.getElementById('tab-dv').classList.toggle('active', TAB==='delivered');
    
    // Navigációs gombok megjelenítése csak Felvett menüben
    document.getElementById('routebar').style.display = (TAB==='picked_up') ? 'flex' : 'none';

    const list = document.getElementById('list');
    list.innerHTML = 'Betöltés…';

    let data = [];
    try{
      if(TAB === 'available'){
        const r = await fetch(`${API}/api/orders_by_status?status=pending`);
        if (!r.ok) throw new Error(`HTTP ${r.status}: ${r.statusText}`);
        data = await r.json();
      }else{
        const r = await fetch(`${API}/api/my_orders`, {
          method:'POST', 
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ initData: tg?.initData || '', status: TAB })
        });
        if (!r.ok) throw new Error(`HTTP ${r.status}: ${r.statusText}`);
        const j = await r.json();
        if(!j.ok) throw new Error(j.error||'Hálózati hiba');
        data = j.orders || [];
      }
    }catch(e){
      console.error('Load error:', e);
      err(e.message||'Hiba a betöltésnél');
      data = [];
    }

    if(!data.length){ 
      list.innerHTML = '<div class="muted">Nincs rendelés.</div>'; 
      return; 
    }
    
    list.innerHTML = data.map(render).join('');
    wireTimeButtons();
  }

  async function doAction(orderId, status){
    const btn = document.getElementById(`btn-${orderId}`);
    if(!btn || btn.disabled) return;
    
    btn.disabled = true; 
    const old = btn.textContent; 
    btn.textContent = '⏳...';
    
    try{
      let apiUrl, payload;
      
      if(status==='pending'){
        const eta = selectedETA[orderId]; 
        if(!eta) throw new Error('Válassz időt (10/20/30 perc).');
        apiUrl = `${API}/api/accept_order`;
        payload = { order_id: orderId, estimated_time: eta, initData: tg?.initData || '' };
      } else if(status==='accepted'){
        apiUrl = `${API}/api/pickup_order`;
        payload = { order_id: orderId, initData: tg?.initData || '' };
      } else if(status==='picked_up'){
        apiUrl = `${API}/api/mark_delivered`;
        payload = { order_id: orderId, initData: tg?.initData || '' };
      } else {
        throw new Error('Ismeretlen státusz');
      }
      
      const r = await fetch(apiUrl, {
        method:'POST', 
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify(payload)
      });
      
      if (!r.ok) throw new Error(`HTTP ${r.status}: ${r.statusText}`);
      const j = await r.json(); 
      if(!j.ok) throw new Error(j.error||'Szerver hiba');
      
      // Sikeres műveletek kezelése
      if(status==='pending'){
        ok('Elfogadva.');
        btn.textContent = '✅ Felvettem';
        btn.setAttribute('onclick', `doAction(${orderId}, 'accepted')`);
        const tb = document.querySelector(`#card-${orderId} .time-buttons`); 
        if(tb) tb.style.display='none';
        const pill = document.querySelector(`#card-${orderId} .pill`); 
        if(pill) pill.textContent='accepted';
      } else if(status==='accepted'){
        ok('Felvéve.');
        btn.textContent = '✅ Kiszállítva / Leadva';
        btn.setAttribute('onclick', `doAction(${orderId}, 'picked_up')`);
        const pill = document.querySelector(`#card-${orderId} .pill`); 
        if(pill) pill.textContent='picked_up';
      } else if(status==='picked_up'){
        ok('Kiszállítva.');
        const card = document.getElementById(`card-${orderId}`);
        if(card){ 
          card.style.opacity='0.4'; 
          setTimeout(()=>card.remove(), 400); 
        }
      }
      
      btn.disabled = false;
      if(tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
      
    }catch(e){
      console.error('Action error:', e);
      err(e.message || 'Hiba a művelet végrehajtásakor');
      btn.disabled = false; 
      btn.textContent = old;
      if(tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('error');
    }
  }

  // Útvonal optimalizáló függvény
  async function openOptimizedRoute(mapType = 'google'){
    try{
      // Optimalizált útvonal lekérése
      const r = await fetch(`${API}/api/optimize_route`, {
        method:'POST', 
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ 
          initData: tg?.initData || ''
        })
      });
      
      if (!r.ok) throw new Error(`HTTP ${r.status}: ${r.statusText}`);
      const j = await r.json();
      if(!j.ok) throw new Error(j.error||'Hálózati hiba');
      
      const addresses = j.addresses || [];
      if(addresses.length === 0){
        err('Nincs felvett rendelés az útvonaltervezéshez');
        return;
      }
      
      // Navigációs URL generálása
      let url;
      if(mapType === 'apple'){
        // Apple Maps - minden címet külön daddr paraméterrel
        const daddr_params = addresses.map(addr => `daddr=${encodeURIComponent(addr)}`).join('&');
        url = `https://maps.apple.com/?${daddr_params}&dirflg=d`;
      } else if(mapType === 'waze'){
        // Waze - csak az első cím (Waze nem támogatja a waypoints-ot)
        url = `https://waze.com/ul?q=${encodeURIComponent(addresses[0])}&navigate=yes`;
      } else {
        // Google Maps - optimalizált útvonal
        if(addresses.length === 1){
          url = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(normalizeAddress(addresses[0]))}`;
        } else {
          const destination = encodeURIComponent(normalizeAddress(addresses[addresses.length-1]));
          const waypoints = addresses
            .slice(0, -1)
            .map(addr => encodeURIComponent(normalizeAddress(addr)))
            .join('|');
          url = `https://www.google.com/maps/dir/?api=1&destination=${destination}&waypoints=${waypoints}&travelmode=driving`;
        }
      }

      // Link megnyitása
      if (tg?.openLink) {
        
        tg.openLink(url);
      } else {
        window.open(url, '_blank');
      }
      
      const mapNames = {
        'google': 'Google Maps',
        'apple': 'Apple Maps', 
        'waze': 'Waze'
      };
      
      ok(`${mapNames[mapType]} megnyitva ${addresses.length} optimalizált címmel`);
      
    }catch(e){
      console.error('Route error:', e);
      err(e.message || 'Hiba az útvonaltervezésnél');
    }
  }
  
  function setTab(t){
    TAB = t;
    load();
  }

  // Kezdeti betöltés és automatikus frissítés
  load();
  setInterval(load, 30000); // 30 másodpercenként frissít
</script>
</body>
</html>
"""

ADMIN_HTML = """
<!doctype html>
<html lang="hu">
<head><meta charset="utf-8"><title>Admin</title></head>
<body>
  <h1>Admin statisztika</h1>
  <h2>Heti futár bontás</h2>
  <table border="1">
    <tr><th>Hét</th><th>Futár</th><th>Darab</th><th>Átlag idő (perc)</th></tr>
    {% for r in weekly_courier %}
    <tr>
      <td>{{ r.week }}</td>
      <td>{{ r.courier_name or r.delivery_partner_id }}</td>
      <td>{{ r.cnt }}</td>
      <td>{{ r.avg_min }}</td>
    </tr>
    {% endfor %}
  </table>

  <h2>Étterem bontás</h2>
  <table border="1">
    <tr><th>Hét</th><th>Csoport</th><th>Darab</th><th>Átlag idő</th></tr>
    {% for r in weekly_restaurant %}
    <tr>
      <td>{{ r.week }}</td>
      <td>{{ r.group_name }}</td>
      <td>{{ r.cnt }}</td>
      <td>{{ r.avg_min }}</td>
    </tr>
    {% endfor %}
  </table>

  <h2>Részletes kézbesítések</h2>
  <table border="1">
    <tr><th>Dátum</th><th>Futár</th><th>Csoport</th><th>Cím</th><th>Idő (perc)</th></tr>
    {% for r in deliveries %}
    <tr>
      <td>{{ r.delivered_at }}</td>
      <td>{{ r.courier_name or r.delivery_partner_id }}</td>
      <td>{{ r.group_name }}</td>
      <td>{{ r.restaurant_address }}</td>
      <td>{{ r.min }}</td>
    </tr>
    {% endfor %}
  </table>
</body>
</html>
"""
