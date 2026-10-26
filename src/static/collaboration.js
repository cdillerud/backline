/* Session-bound collaboration. No preview impersonation and no live mail transport. */
nav.splice(3,0,['collaboration','☏','Band Hub'],['notifications','●','Notifications']);
const collabAdmin=()=>['owner','manager'].includes(state.data.collaboration?.role);
const collabWriter=()=>['owner','manager','member'].includes(state.data.collaboration?.role);
async function refreshCollaboration(){
 if(!sessionStorage.getItem('backline_session')){state.data.collaboration=null;state.data.collaborationNotice='Sign in with an individual band account to use RSVP, discussions and personal notifications.';render();return}
 try{
  const [summary,threads]=await Promise.all([api(workspaceBase()+'/collaboration'),api(workspaceBase()+'/discussions')]);
  state.data.collaboration=summary;state.data.discussions=threads;state.data.collaborationNotice='';
  if(!threads.some(t=>t.id===state.discussionThread))state.discussionThread=threads[0]?.id;
  const events=get('events');if(!events.some(e=>e.id===state.rsvpEvent))state.rsvpEvent=events[0]?.id;
  state.data.rsvps=state.rsvpEvent?await api(workspaceBase()+'/events/'+state.rsvpEvent+'/rsvps'):[];
  state.data.threadPosts=state.discussionThread?await api(workspaceBase()+'/discussions/'+state.discussionThread+'/posts'):[];
  render();renderLiveThread();
 }catch(error){state.data.collaborationNotice=error.message;render()}
}
function collaborationBoard(){
 const info=state.data.collaboration;if(!info)return panel('Band collaboration',empty(state.data.collaborationNotice||'Sign in to your band account.'));
 const event=get('events').find(e=>e.id===state.rsvpEvent),own=get('rsvps').find(r=>r.user_id===info.user_id),thread=get('discussions').find(t=>t.id===state.discussionThread);
 return panel('Availability and RSVP','<label>Event<select id="rsvpEvent" aria-label="RSVP event">'+get('events').map(e=>'<option value="'+e.id+'" '+(e.id===state.rsvpEvent?'selected':'')+'>'+esc(e.title)+' · '+esc(e.date)+'</option>').join('')+'</select></label>'+
  (event?'<div class="list">'+get('rsvps').map(r=>'<div class="entry">'+memberAvatar(r.member_id,r.display_name)+'<div><strong>'+esc(r.display_name)+'</strong><small> '+esc(r.instrument)+'</small><p>'+esc(r.note)+'</p></div><span class="tag">'+esc(r.response)+'</span></div>').join('')+'</div>'+(collabWriter()?'<form id="rsvpForm"><div class="advanceGrid">'+wsSelect('response','My RSVP',[['unknown','Not answered'],['yes','Yes'],['no','No'],['maybe','Maybe']],own?.response||'unknown')+wsInput('note','Availability note',own?.note||'','text',false,1000)+'</div><button class="primary">Save my RSVP</button></form>':'<p class="sub">Your band role can view attendance.</p>')+(collabAdmin()?'<button data-request-rsvp>Request responses</button>':''):empty('Add an event to request availability.')))+
 panel('Discussions',(collabAdmin()?'<button data-new-thread>+ New discussion</button>':'')+'<div class="list">'+get('discussions').map(t=>'<button class="threadChoice" data-thread="'+t.id+'">'+esc(t.title)+' · '+esc(t.scope)+'</button>').join('')+'</div>'+(thread?'<h3>'+esc(thread.title)+'</h3><div id="threadPosts" class="discussionPosts" aria-live="polite"></div><p id="threadTyping" role="status"></p>'+(collabWriter()?'<form id="discussionForm"><label>Reply<textarea id="discussionReply" name="body" required maxlength="5000" rows="3"></textarea></label><fieldset class="mentionPills"><legend>@mention bandmates</legend>'+info.members.filter(m=>m.id!==info.user_id).map(m=>'<label><input type="checkbox" name="mention_user_ids" value="'+m.id+'">@'+esc(m.display_name)+'</label>').join('')+'</fieldset><button class="primary">Post reply</button></form>':''):empty('A band manager can start a discussion on the band, a song or a setlist.')))+
 (collabAdmin()?panel('Link roster identities','<p class="sub">Link each roster member to the correct band account. This keeps task assignments, discussion names and RSVP instruments consistent.</p><div class="list">'+get('members').map(m=>'<div class="entry"><span>'+esc(m.name)+' · '+esc(m.instrument)+'</span><button data-link-roster="'+m.id+'">'+(info.members.some(a=>a.member_id===m.id)?'Change account link':'Link account')+'</button></div>').join('')+'</div>'):'');
}
function renderLiveThread(){
 const container=document.querySelector('#threadPosts');if(!container)return;
 const rows=get('threadPosts'),signature=JSON.stringify(rows);if(container.dataset.signature===signature)return;
 container.dataset.signature=signature;container.innerHTML=rows.length?rows.map(post=>'<article class="discussionPost">'+memberAvatar(post.member_id,post.display_name)+'<strong>'+esc(post.display_name)+'</strong><p>'+esc(post.body).replace(/\n/g,'<br>')+'</p><small>'+new Date(post.updated_at*1000).toLocaleString()+'</small>'+(post.user_id===state.data.collaboration?.user_id?'<button data-edit-reply="'+post.id+'">Edit my reply</button>':'')+'</article>').join(''):empty('No replies yet.');
}
async function refreshNotifications(){
 if(!sessionStorage.getItem('backline_session')){state.data.personalNotifications=null;render();return}
 try{const [items,prefs]=await Promise.all([api('/me/notifications'),api('/me/notification-preferences')]);state.data.personalNotifications=items;state.data.notificationPreferences=prefs;render()}catch(error){toast(error.message,true)}
}
function notificationCentre(){
 if(!state.data.personalNotifications)return panel('Personal notifications',empty('Sign in with an individual account to see your notifications.'));
 const prefs=state.data.notificationPreferences||{};
 return panel('Notification centre','<p class="sub">Assignments, RSVP requests and mentions across your active bands. Email is queued for testing; live delivery is disabled.</p><div class="list">'+state.data.personalNotifications.map(n=>'<div class="entry"><div><strong>'+esc(n.title)+'</strong><p>'+esc(state.bands.find(b=>b.id===n.band_id)?.name||'Band')+' · '+esc(n.category)+'</p></div>'+(n.read_at?'<span class="tag">Read</span>':'<button data-read-notification="'+n.id+'">Mark read</button>')+'</div>').join('')+'</div>')+
 panel('Email preferences','<form id="notificationPreferences"><div class="advanceGrid">'+['task','rsvp','mention'].map(category=>wsSelect(category,{task:'Task assignments',rsvp:'RSVP requests',mention:'Mentions'}[category],[['immediate','Immediate'],['daily','Daily summary'],['none','None']],prefs[category])).join('')+wsInput('timezone','Digest time zone',prefs.timezone||'America/Chicago','text',true,100)+'</div><p class="sub">Daily summaries are scheduled for 9:00 AM in your selected zone. Live email delivery is not enabled.</p><button class="primary">Save preferences</button></form>');
}
document.addEventListener('change',async event=>{if(event.target.id==='rsvpEvent'){state.rsvpEvent=Number(event.target.value);await refreshCollaboration()}});
document.addEventListener('submit',async event=>{if(!['rsvpForm','discussionForm','notificationPreferences'].includes(event.target.id))return;event.preventDefault();const form=event.target,button=event.submitter;button.disabled=true;try{
 const data=Object.fromEntries(new FormData(form));
 if(form.id==='rsvpForm'){await api(workspaceBase()+'/events/'+state.rsvpEvent+'/rsvp',{method:'PUT',body:JSON.stringify(data)});await refreshCollaboration();toast('Your RSVP saved')}
 if(form.id==='discussionForm'){data.mention_user_ids=new FormData(form).getAll('mention_user_ids').map(Number);await api(workspaceBase()+'/discussions/'+state.discussionThread+'/posts',{method:'POST',body:JSON.stringify(data)});await refreshCollaboration();toast('Reply posted')}
 if(form.id==='notificationPreferences'){await api('/me/notification-preferences',{method:'PUT',body:JSON.stringify(data)});await refreshNotifications();toast('Preferences saved')}
 }catch(error){toast(error.message,true);button.disabled=false}});
let lastTyping=0;
document.addEventListener('input',event=>{if(event.target.id!=='discussionReply'||Date.now()-lastTyping<3000)return;lastTyping=Date.now();api(workspaceBase()+'/discussions/'+state.discussionThread+'/typing',{method:'POST'}).catch(()=>{})});
document.addEventListener('click',async event=>{const b=event.target.closest('[data-new-thread],[data-thread],[data-link-roster],[data-edit-reply],[data-request-rsvp],[data-read-notification]');if(!b)return;try{
 if(b.dataset.thread){state.discussionThread=Number(b.dataset.thread);await refreshCollaboration()}
 if(b.hasAttribute('data-request-rsvp')){await api(workspaceBase()+'/events/'+state.rsvpEvent+'/rsvp-requests',{method:'POST'});toast('RSVP requests added to bandmates’ notifications')}
 if(b.hasAttribute('data-new-thread')){const options=[['band','Band'],...get('songs').map(s=>['song:'+s.id,'Song: '+s.title]),...get('setlists').map(s=>['setlist:'+s.id,'Set: '+s.title])];workspaceDialog('New discussion',wsInput('title','Discussion title','','text',true,160)+wsSelect('target','Discuss',options),async data=>{const [scope,id]=data.target.split(':');const made=await api(workspaceBase()+'/discussions',{method:'POST',body:JSON.stringify({title:data.title,scope,scope_id:id?Number(id):null})});state.discussionThread=made.id;await refreshCollaboration()})}
 if(b.dataset.linkRoster)workspaceDialog('Link roster account',wsSelect('user_id','Band account',state.data.collaboration.members.map(m=>[m.id,m.display_name])),async data=>{await api(workspaceBase()+'/members/'+b.dataset.linkRoster+'/account',{method:'PUT',body:JSON.stringify({user_id:Number(data.user_id)})});await refreshCollaboration()});
 if(b.dataset.editReply){const post=get('threadPosts').find(p=>String(p.id)===b.dataset.editReply);workspaceDialog('Edit my reply','<label>Reply<textarea aria-label="Reply" name="body" required maxlength="5000">'+esc(post.body)+'</textarea></label>',async data=>{await api(workspaceBase()+'/discussions/'+state.discussionThread+'/posts/'+post.id,{method:'PUT',body:JSON.stringify({...data,mention_user_ids:post.mention_user_ids})});await refreshCollaboration()})}
 if(b.dataset.readNotification){await api('/me/notifications/'+b.dataset.readNotification+'/read',{method:'POST'});await refreshNotifications()}
 }catch(error){toast(error.message,true)}});
let polling=false;
setInterval(async()=>{if(polling||state.section!=='collaboration'||!state.discussionThread||!sessionStorage.getItem('backline_session')||document.visibilityState==='hidden')return;polling=true;const band=state.band,thread=state.discussionThread;try{const [posts,typing]=await Promise.all([api('/bands/'+band+'/discussions/'+thread+'/posts'),api('/bands/'+band+'/discussions/'+thread+'/typing')]);if(state.band!==band||state.discussionThread!==thread)return;state.data.threadPosts=posts;renderLiveThread();const node=document.querySelector('#threadTyping');if(node)node.textContent=typing.length?typing.map(u=>u.display_name).join(', ')+' typing…':''}catch(error){if(state.band===band&&state.discussionThread===thread){state.data.threadPosts=[];const node=document.querySelector('#threadPosts');if(node)node.textContent='Discussion refresh is unavailable. Reopen the Band Hub to verify access.'}}finally{polling=false}},2000);
document.addEventListener('backline-render',()=>{
 if(!state.accountRole||['owner','manager'].includes(state.accountRole))return;
 const selectors=['new-venue','edit-venue','share-venue','link-venue','new-task','edit-task','toggle-task','new-setlist','build-setlist','edit-song','edit-stage','create-packet','edit-packet','ready-packet','save-advance','upload-show-file','new-tour','add-stop','edit-stop','edit-timeline','new-calendar','assign-calendar','calendar-subscriptions'];
 document.querySelectorAll(selectors.map(name=>'[data-'+name+']').join(',')).forEach(node=>node.hidden=true);
 document.querySelectorAll('[data-action]').forEach(node=>{if(['event','song','member','booking','setlist','market','campaign','invitation','issueRecovery'].includes(node.dataset.action))node.hidden=true});
 document.querySelectorAll('[data-advance-field],[data-advance-day],#advanceStatus').forEach(node=>node.disabled=true);
});
