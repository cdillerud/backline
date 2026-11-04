/* Gig Day: a mobile-first, musician-facing read of existing band-scoped show records.
 * This creates no new show entities and never exposes unrelated guests/room occupants. */
function gigday(){
 const gigs=get('events').filter(e=>e.kind==='Gig').slice().sort((a,b)=>(a.date||'').localeCompare(b.date||''));
 const chosen=gigs.find(e=>Number(e.id)===Number(state.showGig));
 if(!chosen)return '<section class="panel"><h2>Choose a show</h2><p class="sub">Open a scheduled show to see its calls, music, personal work and travel information.</p><button data-go="schedule">Open schedule</button></section>';
 const advance=state.data.showAdvance||{},role=state.data.collaboration?.role;
 const validZone=advance.timezone||'Time zone not recorded';
 const calls=[['Load-in','load_in'],['Soundcheck','soundcheck'],['Doors','doors'],['Showtime','show_time'],['Curfew','curfew']];
 const callCards=calls.map(([label,key])=>{
  const value=advance[key],day=Number(advance.day_offsets?.[key]||0);
  return '<div class="gigdayCall"><span>'+label+'</span><strong>'+esc(value||'TBD')+'</strong>'+
   (value?'<small>'+(day?'Day +'+day:'Show date')+'</small>':'<small>Not recorded</small>')+'</div>';
 }).join('');
 const userId=state.data.collaboration?.user_id;
 const link=(state.data.collaboration?.members||[]).find(m=>userId!=null&&Number(m.id)===Number(userId));
 const rosterId=link?.member_id;
 const assigned=rosterId!=null?get('tasks').filter(t=>!t.completed&&Number(t.event_id)===Number(chosen.id)&&Number(t.assignee_id)===Number(rosterId)):[];
 const setlists=get('setlists').filter(s=>Number(s.event_id)===Number(chosen.id));
 const lodging=state.data.showLodging;
 const stays=(lodging?.items||[]).filter(s=>!s.cancelled&&Number(s.event_id)===Number(chosen.id));
 const rooms=stays.flatMap(stay=>(stay.rooms||[]).filter(room=>
  !lodging?.can_manage||(room.people||[]).some(person=>Number(person.id)===Number(userId))
 ).map(room=>({hotel:stay.hotel||'Hotel not recorded',label:room.label||'Room assigned',checkIn:stay.check_in})));
 const selected='<label class="gigdayPicker">Selected show<select id="gigdayShowPicker" aria-label="Choose gig day show">'+
  gigs.map(e=>'<option value="'+Number(e.id)+'" '+(e.id===chosen.id?'selected':'')+'>'+esc(datePretty(e.date)+' · '+e.title)+'</option>').join('')+'</select></label>';
 const venue=advance.venue_address||chosen.venue||'Venue location not recorded';
 const contact=advance.production_contact||advance.venue_contact||'Contact not recorded';
 const phone=String(advance.contact_phone||'').trim();
 const phoneDigits=phone.replace(/[^+0-9]/g,'');
 const contactActions=(phoneDigits.length>=7?'<a class="gigdayLink" href="tel:'+esc(phoneDigits)+'">Call venue contact</a>':'')+
  (String(advance.contact_email||'').includes('@')?'<a class="gigdayLink" href="mailto:'+encodeURIComponent(advance.contact_email)+'">Email venue contact</a>':'');
 const tasks=assigned.length?'<ul class="gigdayTaskList">'+assigned.slice(0,5).map(t=>'<li>'+esc(t.title)+(t.due_date?' <small>Due '+datePretty(t.due_date)+'</small>':'')+'</li>').join('')+'</ul>':
  '<p class="sub">'+(rosterId==null?'Your band account is not yet linked to a roster member.':'No open tasks assigned to you for this show.')+'</p>';
 const repertoire=setlists.length?'<div class="gigdaySetlists">'+setlists.map(s=>{
  const songs=Array.isArray(s.songs)?s.songs:[];
  return '<div class="gigdaySetlist"><div class="entry"><strong>'+esc(s.title)+'</strong><button class="small" data-gigday-perform="'+Number(s.id)+'">Performance view</button></div>'+
   (songs.length?'<ol class="gigdaySongs">'+songs.slice(0,20).map(song=>'<li>'+esc(song.title||'Untitled song')+
    (song.song_key?' <small>· '+esc(song.song_key)+'</small>':'')+'</li>').join('')+'</ol>':'<p class="sub">No songs on this setlist yet.</p>')+
   (songs.length>20?'<p class="sub">+'+(songs.length-20)+' more songs in performance view</p>':'')+'</div>';
 }).join('')+'</div>':
  '<p class="sub">No setlists are linked to this show yet.</p>';
 const hotel=rooms.length?rooms.map(r=>'<div class="entry"><div><strong>'+esc(r.hotel)+'</strong><p class="sub">'+esc(r.label)+
  (r.checkIn?' · Check-in '+esc(String(r.checkIn).slice(0,10)):'')+'</p></div></div>').join(''):
  '<p class="sub">No personal hotel room linked to this show.</p>';
 const alerts=state.data.showAlerts;
 const pending=Array.isArray(alerts)?alerts.filter(a=>!a.acknowledged_at):[];
 const alertPanel='<section class="gigdayPanel gigdayAlerts" aria-label="Urgent show changes"><div class="gigdayPanelTitle"><h3>Urgent show changes</h3>'+
  '<span class="tag muted">'+(Array.isArray(alerts)?pending.length+' awaiting acknowledgement':'Status unavailable')+'</span></div>'+
  (pending.length?'<div class="list">'+pending.slice(0,8).map(a=>'<div class="entry"><div class="entryMain"><strong>'+esc(a.title)+'</strong></div>'+
   '<button type="button" class="small" data-gigday-ack="'+Number(a.id)+'">Acknowledge</button></div>').join('')+'</div>':
   '<p class="sub">'+(Array.isArray(alerts)?'No unacknowledged urgent changes for this show.':'Urgent changes could not be checked.')+'</p>')+
  '<p class="sub" role="status" id="gigdayAlertStatus"></p></section>';
 const manager=['owner','manager'].includes(role);
 return '<section class="gigdayScreen" aria-label="Musician gig-day workspace"><div class="gigdayHero"><div><span class="eyebrow">SHOW DAY · MY BACKLINE</span><h2>'+esc(chosen.title)+'</h2>'+
  '<p>'+datePretty(chosen.date)+' · '+esc(chosen.venue||'Venue TBD')+'</p>'+
  '<span class="tag muted">'+(advance.status==='confirmed'?'Venue advance confirmed':'Advance not confirmed')+'</span></div>'+
  selected+'</div>'+
  '<div class="gigdayActionBar" aria-label="Gig-day quick actions"><button class="primary" data-gigday-rsvp>My RSVP</button>'+
  '<button data-gigday-setlists>Setlist</button><button data-gigday-tasks>My tasks</button>'+
  '<button data-gigday-updates>Notifications</button><button data-gigday-refresh aria-label="Refresh gig-day details">Refresh</button></div>'+
  '<section class="gigdayPanel gigdayCallsPanel" aria-label="Show-day call times"><div class="gigdayPanelTitle"><h3>Where to be, and when</h3><span class="sub">'+esc(validZone)+'</span></div>'+
  '<div class="gigdayCallGrid">'+callCards+'</div><p class="sub">Times are venue-local. “Day +1/+2” means after the show date. TBD is not a confirmed call.</p></section>'+
  alertPanel+'<div class="gigdayColumns"><section class="gigdayPanel" aria-label="Venue and contact"><h3>Venue & contact</h3><p><strong>'+esc(venue)+'</strong></p><p>'+esc(contact)+'</p>'+
  '<p class="sub">'+esc(advance.parking||'Parking and access not recorded')+'</p><div class="gigdayContactActions">'+contactActions+'</div></section>'+
  '<section class="gigdayPanel" aria-label="My show tasks"><div class="gigdayPanelTitle"><h3>My assignments</h3><span class="tag muted">'+assigned.length+' open</span></div>'+
  tasks+'<button class="small" data-gigday-tasks>Show task list</button></section>'+
  '<section class="gigdayPanel" aria-label="Show music"><h3>Show music</h3>'+repertoire+
  '<button class="small" data-gigday-setlists>Manage show setlists</button></section>'+
  '<section class="gigdayPanel" aria-label="Personal lodging"><h3>My lodging</h3>'+hotel+'</section></div>'+
  '<div class="gigdayFooterActions"><button data-gigday-production>Detailed production</button>'+
  (manager?'<button data-gigday-crew>Crew & guests</button>':'')+
  '<button data-gigday-schedule>Back to schedule</button></div></section>';
}
document.addEventListener('change',async event=>{
 if(event.target.id!=='gigdayShowPicker')return;
 await openShowPacketGig(Number(event.target.value),'gigday');
});
document.addEventListener('click',async event=>{
 const button=event.target.closest('[data-gigday-rsvp],[data-gigday-setlists],[data-gigday-tasks],[data-gigday-updates],[data-gigday-refresh],[data-gigday-perform],[data-gigday-production],[data-gigday-crew],[data-gigday-schedule],[data-gigday-ack]');
 if(!button)return;
 event.preventDefault();
 const gig=Number(state.showGig),band=state.band;
 try{
  if(button.hasAttribute('data-gigday-ack')){
   const id=Number(button.dataset.gigdayAck);
   if(!Number.isSafeInteger(id)||id<=0)return;
   button.disabled=true;
   try{
    await api('/me/operations-alerts/'+id+'/acknowledge',{method:'POST'});
    if(state.band===band&&Number(state.showGig)===gig){await openShowPacketGig(gig,'gigday');toast('Urgent change acknowledged')}
   }catch(error){if(button.isConnected){button.disabled=false;document.querySelector('#gigdayAlertStatus').textContent=error.message}}
   return;
  }
  if(button.hasAttribute('data-gigday-refresh')){await openShowPacketGig(gig,'gigday');return}
  if(button.hasAttribute('data-gigday-rsvp')){
   state.section='schedule';await refreshCalendar(state.calendarAll||false);
   if(state.band!==band)return;
   openCalendarEventDialog(gig);await openEventAttendance(gig);return;
  }
  if(button.hasAttribute('data-gigday-perform')){openSetlistPerformance(Number(button.dataset.gigdayPerform));return}
  if(button.hasAttribute('data-gigday-setlists')){state.musicGig=gig;state.section='setlists';render();return}
  if(button.hasAttribute('data-gigday-tasks')){state.prepGig=gig;state.section='tasks';render();return}
  if(button.hasAttribute('data-gigday-updates')){state.section='notifications';await refreshNotifications();return}
  if(button.hasAttribute('data-gigday-production')){await openShowPacketGig(gig,'showops');return}
  if(button.hasAttribute('data-gigday-crew')){
   if(!['owner','manager'].includes(state.data.collaboration?.role))return;
   state.opsGig=gig;state.opsTab='guests';state.section='operations';await refreshOperations();return;
  }
  if(button.hasAttribute('data-gigday-schedule')){state.section='schedule';await refreshCalendar(state.calendarAll||false);return}
 }catch(error){toast(error.message,true)}
});
