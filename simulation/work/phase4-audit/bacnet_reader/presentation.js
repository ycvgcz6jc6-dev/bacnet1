/* Pure presentation rules: raw BACnet evidence remains the source of truth. */
(function(root) {
  'use strict';
  const point = r => /^(analog|binary|multi-state)-/.test(r.object_type);
  const seconds = (stamp, now=Date.now()) => stamp && Number.isFinite(Date.parse(stamp)) ? Math.max(0,(now-Date.parse(stamp))/1000) : Infinity;
  const fresh = (r,s,now=Date.now()) => !!r.available && r.in_object_list!==false && seconds(r.last_read,now)<(s.stale_after||180);
  const units = {'degrees-celsius':'°C','degrees-kelvin':'K','percent':'%','parts-per-million':'ppm','percent-relative-humidity':'% HR','cubic-meters-per-hour':'m³/h','liters-per-second':'L/s','pascals':'Pa','kilopascals':'kPa','kilowatts':'kW','watts':'W','kilowatt-hours':'kWh','megawatt-hours':'MWh','cubic-meters':'m³','liters':'L','no-units':'','seconds':'s','minutes':'min','hours':'h'};
  function value(r) {
    const v=r.display_value;
    if(v===null||v===undefined)return 'Non lue';
    return typeof v==='number'?new Intl.NumberFormat('fr-BE',{maximumFractionDigits:2}).format(v):typeof v==='object'?JSON.stringify(v):String(v);
  }
  function group(r,zone) {
    if(zone==='Vue générale'||zone==='BACnet Explorer')return true;
    if(zone==='CTA')return r.mct_subsystem==='Ventilation / CTA';
    if(zone==='Comptages')return !!r.meter_candidate;
    if(zone==='Horaires')return r.object_type==='schedule';
    if(zone==='Alarmes')return ['event-enrollment','notification-class'].includes(r.object_type)||r.mct_subsystem==='Alarme';
    return r.mct_zone===zone;
  }
  function propertyFresh(r,p,s,now=Date.now()) {
    const read=r.metadata_reads?.[p];
    return read?.status==='read'&&seconds(read.last_success,now)<(s.metadata_interval||1800)+60;
  }
  function annotations(data) {
    const candidates=new Map();
    for(const view of data.objects||[]) {
      if(view.object_type!=='structured-view')continue;
      const refs=view.metadata?.subordinateList,labels=view.metadata?.subordinateAnnotations;
      if(!Array.isArray(refs)||!Array.isArray(labels))continue;
      refs.forEach((ref,i)=>{
        if(ref['device-identifier']&&ref['device-identifier']!==`device,${data.device_instance}`)return;
        const match=/^([a-z-]+),(\d+)$/.exec(ref['object-identifier']||'');
        const label=labels[i];
        if(!match||typeof label!=='string'||!label.trim())return;
        const key=match[1]+'_'+match[2];
        if(!candidates.has(key))candidates.set(key,new Set());
        candidates.get(key).add(label);
      });
    }
    return new Map([...candidates].filter(([,labels])=>labels.size===1).map(([key,labels])=>[key,[...labels][0]]));
  }
  function alarmEvidence(data,now=Date.now()) {
    const objects=data.objects||[], summary=data.summary||{};
    const events=objects.filter(r=>r.object_type==='event-enrollment');
    const classes=new Map(objects.filter(r=>r.object_type==='notification-class').map(r=>[Number(r.metadata?.notificationClass??r.object_instance),r]));
    const rows=events.map(r=>{
      const m=r.metadata||{},known=propertyFresh(r,'eventState',summary,now)&&m.eventState!==null&&m.eventState!==undefined;
      const state=String(m.eventState??'Non lu');
      const normal=state==='normal'||state==='0';
      const cls=classes.get(Number(m.notificationClass));
      return {record:r,state,known,active:known&&!normal,className:cls?.object_name||'Classe non lue',priority:cls?.metadata?.priority??null};
    });
    const flags=objects.filter(r=>point(r)&&propertyFresh(r,'statusFlags',summary,now)&&Array.isArray(r.status_flags)&&(r.status_flags[0]===1||r.status_flags[0]===true));
    return {rows,active:rows.filter(r=>r.active),flags,unknown:rows.filter(r=>!r.known).length,complete:events.length>0&&rows.every(r=>r.known)};
  }
  function globalState(data,now=Date.now()) {
    const s=data.summary||{},p=(data.objects||[]).filter(point),a=alarmEvidence(data,now);
    const online=seconds(s.last_bacnet_success,now)<(s.stale_after||180);
    if(!online)return {tone:'bad',label:'Communication à vérifier',detail:'Aucun échange BACnet récent. Les dernières valeurs restent horodatées.'};
    if(a.active.length||a.flags.length)return {tone:'bad',label:'Signalement CPO',detail:`${a.active.length} événement(s) hors état normal · ${a.flags.length} point(s) avec in-alarm. État issu des métadonnées horodatées.`};
    const missing=p.filter(r=>!fresh(r,s,now)).length;
    if(missing||!s.metadata_complete||!a.complete)return {tone:'warn',label:'Observation partielle',detail:`${missing} valeur(s) périmée(s) ou absente(s). La couverture des alarmes dépend des propriétés lues.`};
    return {tone:'good',label:'Données disponibles',detail:'Aucun événement actif dans les données collectées. Occupation et mode spectacle non déduits.'};
  }
  function filters(rows,{query='',type='',zone='',subsystem='',issue=false,meter=false},s,now=Date.now()) {
    const q=query.toLocaleLowerCase();
    return rows.filter(r=>(!q||[r.object_name,r.description,r.key,r.object_type,r.object_instance].join(' ').toLocaleLowerCase().includes(q))&&(!type||r.object_type===type)&&(!zone||r.mct_zone===zone)&&(!subsystem||r.mct_subsystem===subsystem)&&(!meter||r.meter_candidate)&&(!issue||r.read_error||(point(r)&&!fresh(r,s,now))||Object.values(r.metadata_reads||{}).some(v=>v.status!=='read')));
  }
  const api={point,seconds,fresh,units,value,group,propertyFresh,annotations,alarmEvidence,globalState,filters};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  root.MCT=api;
})(typeof globalThis!=='undefined'?globalThis:this);
