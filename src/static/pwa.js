if('serviceWorker' in navigator)navigator.serviceWorker.register('/service-worker.js',{scope:'/'}).catch(()=>{});
let installPrompt=null;
window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();installPrompt=event;document.querySelectorAll('[data-install-app]').forEach(n=>n.hidden=false)});
document.addEventListener('click',async event=>{if(!event.target.closest('[data-install-app]')||!installPrompt)return;await installPrompt.prompt();installPrompt=null;document.querySelectorAll('[data-install-app]').forEach(n=>n.hidden=true)});

document.addEventListener('backline-render',()=>{if(installPrompt)document.querySelectorAll('[data-install-app]').forEach(node=>node.hidden=false)});
