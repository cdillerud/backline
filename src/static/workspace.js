/* Private venue, checklist and repertoire workflows. Existing account rules apply. */
nav.splice(6,0,['venues','⌂','Venue Book'],['tasks','☑','Tasks']);
const workspaceBase=()=>'/bands/'+state.band;
const wsInput=(name,label,value='',type='text',required=false,max=200)=>'<label>'+label+'<input name="'+name+'" type="'+type+'" value="'+esc(value)+'" maxlength="'+max+'" '+(required?'required':'')+'></label>';
const wsSelect=(name,label,items,value='')=>'<label>'+label+'<select aria-label="'+esc(label)+'" name="'+name+'">'+items.map(([id,text])=>'<option value="'+esc(id)+'" '+(String(id)===String(value)?'selected':'')+'>'+esc(text)+'</option>').join('')+'</select></label>';
function workspaceDialog(title,content,save){
 const modal=document.createElement('dialog');modal.className='timelineDialog';modal.setAttribute('aria-label',title);
 modal.innerHTML='<form><h2>'+esc(title)+'</h2>'+content+'<p class="workspaceError" role="alert"></p><div class="actions"><button type="button" data-cancel-workspace>Cancel</button><button class="primary" type="submit">Save</button></div></form>';
 document.body.append(modal);modal.addEventListener('close',()=>modal.remove());modal.querySelector('[data-cancel-workspace]').onclick=()=>modal.close();
 modal.querySelector('form').onsubmit=async event=>{event.preventDefault();const button=event.submitter;button.disabled=true;try{await save(Object.fromEntries(new FormData(event.target)),modal);modal.close();await load();toast('Saved successfully')}catch(error){modal.querySelector('.workspaceError').textContent=error.message;button.disabled=false}};
 modal.showModal();return modal;
}
function privateVenueBook(){
 const venues=get('venues');return panel('Private venue book','<p class="sub">Keep promoter and engineer contacts, access notes and curfews with the band. Link records to shows from Advances & riders.</p><button data-new-venue>+ Add venue</button><div class="list">'+venues.slice().sort((a,b)=>Number(b.favourite)-Number(a.favourite)||a.name.localeCompare(b.name)).map(v=>'<div class="entry"><div><strong>'+(v.favourite?'★ ':'')+esc(v.name)+'</strong><p>'+esc(v.address)+'</p><p>'+v.tags.map(esc).join(' · ')+'</p><p>'+(v.contacts||[]).map(c=>esc([c.name,c.role,c.email,c.phone].filter(Boolean).join(' · '))).join('<br>')+'</p><p>Load-in: '+esc(v.load_in_notes)+'</p><p>Curfew: '+esc(v.curfew_notes)+'</p><button data-edit-venue="'+v.id+'">Edit venue</button> <button data-share-venue="'+v.id+'">Manage venue sharing</button></div></div>').join('')+'</div>');
}
function editVenue(v={}){
 const contacts=JSON.parse(JSON.stringify(v.contacts||[]));
 const modal=workspaceDialog(v.id?'Edit venue':'Add venue','<div class="advanceGrid">'+wsInput('name','Venue name',v.name,'text',true,150)+wsInput('address','Address',v.address,'text',false,500)+wsInput('tags','Tags (comma separated)',(v.tags||[]).join(', '))+wsSelect('favourite','Favourite',[['0','No'],['1','Yes']],v.favourite?'1':'0')+wsInput('load_in_notes','Load-in and access notes',v.load_in_notes,'text',false,2000)+wsInput('curfew_notes','Curfew notes',v.curfew_notes,'text',false,1000)+'</div><h3>Venue contacts</h3><div id="venueContacts"></div><button type="button" id="addVenueContact">+ Contact</button>',async data=>{
  data.contacts=contacts;data.tags=data.tags.split(',').map(t=>t.trim()).filter(Boolean);data.favourite=data.favourite==='1';
  await api(workspaceBase()+'/venues'+(v.id?'/'+v.id:''),{method:v.id?'PUT':'POST',body:JSON.stringify(data)});
 });
 const draw=()=>{const list=modal.querySelector('#venueContacts');list.replaceChildren();contacts.forEach((contact,index)=>{const row=document.createElement('fieldset');row.innerHTML='<legend>Contact '+(index+1)+'</legend>';for(const [key,label,max] of [['name','Contact name',120],['role','Contact role',100],['email','Contact email',200],['phone','Contact phone',80]]){const wrap=document.createElement('label');wrap.textContent=label;const input=document.createElement('input');input.setAttribute('aria-label',label+' '+(index+1));input.value=contact[key]||'';input.maxLength=max;input.required=key==='name';input.type=key==='email'?'email':key==='phone'?'tel':'text';input.oninput=()=>contact[key]=input.value;wrap.append(input);row.append(wrap)}const remove=document.createElement('button');remove.type='button';remove.textContent='Remove contact '+(index+1);remove.onclick=()=>{contacts.splice(index,1);draw()};row.append(remove);list.append(row)})};
 modal.querySelector('#addVenueContact').onclick=()=>{if(contacts.length>=30)return;contacts.push({name:'',role:'',email:'',phone:''});draw();modal.querySelector('#venueContacts fieldset:last-child input').focus()};draw();
}
function sharedVenueCards(){return panel('Venues shared with this band',get('shared-venues').length?get('shared-venues').map(v=>'<div class="entry"><div><strong>'+esc(v.name)+'</strong><p>'+esc(v.address||'')+'</p><p>'+(v.contacts||[]).map(c=>esc(Object.values(c).filter(Boolean).join(' · '))).join('<br>')+'</p><p>'+esc(v.load_in_notes||'')+'</p><p>'+esc(v.curfew_notes||'')+'</p><small>Only the fields selected by the source band are visible. Link this venue on a show’s advance.</small></div></div>').join(''):empty('No active venue shares.'))}
function taskBoard(){
 return panel('Band task checklists','<p class="sub">Assign work to band members and link it to shows, songs or sets. Due-tomorrow reminders appear here; outbound email is not enabled.</p><button data-new-task>+ Add task</button><div class="list">'+get('tasks').map(t=>{
  const member=get('members').find(m=>m.id===t.assignee_id),event=get('events').find(e=>e.id===t.event_id),song=get('songs').find(s=>s.id===t.song_id),set=get('setlists').find(s=>s.id===t.setlist_id);
  return '<div class="entry"><div><strong>'+esc(t.title)+'</strong> <span class="tag">'+esc(t.reminder.replaceAll('_',' ')||'Open')+'</span><p>'+esc(member?.name||'Unassigned')+' · '+esc(t.due_date||'No due date')+'</p><p>'+esc([event?.title,song?.title,set?.title].filter(Boolean).join(' · '))+'</p><p>'+esc(t.notes)+'</p><button data-edit-task="'+t.id+'">Edit task</button> <button data-toggle-task="'+t.id+'">'+(t.completed?'Reopen':'Complete')+'</button></div></div>'}).join('')+'</div>');
}
function editTask(t={}){
 const options=(key)=>[['','None'],...get(key).map(x=>[x.id,x.name||x.title])];
 workspaceDialog(t.id?'Edit task':'Add task','<div class="advanceGrid">'+wsInput('title','Task title',t.title,'text',true,200)+wsInput('due_date','Due date',t.due_date,'date')+wsSelect('assignee_id','Assignee',options('members'),t.assignee_id)+wsSelect('event_id','Linked event',options('events'),t.event_id)+wsSelect('song_id','Linked song',options('songs'),t.song_id)+wsSelect('setlist_id','Linked setlist',options('setlists'),t.setlist_id)+wsInput('notes','Task notes',t.notes,'text',false,3000)+'</div>',async data=>{for(const key of ['assignee_id','event_id','song_id','setlist_id'])data[key]=data[key]?Number(data[key]):null;data.due_date=data.due_date||null;data.completed=t.completed||false;await api(workspaceBase()+'/tasks'+(t.id?'/'+t.id:''),{method:t.id?'PUT':'POST',body:JSON.stringify(data)})});
}
function repertoireLibrary(){
 return panel('Song library','<p class="sub">Musical cues, tags and a shared reference recording for each arrangement.</p><button data-action="song">+ Add song</button><div class="list">'+get('songs').map(s=>{const details=get('song-details').find(d=>d.song_id===s.id)||{};return '<div class="entry"><div><strong>'+esc(s.title)+'</strong>'+(get('recordings').find(r=>r.song_id===s.id)?'<button data-play-recording="'+get('recordings').find(r=>r.song_id===s.id).media_id+'">Play reference recording</button>':'')+'<p>'+esc(s.artist)+' · '+esc(s.song_key||'Key TBC')+' · '+(s.bpm||'Tempo TBC')+' BPM · '+Math.floor(s.duration_seconds/60)+':'+String(s.duration_seconds%60).padStart(2,'0')+'</p><p>'+esc((details.tags||[]).join(' · '))+'</p>'+(details.reference_url?'<a href="'+esc(details.reference_url)+'" target="_blank" rel="noopener noreferrer">Reference recording</a> ':'')+'<button data-edit-song="'+s.id+'">Edit song</button></div></div>'}).join('')+'</div>');
}
function editRepertoire(s){
 const details=get('song-details').find(d=>d.song_id===s.id)||{};
 workspaceDialog('Edit song','<div class="advanceGrid">'+wsInput('title','Song title',s.title,'text',true,180)+wsInput('artist','Original artist',s.artist)+wsInput('song_key','Musical key',s.song_key)+wsInput('bpm','Tempo BPM',s.bpm||'','number')+wsInput('duration_seconds','Duration in seconds',s.duration_seconds,'number')+wsInput('tags','Song tags (comma separated)',(details.tags||[]).join(', '))+wsInput('reference_url','Reference recording HTTPS URL',details.reference_url,'url',false,1500)+wsInput('status','Readiness',s.status)+wsInput('notes','Arrangement notes',s.notes,'text',false,5000)+'</div>',async data=>{data.bpm=data.bpm?Number(data.bpm):null;data.duration_seconds=Number(data.duration_seconds);data.tags=data.tags.split(',').map(v=>v.trim()).filter(Boolean);await api(workspaceBase()+'/songs/'+s.id,{method:'PUT',body:JSON.stringify(data)})});
}
const runtime=songs=>{const seconds=songs.reduce((n,s)=>n+s.duration_seconds,0);return Math.floor(seconds/60)+':'+String(seconds%60).padStart(2,'0')};
function setlistLibrary(){
 return panel('Setlist studio','<p class="sub">Build a running order with musical cues and measured duration. Breaks and transitions are additional.</p><button data-new-setlist>+ Create setlist</button>'+get('setlists').map(s=>'<div class="panel"><h3>'+esc(s.title)+'</h3><p>'+s.songs.length+' songs · Runtime '+runtime(s.songs)+'</p><ol>'+s.songs.map(song=>'<li>'+esc(song.title)+' · '+esc(song.song_key)+' · '+(song.bpm||'—')+' BPM</li>').join('')+'</ol><button data-build-setlist="'+s.id+'">Edit running order</button> <button data-setlist-pdf="'+s.id+'">Download setlist PDF</button></div>').join(''));
}
function openSetlistBuilder(s={}){
 const order=(s.songs||[]).map(song=>song.id);
 const modal=workspaceDialog(s.id?'Edit setlist':'Create setlist',wsInput('title','Setlist title',s.title,'text',true,160)+wsSelect('event_id','Linked show',[['','None'],...get('events').filter(e=>e.kind==='Gig').map(e=>[e.id,e.title])],s.event_id)+
 '<div class="actions"><select id="setlistSongPicker" aria-label="Song to add">'+get('songs').map(song=>'<option value="'+song.id+'">'+esc(song.title)+'</option>').join('')+'</select><button type="button" id="appendSetlistSong">+ Add song</button></div><p id="setlistRuntime" role="status"></p><ol id="setlistOrder"></ol>',async data=>{
  data.event_id=data.event_id?Number(data.event_id):null;data.song_ids=order;
  await api(workspaceBase()+'/setlists'+(s.id?'/'+s.id:''),{method:s.id?'PUT':'POST',body:JSON.stringify(data)});
 });
 const move=(from,to)=>{if(to<0||to>=order.length)return;const [id]=order.splice(from,1);order.splice(to,0,id);draw()};
 const draw=()=>{const list=modal.querySelector('#setlistOrder');list.replaceChildren();const songs=order.map(id=>get('songs').find(song=>song.id===id));modal.querySelector('#setlistRuntime').textContent='Runtime '+runtime(songs)+' · '+songs.length+' songs'+(songs.some(song=>!song.duration_seconds)?' · Some durations are missing':'');songs.forEach((song,index)=>{const row=document.createElement('li');row.draggable=true;row.className='setlistOrderRow';const name=document.createElement('span');name.textContent=song.title+' · '+(song.song_key||'Key TBC')+' · '+(song.bpm||'—')+' BPM';row.append(name);row.ondragstart=event=>event.dataTransfer.setData('text/plain',String(index));row.ondragover=event=>event.preventDefault();row.ondrop=event=>{event.preventDefault();const from=Number(event.dataTransfer.getData('text/plain'));if(Number.isInteger(from)&&from>=0&&from<order.length)move(from,index)};for(const [label,delta] of [['Move song up',-1],['Move song down',1]]){const button=document.createElement('button');button.type='button';button.textContent=delta<0?'↑':'↓';button.setAttribute('aria-label',label+' '+(index+1));button.disabled=index+delta<0||index+delta>=order.length;button.onclick=()=>{move(index,index+delta);modal.querySelectorAll('.setlistOrderRow')[index+delta]?.querySelector('button')?.focus()};row.append(button)}const remove=document.createElement('button');remove.type='button';remove.textContent='Remove';remove.setAttribute('aria-label','Remove song '+(index+1));remove.onclick=()=>{order.splice(index,1);draw()};row.append(remove);list.append(row)})};
 modal.querySelector('#appendSetlistSong').onclick=()=>{const id=Number(modal.querySelector('#setlistSongPicker').value);if(id&&order.length<200){order.push(id);draw()}};draw();
}
async function workspaceDownload(path,filename){
 const token=sessionStorage.getItem('backline_session'),response=await fetch('/api'+path,{headers:token?{Authorization:'Bearer '+token}:{}});if(!response.ok)throw Error('Download failed');const url=URL.createObjectURL(await response.blob()),link=document.createElement('a');link.href=url;link.download=filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
document.addEventListener('click',async event=>{const button=event.target.closest('[data-new-venue],[data-edit-venue],[data-new-task],[data-edit-task],[data-toggle-task],[data-edit-song],[data-new-setlist],[data-build-setlist],[data-setlist-pdf],[data-link-venue]');if(!button)return;try{
 if(button.hasAttribute('data-new-venue'))editVenue();
 if(button.dataset.editVenue)editVenue(get('venues').find(v=>String(v.id)===button.dataset.editVenue));
 if(button.hasAttribute('data-new-task'))editTask();
 if(button.dataset.editTask)editTask(get('tasks').find(t=>String(t.id)===button.dataset.editTask));
 if(button.dataset.toggleTask){const t=get('tasks').find(t=>String(t.id)===button.dataset.toggleTask);await api(workspaceBase()+'/tasks/'+t.id,{method:'PUT',body:JSON.stringify({...t,completed:!t.completed})});await load()}
 if(button.dataset.editSong)editRepertoire(get('songs').find(s=>String(s.id)===button.dataset.editSong));
 if(button.hasAttribute('data-new-setlist'))openSetlistBuilder();
 if(button.dataset.buildSetlist)openSetlistBuilder(get('setlists').find(s=>String(s.id)===button.dataset.buildSetlist));
 if(button.dataset.setlistPdf)await workspaceDownload(workspaceBase()+'/setlists/'+button.dataset.setlistPdf+'/pdf','backline-setlist.pdf');
 if(button.hasAttribute('data-link-venue')){const value=document.querySelector('#showVenueLink').value,shared=value.startsWith('shared:');const venue_id=Number(shared?value.slice(7):value);if(!venue_id)throw Error('Choose a venue first');await api(workspaceBase()+'/events/'+state.showGig+(shared?'/shared-venue':'/venue'),{method:'PUT',body:JSON.stringify(shared?{share_id:venue_id}:{venue_id})});await openShowPacketGig(state.showGig);toast('Venue linked to show')}
 }catch(error){toast(error.message,true)}});
function venueLinkPanel(){
 const v=state.data.showVenue;
 return panel('Linked venue book record','<p class="sub">Directory details stay linked to the show. Review and confirm show-specific arrangements below.</p><label>Venue<select id="showVenueLink"><option value="">Select venue</option>'+get('shared-venues').map(venue=>'<option value="shared:'+venue.share_id+'">'+esc(venue.name)+' (shared)</option>').join('')+get('venues').map(venue=>'<option value="'+venue.id+'" '+(venue.id===v?.id?'selected':'')+'>'+esc(venue.name)+'</option>').join('')+'</select></label> <button data-link-venue>Link venue to show</button>'+(v?'<h3>'+esc(v.name)+'</h3><p>'+esc(v.address)+'</p><p>'+(v.contacts||[]).map(c=>esc([c.name,c.role,c.email,c.phone].filter(Boolean).join(' · '))).join('<br>')+'</p><p>'+esc(v.load_in_notes)+'</p><p>'+esc(v.curfew_notes)+'</p>':''));
}
// Schedule exposes the same named calendars without duplicate navigation.
async function refreshCalendar(all=false){
 const bands=all?state.bands:state.bands.filter(b=>b.id===state.band);
 const results=await Promise.all(bands.map(async band=>{const events=await api('/bands/'+band.id+'/calendar/events');return events.map(event=>({...event,band_name:band.name}))}));
 state.data.calendarEvents=results.flat().sort((a,b)=>a.date.localeCompare(b.date)||a.time.localeCompare(b.time));state.data.bandCalendars=await api(workspaceBase()+'/calendars');state.calendarAll=all;render();
}
function scheduleBoard(){
 const head='<div class="toolbar"><p>Shows, rehearsals, meetings, and sessions all live on this calendar. Select an entry for details.</p><button class="primary" data-action="event">+ Add event</button></div>';
 return head+calendarBoard();
}
function openCalendarEventDialog(id){
 const item=get('events').find(e=>e.id===id);
 if(!item)return;
 document.querySelector('#calendarEventDialog')?.close();
 const calendar=(state.data.calendarEvents||[]).find(e=>e.id===id&&e.band_id===state.band);
 const kind=item.kind||'Event';
 const modal=document.createElement('dialog');
 modal.id='calendarEventDialog';
 modal.className='timelineDialog calendarEventDialog';
 modal.setAttribute('aria-label','Event details: '+item.title);
 const action=(name,label)=>'<button type="button" '+name+'="'+id+'">'+label+'</button>';
 const extras=kind==='Gig'?action('data-schedule-packet','Show production'):
  kind==='Rehearsal'?action('data-rehearsal-plan','Objectives & notes')+
   '<button type="button" data-go="songs">Songs to practice</button>'+
   '<button type="button" data-go="setlists">Rehearsal repertoire</button>'+
   '<button type="button" data-go="tasks">Preparation tasks</button>':
   '<button type="button" data-go="tasks">Preparation tasks</button>';
 modal.innerHTML='<header class="calendarDialogHeader"><div><span class="tag muted">'+esc(kind)+'</span><h2>'+esc(item.title)+'</h2></div><button type="button" data-schedule-close aria-label="Close event details">×</button></header>'+
  '<dl class="calendarEventFacts"><div><dt>Date</dt><dd>'+datePretty(item.date)+'</dd></div>'+
  '<div><dt>Time</dt><dd>'+esc(item.time||'Time TBD')+'</dd></div>'+
  '<div><dt>Location</dt><dd>'+esc(item.venue||'Location TBD')+'</dd></div>'+
  '<div><dt>Status</dt><dd>'+esc(item.status||'Planned')+'</dd></div>'+
  (calendar?'<div><dt>Calendar</dt><dd>'+esc(calendar.calendar_name||kind)+'</dd></div>':'')+'</dl>'+
  (item.notes?'<section class="calendarEventNotes"><h3>Notes</h3><p>'+esc(item.notes)+'</p></section>':'')+
  '<div class="actions calendarDialogActions">'+action('data-schedule-edit','Edit event')+
  action('data-schedule-move','Change date')+action('data-assign-calendar','Choose calendar')+
  action('data-schedule-rsvp','Availability & RSVPs')+extras+'</div>';
 document.body.append(modal);
 const origin=document.activeElement;
 modal.addEventListener('close',()=>{
  modal.remove();
  const entry=document.querySelector('[data-calendar-event="'+id+'"]');
  if(entry)entry.focus();
  else if(origin?.isConnected)origin.focus();
 },{once:true});
 modal.addEventListener('click',event=>{
  if(event.target===modal||event.target.closest('[data-schedule-close]')){modal.close();return}
  if(event.target.closest('[data-schedule-edit],[data-schedule-move],[data-assign-calendar],[data-schedule-rsvp],[data-schedule-packet],[data-rehearsal-plan],[data-go]')){
   modal.close();
  }
 });
 modal.showModal();
}
async function openRehearsalPlan(id){
 const base=workspaceBase()+'/rehearsals/'+id+'/plan';
 const plan=await api(base);
 const info=state.data.collaboration;
 const permitted=['owner','manager'].includes(info?.role||state.accountRole);
 const dialog=document.createElement('dialog');
 dialog.className='timelineDialog';
 dialog.setAttribute('aria-label','Rehearsal objectives and notes');
 const safeText=v=>esc(v||'');
 dialog.innerHTML='<form><h2>Rehearsal objectives & notes</h2>'+
  '<p class="sub">Private to the band. Managers can update preparation plans.</p>'+
  '<label>Objectives<textarea name="objectives" rows="4" maxlength="4000" '+(permitted?'':'readonly')+'>'+safeText(plan.objectives)+'</textarea></label>'+
  '<label>Preparation notes<textarea name="notes" rows="5" maxlength="8000" '+(permitted?'':'readonly')+'>'+safeText(plan.notes)+'</textarea></label>'+
  '<p role="alert"></p><div class="actions"><button type="button" data-close-plan>Close</button>'+
  (permitted?'<button class="primary" type="submit">Save plan</button>':'')+'</div></form>';
 document.body.append(dialog);
 dialog.addEventListener('close',()=>dialog.remove());
 dialog.querySelector('[data-close-plan]').onclick=()=>dialog.close();
 dialog.querySelector('form').onsubmit=async event=>{
  event.preventDefault();
  if(!permitted)return;
  const button=dialog.querySelector('[type="submit"]');button.disabled=true;
  try{
   const data=Object.fromEntries(new FormData(event.target));
   await api(base,{method:'PUT',body:JSON.stringify(data)});
   dialog.close();toast('Rehearsal plan saved');
  }catch(error){dialog.querySelector('[role="alert"]').textContent=error.message;button.disabled=false}
 };
 dialog.showModal();
}
document.addEventListener('click',async event=>{
 const b=event.target.closest('[data-schedule-packet],[data-schedule-rsvp],[data-calendar-event],[data-schedule-details],[data-schedule-move],[data-schedule-edit],[data-schedule-close],[data-rehearsal-plan]');if(!b)return;
 if(b.dataset.rehearsalPlan){try{await openRehearsalPlan(Number(b.dataset.rehearsalPlan))}catch(error){toast(error.message,true)}return}
 if(b.hasAttribute('data-schedule-close')){document.querySelector('#calendarEventDialog')?.close();state.scheduleSelected=null;return}
 if(b.dataset.scheduleMove){
  const item=get('events').find(e=>e.id===Number(b.dataset.scheduleMove));
  if(item)workspaceDialog('Move '+item.title,'<label class="field">New date<input type="date" name="date" required value="'+esc(item.date)+'"></label>',async data=>{
   await api(workspaceBase()+'/events/'+item.id+'/reschedule',{method:'PUT',body:JSON.stringify({date:data.date})});
   const local=get('events').find(e=>e.id===item.id);
   if(local)local.date=data.date;
   if(state.calendarMonth!==data.date.slice(0,7))state.calendarMonth=data.date.slice(0,7);
   await refreshCalendar(state.calendarAll===true);
   openCalendarEventDialog(item.id);
  });
  return;
 }
 if(b.dataset.scheduleEdit){
  const selected=get('events').find(e=>e.id===Number(b.dataset.scheduleEdit));
  if(selected){state.eventEdit=selected.id;state.eventDraftDate=null;state.modal='event';render()}
  return;
 }
 if(b.dataset.scheduleDetails){openCalendarEventDialog(Number(b.dataset.scheduleDetails));return}
 if(b.dataset.calendarEvent){
  const id=Number(b.dataset.calendarEvent);
  state.scheduleSelected=id;openCalendarEventDialog(id);return
 }
 if(b.dataset.schedulePacket){await openShowPacketGig(Number(b.dataset.schedulePacket));return}
 if(b.dataset.scheduleRsvp){state.rsvpEvent=Number(b.dataset.scheduleRsvp);state.hubTab='availability';state.section='collaboration';await refreshCollaboration();return}
});
function calendarBoard(){
 const month=state.calendarMonth||today().slice(0,7),rows=(state.data.calendarEvents||[]).filter(event=>event.date.startsWith(month));
 const [year,m]=month.split('-').map(Number),days=new Date(year,m,0).getDate(),offset=(new Date(year,m-1,1).getDay()+6)%7;
 let cells=Array.from({length:offset},()=>'<div></div>');
 for(let day=1;day<=days;day++){const date=month+'-'+String(day).padStart(2,'0'),events=rows.filter(event=>event.date===date);cells.push('<div class="calendarDay" data-calendar-day="'+date+'" tabindex="0" role="button" aria-label="Create event on '+date+'" title="Double-click or use Add to create an event"><strong>'+day+'</strong><button type="button" class="calendarDayAdd" data-calendar-add="'+date+'" aria-label="Add event on '+date+'">+</button>'+events.map(event=>{const kind=get('events').find(e=>e.id===event.id)?.kind||event.kind||'';const type=/^(gig|show)$/i.test(kind)?'show':/^rehearsal$/i.test(kind)?'rehearsal':/^(session|meeting)$/i.test(kind)?'meeting':'other';return '<div class="calendarEvent calendarEvent--'+type+'"'+(type==='other'?' style="border-color:'+esc(event.calendar_color||'#567')+'"':'')+'>'+(event.band_id===state.band?'<button class="scheduleEventLink" data-calendar-event="'+event.id+'" draggable="true" title="Click for details or drag to reschedule" data-calendar-kind="'+esc(get('events').find(e=>e.id===event.id)?.kind||event.kind||'')+'"><strong>'+esc(event.title)+'</strong></button>':'<strong>'+esc(event.title)+'</strong>')+'<small>'+esc(event.calendar_name)+' · '+esc(event.advance.show_time||event.time||'Time TBC')+'</small>'+(state.calendarAll?'<small>'+esc(event.band_name)+'</small>':'')+'</div>'}).join('')+'</div>')}
 return panel('Band calendars','<div class="actions"><button type="button" data-calendar-month-step="-1" aria-label="Previous month">‹</button><button type="button" data-calendar-today>Today</button><button type="button" data-calendar-month-step="1" aria-label="Next month">›</button><label>Month<input id="calendarMonth" type="month" value="'+esc(month)+'"></label><button data-calendar-all>'+(state.calendarAll?'This band only':'My bands combined')+'</button><button data-new-calendar>+ Calendar</button><button data-calendar-export>Download iCal</button><button data-calendar-subscriptions>Subscriptions</button></div><p class="sub">Double-click a day to add a dated event. Use Enter on a focused day, or + Add event on touch devices.</p><div class="calendarTypeLegend" aria-label="Event colors"><span class="show"><i></i>Shows</span><span class="rehearsal"><i></i>Rehearsals</span><span class="meeting"><i></i>Meetings</span></div><div class="calendarWrap"><div class="calendarGrid">'+['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map(day=>'<strong>'+day+'</strong>').join('')+cells.join('')+'</div></div>');
}
function createEventOnCalendarDate(day){
 if(!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(day))return;
 state.eventDraftDate=day;state.modal='event';render();
}
document.addEventListener('click',event=>{
 const add=event.target.closest('[data-calendar-add]');
 if(!add)return;
 event.stopPropagation();
 createEventOnCalendarDate(add.dataset.calendarAdd);
});
document.addEventListener('dblclick',event=>{
 const day=event.target.closest('[data-calendar-day]');
 if(day&&!event.target.closest('[data-calendar-event]'))createEventOnCalendarDate(day.dataset.calendarDay);
});
let draggedCalendarEvent=null;
document.addEventListener('dragstart',event=>{
 const button=event.target.closest('[data-calendar-event]');
 if(!button)return;
 draggedCalendarEvent=Number(button.dataset.calendarEvent);
 event.dataTransfer.effectAllowed='move';
 event.dataTransfer.setData('text/plain',String(draggedCalendarEvent));
});
document.addEventListener('dragend',()=>{draggedCalendarEvent=null});
document.addEventListener('dragover',event=>{
 if(draggedCalendarEvent!==null&&event.target.closest('[data-calendar-day]')){
  event.preventDefault();event.dataTransfer.dropEffect='move';
 }
});
document.addEventListener('drop',async event=>{
 const day=event.target.closest('[data-calendar-day]');
 const id=Number(event.dataTransfer?.getData('text/plain'))||draggedCalendarEvent;
 draggedCalendarEvent=null;
 if(!day||!id)return;
 event.preventDefault();
 const item=get('events').find(e=>e.id===id),target=day.dataset.calendarDay;
 if(!item||item.date===target)return;
 if(!confirm('Move '+item.title+' from '+datePretty(item.date)+' to '+datePretty(target)+'?'))return;
 try{
  await api(workspaceBase()+'/events/'+id+'/reschedule',{method:'PUT',body:JSON.stringify({date:target})});
  // Update both cached event views immediately, then reconcile from the server.
  const local=get('events').find(e=>e.id===id);
  if(local)local.date=target;
  for(const entry of state.data.calendarEvents||[]){
   if(entry.id===id&&entry.band_id===state.band)entry.date=target;
  }
  render();
  await load();
  await refreshCalendar(state.calendarAll===true);
  toast('Event rescheduled');
 }catch(error){toast(error.message,true)}
});
document.addEventListener('keydown',event=>{
 if((event.key==='Enter'||event.key===' ')&&event.target.matches('[data-calendar-day]')){
  event.preventDefault();createEventOnCalendarDate(event.target.dataset.calendarDay);
 }
});
document.addEventListener('click',event=>{
 const step=event.target.closest('[data-calendar-month-step]'),todayButton=event.target.closest('[data-calendar-today]');
 if(!step&&!todayButton)return;
 if(todayButton)state.calendarMonth=today().slice(0,7);
 else {
  const [year,month]=(state.calendarMonth||today().slice(0,7)).split('-').map(Number);
  const date=new Date(year,month-1+Number(step.dataset.calendarMonthStep),1);
  state.calendarMonth=date.getFullYear()+'-'+String(date.getMonth()+1).padStart(2,'0');
 }
 render();
});
document.addEventListener('change',event=>{if(event.target.id==='calendarMonth'){state.calendarMonth=event.target.value;render()}});
document.addEventListener('click',async event=>{const b=event.target.closest('[data-calendar-all],[data-new-calendar],[data-calendar-export],[data-assign-calendar]');if(!b)return;try{
 if(b.hasAttribute('data-calendar-all'))await refreshCalendar(!state.calendarAll);
 if(b.hasAttribute('data-calendar-export'))await workspaceDownload(workspaceBase()+'/calendar.ics','backline-calendar.ics');
 if(b.hasAttribute('data-new-calendar'))workspaceDialog('Create calendar',wsInput('name','Calendar name','','text',true,100)+wsInput('color','Calendar colour','#b9fb74','color'),async data=>{await api(workspaceBase()+'/calendars',{method:'POST',body:JSON.stringify(data)});await refreshCalendar(state.calendarAll)});
 if(b.dataset.assignCalendar)workspaceDialog('Choose event calendar',wsSelect('calendar_id','Calendar',(state.data.bandCalendars||[]).map(c=>[c.id,c.name])),async data=>{if(!data.calendar_id)throw Error('Create a calendar first');await api(workspaceBase()+'/events/'+b.dataset.assignCalendar+'/calendar',{method:'PUT',body:JSON.stringify({calendar_id:Number(data.calendar_id)})});await refreshCalendar(state.calendarAll===true);openCalendarEventDialog(Number(b.dataset.assignCalendar))});
 }catch(error){toast(error.message,true)}});

function venueBook(){return privateVenueBook()+sharedVenueCards()}
