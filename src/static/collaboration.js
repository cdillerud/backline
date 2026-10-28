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
 const info=state.data.collaboration;
 if(!info){
  const upcoming=(get('events')||[]).filter(e=>e.date>=today()).sort((a,b)=>a.date.localeCompare(b.date)).slice(0,4);
  const people=(get('members')||[]).filter(m=>m.active!==0).slice(0,8);
  return panel('Your band, connected','<p class="sub">Your shared home for shows, rehearsals, music and the people behind them.</p><div class="hubShortcuts"><button data-go="schedule">Schedule</button><button data-go="songs">Songs & setlists</button><button data-go="touring">Shows & tours</button></div>')+
   '<div class="panels">'+
   panel('Coming up',upcoming.length?'<div class="list">'+upcoming.map(e=>item(e.title,datePretty(e.date)+' · '+(e.time||'Time to confirm')+' · '+(e.venue||'Venue to confirm'),e.kind)).join('')+'</div>':empty('Nothing scheduled yet.'),'<button class="small" data-go="schedule">Open schedule</button>')+
   panel('Bandmates',people.length?'<div class="list">'+people.map(m=>item(m.name,m.instrument||'Band member')).join('')+'</div>':empty('Add your bandmates to get started.'),'<button class="small" data-go="members">View members</button>')+
   '</div>'+
   panel('Private conversations and RSVPs','<p class="sub">'+esc(state.data.collaborationNotice||'Individual band sign-in is required for private conversations, RSVPs and notifications.')+'</p><p class="sub">The shared overview uses existing band records; private collaboration remains protected.</p>');
 }

 const event=get('events').find(e=>e.id===state.rsvpEvent);
 const own=get('rsvps').find(r=>r.user_id===info.user_id);
 const threads=get('discussions').slice().sort((a,b)=>Number(b.updated_at||b.created_at||0)-Number(a.updated_at||a.created_at||0));
 const thread=threads.find(t=>t.id===state.discussionThread);
 const choices=threads.map(t=>'<button type="button" class="threadChoice '+(thread?.id===t.id?'active':'')+'" data-thread="'+t.id+'" aria-current="'+(thread?.id===t.id?'true':'false')+'"><strong>'+esc(t.title)+'</strong><small>'+esc(t.scope||'Band')+'</small></button>').join('');
 const chat=thread?
  '<section class="messenger" aria-label="Conversation"><header class="messengerHeader"><div><h3>'+esc(thread.title)+'</h3><small>'+esc(thread.scope||'Band')+'</small></div></header>'+
  '<div id="threadPosts" class="discussionPosts" role="log" aria-label="Messages" aria-live="polite" aria-relevant="additions"></div><p id="threadTyping" role="status"></p>'+
  (collabWriter()?'<form id="discussionForm" class="messengerComposer"><label for="discussionReply">Message</label><div class="messengerComposeRow"><textarea id="discussionReply" name="body" required maxlength="5000" rows="2" placeholder="Message the band…"></textarea><button class="primary" type="submit">Send message</button></div>'+
   '<details class="mentionDisclosure"><summary>@ Mention bandmates</summary><fieldset class="mentionPills"><legend>Select people to notify</legend>'+info.members.filter(m=>m.id!==info.user_id).map(m=>'<label><input type="checkbox" name="mention_user_ids" value="'+m.id+'">@'+esc(m.display_name)+'</label>').join('')+'</fieldset></details></form>':'')+'</section>':
  '<section class="messenger messengerEmpty"><p>Select a conversation to start messaging.</p></section>';
 const primary='<section class="hubChatWorkspace" aria-label="Band conversations"><aside class="hubThreadRail"><header><h2>Conversations</h2>'+(collabAdmin()?'<button type="button" data-new-thread aria-label="New discussion">+ New</button>':'')+'</header><nav aria-label="Band conversations">'+(choices||'<p class="sub">No conversations yet.</p>')+'</nav></aside>'+chat+'</section>';
 const admin=collabAdmin()?'<details class="hubDisclosure"><summary>Band administration</summary><div class="hubDisclosureBody"><h3>Link roster identities</h3><p class="sub">Connect roster members with their band accounts.</p><div class="list">'+get('members').map(m=>'<div class="entry"><span>'+esc(m.name)+' · '+esc(m.instrument)+'</span><button data-link-roster="'+m.id+'">'+(info.members.some(a=>a.member_id===m.id)?'Change account link':'Link account')+'</button></div>').join('')+'</div></div></details>':'';
 return primary+'<div class="hubSecondary"><div class="hubQuickLinks"><button data-go="schedule">Schedule</button><button data-go="notifications">Notifications</button><button data-go="media">Photos & albums</button><button data-go="tasks">Tasks</button></div>'+admin+'</div>';
}
// Messenger keyboard convention: Enter sends, Shift+Enter creates a newline.
// Composition events must never send a partially composed IME message.
document.addEventListener('keydown',event=>{
 const editor=event.target.closest('#discussionReply');
 if(!editor||event.key!=='Enter'||event.shiftKey||event.isComposing||event.keyCode===229)return;
 const form=editor.closest('#discussionForm');
 if(!form||!editor.value.trim())return;
 event.preventDefault();
 if(form.requestSubmit)form.requestSubmit();
});
function renderLiveThread(){
 const container=document.querySelector('#threadPosts');if(!container)return;
 const rows=get('threadPosts'),signature=JSON.stringify(rows);if(container.dataset.signature===signature)return;
 const followBottom=container.scrollHeight-container.scrollTop-container.clientHeight<72;
 container.dataset.signature=signature;
 container.innerHTML=rows.length?rows.map(post=>{
  const own=post.user_id===state.data.collaboration?.user_id;
  return '<article class="discussionPost '+(own?'discussionPost--own':'discussionPost--other')+'">'+
   (own?'':memberAvatar(post.member_id,post.display_name))+
   '<div class="messageBubble"><div class="messageByline"><strong>'+esc(own?'You':post.display_name)+'</strong><time>'+new Date(post.updated_at*1000).toLocaleString()+'</time></div>'+
   '<p>'+esc(post.body).replace(/\\n/g,'<br>')+'</p>'+
   (own?'<button type="button" data-edit-reply="'+post.id+'">Edit message</button>':'')+'</div></article>';
 }).join(''):empty('No messages yet. Start the conversation below.');
 if(followBottom)container.scrollTop=container.scrollHeight;
}
async function refreshNotifications(){
 if(!sessionStorage.getItem('backline_session')){state.data.personalNotifications=null;render();return}
 try{const [items,prefs]=await Promise.all([api('/me/notifications'),api('/me/notification-preferences')]);state.data.personalNotifications=items;state.data.notificationPreferences=prefs;render()}catch(error){toast(error.message,true)}
}
function notificationCentre(){
 if(!state.data.personalNotifications)return panel('Personal notifications',empty('Sign in with an individual account to see your notifications.'));
 const prefs=state.data.notificationPreferences||{};
 return panel('Notification centre','<p class="sub">Assignments, RSVP requests and mentions across your active bands. Email is queued for testing; live delivery is disabled.</p><div class="list">'+state.data.personalNotifications.map(n=>'<div class="entry"><div><strong>'+esc(n.title)+'</strong><p>'+esc(state.bands.find(b=>b.id===n.band_id)?.name||'Band')+' · '+esc(n.category)+'</p></div>'+(n.read_at?'<span class="tag">Read</span>':'<button data-read-notification="'+n.id+'">Mark read</button>')+'</div>').join('')+'</div>')+
 panel('Email preferences','<form id="notificationPreferences"><div class="advanceGrid">'+['task','rsvp','mention','operations'].map(category=>wsSelect(category,{task:'Task assignments',rsvp:'RSVP requests',mention:'Mentions',operations:'Show operations'}[category],[['immediate','Immediate'],['daily','Daily summary'],['none','None']],prefs[category])).join('')+wsInput('timezone','Digest time zone',prefs.timezone||'America/Chicago','text',true,100)+'</div><p class="sub">Daily summaries are scheduled for 9:00 AM in your selected zone. Live email delivery is not enabled.</p><button class="primary">Save preferences</button></form>');
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
