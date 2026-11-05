// Calendar response isolation regression, backed only by synthetic deferred promises.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('src/static/workspace.js','utf8');
const start=source.indexOf('async function refreshCalendar(all=false)');
const end=source.indexOf('\nfunction scheduleBoard()',start);
assert(start>=0&&end>start,'calendar function changed location');
const snippet=source.slice(start,end)+'\nglobalThis.refreshCalendar=refreshCalendar;';
function scenario(){
 let session='token-a';const pending=[];
 const state={band:1,bands:[{id:1,name:'Band One'},{id:2,name:'Band Two'}],data:{calendarEvents:[{title:'prior'}]}};
 const context={state,sessionStorage:{getItem:()=>session},render:()=>{context.renders++},
  toast:()=>{context.toasts++},renders:0,toasts:0,
  api:path=>new Promise((resolve,reject)=>pending.push({path,resolve,reject}))};
 vm.runInNewContext(snippet,context);
 const take=q=>{const index=pending.findIndex(item=>item.path===q);assert(index>=0,'missing deferred '+q);return pending.splice(index,1)[0]};
 return {state,context,take,setSession:value=>{session=value}};
}
async function changedBand(){
 const t=scenario(),p=t.context.refreshCalendar();
 t.state.band=2;
 t.take('/bands/1/calendar/events').resolve([{date:'2026-11-05',time:'18:00',title:'Private old band show'}]);
 t.take('/bands/1/calendars').resolve([]);
 await p;
 assert.equal(t.state.data.calendarEvents[0].title,'prior');
 assert.equal(t.context.renders,0);
}
async function sessionLost(){
 const t=scenario(),p=t.context.refreshCalendar();
 t.setSession(null);
 t.take('/bands/1/calendar/events').reject(new Error('expired session'));
 t.take('/bands/1/calendars').resolve([]);
 await p;
 assert.equal(t.context.toasts,0);
}
async function overlapping(){
 const t=scenario(),first=t.context.refreshCalendar(false);
 const second=t.context.refreshCalendar(false);
 const oldestEvents=t.take('/bands/1/calendar/events');
 const oldestCalendars=t.take('/bands/1/calendars');
 t.take('/bands/1/calendar/events').resolve([{date:'2026-11-06',time:'19:00',title:'Latest'}]);
 t.take('/bands/1/calendars').resolve([{id:1}]);
 await second;
 oldestEvents.resolve([{date:'2026-11-05',time:'19:00',title:'Old'}]);
 oldestCalendars.resolve([]);
 await first;
 assert.equal(t.state.data.calendarEvents[0].title,'Latest');
 assert.equal(t.context.renders,1);
}
async function combined(){
 const t=scenario(),p=t.context.refreshCalendar(true);
 t.take('/bands/1/calendar/events').resolve([{date:'2026-11-07',time:'21:00',title:'A'}]);
 t.take('/bands/2/calendar/events').resolve([{date:'2026-11-06',time:'19:00',title:'B'}]);
 t.take('/bands/1/calendars').resolve([]);
 await p;
 assert.equal(t.state.data.calendarEvents.length,2);
 assert.equal(t.state.data.calendarEvents[0].title,'B');
 assert.equal(t.state.calendarAll,true);
 assert.equal(t.context.renders,1);
}
(async()=>{await changedBand();await sessionLost();await overlapping();await combined();console.log('Calendar isolation: 4 scenarios passed')})().catch(e=>{console.error(e);process.exitCode=1});
