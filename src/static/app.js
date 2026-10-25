const nav=[['dashboard','◫','Dashboard'],['events','▦','Shows & Rehearsals'],['finance','＄','Finances'],['bookings','✉','Booking Tracker'],['studio','✦','AI Gig Studio'],['showops','▤','Show Packets'],['touring','⌁','Tour Routing'],['songs','♫','Songs'],['setlists','≡','Setlists'],['members','♟','Members']];
const state={band:1,section:'dashboard',bands:[],data:{},modal:null};
const $=s=>document.querySelector(s);const esc=s=>String(s??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const dollars=n=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format((n||0)/100);
const datePretty=s=>{if(!s)return '';let [y,m,d]=s.split('-');return new Date(Number(y),Number(m)-1,Number(d)).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'})};
const today=()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`};
const api=async(path,options={})=>{const token=sessionStorage.getItem('backline_session');const headers={'Content-Type':'application/json',...(token?{'Authorization':'Bearer '+token}:{})};const r=await fetch('/api'+path,{...options,headers:{...headers,...(options.headers||{})}});const x=await r.json();if(!r.ok)throw Error(typeof x.detail==='string'?x.detail:'Request failed');return x};
function loginScreen(){document.querySelector('#app').innerHTML='<main style="min-height:100vh;display:grid;place-items:center;padding:24px"><form id="loginForm" class="panel" style="width:min(420px,100%)"><h1>Backline</h1><p class="sub">Sign in to your band workspace</p><div class="field"><label for="loginEmail">Email</label><input id="loginEmail" type="email" autocomplete="username" required></div><div class="field" style="margin-top:14px"><label for="loginPassword">Password</label><input id="loginPassword" type="password" autocomplete="current-password" required></div><div class="actions"><button class="primary" type="submit">Sign in</button></div><div style="margin-top:16px"><button type="button" id="showInviteSignup">Have an invitation? Create account</button><button type="button" id="showRecovery">Have a recovery code?</button></div></form></main>'}
document.addEventListener('click',e=>{if(e.target.id!=='showInviteSignup')return;document.querySelector('#app').innerHTML='<main style="min-height:100vh;display:grid;place-items:center;padding:24px"><form class="panel" id="inviteSignup" style="width:min(480px,100%)"><h1>Join Backline</h1><p class="sub">Create an account using a band invitation.</p><div class="field"><label>Invitation token</label><input name="token" required autocomplete="off"></div><div class="field"><label>Email</label><input name="email" type="email" required></div><div class="field"><label>Your name</label><input name="display_name" required></div><div class="field"><label>Password (12+ characters)</label><input name="password" type="password" minlength="12" required autocomplete="new-password"></div><div class="actions"><button class="primary" type="submit">Create account</button><button type="button" id="backToLogin">Back</button></div></form></main>'});
document.addEventListener('click',e=>{if(e.target.id==='backToLogin')loginScreen()});
document.addEventListener('click',e=>{if(e.target.id!=='showRecovery')return;document.querySelector('#app').innerHTML='<main style="min-height:100vh;display:grid;place-items:center;padding:24px"><form class="panel" id="recoveryForm" style="width:min(480px,100%)"><h1>Recover account</h1><p class="sub">Enter the recovery code securely provided by your band owner. Codes expire after 30 minutes.</p><div class="field"><label>Recovery code</label><input name="token" required autocomplete="off"></div><div class="field"><label>New password</label><input name="password" minlength="12" type="password" required autocomplete="new-password"></div><div class="actions"><button class="primary" type="submit">Reset password</button><button type="button" id="backToLogin">Back</button></div></form></main>'});
document.addEventListener('submit',async e=>{if(e.target.id!=='recoveryForm')return;e.preventDefault();const data=Object.fromEntries(new FormData(e.target));try{await api('/auth/recover',{method:'POST',body:JSON.stringify(data)});sessionStorage.removeItem('backline_session');loginScreen();toast('Password updated. Please sign in.')}catch(error){toast(error.message,true)}});

document.addEventListener('submit',async e=>{if(e.target.id!=='inviteSignup')return;e.preventDefault();const data=Object.fromEntries(new FormData(e.target));try{await api('/auth/accept-invite',{method:'POST',body:JSON.stringify(data)});loginScreen();toast('Account created. Please sign in.')}catch(error){toast(error.message,true)}});
document.addEventListener('submit',async e=>{if(e.target.id!=='loginForm')return;e.preventDefault();const email=document.querySelector('#loginEmail').value;const password=document.querySelector('#loginPassword').value;try{const result=await api('/auth/login',{method:'POST',body:JSON.stringify({email,password})});sessionStorage.setItem('backline_session',result.access_token);await load()}catch(error){toast('Sign in failed: '+error.message,true)}});
document.addEventListener('click',async e=>{if(!e.target.closest('#logoutButton'))return;try{await api('/auth/logout',{method:'POST'})}catch(error){}sessionStorage.removeItem('backline_session');state.data={};loginScreen()});
const get=key=>state.data[key]||[];
async function load(){try{state.bands=await api('/bands');if(!state.bands.find(b=>b.id===state.band))state.band=state.bands[0]?.id;const b=`/bands/${state.band}`;let names=['dashboard','events','finance','transactions','songs','setlists','members','settlements','bookings','booking-followups'];const vals=await Promise.all(names.map(x=>api(`${b}/${x}`)));names.forEach((x,i)=>state.data[x]=vals[i]);render()}catch(e){if(/Account login required|Invalid or expired session/.test(e.message)){sessionStorage.removeItem('backline_session');loginScreen();return}toast(e.message,true)}}
function toast(msg,err=false){document.querySelector('.toast')?.remove();let e=document.createElement('div');e.className='toast'+(err?' errorToast':'');e.textContent=msg;document.body.append(e);setTimeout(()=>e.remove(),3600)}
function button(text,action=''){return `<button class="primary" data-action="${action}">${text}</button>`}
function empty(msg){return `<div class="empty">${esc(msg)}</div>`}
function item(title,sub,tag=''){return `<div class="entry"><div class="entryMain"><strong>${esc(title)}</strong><small>${esc(sub)}</small></div>${tag?`<span class="tag">${esc(tag)}</span>`:''}</div>`}
function panel(title,content,action=''){return `<div class="panel"><div class="panelHeading"><h2>${title}</h2>${action}</div>${content}</div>`}
function dashboard(){let d=get('dashboard'),f=d.finance||{},events=d.upcoming||[];const cards=[['Upcoming gigs',d.counts?.gigs??0],['Active members',d.counts?.members??0],['Songs in library',d.counts?.songs??0],['Band cash balance',dollars(f.balance_cents)]];return `<div class="hero"><div><div class="eyebrow">Your band. One place.</div><h2>Keep the music moving.</h2><p>Shows, songs, people and money — everything your band needs to stay organized, with the important details connected.</p></div><button class="primary" data-action="event">+ Add event</button></div><div class="cards">${cards.map(([k,v])=>`<div class="card"><span>${k}</span><strong>${v}</strong></div>`).join('')}</div><div class="panels">${panel('Coming up',events.length?`<div class="list">${events.map(e=>item(e.title,`${datePretty(e.date)} · ${e.time||'Time TBD'} · ${e.venue||'Venue TBD'}`,e.kind)).join('')}</div>`:empty('No events scheduled yet. Add your first show or rehearsal.'),`<button class="small" data-go="events">View all →</button>`)}${panel('Finance snapshot',`<div class="list">${[['Gig and other revenue',f.income_cents],['Operating expenses',f.expenses_cents],['Member payouts',f.payouts_cents],['Current band balance',f.balance_cents]].map(([k,v])=>`<div class="entry"><div class="entryMain"><strong>${k}</strong></div><strong>${dollars(v)}</strong></div>`).join('')}</div><p class="footNote">Cash balance is based on recorded transactions, not connected bank accounts.</p>`,`<button class="small" data-go="finance">View ledger →</button>`)}</div>`}
function events(){let a=get('events');return `<div class="toolbar"><p>Book performances, track rehearsals and keep dates aligned.</p>${button('+ New event','event')}</div>${panel('Event calendar',a.length?`<div class="tableWrap"><table class="table"><thead><tr><th>Date</th><th>Type</th><th>Event</th><th>Venue / Location</th><th>Fee</th><th>Status</th></tr></thead><tbody>${a.map(e=>`<tr><td>${datePretty(e.date)}<br><span class="dim">${esc(e.time)}</span></td><td><span class="tag muted">${e.kind}</span></td><td><strong>${esc(e.title)}</strong></td><td>${esc(e.venue)}</td><td>${e.kind==='Gig'?dollars(e.fee_cents):'—'}</td><td>${esc(e.status)}</td></tr>`).join('')}</tbody></table></div>`:empty('Your gig and rehearsal calendar is empty.'))}`}
function bookings(){let leads=get('bookings');let due=get('booking-followups');let count=due.count||0;return `<div class="panel"><div class="panelHeading"><h2>Follow-ups requiring attention</h2><span class="tag">${count} due</span></div>${count?due.items.map(x=>item(x.venue,'Follow up: '+datePretty(x.next_followup)+' · '+(x.contact_name||'Contact not set'),x.stage)).join(''):empty('You are caught up on scheduled follow-ups.')}</div>`+`<div class="toolbar"><p>Keep a complete record of conversations, follow-ups and booking outcomes.</p>${button('+ Add prospect','booking')}</div>${panel('Venue pipeline',leads.length?`<div class="tableWrap"><table class="table"><thead><tr><th>Venue / Booker</th><th>Stage</th><th>Next follow-up</th><th>Last contact</th><th>Actions</th></tr></thead><tbody>${leads.map(x=>`<tr><td><strong>${esc(x.venue)}</strong><div class="dim">${esc(x.contact_name)} ${esc(x.city)}</div></td><td><span class="tag muted">${esc(x.stage)}</span></td><td>${datePretty(x.next_followup)||'—'}</td><td>${esc(x.last_contact?.slice(0,10)||'—')}</td><td><button class="small" data-booking="${x.id}">View history</button></td></tr>`).join('')}</tbody></table></div>`:empty('No venue contacts yet. Add a booker or venue to start tracking outreach.'))}`}
async function openStudioGig(id){state.studioGig=Number(id);await refreshStudio();}
async function refreshStudio(){if(!state.studioGig)return;try{const base=`/bands/${state.band}/gigs/${state.studioGig}`;const [market,drafts]=await Promise.all([api(base+'/market'),api(base+'/campaign')]);state.data.studioMarket=market;state.data.studioDrafts=drafts;state.section='studio';render()}catch(e){toast(e.message,true)}}
function studio(){
 const gigs=get('events').filter(e=>e.kind==='Gig');
 const gig=gigs.find(e=>e.id===state.studioGig);
 const findings=get('studioMarket'), drafts=get('studioDrafts');
 const gigRows=gigs.map(e=>'<div class="entry"><div><strong>'+esc(e.title)+'</strong><small>'+datePretty(e.date)+' · '+esc(e.venue)+'</small></div><button class="small" data-studio-gig="'+e.id+'">'+(state.studioGig===e.id?'Selected':'Open studio')+'</button></div>').join('');
 let result='<div class="toolbar"><p>Evidence-backed gig marketing. Market scanning, AI generation and automatic publishing are not connected yet.</p></div>';
 result+=panel('Select a gig',gigs.length?'<div class="list">'+gigRows+'</div>':empty('Create a gig first.'));
 if(!gig)return result;
 const marketRows=findings.map(x=>item(x.title,datePretty(x.event_date)+' · '+x.venue+' · '+x.source_url,x.category)).join('');
 result+=panel('Market research · '+esc(gig.title),'<p class="sub">Add only events supported by verifiable sources.</p>'+button('+ Record nearby event','market')+' <button class="small" data-scan-market="1">Scan city events</button>'+(findings.length?'<div class="list">'+marketRows+'</div>':empty('No market findings yet.')));
 const draftRows=drafts.map(d=>'<div class="entry" style="display:block"><strong>'+esc(d.channel)+' · '+esc(d.angle)+'</strong><p style="white-space:pre-wrap">'+esc(d.body)+'</p><div class="actions"><span class="tag muted">'+esc(d.status)+'</span>'+(d.status==='draft'?'<button class="small" data-edit-draft="'+d.id+'">Edit</button><button class="small" data-approve-draft="'+d.id+'">Approve</button>':'')+'</div></div>').join('');
 result+=panel('Marketing drafts',button('+ Create draft','campaign')+' <button class="small" data-voice="1">Band voice</button>'+' <button class="small" data-generate-campaign="1">Generate marketing drafts</button>'+(drafts.length?'<div class="list">'+draftRows+'</div>':empty('No drafts created yet.')));
 return result;
}

async function openShowPacketGig(id){
 state.showGig=Number(id);
 try{
  const base='/bands/'+state.band+'/gigs/'+state.showGig;
  const [packets,files,templates,stage]=await Promise.all([
   api(base+'/packet'),api(base+'/files'),api('/bands/'+state.band+'/show-templates'),api(base+'/stage')]);
  state.data.showPackets=packets;state.data.showFiles=files;state.data.showTemplates=templates;state.data.showStage=stage;
  state.section='showops';render();
 }catch(error){toast(error.message,true)}
}

async function refreshTours(){
 try{
  state.data.tours=await api('/bands/'+state.band+'/tours');
  if(state.selectedTour){
   state.data.currentRoute=await api('/bands/'+state.band+'/tours/'+state.selectedTour+'/route');
  }
  state.section='touring';render();
 }catch(error){toast(error.message,true)}
}
function touring(){
 const tours=get('tours'),route=state.data.currentRoute;
 let html=panel('Tour planning','<p class="sub">Build a dated tour itinerary, attach confirmed gigs, track holds and travel days. Routing times require a map provider.</p><button class="small" data-new-tour="1">+ Create tour</button>'+
  '<div class="list">'+tours.map(t=>'<div class="entry"><strong>'+esc(t.name)+'</strong> <button class="small" data-open-tour="'+t.id+'">Open itinerary</button></div>').join('')+'</div>');
 if(!route || !state.selectedTour)return html;
 html+=panel('Itinerary · '+esc(route.tour.name),'<button class="small" data-add-stop="1">+ Add stop</button>'+
  (route.stops.length?'<div class="list">'+route.stops.map(stop=>
  '<div class="entry"><div><strong>'+datePretty(stop.stop_date)+' · '+esc(stop.city)+', '+esc(stop.region)+'</strong>'+
  '<p>'+esc(stop.venue||'Travel / routing day')+' · '+esc(stop.status)+'</p>'+
  '<p>'+esc(stop.lodging||'No lodging recorded')+'</p></div></div>').join('')+'</div>':empty('Add your first tour stop.'))+
  '<p class="footNote">'+esc(route.note)+'</p>');
 if(route.warnings.length)html+=panel('Routing flags','<div class="list">'+route.warnings.map(w=>
  '<div class="entry">'+esc(w.message)+'</div>').join('')+'</div>');
 return html;
}

function stagePreview(stage){
 const items=stage?.items||[];
 const shapes=items.map(item=>{
  const cx=10+Number(item.x)*4.4,cy=10+Number(item.y)*2.15;
  return '<g><circle cx="'+cx+'" cy="'+cy+'" r="11" fill="#334155" stroke="#93c5fd" stroke-width="1.5"/>'+
   '<text x="'+cx+'" y="'+(cy+18)+'" text-anchor="middle" fill="#e2e8f0" font-size="9">'+esc(item.label).slice(0,55)+'</text></g>';
 }).join('');
 return '<div style="overflow:auto"><svg viewBox="0 0 460 250" role="img" aria-label="Stage layout, audience at the bottom" style="width:100%;max-width:700px;background:#0f172a;border-radius:8px"><rect x="5" y="5" width="450" height="235" rx="9" fill="none" stroke="#64748b"/>'+
 '<text x="230" y="18" text-anchor="middle" fill="#cbd5e1" font-size="10">UPSTAGE</text>'+shapes+
 '<text x="230" y="234" text-anchor="middle" fill="#cbd5e1" font-size="10">AUDIENCE / DOWNSTAGE</text></svg></div>'
}
function openStageDesigner(){
 const original=state.data.showStage||{items:[],inputs:[],notes:''};
 let working=JSON.parse(JSON.stringify(original));
 const kinds=['vocal','guitar','bass','drums','keys','monitor','amp','other'];
 const shade={vocal:'#818cf8',guitar:'#f59e0b',bass:'#34d399',drums:'#fb7185',keys:'#38bdf8',monitor:'#c084fc',amp:'#fbbf24',other:'#94a3b8'};
 const dialog=document.createElement('div');dialog.className='stageDesignerBackdrop';dialog.id='stageDesigner';
 dialog.innerHTML='<div class="stageDesigner"><header class="stageDesignerHeader"><div><h2>Stage Designer</h2><p class="sub">Drag equipment around the stage. Front of house is at the bottom.</p></div><button type="button" id="stageClose">✕ Close</button></header><div class="stageTools"><button id="stageAddItem" type="button">+ Equipment</button><button id="stageAddInput" type="button">+ Input channel</button><button id="stageDemo" type="button">Example four-piece band</button></div><div class="stageEditorGrid"><div><div id="stageCanvas" class="stageCanvas" aria-label="Drag stage equipment"><span class="stageBack">UPSTAGE</span><span class="stageFront">AUDIENCE / FRONT OF HOUSE</span></div><p class="footNote">Click a piece to change its name or type. Drag to reposition.</p></div><div class="stagePatchPanel"><h3>Input patch list</h3><div id="stageInputs"></div><label>Production notes<textarea id="stageNotes" rows="3"></textarea></label></div></div><footer class="stageDesignerFooter"><span id="stageDesignerStatus">Draft changes — not saved</span><button class="primary" type="button" id="stageSave">Save stage setup</button></footer></div>';
 document.body.append(dialog);
 const $d=sel=>dialog.querySelector(sel);
 function draw(){
  const canvas=$d('#stageCanvas');
  canvas.querySelectorAll('.stageItem').forEach(n=>n.remove());
  working.items.forEach((item,index)=>{
   const node=document.createElement('button');node.type='button';node.className='stageItem';
   node.style.left=item.x+'%';node.style.top=item.y+'%';
   node.style.borderColor=shade[item.kind]||'#94a3b8';
   node.textContent=item.label;
   node.title=item.kind+' — drag to position, click to edit';
   node.addEventListener('pointerdown',event=>{
    if(event.button!==0)return;
    node.setPointerCapture(event.pointerId);
    const x=event.clientX,y=event.clientY;let moved=false;
    const move=e=>{
     if(Math.abs(e.clientX-x)+Math.abs(e.clientY-y)>5)moved=true;
     const rect=canvas.getBoundingClientRect();
     item.x=Math.max(0,Math.min(100,Math.round((e.clientX-rect.left)/rect.width*100)));
     item.y=Math.max(0,Math.min(100,Math.round((e.clientY-rect.top)/rect.height*100)));
     node.style.left=item.x+'%';node.style.top=item.y+'%';
    };
    const up=()=>{
     node.removeEventListener('pointermove',move);
     node.removeEventListener('pointerup',up);
     if(!moved){
      const label=prompt('Instrument or position',item.label);if(label?.trim())item.label=label.trim().slice(0,100);
      const kind=prompt('Type: '+kinds.join(', '),item.kind);if(kinds.includes(kind))item.kind=kind;
      draw();
     }
    };
    node.addEventListener('pointermove',move);node.addEventListener('pointerup',up);
   });
   canvas.append(node);
  });
  const inputs=$d('#stageInputs');inputs.replaceChildren();
  working.inputs.sort((a,b)=>a.channel-b.channel).forEach((item,index)=>{
   const row=document.createElement('div');row.className='stageInputRow';
   row.innerHTML='<span class="stageChannel"></span><input class="stageInputSource" aria-label="Audio source"><input class="stageInputMic" aria-label="Microphone or DI"><button type="button" aria-label="Remove channel">✕</button>';
   row.querySelector('.stageChannel').textContent='CH '+item.channel;
   const source=row.querySelector('.stageInputSource');source.value=item.source;source.placeholder='Source';source.oninput=()=>item.source=source.value;
   const mic=row.querySelector('.stageInputMic');mic.value=item.microphone||'';mic.placeholder='Mic / DI';mic.oninput=()=>item.microphone=mic.value;
   row.querySelector('button').onclick=()=>{working.inputs.splice(index,1);draw()};
   inputs.append(row);
  });
 }
 $d('#stageNotes').value=working.notes||'';
 $d('#stageClose').onclick=()=>dialog.remove();
 $d('#stageAddItem').onclick=()=>{
  const label=prompt('Equipment label (example: Lead vocal)');if(!label?.trim())return;
  const kind=prompt('Type: '+kinds.join(', '),'vocal');
  if(!kinds.includes(kind)){toast('Choose a valid equipment type',true);return}
  working.items.push({label:label.trim().slice(0,100),kind,x:50,y:50});draw()
 };
 $d('#stageAddInput').onclick=()=>{
  const used=new Set(working.inputs.map(x=>x.channel));let channel=1;
  while(used.has(channel)&&channel<=128)channel++;
  if(channel>128){toast('Maximum input count reached',true);return}
  working.inputs.push({channel,source:'New input',microphone:'',stand:'',notes:''});draw()
 };
 $d('#stageDemo').onclick=()=>{
  if(working.items.length&&!confirm('Replace your unsaved stage setup with the example?'))return;
  working.items=[{label:'Drums',kind:'drums',x:50,y:18},{label:'Bass',kind:'bass',x:25,y:49},
   {label:'Guitar',kind:'guitar',x:77,y:49},{label:'Lead vocal',kind:'vocal',x:50,y:80},
   {label:'Monitor L',kind:'monitor',x:28,y:88},{label:'Monitor R',kind:'monitor',x:73,y:88}];
  working.inputs=[{channel:1,source:'Kick',microphone:'D112',stand:'',notes:''},
   {channel:2,source:'Snare',microphone:'SM57',stand:'',notes:''},
   {channel:3,source:'Bass DI',microphone:'DI',stand:'',notes:''},
   {channel:4,source:'Guitar',microphone:'SM57',stand:'',notes:''},
   {channel:5,source:'Lead vocal',microphone:'SM58',stand:'',notes:''}];
  draw()
 };
 $d('#stageSave').onclick=async()=>{
  working.notes=$d('#stageNotes').value;
  try{
   await api('/bands/'+state.band+'/gigs/'+state.showGig+'/stage',
    {method:'PUT',body:JSON.stringify(working)});
   dialog.remove();await openShowPacketGig(state.showGig);toast('Stage setup saved')
  }catch(error){$d('#stageDesignerStatus').textContent=error.message;toast(error.message,true)}
 };
 draw()
}
function showops(){
 const gigs=get('events').filter(g=>g.kind==='Gig');
 const chosen=gigs.find(g=>g.id===state.showGig);
 const labels={technical_rider:'Technical rider',hospitality_rider:'Hospitality rider',
    show_advance:'Show advance',day_of_show:'Day-of-show schedule',
    tour_call_sheet:'Tour call sheet',settlement_sheet:'Settlement checklist'};
 let html=panel('Choose a show','<div class="list">'+gigs.map(g=>
  '<div class="entry"><strong>'+esc(g.title)+'</strong> · '+datePretty(g.date)+
  ' · '+esc(g.venue)+' <button class="small" data-show-gig="'+g.id+'">Open packet</button></div>'
 ).join('')+'</div>');
 if(!chosen)return html;
 const docs=get('showPackets'),files=get('showFiles');
 html+=panel('Show packet · '+esc(chosen.title),
  '<p class="sub">Create riders, advances and schedules; then edit each section before marking ready.</p>'+
  '<div class="actions">'+Object.entries(labels).map(([key,name])=>
   '<button class="small" data-create-packet="'+key+'">+ '+esc(name)+'</button>').join('')+'</div>'+
  (docs.length?'<div class="list">'+docs.map(d=>
   '<div class="entry"><div><strong>'+esc(d.title)+'</strong> <span class="tag muted">'+esc(d.status)+'</span>'+
   '<p>'+d.sections.map(x=>esc(x.heading)).join(' · ')+'</p></div>'+
   '<button class="small" data-edit-packet="'+d.id+'">Edit</button> '+
   '<button class="small" data-ready-packet="'+d.id+'">Mark ready</button></div>').join('')+'</div>':
   empty('Create a document from the defaults to start your packet.')));
 html+=panel('Stage plot and audio input list',
  '<p class="sub">Place instruments on a 0–100 stage grid, and number your patch list.</p>'+
  '<button class="small" data-edit-stage="1">Edit stage setup</button> '+ 
  '<button class="small" data-stage-export="stage.svg">Download stage plot</button> '+
  '<button class="small" data-stage-export="inputs.csv">Download input list</button>'+stagePreview(state.data.showStage)+
  '<div class="list">'+(get('showStage').items||[]).map(i=>'<div class="entry">'+esc(i.label)+' · '+esc(i.kind)+' (x:'+i.x+', y:'+i.y+')</div>').join('')+
  (get('showStage').inputs||[]).map(i=>'<div class="entry">CH '+i.channel+' · '+esc(i.source)+' · '+esc(i.microphone)+'</div>').join('')+'</div>');
 html+=panel('Contracts and show files',
  '<p class="sub">Upload PDF contracts, stage plots, input lists, receipts or W-9 forms. Files stay attached to this show.</p>'+
  '<div class="actions"><select id="showFileCategory"><option value="contract">Performance contract</option><option value="stage_plot">Stage plot</option><option value="input_list">Input list</option><option value="technical_rider">Technical rider</option><option value="hospitality_rider">Hospitality rider</option><option value="receipt">Receipt</option><option value="w9">W-9</option><option value="insurance">Insurance</option><option value="other">Other</option></select>'+
  '<input id="showFileInput" type="file" accept=".pdf,application/pdf"><button class="small" data-upload-show-file="1">Upload PDF</button></div>'+
  (files.length?'<div class="list">'+files.map(x=>
   '<div class="entry"><strong>'+esc(x.filename)+'</strong> · '+esc(x.category)+
   ' <button class="small" data-download-show-file="'+x.id+'">Download</button></div>').join('')+'</div>':
   empty('No PDF documents stored for this show.')));
 return html;
}

function songs(){let a=get('songs');return `<div class="toolbar"><p>A centralized repertoire for every show and rehearsal.</p>${button('+ Add song','song')}</div>${panel('Song library',a.length?`<div class="tableWrap"><table class="table"><thead><tr><th>Song</th><th>Artist</th><th>Key</th><th>Tempo</th><th>Duration</th><th>Status</th></tr></thead><tbody>${a.map(s=>`<tr><td><strong>${esc(s.title)}</strong></td><td>${esc(s.artist)}</td><td>${esc(s.song_key)||'—'}</td><td>${s.bpm||'—'}</td><td>${s.duration_seconds?`${Math.floor(s.duration_seconds/60)}:${String(s.duration_seconds%60).padStart(2,'0')}`:'—'}</td><td><span class="tag muted">${esc(s.status)}</span></td></tr>`).join('')}</tbody></table></div>`:empty('Add songs to build your repertoire.'))}`}
function members(){let a=get('members');return `<div class="toolbar"><p>Your roster, responsibilities and band contacts.</p><div style="display:flex;gap:8px">${sessionStorage.getItem('backline_session')?button('+ Invite user','invitation')+button('Member recovery','issueRecovery'):''}${button('+ Add member','member')}</div></div>${panel('Band roster',a.length?`<div class="list">${a.map(m=>item(m.name,`${m.instrument||'Instrument not set'} · ${m.email||'No email'} · ${m.role}`,m.active?'Active':'Inactive')).join('')}</div>`:empty('Add your first band member.'))}`}
function setlists(){let a=get('setlists');return `<div class="toolbar"><p>Build show-ready sets from your song library.</p>${button('+ Create setlist','setlist')}</div>${a.length?a.map(s=>panel(`${esc(s.title)} <span class="sub">· ${s.songs.length} songs</span>`,s.songs.length?`<div class="list">${s.songs.map((song,i)=>item(`${i+1}. ${song.title}`,`${song.artist||'Original'} ${song.song_key?' · Key: '+song.song_key:''}`)).join('')}</div>`:empty('No songs in this setlist.'))).join(''):panel('Setlist library',empty('Create your first setlist after adding songs.'))}`}
function finance(){let f=get('finance'),ts=get('transactions'),settlements=get('settlements');let cards=[['Cash on hand',f.balance_cents],['Revenue',f.income_cents],['Expenses',f.expenses_cents],['Member payouts',f.payouts_cents]];let gigs=get('events').filter(e=>e.kind==='Gig'&&!settlements.find(s=>s.event_id===e.id));return `<div class="toolbar"><p>Transparent band bookkeeping, connected to gigs and members.</p><div style="display:flex;gap:8px">${button('+ Transaction','transaction')}${button('Settle gig','settlement')}<button data-export="ledger">Export CSV</button></div></div><div class="cards">${cards.map(([label,v])=>`<div class="card"><span>${label}</span><strong>${dollars(v)}</strong></div>`).join('')}</div>${panel('Settlements',settlements.length?`<div class="list">${settlements.map(s=>`<div class="entry" style="display:block"><strong>${esc(s.event_title)}</strong><div class="sub" style="margin:7px 0">${datePretty(s.event_date)} · Band reserve: ${s.reserve_basis_points/100}%</div>${s.shares.map(sh=>`<div style="display:flex;justify-content:space-between;padding:6px 0;font-size:13px"><span>${esc(sh.member_name)}</span><span>${dollars(sh.amount_cents)} due · ${dollars(sh.paid_cents)} paid</span></div>`).join('')}</div>`).join('')}</div>`:empty('No settled gigs yet. Record gig revenue and expenses, then create a settlement.'))}${panel('Transaction ledger',ts.length?`<div class="tableWrap"><table class="table"><thead><tr><th>Date</th><th>Type</th><th>Detail</th><th>Gig / Member</th><th>Amount</th><th></th></tr></thead><tbody>${ts.map(t=>`<tr><td>${datePretty(t.date)}</td><td><span class="tag muted">${esc(t.kind)}</span></td><td>${esc(t.description)}<div class="dim">${esc(t.category)}</div></td><td>${esc([t.event_title,t.member_name].filter(Boolean).join(' / '))}</td><td class="${['income','contribution'].includes(t.kind)?'positive':'negative'}">${['income','contribution'].includes(t.kind)?'+':'−'}${dollars(t.amount_cents)}</td><td>${!t.reversal_of&&!ts.some(q=>q.reversal_of===t.id)?`<button class="small" data-reverse="${t.id}">Reverse</button>`:''}</td></tr>`).join('')}</tbody></table></div>`:empty('No transactions yet. Record your first payment or expense.'))}<p class="footNote">Ledger records are immutable. Corrections create an offsetting transaction, preserving the original entry. Reconciled bank balances, tax preparation, and payment transfers require additional integrations.</p>`}
function render(){const b=state.bands.find(x=>x.id===state.band)||{name:'Your band'};let titles={dashboard:'Overview',events:'Shows & Rehearsals',finance:'Band Finances',bookings:'Booking Tracker',studio:'AI Gig Studio',songs:'Song Library',setlists:'Setlist Studio',members:'Band Members',showops:'Show Packets',touring:'Tour Routing'};$('#app').innerHTML=`<div class="app"><aside class="side"><div class="brand"><span class="mark">⌁</span>BACKLINE</div><div><div class="overline">Workspace</div><select class="bandPicker" id="bandPicker">${state.bands.map(b=>`<option value="${b.id}" ${b.id===state.band?'selected':''}>${esc(b.name)}</option>`).join('')}</select></div><div><div class="overline">Manage</div><nav class="nav">${nav.map(([id,ico,label])=>`<button data-go="${id}" class="${state.section===id?'active':''}"><span>${ico}</span><span class="navName">${label}</span></button>`).join('')}</nav></div><button class="ghost" data-action="band">+ New band</button><div class="sideFoot">BACKLINE V0.1<br>Local-first prototype<br>Data stays in your SQLite database.</div></aside><main class="main"><header class="top"><div><span class="eyebrow">${esc(b.name)}</span><h1>${titles[state.section]}</h1></div><div style="display:flex;gap:10px;align-items:center"><span class="chip">● Band workspace</span><button class="small" data-action="joinband">Join band</button><button class="small" id="logoutButton">Sign out</button></div></header><section class="content">${({dashboard,events,finance,bookings,studio,songs,setlists,members,showops,touring})[state.section]()}</section></main><div class="mobileNav">${nav.map(([id,ico,label])=>`<button class="${state.section===id?'active':''}" data-go="${id}">${ico}<br>${label.split(' ')[0]}</button>`).join('')}</div></div>${state.modal?modalHTML():''}`;$('#bandPicker')?.addEventListener('change',async e=>{state.band=Number(e.target.value);await load()})}
const field=(name,label,type='text',extras='')=>`<div class="field"><label for="f_${name}">${label}</label><input id="f_${name}" name="${name}" type="${type}" ${extras}></div>`;
const select=(name,label,options)=>`<div class="field"><label for="f_${name}">${label}</label><select id="f_${name}" name="${name}">${options.map(([v,l])=>`<option value="${esc(v)}">${esc(l)}</option>`).join('')}</select></div>`;
function modalHTML(){let type=state.modal;let fields='',title='';let evs=get('events'), mem=get('members'), songs=get('songs');const eventOpts=[['','None'],...evs.map(e=>[String(e.id),e.title])];const memberOpts=[['','None'],...mem.map(m=>[String(m.id),m.name])];
if(type==='market'){title='Record nearby event';fields=field('title','Event title','text','required')+field('source_url','Verified source URL','url','required')+field('event_date','Event date','date','required')+field('venue','Venue')+field('category','Category')+field('relevance','Why might it matter?')}
if(type==='campaign'){title='Create promotional draft';fields=select('channel','Channel',[['Facebook','Facebook'],['Instagram','Instagram'],['Email','Email'],['Press','Press']])+field('angle','Marketing angle','text','required')+`<div class="field full"><label for="f_body">Post copy</label><textarea id="f_body" name="body" required></textarea></div>`}
if(type==='invitation'){title='Invite a band user';fields=field('email','Recipient email','email','required')+select('role','Access',[['member','Member'],['viewer','Viewer'],['treasurer','Treasurer'],['manager','Manager']])+'<p class="footNote">Invitation tokens are shown once for secure manual delivery. Never post them publicly.</p>'}
if(type==='issueRecovery'){title='Issue member recovery code';fields=field('email','Existing member account email','email','required')+'<p class="footNote">Only a band owner can issue a recovery code. Verify the member through an existing trusted channel before securely delivering the code. Codes expire in 30 minutes.</p>'}
if(type==='joinband'){title='Join an existing band';fields=field('token','Invitation token','text','required')}
if(type==='booking'){title='Add booking prospect';fields=field('venue','Venue','text','required')+field('contact_name','Booker / contact')+field('contact_email','Contact email','email')+field('contact_phone','Phone')+field('city','City')+field('target_date','Target show date','date')+field('next_followup','Follow up on','date')+field('notes','Notes')}
if(type==='band'){title='Create a band';fields=field('name','Band name','text','required')+field('genre','Genre / style')}
if(type==='member'){title='Add band member';fields=field('name','Name','text','required')+field('instrument','Instrument')+field('email','Email','email')+select('role','Role',[['Member','Member'],['Manager','Manager'],['Treasurer','Treasurer']])}
if(type==='event'){title='Add show or rehearsal';fields=select('kind','Event type',[['Gig','Gig'],['Rehearsal','Rehearsal']])+field('title','Name','text','required')+field('venue','Venue / location')+field('date','Date','date',`required value="${today()}"`)+field('time','Time','time')+field('fee','Agreed gig fee ($)','number','min="0" step="0.01" value="0"')+select('status','Status',[['Planned','Planned'],['Confirmed','Confirmed'],['Completed','Completed']])}
if(type==='song'){title='Add song';fields=field('title','Song title','text','required')+field('artist','Artist / writer')+field('song_key','Key')+field('bpm','Tempo (BPM)','number','min="1" max="400"')+field('duration_seconds','Duration in seconds','number','min="0" value="0"')+select('status','Status',[['Learning','Learning'],['Ready','Ready'],['Retired','Retired']])}
if(type==='transaction'){title='Record transaction';fields=select('kind','Type',[['income','Income'],['expense','Expense'],['payout','Member payout'],['contribution','Member contribution']])+field('amount','Amount ($)','number','min="0.01" step="0.01" required')+field('description','Description','text','required')+field('category','Category')+field('date','Date','date',`required value="${today()}"`)+select('event_id','Related event',eventOpts)+select('member_id','Related member',memberOpts)}
if(type==='setlist'){title='Create setlist';fields=field('title','Setlist title','text','required')+select('event_id','For gig (optional)',eventOpts)+`<div class="field full"><label>Choose songs (sorted by title)</label><div class="setSongs">${songs.length?songs.map(s=>`<label><input type="checkbox" name="song_ids" value="${s.id}">${esc(s.title)}${s.song_key?' · '+esc(s.song_key):''}</label>`).join(''):'Add songs first.'}</div></div>`}
if(type==='settlement'){title='Settle a gig';let settled=get('settlements').map(s=>s.event_id);fields=select('event_id','Gig',evs.filter(e=>e.kind==='Gig'&&!settled.includes(e.id)).map(e=>[String(e.id),e.title]))+field('reserve_percent','Retain for band (%)','number','min="0" max="100" value="10" required')+`<div class="field full"><label>Musicians to pay</label><div class="setSongs">${mem.length?mem.map(m=>`<label><input type="checkbox" name="member_ids" value="${m.id}" checked>${esc(m.name)}</label>`).join(''):'Add members first.'}</div></div><p class="footNote">Record actual gig income and expenses in the ledger before settling. The settlement uses the net recorded cash and reserves the specified percentage.</p>`}
return `<div class="modalWrap" id="modalWrap"><div class="modal" role="dialog" aria-modal="true" aria-label="${title}"><h2>${title}</h2><p class="sub">${esc(state.bands.find(b=>b.id===state.band)?.name||'')}</p><form id="entryForm"><div class="formGrid">${fields}</div><div class="actions"><button type="button" data-action="close">Cancel</button><button class="primary" type="submit">Save</button></div></form></div></div>`}
document.addEventListener('click',async e=>{let btn=e.target.closest('[data-go],[data-action],[data-reverse],[data-export],[data-booking],[data-studio-gig],[data-approve-draft],[data-scan-market],[data-generate-campaign],[data-edit-draft],[data-voice],[data-show-gig],[data-create-packet],[data-edit-packet],[data-ready-packet],[data-upload-show-file],[data-download-show-file],[data-edit-stage],[data-stage-export],[data-new-tour],[data-open-tour],[data-add-stop]');if(!btn){if(e.target.id==='modalWrap'){state.modal=null;render()}return}if(btn.dataset.newTour){
 const name=prompt('Name this tour (example: Upper Midwest Weekend)');if(!name?.trim())return;
 try{const tour=await api('/bands/'+state.band+'/tours',
  {method:'POST',body:JSON.stringify({name:name.trim()})});
  state.selectedTour=tour.id;await refreshTours();toast('Tour created')
 }catch(err){toast(err.message,true)}return
}
if(btn.dataset.openTour){
 state.selectedTour=Number(btn.dataset.openTour);await refreshTours();return
}
if(btn.dataset.addStop){
 const gigs=get('events').filter(x=>x.kind==='Gig');
 const choice=prompt('Optional existing gig ID to link (leave blank for travel or held dates).\\n'+gigs.map(x=>x.id+': '+x.title+' · '+x.date).join('\\n'),'');
 if(choice===null)return;
 const linked=choice.trim()?gigs.find(x=>String(x.id)===choice.trim()):null;
 if(choice.trim()&&!linked){toast('Choose a gig from this band',true);return}
 const date=linked?.date||prompt('Stop date (YYYY-MM-DD)');if(!date)return;
 const city=prompt('City');if(!city?.trim())return;
 const region=prompt('State or region (e.g., MN)')||'';
 const venue=linked?.venue||prompt('Venue (optional)')||'';
 const status=prompt('Status: planned, hold, confirmed, cancelled, travel',linked?'confirmed':'planned')||'planned';
 const lodging=prompt('Hotel or lodging notes (optional)')||'';
 const travel_notes=prompt('Travel / advance notes (optional)')||'';
 try{await api('/bands/'+state.band+'/tours/'+state.selectedTour+'/stops',
  {method:'POST',body:JSON.stringify({date,city,region,venue,status,lodging,travel_notes,event_id:linked?.id||null})});
  await refreshTours();toast('Tour stop added')
 }catch(err){toast(err.message,true)}return
}
if(btn.dataset.stageExport){
 try{
  const token=sessionStorage.getItem('backline_session');
  const response=await fetch('/api/bands/'+state.band+'/gigs/'+state.showGig+'/'+btn.dataset.stageExport,
    {headers:token?{Authorization:'Bearer '+token}:{}});
  if(!response.ok)throw Error('Export failed');
  const blob=await response.blob(),url=URL.createObjectURL(blob),link=document.createElement('a');
  link.href=url;link.download=btn.dataset.stageExport==='stage.svg'?'stage-plot.svg':'input-list.csv';
  link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
 }catch(error){toast(error.message,true)}return
}
if(btn.dataset.editStage){
 openStageDesigner();return
}
if(btn.dataset.showGig){await openShowPacketGig(btn.dataset.showGig);return}
if(btn.dataset.createPacket){
 try{await api('/bands/'+state.band+'/gigs/'+state.showGig+'/packet',{
  method:'POST',body:JSON.stringify({kind:btn.dataset.createPacket})});
  await openShowPacketGig(state.showGig);toast('Show document created');
 }catch(error){toast(error.message,true)}return
}
if(btn.dataset.editPacket){
 const p=get('showPackets').find(x=>String(x.id)===btn.dataset.editPacket);
 if(!p)return;
 const title=prompt('Document title',p.title);if(!title?.trim())return;
 const sections=[];
 for(const part of p.sections){
  const body=prompt(part.heading,part.body);if(body===null)return;
  sections.push({heading:part.heading,body});
 }
 try{await api('/bands/'+state.band+'/gigs/'+state.showGig+'/packet/'+p.id,
  {method:'PUT',body:JSON.stringify({title:title.trim(),sections})});
  await openShowPacketGig(state.showGig);toast('Document saved as draft')
 }catch(error){toast(error.message,true)}return
}
if(btn.dataset.readyPacket){
 try{await api('/bands/'+state.band+'/gigs/'+state.showGig+'/packet/'+btn.dataset.readyPacket+'/ready',
  {method:'POST'});await openShowPacketGig(state.showGig);toast('Marked ready — nothing sent')
 }catch(error){toast(error.message,true)}return
}
if(btn.dataset.uploadShowFile){
 const file=document.querySelector('#showFileInput')?.files?.[0];
 const category=document.querySelector('#showFileCategory')?.value;
 if(!file){toast('Choose a PDF file',true);return}
 if(file.size>3*1024*1024){toast('Maximum file size is 3 MB',true);return}
 try{
  const bytes=new Uint8Array(await file.arrayBuffer());
  let binary='';for(let i=0;i<bytes.length;i+=8192)
   binary+=String.fromCharCode(...bytes.subarray(i,i+8192));
  await api('/bands/'+state.band+'/gigs/'+state.showGig+'/files',{
   method:'POST',body:JSON.stringify({filename:file.name,category,data_base64:btoa(binary)})});
  await openShowPacketGig(state.showGig);toast('PDF linked to show')
 }catch(error){toast(error.message,true)}return
}
if(btn.dataset.downloadShowFile){
 try{
  const token=sessionStorage.getItem('backline_session');
  const response=await fetch('/api/bands/'+state.band+'/gigs/'+state.showGig+'/files/'+btn.dataset.downloadShowFile+'/download',
   {headers:token?{Authorization:'Bearer '+token}:{}});
  if(!response.ok)throw Error('Download failed');
  const item=get('showFiles').find(x=>String(x.id)===btn.dataset.downloadShowFile);
  const blob=await response.blob(),url=URL.createObjectURL(blob),link=document.createElement('a');
  link.href=url;link.download=item?.filename||'show-file.pdf';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
 }catch(error){toast(error.message,true)}return
}
if(btn.dataset.voice){try{const p='/bands/'+state.band+'/marketing-voice';const existing=await api(p);const tone=prompt('Tone: straightforward, playful, gritty, or warm',existing.tone);if(!tone)return;const tagline=prompt('Band tagline or distinctive phrase (optional)',existing.tagline);if(tagline===null)return;await api(p,{method:'PUT',body:JSON.stringify({tone:tone.trim().toLowerCase(),tagline:tagline.trim()})});toast('Band marketing voice saved')}catch(err){toast(err.message,true)}return}if(btn.dataset.editDraft){const draft=(state.data.studioDrafts||[]).find(x=>String(x.id)===btn.dataset.editDraft);if(!draft){toast('Draft not loaded',true);return}const angle=prompt('Campaign angle',draft.angle);if(!angle?.trim())return;const body=prompt('Edit promotional copy',draft.body);if(!body?.trim())return;try{await api('/bands/'+state.band+'/gigs/'+state.studioGig+'/campaign/'+draft.id,{method:'PATCH',body:JSON.stringify({angle:angle.trim(),body:body.trim()})});await refreshStudio();toast('Draft revised and saved')}catch(err){toast(err.message,true)}return}if(btn.dataset.generateCampaign){try{const result=await api('/bands/'+state.band+'/gigs/'+state.studioGig+'/campaign/generate',{method:'POST'});await refreshStudio();toast('Created '+result.draft_ids.length+' drafts. Verify show details before approval.')}catch(error){toast(error.message,true)}return}if(btn.dataset.scanMarket){const city=prompt('City where the gig takes place:');if(!city || !city.trim())return;try{const path='/bands/'+state.band+'/gigs/'+state.studioGig+'/market/discover?city='+encodeURIComponent(city.trim());const data=await api(path,{method:'POST'});await refreshStudio();toast(data.status==='cached'?'Recent research already available':'Imported '+data.added+' sourced events')}catch(err){toast(err.message,true)}return}if(btn.dataset.studioGig){await openStudioGig(btn.dataset.studioGig);return}if(btn.dataset.approveDraft){if(!confirm('Approve this draft? Approval does not publish anything.'))return;try{await api('/bands/'+state.band+'/gigs/'+state.studioGig+'/campaign/'+btn.dataset.approveDraft+'/approve',{method:'POST',body:JSON.stringify({note:'Manual review'})});await refreshStudio();toast('Approved, not published')}catch(x){toast(x.message,true)}return}if(btn.dataset.booking){const id=Number(btn.dataset.booking);try{const lead=get('bookings').find(x=>x.id===id);const activities=await api('/bands/'+state.band+'/bookings/'+id+'/activity');const lines=activities.map(a=>a.happened_at+' | '+a.kind+' | '+a.detail).join('\\n');const choice=prompt(lead.venue+' booking\\n'+(lines||'No activity')+'\\n\\nChoose: N = note, S = change stage, or Cancel');if(choice?.toUpperCase()==='N'){const detail=prompt('Contact note / communication summary');if(detail?.trim())await api('/bands/'+state.band+'/bookings/'+id+'/activity',{method:'POST',body:JSON.stringify({kind:'Note',detail:detail.trim()})});}else if(choice?.toUpperCase()==='S'){const stage=prompt('Stage: Researching, To Contact, Contacted, Follow Up, Negotiating, Hold, Confirmed, Declined, Closed',lead.stage);if(stage && stage!==lead.stage){const detail=prompt('Reason for status change / agreed next action');if(detail?.trim())await api('/bands/'+state.band+'/bookings/'+id+'/stage',{method:'POST',body:JSON.stringify({stage,detail:detail.trim()})});}}await load();}catch(x){toast(x.message,true)}return}if(btn.dataset.export){const headers=['ID','Date','Type','Description','Category','Event','Member','Amount USD','Reversal of'];const quote=v=>'"'+String(v??'').replace(/"/g,'""')+'"';const rows=get('transactions').map(t=>[t.id,t.date,t.kind,t.description,t.category,t.event_title,t.member_name,((['income','contribution'].includes(t.kind)?1:-1)*t.amount_cents/100).toFixed(2),t.reversal_of]);const csv=[headers,...rows].map(row=>row.map(quote).join(',')).join('\r\n');const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='backline-ledger-'+today()+'.csv';a.click();URL.revokeObjectURL(url)}if(btn.dataset.go){state.section=btn.dataset.go;if(state.section==='touring'){await refreshTours()}else render()}if(btn.dataset.action){state.modal=btn.dataset.action==='close'?null:btn.dataset.action;render()}if(btn.dataset.reverse){if(!confirm('Create an offsetting correction for this transaction? The original record will be kept.'))return;try{await api(`/bands/${state.band}/transactions/${btn.dataset.reverse}/reverse`,{method:'POST'});toast('Correction recorded');await load()}catch(x){toast(x.message,true)}}});
document.addEventListener('submit',async e=>{if(e.target.id!=='entryForm')return;e.preventDefault();let type=state.modal;let data=Object.fromEntries(new FormData(e.target));let fd=new FormData(e.target);if(type==='setlist')data.song_ids=fd.getAll('song_ids').map(Number);if(type==='settlement')data.member_ids=fd.getAll('member_ids').map(Number);for(let k of ['event_id','member_id'])if(k in data)data[k]=data[k]?Number(data[k]):null;if(type==='song'){data.bpm=data.bpm?Number(data.bpm):null;data.duration_seconds=Number(data.duration_seconds||0)}if(type==='settlement')data.reserve_percent=Number(data.reserve_percent);let b=`/bands/${state.band}`;const urls={issueRecovery:b+'/account-recovery',invitation:b+'/invitations',joinband:'/auth/accept-existing-invite',band:'/bands',market:b+'/gigs/'+state.studioGig+'/market',campaign:b+'/gigs/'+state.studioGig+'/campaign',booking:b+'/bookings',member:b+'/members',event:b+'/events',song:b+'/songs',transaction:b+'/transactions',setlist:b+'/setlists',settlement:b+`/events/${data.event_id}/settle`};if(type==='settlement')delete data.event_id;if(type==='booking'){if(!data.target_date)data.target_date=null;if(!data.next_followup)data.next_followup=null;}try{let response=await api(urls[type],{method:'POST',body:JSON.stringify(data)});state.modal=null;if(type==='band'||type==='joinband')state.band=response.band_id||response.id;if(type==='issueRecovery'){const box=document.createElement('div');box.className='modalWrap';box.id='recoveryResult';box.innerHTML='<div class="modal"><h2>Recovery code issued</h2><p class="sub">Verify the intended member, then deliver this one-time code securely. It expires after 30 minutes.</p><textarea readonly id="recoveryIssuedToken" aria-label="Recovery code"></textarea><div class="actions"><button id="copyRecovery" type="button">Copy code</button><button id="closeRecovery" type="button">Close</button></div></div>';document.body.append(box);document.querySelector('#recoveryIssuedToken').value=response.recovery_token;document.querySelector('#copyRecovery').onclick=()=>navigator.clipboard.writeText(response.recovery_token).then(()=>toast('Code copied')).catch(()=>toast('Copy the code manually',true));document.querySelector('#closeRecovery').onclick=()=>box.remove()}
if(type==='invitation'){const box=document.createElement('div');box.className='modalWrap';box.id='inviteResult';box.innerHTML='<div class="modal"><h2>Invitation created</h2><p class="sub">Copy this secret token and deliver it securely to the invited user. It expires in seven days.</p><textarea readonly id="invitationToken" aria-label="Invitation token"></textarea><div class="actions"><button id="copyInvite" type="button">Copy token</button><button id="closeInvite" type="button">Close</button></div></div>';document.body.append(box);document.querySelector('#invitationToken').value=response.invite_token;document.querySelector('#copyInvite').onclick=()=>navigator.clipboard.writeText(response.invite_token).then(()=>toast('Token copied')).catch(()=>toast('Select and copy the token manually',true));document.querySelector('#closeInvite').onclick=()=>box.remove()}toast(type==='invitation'?'Invitation created':'Saved successfully');await load();if(type==='campaign'||type==='market')await refreshStudio()}catch(x){toast(x.message,true)}});
load();
