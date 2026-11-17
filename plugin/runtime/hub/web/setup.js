export function createSetup(ctx){
  const $=s=>document.querySelector(s),e=ctx.esc;
  let readiness=null,rehearsals=null,busy=false;
  let draft={title:'Private rehearsal',kind:'gaming',media_id:'',checks:{},notes:'',measured_upload_mbps:null,owner_reviewed:false};
  const choices=()=>ctx.state().media.filter(m=>m.audio_tracks&&(draft.kind!=='gaming'||m.video));
  function capture(view){
    if(view!=='connections'||!$('#rehearsal-title'))return;
    draft={...draft,title:$('#rehearsal-title').value,kind:$('#rehearsal-kind').value,media_id:$('#rehearsal-media').value,
      checks:Object.fromEntries([...document.querySelectorAll('[data-rehearsal-check]')].map(el=>[el.dataset.rehearsalCheck,el.checked])),
      notes:$('#rehearsal-notes').value,measured_upload_mbps:$('#rehearsal-upload').value?Number($('#rehearsal-upload').value):null,owner_reviewed:$('#rehearsal-reviewed').checked};
  }
  const shown=v=>v===null||v===undefined?'Unknown':Number(v).toFixed(2);
  function diagnostics(){
    if(!readiness)return '<p class="section-copy">Check this hub’s computer before your next rehearsal. Reading connection status does not start a recording or approve hardware.</p>';
    const r=readiness,o=r.obs;
    return `<p class="setup-time">Checked ${e(new Date(r.checked_at*1000).toLocaleString())} · ${e(r.scope)}</p>
      <div class="setup-status"><span class="status-pill ${o.connected?'setup-connected':''}">OBS: ${o.connected?'authenticated read passed':e(o.state.replaceAll('_',' '))}</span><span class="status-pill">Capture folder: ${r.capture_folder.configured?'configured':'not configured'}</span><span class="status-pill">Phone: ${r.phone.state==='not_configured'?'not configured':'origin set; device unverified'}</span></div>
      <p>${e(o.message)}</p>${o.connected?`<div class="setup-metrics"><div><strong>${e(o.version||'Unknown')}</strong><span>OBS version</span></div><div><strong>${shown(o.stats.fps)}</strong><span>Current FPS</span></div><div><strong>${shown(o.stats.rendering.percent)}${o.stats.rendering.percent===null?'':'%'}</strong><span>Cumulative rendering skips</span></div><div><strong>${shown(o.stats.encoding.percent)}${o.stats.encoding.percent===null?'':'%'}</strong><span>Cumulative encoding skips</span></div></div><p class="footnote">These counters describe this read check; they do not measure a complete timed rehearsal. Recording: ${o.recording_active===true?'active':o.recording_active===false?'not active':'unknown'}. Stream: ${o.streaming_active===true?'active':o.streaming_active===false?'not active':'unknown'}.</p>`:''}
      ${r.blockers.length?`<ol class="setup-blockers">${r.blockers.map(b=>`<li>${e(b.label)}</li>`).join('')}</ol>`:'<p class="setup-positive">The listed connection prerequisites passed. Check your actual source routing in the saved rehearsal.</p>'}`;
  }
  function rehearsal(){
    if(!rehearsals)return '<p class="footnote">Check setup to load your saved owner reports and rehearsal checklist.</p>';
    const items=choices(),selected=items.find(m=>m.id===draft.media_id);
    const checks=rehearsals.requirements[draft.kind];
    return `<div class="panel-heading"><h3>Your rehearsal observations</h3><span>Saved by you · source linked · append only</span></div><p>Record locally, stop, import the intended file, then watch and listen. An agent cannot tick these checks or save this report for you.</p>
      <div class="two-fields"><label>Report title<input id="rehearsal-title" maxlength="100" value="${e(draft.title)}"></label><label>Rehearsal type<select id="rehearsal-kind"><option value="gaming" ${draft.kind==='gaming'?'selected':''}>Gaming picture + sound</option><option value="podcast" ${draft.kind==='podcast'?'selected':''}>Podcast audio</option></select></label></div>
      <label>Saved recording<select id="rehearsal-media"><option value="">Choose an imported recording</option>${items.map(m=>`<option value="${m.id}" ${draft.media_id===m.id?'selected':''}>${e(m.name)} · ${m.duration.toFixed(1)}s</option>`).join('')}</select></label><button id="rehearsal-import">Import rehearsal recording</button>
      ${selected?`<div class="rehearsal-player">${selected.video?`<video controls preload="metadata" playsinline src="/api/media/${selected.id}" aria-label="Rehearsal recording"></video>`:`<audio controls preload="metadata" src="/api/media/${selected.id}" aria-label="Rehearsal recording"></audio>`}</div>`:''}
      <div class="rehearsal-checks">${Object.entries(checks).map(([id,label])=>`<label class="check"><input type="checkbox" data-rehearsal-check="${id}" ${draft.checks[id]?'checked':''}>${e(label)}</label>`).join('')}</div>
      <label>Measured upload Mbps (optional)<input type="number" min="0.01" max="100000" step="0.01" id="rehearsal-upload" placeholder="Not measured" value="${draft.measured_upload_mbps??''}"></label><label>What worked / what needs fixing<textarea id="rehearsal-notes" maxlength="1200" rows="3">${e(draft.notes)}</textarea></label>
      <div class="control-footer"><label class="check"><input type="checkbox" id="rehearsal-reviewed" ${draft.owner_reviewed?'checked':''}>I personally reviewed this saved recording and these observations</label><button class="primary" id="save-rehearsal" ${busy||!items.length?'disabled':''}>Save my observations</button></div><p class="footnote">Unchecked items remain unresolved. All checked means an owner-reported pass, not automatic hardware, phone or public-stream verification. Saving creates a new record and never overwrites an older one.</p>
      <div class="rehearsal-reports">${rehearsals.rehearsals.slice(0,10).map(r=>`<article><div><span class="status-pill">${r.status==='owner_reported_pass'?'Owner-reported pass':'Owner-reported attention needed'}</span><h4>${e(r.title)}</h4><p>${e(r.media_name)} · ${e(new Date(r.created*1000).toLocaleString())}</p><p>${r.unconfirmed.length?e(r.unconfirmed.map(k=>r.check_labels[k]).join('; ')):'All applicable checks were reported by the owner.'}</p>${r.notes?`<p>${e(r.notes)}</p>`:''}</div><a class="download" href="/api/rehearsal?id=${r.id}&download=1" download>Download report</a></article>`).join('')}</div>`;
  }
  function panel(){return `<section class="connection-group setup-panel"><div class="panel-heading"><div><span class="eyebrow">BEFORE THE NEXT TAKE</span><h3>Connect. Rehearse. Keep the evidence.</h3></div><button id="setup-check" ${busy?'disabled':''}>${busy?'Checking this computer…':'Check setup'}</button></div>${diagnostics()}<details class="setup-help"><summary>Connect OBS privately on the laptop</summary><p>Keep OBS WebSocket password authentication enabled. This local helper verifies the existing connection and stores a credential protected by your Windows account. It does not enable the OBS server or change its network settings.</p><code>python -m tools.connect_obs --from-obs</code><p>Or enter its current password in a private local prompt:</p><code>python -m tools.connect_obs --prompt --port 4455</code><p class="footnote">Use the actual saved OBS port. Never put the password in chat, a command argument, or Git. The stored Windows credential cannot be used as a portable hosted/mobile connection. Existing private environment-password setup remains supported.</p></details>${readiness?'<a class="download" href="/api/readiness-report" download>Download setup report</a>':''}</section><section class="connection-group setup-panel">${rehearsal()}</section>`;}
  function paint(){const host=$('#studio-setup');if(host){host.innerHTML=panel();bind();}}
  const action=(s,fn,event='click')=>{const el=$(s);if(el)el.addEventListener(event,async ev=>{try{await fn(ev);}catch(err){ctx.notice(err.message,true);}});};
  async function refresh(){capture('connections');busy=true;paint();try{[readiness,rehearsals]=await Promise.all([ctx.api('/api/readiness'),ctx.api('/api/rehearsals')]);}finally{busy=false;paint();}}
  function bind(){
    action('#setup-check',refresh);
    action('#rehearsal-import',()=>{capture('connections');ctx.importFor('connections');});
    action('#rehearsal-kind',()=>{capture('connections');draft.checks={};draft.owner_reviewed=false;if(!choices().some(m=>m.id===draft.media_id))draft.media_id='';paint();},'change');
    action('#rehearsal-media',()=>{capture('connections');draft.checks={};draft.owner_reviewed=false;paint();},'change');
    action('#save-rehearsal',async()=>{capture('connections');busy=true;paint();try{const result=await ctx.api('/api/rehearsals',draft);draft.owner_reviewed=false;rehearsals=await ctx.api('/api/rehearsals');ctx.notice(result.status==='owner_reported_pass'?'Saved your reported pass. Device and publication checks remain separate.':'Saved your observations with unresolved checks.');}finally{busy=false;paint();}});
  }
  return {render:()=>`<div id="studio-setup">${panel()}</div>`,bind:view=>{if(view==='connections')bind();},capture,
    importDone:(asset,target)=>{if(target==='connections'&&asset.audio_tracks){draft.media_id=asset.id;if(!asset.video)draft.kind='podcast';draft.checks={};draft.owner_reviewed=false;}}};
}
