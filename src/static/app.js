const nav=[['dashboard','◫','Dashboard'],['schedule','▦','Schedule'],['finance','＄','Finances'],['bookings','✉','Booking Tracker'],['studio','✦','AI Gig Studio'],['showops','▤','Show Packets'],['touring','⌁','Tours'],['songs','♫','Songs'],['setlists','≡','Setlists'],['members','♟','Members']];
const state={band:1,section:'dashboard',bands:[],data:{},modal:null};
/* v0.5 navigation: existing routes remain intact and are grouped into six workspaces.
   Feature scripts may add destinations to nav; resolve those entries at render time. */
const WORKSPACES=[
 ['dashboard','◫','Dashboard',['dashboard']],
 ['schedule','▦','Schedule',['schedule','events','calendars']],
 ['collaboration','☏','Band Hub',['collaboration','notifications','media','tasks','members']],
 ['touring','⌁','Shows & Tours',['touring','showops','operations','venues','bookings']],
 ['songs','♫','Music',['songs','setlists','studio']],
 ['finance','＄','Finances',['finance']]
];
const visibleDestination=id=>id!=='finance'||!state.accountRole||['owner','manager','treasurer'].includes(state.accountRole);
function workspaceFor(section){return WORKSPACES.find(w=>w[3].includes(section))||WORKSPACES[0]}
function workspaceNavigation(mobile=false){
 const current=workspaceFor(state.section);
 if(mobile)return WORKSPACES.filter(w=>visibleDestination(w[0])).map(([id,icon,label,sections])=>
  '<button class="'+(sections.includes(state.section)?'active':'')+'" data-go="'+id+'" aria-label="'+label+'">'+icon+'<span>'+label+'</span></button>').join('');
 const main=WORKSPACES.filter(w=>visibleDestination(w[0])).map(([id,icon,label,sections])=>
  '<button data-go="'+id+'" class="'+(sections.includes(state.section)?'active':'')+'" aria-current="'+(sections.includes(state.section)?'page':'false')+'"><span>'+icon+'</span><span class="navName">'+label+'</span></button>').join('');
 const sub=nav.filter(([id])=>current[3].includes(id)&&id!==current[0]&&visibleDestination(id));
 return '<nav class="nav" aria-label="Primary workspaces">'+main+'</nav>'+
  (sub.length?'<div class="overline">'+current[2]+' tools</div><nav class="nav workspaceSubnav" aria-label="'+current[2]+' tools">'+
   sub.map(([id,icon,label])=>'<button data-go="'+id+'" class="'+(state.section===id?'active':'')+'" aria-current="'+(state.section===id?'page':'false')+'"><span>'+icon+'</span><span class="navName">'+label+'</span></button>').join('')+'</nav>':'');
}

function mobileContextNavigation(){
 const workspace=workspaceFor(state.section);
 const tools=nav.filter(([id])=>workspace[3].includes(id)&&id!==workspace[0]&&visibleDestination(id));
 return tools.length?'<nav class="mobileContextNav" aria-label="'+workspace[2]+' tools">'+
 tools.map(([id,icon,label])=>'<button data-go="'+id+'" class="'+(state.section===id?'active':'')+'">'+esc(label)+'</button>').join('')+'</nav>':'';
}
const $=s=>document.querySelector(s);const esc=s=>String(s??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const dollars=n=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format((n||0)/100);
const datePretty=s=>{if(!s)return '';let [y,m,d]=s.split('-');return new Date(Number(y),Number(m)-1,Number(d)).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'})};
const today=()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`};
const api=async(path,options={})=>{const token=sessionStorage.getItem('backline_session'),requestedBand=state.band;const headers={'Content-Type':'application/json',...(token?{'Authorization':'Bearer '+token}:{})};const r=await fetch('/api'+path,{...options,headers:{...headers,...(options.headers||{})}});const x=await r.json();if(token!==sessionStorage.getItem('backline_session')||requestedBand!==state.band)throw Error('The active account or workspace changed; reopen this view');if(!r.ok)throw Error(typeof x.detail==='string'?x.detail:Array.isArray(x.detail)?x.detail.map(d=>d.loc.slice(1).join('.')+': '+d.msg).join('; '):'Request failed');return x};
function loginScreen(){document.querySelector('#app').innerHTML='<main style="min-height:100vh;display:grid;place-items:center;padding:24px"><form id="loginForm" class="panel" style="width:min(420px,100%)"><h1>Backline</h1><p class="sub">Sign in to your band workspace</p><div class="field"><label for="loginEmail">Email</label><input id="loginEmail" type="email" autocomplete="username" required></div><div class="field" style="margin-top:14px"><label for="loginPassword">Password</label><input id="loginPassword" type="password" autocomplete="current-password" required></div><div class="actions"><button class="primary" type="submit">Sign in</button></div><div style="margin-top:16px"><button type="button" id="showInviteSignup">Have an invitation? Create account</button><button type="button" id="showRecovery">Have a recovery code?</button></div></form></main>'}
document.addEventListener('click',e=>{if(e.target.id!=='showInviteSignup')return;document.querySelector('#app').innerHTML='<main style="min-height:100vh;display:grid;place-items:center;padding:24px"><form class="panel" id="inviteSignup" style="width:min(480px,100%)"><h1>Join Backline</h1><p class="sub">Create an account using a band invitation.</p><div class="field"><label>Invitation token</label><input name="token" required autocomplete="off"></div><div class="field"><label>Email</label><input name="email" type="email" required></div><div class="field"><label>Your name</label><input name="display_name" required></div><div class="field"><label>Password (12+ characters)</label><input name="password" type="password" minlength="12" required autocomplete="new-password"></div><div class="actions"><button class="primary" type="submit">Create account</button><button type="button" id="backToLogin">Back</button></div></form></main>'});
document.addEventListener('click',e=>{if(e.target.id==='backToLogin')loginScreen()});
document.addEventListener('click',e=>{if(e.target.id!=='showRecovery')return;document.querySelector('#app').innerHTML='<main style="min-height:100vh;display:grid;place-items:center;padding:24px"><form class="panel" id="recoveryForm" style="width:min(480px,100%)"><h1>Recover account</h1><p class="sub">Enter the recovery code securely provided by your band owner. Codes expire after 30 minutes.</p><div class="field"><label>Recovery code</label><input name="token" required autocomplete="off"></div><div class="field"><label>New password</label><input name="password" minlength="12" type="password" required autocomplete="new-password"></div><div class="actions"><button class="primary" type="submit">Reset password</button><button type="button" id="backToLogin">Back</button></div></form></main>'});
document.addEventListener('submit',async e=>{if(e.target.id!=='recoveryForm')return;e.preventDefault();const data=Object.fromEntries(new FormData(e.target));try{await api('/auth/recover',{method:'POST',body:JSON.stringify(data)});sessionStorage.removeItem('backline_session');loginScreen();toast('Password updated. Please sign in.')}catch(error){toast(error.message,true)}});

document.addEventListener('submit',async e=>{if(e.target.id!=='inviteSignup')return;e.preventDefault();const data=Object.fromEntries(new FormData(e.target));try{await api('/auth/accept-invite',{method:'POST',body:JSON.stringify(data)});loginScreen();toast('Account created. Please sign in.')}catch(error){toast(error.message,true)}});
document.addEventListener('submit',async e=>{if(e.target.id!=='loginForm')return;e.preventDefault();const email=document.querySelector('#loginEmail').value;const password=document.querySelector('#loginPassword').value;try{const result=await api('/auth/login',{method:'POST',body:JSON.stringify({email,password})});sessionStorage.setItem('backline_session',result.access_token);await load()}catch(error){toast('Sign in failed: '+error.message,true)}});
document.addEventListener('click',async e=>{if(!e.target.closest('#logoutButton'))return;try{await api('/auth/logout',{method:'POST'})}catch(error){}sessionStorage.removeItem('backline_session');clearSessionState();loginScreen()});
function clearSessionState(){document.querySelectorAll('dialog,.stageDesignerBackdrop,.modalWrap').forEach(node=>node.remove());for(const key of Object.keys(state))delete state[key];Object.assign(state,{band:null,section:'dashboard',bands:[],data:{},modal:null});document.querySelector('#app').inert=false;document.dispatchEvent(new Event('backline-signout'))}
const get=key=>state.data[key]||[];
async function load(){try{const previousBand=state.band;state.bands=await api('/bands');if(!state.bands.length){state.data={};state.accountRole='none';state.band=null;state.section='dashboard';render();return}if(!state.bands.find(b=>b.id===state.band))state.band=state.bands[0]?.id;if(!state.previewSelected){const example=state.bands.find(b=>b.name==='The Drunk Uncles (Demo)');if(example){state.band=example.id;state.previewSelected=true}}if(previousBand!==state.band){state.data={};state.discussionThread=null;state.rsvpEvent=null;state.showGig=null;state.selectedTour=null;state.studioGig=null;state.albumId=null;state.section='dashboard';document.dispatchEvent(new Event('backline-band-change'))}const b=`/bands/${state.band}`;if(sessionStorage.getItem('backline_session')){state.data.collaboration=await api(b+'/collaboration');state.accountRole=state.data.collaboration.role}else state.accountRole=null;let names=['dashboard','events','finance','transactions','songs','setlists','members','settlements','bookings','booking-followups','venues','tasks','song-details','shared-venues','member-photos','recordings'];const financial=new Set(['finance','transactions','settlements']);const canFinance=!state.accountRole||['owner','manager','treasurer'].includes(state.accountRole);const vals=await Promise.all(names.map(x=>!canFinance&&financial.has(x)?Promise.resolve(x==='finance'?{}:[]):api(`${b}/${x}`)));names.forEach((x,i)=>state.data[x]=vals[i]);render()}catch(e){if(/Account login required|Invalid or expired session/.test(e.message)){sessionStorage.removeItem('backline_session');clearSessionState();loginScreen();return}toast(e.message,true)}}
function toast(msg,err=false){document.querySelector('.toast')?.remove();let e=document.createElement('div');e.className='toast'+(err?' errorToast':'');e.setAttribute('role',err?'alert':'status');e.textContent=msg;document.body.append(e);setTimeout(()=>e.remove(),3600)}
function button(text,action=''){return `<button class="primary" data-action="${action}">${text}</button>`}
function empty(msg){return `<div class="empty">${esc(msg)}</div>`}
function item(title,sub,tag=''){return `<div class="entry"><div class="entryMain"><strong>${esc(title)}</strong><small>${esc(sub)}</small></div>${tag?`<span class="tag">${esc(tag)}</span>`:''}</div>`}
function panel(title,content,action=''){return `<div class="panel"><div class="panelHeading"><h2>${title}</h2>${action}</div>${content}</div>`}
function fullDashboard(){let d=get('dashboard'),f=d.finance||{},events=d.upcoming||[];const cards=[['Upcoming gigs',d.counts?.gigs??0],['Active members',d.counts?.members??0],['Songs in library',d.counts?.songs??0],['Band cash balance',dollars(f.balance_cents)]];return `<div class="hero"><div><div class="eyebrow">Your band. One place.</div><h2>Keep the music moving.</h2><p>Shows, songs, people and money — everything your band needs to stay organized, with the important details connected.</p></div><button class="primary" data-action="event">+ Add event</button></div><div class="cards">${cards.map(([k,v])=>`<div class="card"><span>${k}</span><strong>${v}</strong></div>`).join('')}</div><div class="panels">${panel('Coming up',events.length?`<div class="list">${events.map(e=>item(e.title,`${datePretty(e.date)} · ${e.time||'Time TBD'} · ${e.venue||'Venue TBD'}`,e.kind)).join('')}</div>`:empty('No events scheduled yet. Add your first show or rehearsal.'),`<button class="small" data-go="schedule">View all →</button>`)}${panel('Finance snapshot',`<div class="list">${[['Gig and other revenue',f.income_cents],['Operating expenses',f.expenses_cents],['Member payouts',f.payouts_cents],['Current band balance',f.balance_cents]].map(([k,v])=>`<div class="entry"><div class="entryMain"><strong>${k}</strong></div><strong>${dollars(v)}</strong></div>`).join('')}</div><p class="footNote">Cash balance is based on recorded transactions, not connected bank accounts.</p>`,`<button class="small" data-go="finance">View ledger →</button>`)}</div>`}
function events(){let a=get('events');return `<div class="toolbar"><p>Book performances, track rehearsals and keep dates aligned.</p>${button('+ New event','event')}</div>${panel('Event calendar',a.length?`<div class="tableWrap"><table class="table"><thead><tr><th>Date</th><th>Type</th><th>Event</th><th>Venue / Location</th><th>Fee</th><th>Status</th></tr></thead><tbody>${a.map(e=>`<tr><td>${datePretty(e.date)}<br><span class="dim">${esc(e.time)}</span></td><td><span class="tag muted">${e.kind}</span></td><td><strong>${esc(e.title)}</strong></td><td>${esc(e.venue)}</td><td>${e.kind==='Gig'?dollars(e.fee_cents):'—'}</td><td>${esc(e.status)}</td></tr>`).join('')}</tbody></table></div>`:empty('Your gig and rehearsal calendar is empty.'))}`}
function dashboard(){if(state.accountRole&&!['owner','manager','treasurer'].includes(state.accountRole)){const data=get('dashboard');return panel('Coming up',(data.upcoming||[]).map(event=>item(event.title,event.date+' · '+event.venue,event.kind)).join('')||empty('No upcoming events.'))+panel('Your band hub','<p>Check availability, discuss arrangements and keep track of your assignments.</p><button data-go="collaboration">Open Band Hub</button><button data-go="notifications">My notifications</button>')}return fullDashboard()}
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
  const [packets,files,templates,stage,advance,timeline,venue]=await Promise.all([
   api(base+'/packet'),api(base+'/files'),api('/bands/'+state.band+'/show-templates'),api(base+'/stage'),api(base+'/advance'),api(base+'/timeline'),api('/bands/'+state.band+'/events/'+state.showGig+'/venue')]);
  state.data.showPackets=packets;state.data.showFiles=files;state.data.showTemplates=templates;state.data.showStage=stage;state.data.showAdvance=advance;state.data.showTimeline=timeline;state.data.showVenue=venue;
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
 const tabs=[['itinerary','Itinerary'],['day','Day of show'],['production','Show production'],['operations','Crew & logistics']];
 const selected=state.tourTab||'itinerary';
 const tabbar='<div class="showTabBar" role="tablist" aria-label="Tour workspace views">'+tabs.map(([key,label])=>'<button role="tab" aria-selected="'+(key===selected)+'" class="'+(key===selected?'selected':'')+'" data-tour-tab="'+key+'">'+label+'</button>').join('')+'</div>';
 const tourSummary=route&&state.selectedTour?panel('Current tour · '+esc(route.tour.name),
  '<div class="hubStats"><span><strong>'+route.stops.length+'</strong> itinerary stops</span><span><strong>'+route.stops.filter(stop=>stop.event_id).length+'</strong> linked shows</span><span><strong>'+route.stops.filter(stop=>!stop.event_id).length+'</strong> travel / unlinked stops</span><span><strong>'+route.warnings.length+'</strong> routing flags</span></div>'+
  '<p class="sub">All changes stay attached to the existing tour and show records. Select Itinerary to edit stops.</p>'):'';
 const linked=route?.stops.filter(stop=>stop.event_id)||[];
 const showActions=linked.length?'<div class="list">'+linked.map(stop=>'<div class="entry"><div><strong>'+esc(stop.city)+' · '+datePretty(stop.stop_date)+'</strong><p>'+esc(stop.venue||'Venue TBC')+' · '+esc(stop.status)+'</p><p>Advance: '+esc(stop.advance?.timeline?.status||'Not linked')+'</p></div><button data-show-gig="'+stop.event_id+'">Open production</button></div>').join('')+'</div>':empty('Link gigs to tour stops to open their production details here.');
 if(selected==='day'){
  const upcoming=route?.stops.slice().sort((a,b)=>a.stop_date.localeCompare(b.stop_date))||[];
  const cards=upcoming.map(stop=>{
    const linkedShow=Boolean(stop.event_id);
    const advance=stop.advance||{},timeline=advance.timeline||{},calls=[
      ['Arrival',stop.arrival_time],['Load-in',timeline.load_in],['Soundcheck',timeline.soundcheck],
      ['Doors',timeline.doors],['Show',timeline.show_time],['Departure',stop.departure_time]
    ].filter(([_,time])=>Boolean(time));
    const gaps=[];
    if(linkedShow&&!timeline.load_in)gaps.push('Load-in');
    if(linkedShow&&!timeline.soundcheck)gaps.push('Soundcheck');
    if(linkedShow&&!timeline.doors)gaps.push('Doors');
    if(linkedShow&&!timeline.show_time)gaps.push('Show time');
    if(linkedShow&&!timeline.timezone)gaps.push('Time zone');
    const readiness=linkedShow?[
      ['Production calls',gaps.filter(g=>g!=='Time zone').length===0],
      ['Venue time zone',Boolean(timeline.timezone)],
      ['Advancement status recorded',Boolean(timeline.status)],
      ['Lodging recorded',Boolean(stop.lodging)]
    ]:[];
    return '<article class="entry scheduleEntry"><div><strong>'+datePretty(stop.stop_date)+' · '+esc(stop.city)+'</strong><p>'+esc(stop.venue||'Venue to confirm')+' · '+esc(stop.status||'planned')+'</p>'+
      '<p><strong>Lodging:</strong> '+esc(stop.lodging||'Not recorded')+'</p>'+(linkedShow?'<div class="showDayReadiness" aria-label="Recorded show-day details"><strong>Recorded details</strong><ul>'+readiness.map(([name,complete])=>'<li>'+esc(name)+': '+(complete?'Recorded':'Needs review')+'</li>').join('')+'</ul><p class="sub">These are record-presence checks, not confirmation that arrangements are approved or complete.</p></div>':'')+(gaps.length?'<p class="sub"><strong>Calls to confirm:</strong> '+esc(gaps.join(', '))+'</p>':'')+ (stop.travel_notes?'<p class="sub">Travel notes: '+esc(stop.travel_notes)+'</p>':'') +'<p class="sub">'+(linkedShow?'Linked show · '+esc(timeline.status||'Advance status not recorded'):'Travel / itinerary stop · no linked show')+'</p><div class="showDayCalls">'+(calls.length?calls.map(([label,value])=>'<span><strong>'+label+'</strong> '+esc(value)+'</span>').join(''):'<span class="sub">No call or travel times recorded</span>')+'</div>'+
      '<p class="sub">'+(linkedShow?'Show-call time zone: '+esc(timeline.timezone||'Not recorded — confirm with venue')+'. Times are shown as recorded.':'Travel times are shown as recorded; confirm local time zone. No production calls are inferred.')+'</p></div>'+
      '<div class="actions">'+(linkedShow?'<button data-show-gig="'+stop.event_id+'">Production</button><button data-tour-crew-gig="'+stop.event_id+'">Guests & crew</button>':'')+'<button data-edit-stop="'+stop.id+'">Edit itinerary stop</button></div></article>';
  }).join('');
  return tabbar+tourSummary+panel('Tour day sheets','<p class="sub">Show days and travel stops in chronological order, with recorded calls, lodging and relevant actions. Missing times are omitted rather than guessed.</p>'+(cards?'<div class="list">'+cards+'</div>':empty('Add itinerary stops to build a tour day-by-day view.')));
 }
 if(selected==='production')return tabbar+tourSummary+panel('Tour production','<p class="sub">Production packets and advances for the shows on this tour.</p>'+showActions+'<button data-go="showops">All show packets</button>');
 if(selected==='operations')return tabbar+tourSummary+panel('Tour crew & logistics','<p class="sub">Show-day crew coordination, guest approvals and private rooming remain permission-scoped.</p>'+(linked.length?'<div class="list">'+linked.map(stop=>'<div class="entry"><div><strong>'+datePretty(stop.stop_date)+' · '+esc(stop.city)+'</strong><p>'+esc(stop.venue||'Venue TBC')+'</p><p class="sub">Guest approvals and private rooming details open in the authorized Show Operations workspace.</p></div><button data-tour-crew-gig="'+stop.event_id+'">Guests & crew</button></div>').join('')+'</div>':empty('No linked show stops yet. Link a gig in the Itinerary tab to open its guest and crew operations.'))+'<button data-go="operations">All crew operations</button>');
 let html=panel('Tour planning','<p class="sub">Build a dated tour itinerary, attach confirmed gigs, track holds and travel days. Routing times require a map provider.</p><button class="small" data-new-tour="1">+ Create tour</button>'+
  '<div class="list">'+tours.map(t=>'<div class="entry"><strong>'+esc(t.name)+'</strong> <button class="small" data-open-tour="'+t.id+'">Open itinerary</button></div>').join('')+'</div>');
 html=tabbar+tourSummary+html;
 if(!route || !state.selectedTour)return html;
 html+=panel('Itinerary · '+esc(route.tour.name),'<button class="small" data-add-stop="1">+ Add stop</button>'+
  (route.stops.length?'<div class="list">'+route.stops.map(stop=>
  '<div class="entry"><div><strong>'+datePretty(stop.stop_date)+' · '+esc(stop.city)+', '+esc(stop.region)+'</strong>'+
  '<p>'+esc(stop.venue||'Travel / routing day')+' · '+esc(stop.status)+'</p>'+
  '<p>'+esc(stop.lodging||'No lodging recorded')+'</p><p>Arrive '+esc(stop.arrival_time||'TBC')+' · Depart '+esc(stop.departure_time||'TBC')+'</p><p>'+esc(stop.travel_notes)+'</p>'+
  (stop.advance?'<p>Advance: '+esc(stop.advance.timeline.status)+' · '+esc(stop.advance.timeline.timezone||'Time zone TBC')+'</p><p>'+esc(stop.advance.venue_contact)+' · '+esc(stop.advance.contact_phone)+'</p><p>'+esc(stop.advance.parking)+'</p><button data-show-gig="'+stop.event_id+'">Open show call sheet</button> ':'')+
  '<button data-edit-stop="'+stop.id+'">Edit stop</button></div></div>').join('')+'</div>':empty('Add your first tour stop.'))+
  '<p class="footNote">'+esc(route.note)+'</p>');
 if(route.warnings.length)html+=panel('Routing flags','<div class="list">'+route.warnings.map(w=>
  '<div class="entry">'+esc(w.message)+'</div>').join('')+'</div>');
 return html;
}

function openTourStopEditor(stop=null){
 const modal=document.createElement('dialog');modal.className='timelineDialog';modal.setAttribute('aria-label',stop?'Edit tour stop':'Add tour stop');
 const gigs=get('events').filter(e=>e.kind==='Gig'),v=stop||{};
 modal.innerHTML='<form><h2>'+(stop?'Edit tour stop':'Add tour stop')+'</h2><label>Linked gig<select name="event_id"><option value="">Travel or unlinked stop</option>'+gigs.map(g=>'<option value="'+g.id+'" '+(g.id===v.event_id?'selected':'')+'>'+esc(g.title)+' · '+esc(g.date)+'</option>').join('')+'</select></label><div class="advanceGrid">'+
 [['date','Date','date',10],['city','City','text',120],['region','State / region','text',80],['venue','Venue','text',160],['arrival_time','Arrival time','time',5],['departure_time','Departure time','time',5],['lodging','Lodging','text',250],['travel_notes','Travel and access notes','text',2000],['change_reason','Reason for change','text',500]].map(([key,label,type,max])=>'<label>'+label+'<input name="'+key+'" type="'+type+'" maxlength="'+max+'" '+(['city','date'].includes(key)?'required':'')+' value="'+esc(key==='date'?v.stop_date||'':v[key]||'')+'"></label>').join('')+
 '<label>Status<select name="status">'+['planned','hold','confirmed','cancelled','travel'].map(status=>'<option '+((v.status||'planned')===status?'selected':'')+'>'+status+'</option>').join('')+'</select></label></div><p role="alert" id="stopError"></p><div class="actions"><button type="button" id="cancelStop">Cancel</button><button class="primary">Save stop</button></div></form>';
 document.body.append(modal);modal.addEventListener('close',()=>modal.remove());modal.querySelector('#cancelStop').onclick=()=>modal.close();
 modal.querySelector('[name="event_id"]').onchange=event=>{const gig=gigs.find(g=>String(g.id)===event.target.value);if(gig){modal.querySelector('[name="date"]').value=gig.date;modal.querySelector('[name="venue"]').value=gig.venue||''}};
 modal.querySelector('form').onsubmit=async event=>{event.preventDefault();const data=Object.fromEntries(new FormData(event.target));data.event_id=data.event_id?Number(data.event_id):null;data.revision=stop?.revision??null;try{
  await api('/bands/'+state.band+'/tours/'+state.selectedTour+'/stops'+(stop?'/'+stop.id:''),{method:stop?'PUT':'POST',body:JSON.stringify(data)});modal.close();await refreshTours();toast('Tour stop saved')
 }catch(error){modal.querySelector('#stopError').textContent=error.message}};modal.showModal();
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
 let working=JSON.parse(JSON.stringify(original));let selected=-1;
 const kinds=['vocal','guitar','bass','drums','keys','monitor','amp','other'];
 const shade={vocal:'#818cf8',guitar:'#f59e0b',bass:'#34d399',drums:'#fb7185',keys:'#38bdf8',monitor:'#c084fc',amp:'#fbbf24',other:'#94a3b8'};
 const dialog=document.createElement('div');dialog.className='stageDesignerBackdrop';dialog.id='stageDesigner';
 dialog.innerHTML='<div class="stageDesigner"><header class="stageDesignerHeader"><div><h2>Stage Designer</h2><p class="sub">Drag equipment around the stage. Front of house is at the bottom.</p></div><button type="button" id="stageClose">✕ Close</button></header><div class="stageTools"><button id="stageAddItem" type="button">+ Equipment</button><button id="stageAddInput" type="button">+ Input channel</button><button id="stageDemo" type="button">Example four-piece band</button></div><div class="stageEditorGrid"><div><div id="stageCanvas" class="stageCanvas" aria-label="Drag stage equipment"><span class="stageBack">UPSTAGE</span><span class="stageFront">AUDIENCE / FRONT OF HOUSE</span></div><p class="footNote">Select equipment to edit. Drag or use arrow keys to move; Shift moves 10 grid units.</p><div id="equipmentEditor"></div></div><div class="stagePatchPanel"><h3>Input patch list</h3><div id="stageInputs"></div><label>Production notes<textarea id="stageNotes" rows="3"></textarea></label></div></div><footer class="stageDesignerFooter"><span id="stageDesignerStatus">Draft changes — not saved</span><button class="primary" type="button" id="stageSave">Save stage setup</button></footer></div>';
 dialog.setAttribute('role','dialog');dialog.setAttribute('aria-modal','true');dialog.setAttribute('aria-label','Stage Designer');
 const opener=document.activeElement;document.body.append(dialog);document.querySelector('#app').inert=true;
 const close=(saved=false)=>{working.notes=$d('#stageNotes').value;if(!saved&&JSON.stringify(working)!==JSON.stringify(original)&&!confirm('Discard unsaved stage changes?'))return;document.querySelector('#app').inert=false;dialog.remove();opener?.focus()};
 dialog.addEventListener('keydown',event=>{if(event.key==='Escape'){event.preventDefault();close()}if(event.key==='Tab'){const nodes=[...dialog.querySelectorAll('button,input,select,textarea')].filter(n=>!n.disabled);const first=nodes[0],last=nodes.at(-1);if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus()}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}}});
 const $d=sel=>dialog.querySelector(sel);
 function draw(){
  const canvas=$d('#stageCanvas');
  canvas.querySelectorAll('.stageItem').forEach(n=>n.remove());
  working.items.forEach((item,index)=>{
   const node=document.createElement('button');node.type='button';node.className='stageItem';
   node.style.left=item.x+'%';node.style.top=item.y+'%';
   node.style.borderColor=shade[item.kind]||'#94a3b8';
   node.textContent=item.label;
   node.title=item.kind+' — drag or arrow keys to move; Enter to edit';
   node.setAttribute('aria-label',item.label+', x '+item.x+', y '+item.y);
   node.addEventListener('keydown',event=>{
    const directions={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]};
    if(directions[event.key]){event.preventDefault();const [dx,dy]=directions[event.key],step=event.shiftKey?10:1;item.x=Math.max(0,Math.min(100,item.x+dx*step));item.y=Math.max(0,Math.min(100,item.y+dy*step));draw();$d('#stageCanvas').querySelectorAll('.stageItem')[index].focus()}
    if(event.key==='Enter'||event.key===' '){event.preventDefault();selected=index;draw();$d('#equipmentLabel').focus()}
   });
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
      selected=index;
      draw();
     }
    };
    node.addEventListener('pointermove',move);node.addEventListener('pointerup',up);node.addEventListener('pointercancel',up,{once:true});
   });
   canvas.append(node);
  });
  const editor=$d('#equipmentEditor');editor.replaceChildren();
  if(working.items[selected]){
   const item=working.items[selected];
   for(const [key,label] of [['label','Equipment label'],['kind','Equipment type'],['x','Horizontal position'],['y','Vertical position']]){
    const wrap=document.createElement('label');wrap.textContent=label;const input=document.createElement(key==='kind'?'select':'input');
    input.id='equipment'+(key==='label'?'Label':key);input.setAttribute('aria-label',label);
    if(key==='kind')kinds.forEach(kind=>input.add(new Option(kind,kind)));
    else if(key==='x'||key==='y'){input.type='number';input.min=0;input.max=100}else input.maxLength=100;
    input.value=item[key];input.onchange=()=>{item[key]=(key==='x'||key==='y')?Math.max(0,Math.min(100,Number(input.value))):input.value;draw()};wrap.append(input);editor.append(wrap);
   }
   const remove=document.createElement('button');remove.textContent='Remove equipment';remove.type='button';remove.onclick=()=>{working.items.splice(selected,1);selected=-1;draw();$d('#stageAddItem').focus()};editor.append(remove);
  }
  const inputs=$d('#stageInputs');inputs.replaceChildren();
  working.inputs.sort((a,b)=>a.channel-b.channel).forEach((item,index)=>{
   const row=document.createElement('div');row.className='stageInputRow';
   for(const [key,label,max] of [['channel','Channel',128],['source','Audio source',120],['microphone','Microphone or DI',120],['stand','Stand',60],['notes','Channel notes',300]]){
    const wrap=document.createElement('label');wrap.textContent=label;
    const input=document.createElement('input');input.setAttribute('aria-label',label+' '+(index+1));input.type=key==='channel'?'number':'text';
    if(key==='channel'){input.min=1;input.max=128}else input.maxLength=max;
    input.value=item[key]||'';input.oninput=()=>item[key]=key==='channel'?Number(input.value):input.value;wrap.append(input);row.append(wrap);
   }
   for(const [title,delta] of [['Move channel up',-1],['Move channel down',1]]){
    const move=document.createElement('button');move.type='button';move.textContent=delta<0?'↑':'↓';move.setAttribute('aria-label',title+' '+(index+1));move.disabled=index+delta<0||index+delta>=working.inputs.length;
    move.onclick=()=>{const other=working.inputs[index+delta];[item.channel,other.channel]=[other.channel,item.channel];draw()};row.append(move);
   }
   const remove=document.createElement('button');remove.type='button';remove.textContent='Remove';remove.setAttribute('aria-label','Remove channel '+(index+1));remove.onclick=()=>{working.inputs.splice(index,1);draw()};row.append(remove);
   inputs.append(row);
  });
 }
 $d('#stageNotes').value=working.notes||'';
 $d('#stageClose').onclick=()=>close();
 $d('#stageAddItem').onclick=()=>{
  if(working.items.length>=80){toast('Maximum equipment count reached',true);return}
  working.items.push({label:'New equipment',kind:'vocal',x:50,y:50});selected=working.items.length-1;draw();$d('#equipmentLabel').focus()
 };
 $d('#stageAddInput').onclick=()=>{
  const used=new Set(working.inputs.map(x=>x.channel));let channel=1;
  while(used.has(channel)&&channel<=128)channel++;
  if(channel>128){toast('Maximum input count reached',true);return}
  working.inputs.push({channel,source:'New input',microphone:'',stand:'',notes:''});draw()
 };
 $d('#stageDemo').onclick=()=>{
  if((working.items.length||working.inputs.length)&&!confirm('Replace your unsaved stage setup with the example?'))return;
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
   close(true);await openShowPacketGig(state.showGig);toast('Stage setup saved')
  }catch(error){$d('#stageDesignerStatus').textContent=error.message;toast(error.message,true)}
 };
 draw();$d('#stageClose').focus()
}
function printShowPacket(){
 const gig=get('events').find(g=>g.id===state.showGig);
 const docs=get('showPackets');
 if(!gig||!docs.length){toast('Create show documents before printing',true);return}
 const content=timelinePanel(true)+'<header><h1>'+esc(gig.title)+'</h1><p>'+datePretty(gig.date)+' · '+esc(gig.venue||'Venue TBD')+'</p></header>'+
 docs.map(doc=>'<article><h2>'+esc(doc.title)+'</h2><p class="printStatus">Status: '+esc(doc.status)+'</p>'+
 doc.sections.map(section=>'<section><h3>'+esc(section.heading)+'</h3><p>'+esc(section.body).replace(/\\n/g,'<br>')+'</p></section>').join('')+'</article>').join('');
 const w=window.open('','_blank');
 if(!w){toast('Allow pop-ups to print show documents',true);return}
 w.document.write('<!doctype html><html><head><title>Show Packet</title><style>body{font:14px/1.6 Arial,sans-serif;max-width:900px;margin:35px auto;color:#17202a}h1{font-size:29px}h2{margin-top:32px;border-bottom:2px solid #2c4058;padding-bottom:8px}h3{margin-bottom:4px}p{white-space:pre-wrap}article{break-before:page}.printStatus{font-size:12px;color:#526275}@media print{body{margin:0;padding:12mm}article{break-inside:avoid}}</style></head><body>'+content+'</body></html>');
 w.document.close();w.focus();
}
function openPacketEditor(packet){
 const modal=document.createElement('div');modal.className='stageDesignerBackdrop';modal.id='packetEditor';
 const safe=esc;
 modal.innerHTML='<div class="stageDesigner packetEditor"><div class="stageDesignerHeader"><div><span class="eyebrow">SHOW DOCUMENT EDITOR</span><h2>Edit '+safe(packet.title)+'</h2><p class="sub">Edit each section, then save the entire document as a draft.</p></div><button type="button" id="packetCancel">Close</button></div>'+
 '<label class="packetTitle">Document title<input id="packetTitle" maxlength="140" required value="'+safe(packet.title)+'"></label>'+
 '<div id="packetSections">'+packet.sections.map((section,i)=>'<div class="packetSection"><label>Section heading<input class="packetHeading" maxlength="100" value="'+safe(section.heading)+'" required></label><label>Content<textarea class="packetBody" maxlength="6000" rows="6">'+safe(section.body)+'</textarea></label></div>').join('')+'</div>'+
 '<div class="stageDesignerFooter"><span id="packetStatus">Changes have not been saved</span><div class="actions"><button type="button" id="packetDiscard">Discard</button><button type="button" class="primary" id="packetSave">Save draft</button></div></div></div>';
 document.body.append(modal);
 const close=()=>modal.remove();
 modal.querySelector('#packetCancel').onclick=close;
 modal.querySelector('#packetDiscard').onclick=close;
 modal.querySelector('#packetSave').onclick=async()=>{
  const title=modal.querySelector('#packetTitle').value.trim();
  const sections=[...modal.querySelectorAll('.packetSection')].map(el=>({
   heading:el.querySelector('.packetHeading').value.trim(),
   body:el.querySelector('.packetBody').value
  }));
  if(!title||sections.some(x=>!x.heading)){modal.querySelector('#packetStatus').textContent='Title and all section headings are required';return}
  const save=modal.querySelector('#packetSave');save.disabled=true;
  try{
   await api('/bands/'+state.band+'/gigs/'+state.showGig+'/packet/'+packet.id,
    {method:'PUT',body:JSON.stringify({title,sections})});
   close();await openShowPacketGig(state.showGig);toast('Show document saved as draft')
  }catch(error){modal.querySelector('#packetStatus').textContent=error.message;save.disabled=false}
 };
}
function timelinePanel(printing=false){
 const t=state.data.showTimeline||{entries:[],warnings:[]},a=state.data.showAdvance||{};
 const contacts=[['Venue contact',a.venue_contact],['Production contact',a.production_contact],['Email',a.contact_email],['Phone',a.contact_phone],['Venue address',a.venue_address],['Parking and access',a.parking],['Lodging',a.lodging],['Meals and hospitality',a.hospitality],['Settlement',a.settlement]];
 return panel('Day-of-show call sheet','<p><strong>'+esc(t.timezone||'Time zone to confirm')+'</strong> · '+esc(t.status||'draft')+' · All times local to venue. Day +1 / +2 follow the show date.</p>'+t.warnings.map(w=>'<p class="scheduleWarning">'+esc(w)+'</p>').join('')+
 '<dl class="callContacts">'+contacts.filter(x=>x[1]).map(([label,value])=>'<div><dt>'+label+'</dt><dd>'+esc(value)+'</dd></div>').join('')+'</dl>'+
 '<ol class="showTimeline">'+t.entries.map(entry=>'<li><div class="callTime">'+esc(entry.time)+(entry.day_offset?' <small>Day +'+entry.day_offset+'</small>':'')+'</div><div><strong>'+esc(entry.title)+'</strong><p>'+esc([entry.owner,entry.location].filter(Boolean).join(' · '))+'</p><p>'+esc(entry.notes)+'</p><small>'+esc(entry.source==='venue'?'Venue milestone':'Crew call')+'</small></div></li>').join('')+'</ol>'+
 (printing?'':'<div class="actions"><button data-edit-timeline="1">Edit crew calls</button><button data-pdf-packet="1">Download PDF show packet</button></div>'));
}
function openTimelineEditor(){
 const a=state.data.showAdvance||{},working=JSON.parse(JSON.stringify(a.schedule||[]));
 const modal=document.createElement('dialog');modal.className='timelineDialog';modal.setAttribute('aria-label','Edit crew calls');
 modal.innerHTML='<form><h2>Edit crew calls</h2><p>Save venue milestone times on Advances & riders. Each saved change returns advancement to draft for review.</p><div id="crewCalls"></div><button type="button" id="addCrewCall">+ Crew call</button><p role="alert" id="crewError"></p><div class="actions"><button type="button" id="cancelCrew">Cancel</button><button class="primary">Save crew calls</button></div></form>';
 document.body.append(modal);
 const draw=()=>{const list=modal.querySelector('#crewCalls');list.replaceChildren();working.forEach((entry,index)=>{
  const row=document.createElement('fieldset');const legend=document.createElement('legend');legend.textContent='Crew call '+(index+1);row.append(legend);
  for(const [key,label,max] of [['title','Activity',120],['time','Local time',5],['day_offset','Day offset',2],['owner','Owner',150],['location','Location',200],['notes','Notes',1000]]){
   const wrap=document.createElement('label');wrap.textContent=label;const input=document.createElement('input');input.type=key==='time'?'time':key==='day_offset'?'number':'text';input.setAttribute('aria-label',label+' '+(index+1));input.value=entry[key]??'';
   if(key==='title'||key==='time')input.required=true;if(key==='day_offset'){input.min=0;input.max=2}else input.maxLength=max;
   input.oninput=()=>entry[key]=key==='day_offset'?Number(input.value):input.value;wrap.append(input);row.append(wrap);
  }
  const remove=document.createElement('button');remove.type='button';remove.textContent='Remove call '+(index+1);remove.onclick=()=>{working.splice(index,1);draw()};row.append(remove);list.append(row);
 })};
 modal.querySelector('#addCrewCall').onclick=()=>{if(working.length>=50)return;working.push({title:'',time:'',day_offset:0,owner:'',location:'',notes:''});draw();modal.querySelector('#crewCalls fieldset:last-child input').focus()};
 modal.querySelector('#cancelCrew').onclick=()=>modal.close();modal.addEventListener('close',()=>modal.remove());
 modal.querySelector('form').onsubmit=async event=>{event.preventDefault();try{await api('/bands/'+state.band+'/gigs/'+state.showGig+'/advance',{method:'PUT',body:JSON.stringify({...a,schedule:working,status:'draft'})});modal.close();await openShowPacketGig(state.showGig);toast('Crew calls saved — review and confirm advancement')}catch(error){modal.querySelector('#crewError').textContent=error.message}};
 draw();modal.showModal();
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
 const complete=docs.filter(x=>x.status==='ready').length;
 const summary='<div class="showOverview"><div><span class="eyebrow">SHOW PRODUCTION</span><h2>'+esc(chosen.title)+'</h2><p>'+datePretty(chosen.date)+' · '+esc(chosen.venue||'Venue to confirm')+'</p></div><div class="showMetrics"><span><strong>'+complete+'/'+docs.length+'</strong> documents ready</span><span><strong>'+files.length+'</strong> files attached</span><span><strong>'+(state.data.showStage?.inputs?.length||0)+'</strong> audio inputs</span></div></div>';
 const tabs=[['stage','Stage & inputs'],['advance','Advances & riders'],['timeline','Day of show'],['files','Contracts & files']];
 const active=state.showTab||'stage';
 html+=summary+'<div class="showTabBar" role="tablist">'+tabs.map(([key,label])=>'<button role="tab" aria-selected="'+(active===key)+'" class="'+(active===key?'selected':'')+'" data-show-tab="'+key+'">'+label+'</button>').join('')+'</div>';

 if(active==='advance'){
 html+=venueLinkPanel();
 const a=state.data.showAdvance||{};
 const fields=[['timezone','Venue time zone (e.g. America/Chicago)'],['venue_address','Venue address'],['lodging','Lodging'],['hospitality','Meals and hospitality'],['settlement','Settlement arrangements'],['venue_contact','Venue contact'],['production_contact','Production contact'],['contact_email','Contact email'],['contact_phone','Contact phone'],['load_in','Load-in time'],['soundcheck','Soundcheck'],['doors','Doors'],['show_time','Show time'],['curfew','Curfew'],['parking','Parking and access'],['open_questions','Outstanding questions'],['change_reason','Reason for this change']];
 html+=panel('Venue advancement','<p class="sub">Keep show-day contact information and confirmed times together. Confirmation requires key times and no open questions.</p><div class="advanceGrid">'+fields.map(([key,label])=>'<label>'+label+(['parking','open_questions','lodging','hospitality','settlement'].includes(key)?'<textarea data-advance-field="'+key+'" rows="3">'+esc(a[key]||'')+'</textarea>':'<input type="'+(['load_in','soundcheck','doors','show_time','curfew'].includes(key)?'time':key==='contact_email'?'email':key==='contact_phone'?'tel':'text')+'" data-advance-field="'+key+'" value="'+esc(a[key]||'')+'">'+(['load_in','soundcheck','doors','show_time','curfew'].includes(key)?'<select aria-label="'+label+' day" data-advance-day="'+key+'">'+[0,1,2].map(day=>'<option value="'+day+'" '+((a.day_offsets?.[key]||0)===day?'selected':'')+'>'+(day?'Day +'+day:'Show date')+'</option>').join('')+'</select>':''))+'</label>').join('')+'</div><div class="actions"><select id="advanceStatus" aria-label="Advancement status"><option value="draft" '+(a.status==='draft'?'selected':'')+'>Draft</option><option value="awaiting_venue" '+(a.status==='awaiting_venue'?'selected':'')+'>Awaiting venue</option><option value="confirmed" '+(a.status==='confirmed'?'selected':'')+'>Confirmed</option></select><button class="small" data-save-advance="1">Save advancement</button></div>');
 }
 if(active==='advance')html+=panel('Show documents',
  '<p class="sub">Create riders, advances and schedules; then edit each section before marking ready.</p><button class="small" data-pdf-packet="1">Download PDF show packet</button> <button class="small" data-print-packet="1">Print in browser</button>'+
  '<div class="actions">'+Object.entries(labels).map(([key,name])=>
   '<button class="small" data-create-packet="'+key+'">+ '+esc(name)+'</button>').join('')+'</div>'+
  (docs.length?'<div class="list">'+docs.map(d=>
   '<div class="entry"><div><strong>'+esc(d.title)+'</strong> <span class="tag muted">'+esc(d.status)+'</span>'+
   '<p>'+d.sections.map(x=>esc(x.heading)).join(' · ')+'</p></div>'+
   '<button class="small" data-edit-packet="'+d.id+'">Edit</button> '+
   '<button class="small" data-ready-packet="'+d.id+'">Mark ready</button></div>').join('')+'</div>':
   empty('Create a document from the defaults to start your packet.')));
 if(active==='stage')html+=panel('Stage plot and audio input list',
  '<p class="sub">Place instruments on a 0–100 stage grid, and number your patch list.</p>'+
  '<button class="small" data-edit-stage="1">Edit stage setup</button> '+ 
  '<button class="small" data-stage-export="stage.svg">Download stage plot</button> '+
  '<button class="small" data-stage-export="inputs.csv">Download input list</button>'+stagePreview(state.data.showStage)+
  '<div class="list">'+(get('showStage').items||[]).map(i=>'<div class="entry">'+esc(i.label)+' · '+esc(i.kind)+' (x:'+i.x+', y:'+i.y+')</div>').join('')+
  (get('showStage').inputs||[]).map(i=>'<div class="entry">CH '+i.channel+' · '+esc(i.source)+' · '+esc(i.microphone)+'</div>').join('')+'</div>');
 if(active==='timeline')html+=timelinePanel();
 if(active==='files')html+=panel('Contracts and show files',
  '<p class="sub">Upload PDF contracts, stage plots, input lists, receipts or W-9 forms. Files stay attached to this show.</p>'+
  '<div class="actions"><select id="showFileCategory"><option value="contract">Performance contract</option><option value="stage_plot">Stage plot</option><option value="input_list">Input list</option><option value="technical_rider">Technical rider</option><option value="hospitality_rider">Hospitality rider</option><option value="receipt">Receipt</option><option value="w9">W-9</option><option value="insurance">Insurance</option><option value="other">Other</option></select>'+
  '<input id="showFileInput" type="file" accept=".pdf,application/pdf"><button class="small" data-upload-show-file="1">Upload PDF</button></div>'+
  (files.length?'<div class="list">'+files.map(x=>
   '<div class="entry"><strong>'+esc(x.filename)+'</strong> · '+esc(x.category)+
   ' <button class="small" data-download-show-file="'+x.id+'">Download</button></div>').join('')+'</div>':
   empty('No PDF documents stored for this show.')));
 return html;
}

function songs(){return repertoireLibrary()}
function members(){let a=get('members');return `<div class="toolbar"><p>Your roster, responsibilities and band contacts.</p><div style="display:flex;gap:8px">${sessionStorage.getItem('backline_session')?button('+ Invite user','invitation')+button('Member recovery','issueRecovery'):''}${button('+ Add member','member')}</div></div>${panel('Band roster',a.length?`<div class="list">${a.map(m=>'<div class="memberRosterRow">'+memberAvatar(m.id,m.name)+item(m.name,`${m.instrument||'Instrument not set'} · ${m.email||'No email'} · ${m.role}`,m.active?'Active':'Inactive')+'</div>').join('')}</div>`:empty('Add your first band member.'))}`}
function setlists(){return setlistLibrary()}
function finance(){let f=get('finance'),ts=get('transactions'),settlements=get('settlements');let cards=[['Cash on hand',f.balance_cents],['Revenue',f.income_cents],['Expenses',f.expenses_cents],['Member payouts',f.payouts_cents]];let gigs=get('events').filter(e=>e.kind==='Gig'&&!settlements.find(s=>s.event_id===e.id));return `<div class="toolbar"><p>Transparent band bookkeeping, connected to gigs and members.</p><div style="display:flex;gap:8px">${button('+ Transaction','transaction')}${button('Settle gig','settlement')}<button data-export="ledger">Export CSV</button></div></div><div class="cards">${cards.map(([label,v])=>`<div class="card"><span>${label}</span><strong>${dollars(v)}</strong></div>`).join('')}</div>${panel('Settlements',settlements.length?`<div class="list">${settlements.map(s=>`<div class="entry" style="display:block"><strong>${esc(s.event_title)}</strong><div class="sub" style="margin:7px 0">${datePretty(s.event_date)} · Band reserve: ${s.reserve_basis_points/100}%</div>${s.shares.map(sh=>`<div style="display:flex;justify-content:space-between;padding:6px 0;font-size:13px"><span>${esc(sh.member_name)}</span><span>${dollars(sh.amount_cents)} due · ${dollars(sh.paid_cents)} paid</span></div>`).join('')}</div>`).join('')}</div>`:empty('No settled gigs yet. Record gig revenue and expenses, then create a settlement.'))}${panel('Transaction ledger',ts.length?`<div class="tableWrap"><table class="table"><thead><tr><th>Date</th><th>Type</th><th>Detail</th><th>Gig / Member</th><th>Amount</th><th></th></tr></thead><tbody>${ts.map(t=>`<tr><td>${datePretty(t.date)}</td><td><span class="tag muted">${esc(t.kind)}</span></td><td>${esc(t.description)}<div class="dim">${esc(t.category)}</div></td><td>${esc([t.event_title,t.member_name].filter(Boolean).join(' / '))}</td><td class="${['income','contribution'].includes(t.kind)?'positive':'negative'}">${['income','contribution'].includes(t.kind)?'+':'−'}${dollars(t.amount_cents)}</td><td>${!t.reversal_of&&!ts.some(q=>q.reversal_of===t.id)?`<button class="small" data-reverse="${t.id}">Reverse</button>`:''}</td></tr>`).join('')}</tbody></table></div>`:empty('No transactions yet. Record your first payment or expense.'))}<p class="footNote">Ledger records are immutable. Corrections create an offsetting transaction, preserving the original entry. Reconciled bank balances, tax preparation, and payment transfers require additional integrations.</p>`}
function render(){const b=state.bands.find(x=>x.id===state.band)||{name:'Your band'};let titles={dashboard:'Overview',events:'Shows & Rehearsals',schedule:'Schedule',finance:'Band Finances',bookings:'Booking Tracker',studio:'AI Gig Studio',songs:'Song Library',setlists:'Setlist Studio',members:'Band Members',showops:'Show Packets',touring:'Tour Routing',venues:'Venue Book',tasks:'Tasks',calendars:'Calendars',collaboration:'Band Hub',notifications:'Notifications',media:'Photos & Media',operations:'Show Operations'};$('#app').innerHTML=`<div class="app"><aside class="side"><div class="brand"><span class="mark">⌁</span>BACKLINE</div><div><div class="overline">Workspace</div><select class="bandPicker" id="bandPicker">${state.bands.map(b=>`<option value="${b.id}" ${b.id===state.band?'selected':''}>${esc(b.name)}</option>`).join('')}</select></div><div><div class="overline">Manage</div>${workspaceNavigation()}</div><button class="ghost" data-action="band">+ New band</button><div class="sideFoot">BACKLINE v0.5 UX development<br>Private development preview<br>Data stays in your SQLite database.</div></aside><main class="main"><header class="top"><div><span class="eyebrow">${esc(b.name)}</span><h1>${titles[state.section]}</h1>${workspaceFor(state.section)[0]!==state.section?`<p class="sub" aria-label="Current workspace">${workspaceFor(state.section)[2]} · ${titles[state.section]}</p>`:''}</div><div style="display:flex;gap:10px;align-items:center"><select id="mobileBandPicker" class="mobileBandPicker" aria-label="Band workspace">${state.bands.map(b=>`<option value="${b.id}" ${b.id===state.band?'selected':''}>${esc(b.name)}</option>`).join('')}</select><span class="chip">● Band workspace</span><button class="small" data-action="joinband">Join band</button><button class="small urgentOperationsButton" id="urgentOperationsButton" data-go="operations" data-ops-updates hidden>Urgent changes</button><button class="small" data-install-app hidden>Install app</button><button class="small" id="logoutButton">Sign out</button></div></header>${mobileContextNavigation()}<section class="content">${({dashboard,events,schedule:scheduleBoard,finance,bookings,studio,songs,setlists,members,showops,touring,venues:venueBook,tasks:taskBoard,calendars:calendarBoard,collaboration:collaborationBoard,notifications:notificationCentre,media:mediaBoard,operations:operationsBoard})[state.section]()}</section></main><div class="mobileNav">${workspaceNavigation(true)}</div></div>${state.modal?modalHTML():''}`;document.querySelectorAll('#bandPicker,#mobileBandPicker').forEach(picker=>picker.addEventListener('change',async e=>{state.band=Number(e.target.value);state.showGig=null;state.selectedTour=null;state.studioGig=null;state.discussionThread=null;state.rsvpEvent=null;state.data={};state.section='dashboard';await load()}));document.dispatchEvent(new Event('backline-render'))}
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
if(type==='event'){title='Add show or rehearsal';fields=select('kind','Event type',[['Gig','Gig'],['Rehearsal','Rehearsal'],['Session','Session']])+field('title','Name','text','required')+field('venue','Venue / location')+field('date','Date','date',`required value="${today()}"`)+field('time','Time','time')+field('fee','Agreed gig fee ($)','number','min="0" step="0.01" value="0"')+select('status','Status',[['Planned','Planned'],['Confirmed','Confirmed'],['Completed','Completed']])}
if(type==='song'){title='Add song';fields=field('title','Song title','text','required')+field('artist','Artist / writer')+field('song_key','Key')+field('bpm','Tempo (BPM)','number','min="1" max="400"')+field('duration_seconds','Duration in seconds','number','min="0" value="0"')+select('status','Status',[['Learning','Learning'],['Ready','Ready'],['Retired','Retired']])}
if(type==='transaction'){title='Record transaction';fields=select('kind','Type',[['income','Income'],['expense','Expense'],['payout','Member payout'],['contribution','Member contribution']])+field('amount','Amount ($)','number','min="0.01" step="0.01" required')+field('description','Description','text','required')+field('category','Category')+field('date','Date','date',`required value="${today()}"`)+select('event_id','Related event',eventOpts)+select('member_id','Related member',memberOpts)}
if(type==='setlist'){title='Create setlist';fields=field('title','Setlist title','text','required')+select('event_id','For gig (optional)',eventOpts)+`<div class="field full"><label>Choose songs (sorted by title)</label><div class="setSongs">${songs.length?songs.map(s=>`<label><input type="checkbox" name="song_ids" value="${s.id}">${esc(s.title)}${s.song_key?' · '+esc(s.song_key):''}</label>`).join(''):'Add songs first.'}</div></div>`}
if(type==='settlement'){title='Settle a gig';let settled=get('settlements').map(s=>s.event_id);fields=select('event_id','Gig',evs.filter(e=>e.kind==='Gig'&&!settled.includes(e.id)).map(e=>[String(e.id),e.title]))+field('reserve_percent','Retain for band (%)','number','min="0" max="100" value="10" required')+`<div class="field full"><label>Musicians to pay</label><div class="setSongs">${mem.length?mem.map(m=>`<label><input type="checkbox" name="member_ids" value="${m.id}" checked>${esc(m.name)}</label>`).join(''):'Add members first.'}</div></div><p class="footNote">Record actual gig income and expenses in the ledger before settling. The settlement uses the net recorded cash and reserves the specified percentage.</p>`}
return `<div class="modalWrap" id="modalWrap"><div class="modal" role="dialog" aria-modal="true" aria-label="${title}"><h2>${title}</h2><p class="sub">${esc(state.bands.find(b=>b.id===state.band)?.name||'')}</p><form id="entryForm"><div class="formGrid">${fields}</div><div class="actions"><button type="button" data-action="close">Cancel</button><button class="primary" type="submit">Save</button></div></form></div></div>`}
document.addEventListener('click',async e=>{let btn=e.target.closest('[data-go],[data-action],[data-reverse],[data-export],[data-booking],[data-studio-gig],[data-approve-draft],[data-scan-market],[data-generate-campaign],[data-edit-draft],[data-voice],[data-show-gig],[data-create-packet],[data-edit-packet],[data-ready-packet],[data-upload-show-file],[data-download-show-file],[data-save-advance],[data-edit-timeline],[data-pdf-packet],[data-print-packet],[data-show-tab],[data-edit-stage],[data-stage-export],[data-new-tour],[data-open-tour],[data-add-stop],[data-edit-stop],[data-tour-tab],[data-tour-crew-gig]');if(!btn){if(e.target.id==='modalWrap'){state.modal=null;render()}return}if(btn.dataset.editTimeline){openTimelineEditor();return}if(btn.dataset.newTour){
 const name=prompt('Name this tour (example: Upper Midwest Weekend)');if(!name?.trim())return;
 try{const tour=await api('/bands/'+state.band+'/tours',
  {method:'POST',body:JSON.stringify({name:name.trim()})});
  state.selectedTour=tour.id;await refreshTours();toast('Tour created')
 }catch(err){toast(err.message,true)}return
}
if(btn.dataset.openTour){
 state.selectedTour=Number(btn.dataset.openTour);await refreshTours();return
}
if(btn.dataset.addStop){openTourStopEditor();return}
if(btn.dataset.editStop){const stop=state.data.currentRoute?.stops.find(s=>String(s.id)===btn.dataset.editStop);if(stop)openTourStopEditor(stop);return}
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
if(btn.dataset.saveAdvance){
 const a={...state.data.showAdvance};document.querySelectorAll('[data-advance-field]').forEach(el=>{a[el.dataset.advanceField]=el.value});
 a.day_offsets={};document.querySelectorAll('[data-advance-day]').forEach(el=>a.day_offsets[el.dataset.advanceDay]=Number(el.value));
 a.status=document.getElementById('advanceStatus').value;
 try{await api('/bands/'+state.band+'/gigs/'+state.showGig+'/advance',{method:'PUT',body:JSON.stringify(a)});await openShowPacketGig(state.showGig);toast('Venue advancement saved')}
 catch(error){toast(error.message,true)}return
}
if(btn.dataset.pdfPacket){
 window.open('/api/bands/'+state.band+'/gigs/'+state.showGig+'/packet.pdf','_blank');
 return
}
if(btn.dataset.printPacket){printShowPacket();return}
if(btn.dataset.showTab){state.showTab=btn.dataset.showTab;render();return}
if(btn.dataset.editStage){
 openStageDesigner();return
}
if(btn.dataset.showGig){if(state.section==='touring')state.showTab='timeline';await openShowPacketGig(btn.dataset.showGig);return}
if(btn.dataset.createPacket){
 try{await api('/bands/'+state.band+'/gigs/'+state.showGig+'/packet',{
  method:'POST',body:JSON.stringify({kind:btn.dataset.createPacket})});
  await openShowPacketGig(state.showGig);toast('Show document created');
 }catch(error){toast(error.message,true)}return
}
if(btn.dataset.editPacket){
 const packet=get('showPackets').find(x=>String(x.id)===btn.dataset.editPacket);
 if(packet)openPacketEditor(packet);
 return
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
if(btn.dataset.voice){try{const p='/bands/'+state.band+'/marketing-voice';const existing=await api(p);const tone=prompt('Tone: straightforward, playful, gritty, or warm',existing.tone);if(!tone)return;const tagline=prompt('Band tagline or distinctive phrase (optional)',existing.tagline);if(tagline===null)return;await api(p,{method:'PUT',body:JSON.stringify({tone:tone.trim().toLowerCase(),tagline:tagline.trim()})});toast('Band marketing voice saved')}catch(err){toast(err.message,true)}return}if(btn.dataset.editDraft){const draft=(state.data.studioDrafts||[]).find(x=>String(x.id)===btn.dataset.editDraft);if(!draft){toast('Draft not loaded',true);return}const angle=prompt('Campaign angle',draft.angle);if(!angle?.trim())return;const body=prompt('Edit promotional copy',draft.body);if(!body?.trim())return;try{await api('/bands/'+state.band+'/gigs/'+state.studioGig+'/campaign/'+draft.id,{method:'PATCH',body:JSON.stringify({angle:angle.trim(),body:body.trim()})});await refreshStudio();toast('Draft revised and saved')}catch(err){toast(err.message,true)}return}if(btn.dataset.generateCampaign){try{const result=await api('/bands/'+state.band+'/gigs/'+state.studioGig+'/campaign/generate',{method:'POST'});await refreshStudio();toast('Created '+result.draft_ids.length+' drafts. Verify show details before approval.')}catch(error){toast(error.message,true)}return}if(btn.dataset.scanMarket){const city=prompt('City where the gig takes place:');if(!city || !city.trim())return;try{const path='/bands/'+state.band+'/gigs/'+state.studioGig+'/market/discover?city='+encodeURIComponent(city.trim());const data=await api(path,{method:'POST'});await refreshStudio();toast(data.status==='cached'?'Recent research already available':'Imported '+data.added+' sourced events')}catch(err){toast(err.message,true)}return}if(btn.dataset.studioGig){await openStudioGig(btn.dataset.studioGig);return}if(btn.dataset.approveDraft){if(!confirm('Approve this draft? Approval does not publish anything.'))return;try{await api('/bands/'+state.band+'/gigs/'+state.studioGig+'/campaign/'+btn.dataset.approveDraft+'/approve',{method:'POST',body:JSON.stringify({note:'Manual review'})});await refreshStudio();toast('Approved, not published')}catch(x){toast(x.message,true)}return}if(btn.dataset.booking){const id=Number(btn.dataset.booking);try{const lead=get('bookings').find(x=>x.id===id);const activities=await api('/bands/'+state.band+'/bookings/'+id+'/activity');const lines=activities.map(a=>a.happened_at+' | '+a.kind+' | '+a.detail).join('\\n');const choice=prompt(lead.venue+' booking\\n'+(lines||'No activity')+'\\n\\nChoose: N = note, S = change stage, or Cancel');if(choice?.toUpperCase()==='N'){const detail=prompt('Contact note / communication summary');if(detail?.trim())await api('/bands/'+state.band+'/bookings/'+id+'/activity',{method:'POST',body:JSON.stringify({kind:'Note',detail:detail.trim()})});}else if(choice?.toUpperCase()==='S'){const stage=prompt('Stage: Researching, To Contact, Contacted, Follow Up, Negotiating, Hold, Confirmed, Declined, Closed',lead.stage);if(stage && stage!==lead.stage){const detail=prompt('Reason for status change / agreed next action');if(detail?.trim())await api('/bands/'+state.band+'/bookings/'+id+'/stage',{method:'POST',body:JSON.stringify({stage,detail:detail.trim()})});}}await load();}catch(x){toast(x.message,true)}return}if(btn.dataset.export){const headers=['ID','Date','Type','Description','Category','Event','Member','Amount USD','Reversal of'];const quote=v=>'"'+String(v??'').replace(/"/g,'""')+'"';const rows=get('transactions').map(t=>[t.id,t.date,t.kind,t.description,t.category,t.event_title,t.member_name,((['income','contribution'].includes(t.kind)?1:-1)*t.amount_cents/100).toFixed(2),t.reversal_of]);const csv=[headers,...rows].map(row=>row.map(quote).join(',')).join('\r\n');const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='backline-ledger-'+today()+'.csv';a.click();URL.revokeObjectURL(url)}if(btn.dataset.tourCrewGig){state.opsGig=Number(btn.dataset.tourCrewGig);state.opsTab='guests';state.section='operations';await refreshOperations();return}if(btn.dataset.tourTab){state.tourTab=btn.dataset.tourTab;render();return}if(btn.dataset.go){state.section=btn.dataset.go;if(state.section==='operations'){await refreshOperations()}else if(state.section==='media'){await refreshMedia()}else if(state.section==='collaboration'){await refreshCollaboration()}else if(state.section==='notifications'){await refreshNotifications()}else if(state.section==='calendars'||state.section==='schedule'){await refreshCalendar(state.calendarAll||false)}else if(state.section==='touring'){if(!state.selectedTour){const tours=await api('/bands/'+state.band+'/tours');state.selectedTour=tours[0]?.id}await refreshTours()}else if(state.section==='showops'){const gigs=get('events').filter(g=>g.kind==='Gig');if(!state.showGig&&gigs.length){await openShowPacketGig(gigs[0].id)}else render()}else render()}if(btn.dataset.action){state.modal=btn.dataset.action==='close'?null:btn.dataset.action;render()}if(btn.dataset.reverse){if(!confirm('Create an offsetting correction for this transaction? The original record will be kept.'))return;try{await api(`/bands/${state.band}/transactions/${btn.dataset.reverse}/reverse`,{method:'POST'});toast('Correction recorded');await load()}catch(x){toast(x.message,true)}}});
document.addEventListener('submit',async e=>{if(e.target.id!=='entryForm')return;e.preventDefault();let type=state.modal;let data=Object.fromEntries(new FormData(e.target));let fd=new FormData(e.target);if(type==='setlist')data.song_ids=fd.getAll('song_ids').map(Number);if(type==='settlement')data.member_ids=fd.getAll('member_ids').map(Number);for(let k of ['event_id','member_id'])if(k in data)data[k]=data[k]?Number(data[k]):null;if(type==='song'){data.bpm=data.bpm?Number(data.bpm):null;data.duration_seconds=Number(data.duration_seconds||0)}if(type==='settlement')data.reserve_percent=Number(data.reserve_percent);let b=`/bands/${state.band}`;const urls={issueRecovery:b+'/account-recovery',invitation:b+'/invitations',joinband:'/auth/accept-existing-invite',band:'/bands',market:b+'/gigs/'+state.studioGig+'/market',campaign:b+'/gigs/'+state.studioGig+'/campaign',booking:b+'/bookings',member:b+'/members',event:b+'/events',song:b+'/songs',transaction:b+'/transactions',setlist:b+'/setlists',settlement:b+`/events/${data.event_id}/settle`};if(type==='settlement')delete data.event_id;if(type==='booking'){if(!data.target_date)data.target_date=null;if(!data.next_followup)data.next_followup=null;}try{let response=await api(urls[type],{method:'POST',body:JSON.stringify(data)});state.modal=null;if(type==='band'||type==='joinband')state.band=response.band_id||response.id;if(type==='issueRecovery'){const box=document.createElement('div');box.className='modalWrap';box.id='recoveryResult';box.innerHTML='<div class="modal"><h2>Recovery code issued</h2><p class="sub">Verify the intended member, then deliver this one-time code securely. It expires after 30 minutes.</p><textarea readonly id="recoveryIssuedToken" aria-label="Recovery code"></textarea><div class="actions"><button id="copyRecovery" type="button">Copy code</button><button id="closeRecovery" type="button">Close</button></div></div>';document.body.append(box);document.querySelector('#recoveryIssuedToken').value=response.recovery_token;document.querySelector('#copyRecovery').onclick=()=>navigator.clipboard.writeText(response.recovery_token).then(()=>toast('Code copied')).catch(()=>toast('Copy the code manually',true));document.querySelector('#closeRecovery').onclick=()=>box.remove()}
if(type==='invitation'){const box=document.createElement('div');box.className='modalWrap';box.id='inviteResult';box.innerHTML='<div class="modal"><h2>Invitation created</h2><p class="sub">Copy this secret token and deliver it securely to the invited user. It expires in seven days.</p><textarea readonly id="invitationToken" aria-label="Invitation token"></textarea><div class="actions"><button id="copyInvite" type="button">Copy token</button><button id="closeInvite" type="button">Close</button></div></div>';document.body.append(box);document.querySelector('#invitationToken').value=response.invite_token;document.querySelector('#copyInvite').onclick=()=>navigator.clipboard.writeText(response.invite_token).then(()=>toast('Token copied')).catch(()=>toast('Select and copy the token manually',true));document.querySelector('#closeInvite').onclick=()=>box.remove()}toast(type==='invitation'?'Invitation created':'Saved successfully');await load();if(type==='campaign'||type==='market')await refreshStudio()}catch(x){toast(x.message,true)}});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>load(),{once:true});else load();

document.addEventListener('keydown',event=>{const tab=event.target.closest('[role="tab"]');if(!tab?.hasAttribute('data-show-tab')||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();const tabs=[...tab.parentElement.querySelectorAll('[role="tab"]')],index=tabs.indexOf(tab);const next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(index+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;const key=tabs[next].dataset.showTab;tabs[next].click();document.querySelector('[data-show-tab="'+key+'"]')?.focus()});
