/* Reader composition consumes only the explicit server projection. No author import. */
import {api,make,ui} from './atlas-common.js';

export function renderProjection(host,{world,projection,imageUrl,initialPlace}){
 host.replaceChildren();host.className='atlas-reader';
 make('h1',host,projection.title);make('p',host,projection.summary,{class:'atlas-prose'});
 const columns=make('div',host,null,{class:'atlas-columns'}),sidebar=make('section',columns,null,{class:'atlas-panel'});
 const search=make('input',make('label',sidebar,ui('Orte suchen')),null,{type:'search',id:'atlasSearch',maxlength:100});
 const places=make('nav',sidebar,null,{'aria-label':ui('Orte'),id:'atlasPlaces'});
 const main=make('section',columns,null,{class:'atlas-panel'}),toolbar=make('div',main,null,{class:'atlas-actions'});
 const select=make('select',make('label',toolbar,ui('Karte')),null,{id:'atlasMapSelect'});
 for(const map of projection.maps)select.add(new Option(map.title,map.id));
 const zoomOut=make('button',toolbar,ui('Verkleinern'),{type:'button',class:'btn btn-secondary'}),zoomIn=make('button',toolbar,ui('Vergrößern'),{type:'button',class:'btn btn-secondary'});
 const scale=make('p',main,'',{id:'atlasScale'}),viewport=make('div',main,null,{class:'atlas-map-viewport',tabindex:0,'aria-label':ui('Kartenansicht')}),canvas=make('div',viewport,null,{class:'atlas-map-canvas'});
 const detail=make('section',main,null,{id:'atlasPlaceDetail',class:'atlas-prose'}),credits=make('pre',main,'',{class:'atlas-credits'});
 let selected=initialPlace,mapId=projection.places.find(p=>p.id===selected)?.map_id||projection.maps[0]?.id,zoom=1;
 const index=new Map(projection.places.map(place=>[place.id,place]));
 function link(place,parent){const anchor=make('a',parent,place.name,{href:`/atlas?world=${world}&place=${place.id}`,'data-place-id':place.id});anchor.onclick=event=>{event.preventDefault();selected=place.id;if(place.map_id)mapId=place.map_id;history.replaceState(null,'',anchor.href);draw();};return anchor;}
 function draw(){
  places.replaceChildren();const q=search.value.trim().toLocaleLowerCase();
  for(const place of projection.places){if(q&&!`${place.name} ${place.lore}`.toLocaleLowerCase().includes(q))continue;let depth=0,parent=place.parent_id;while(parent&&index.has(parent)){depth++;parent=index.get(parent).parent_id;}
   const row=make('div',places,null);row.style.paddingInlineStart=`${Math.min(depth,12)}em`;link(place,row);}
  const map=projection.maps.find(row=>row.id===mapId);select.value=mapId||'';canvas.replaceChildren();viewport.hidden=!map;zoomIn.disabled=zoomOut.disabled=!map;
  if(map){canvas.style.width=`${map.width*zoom}px`;canvas.style.height=`${map.height*zoom}px`;const image=make('img',canvas,null,{src:imageUrl(map.id),alt:map.title,draggable:'false'});image.style.width='100%';image.style.height='100%';
   for(const place of projection.places.filter(row=>row.map_id===map.id&&row.x!==null)){const pin=make('a',canvas,place.name,{href:`/atlas?world=${world}&place=${place.id}`,class:'atlas-pin','data-place-id':place.id});pin.style.left=`${place.x/map.width*100}%`;pin.style.top=`${place.y/map.height*100}%`;pin.onclick=event=>{event.preventDefault();selected=place.id;history.replaceState(null,'',pin.href);draw();};}
   scale.textContent=map.km_per_pixel===null?ui('Kein physischer Maßstab festgelegt.'):ui('{distance} km pro Kartenpixel.',{distance:map.km_per_pixel});credits.textContent=map.credits||'';
  }else{scale.textContent=ui('Diese Welt hat noch keine veröffentlichte Karte.');credits.textContent='';}
  detail.replaceChildren();const place=index.get(selected);if(place){make('h2',detail,place.name);if(place.parent_id)link(index.get(place.parent_id),detail);make('p',detail,place.lore);const links=make('nav',detail,null,{'aria-label':ui('Verknüpfte Orte')});for(const id of place.links)if(index.has(id))link(index.get(id),links);}
 }
 search.oninput=draw;select.onchange=()=>{mapId=select.value;zoom=1;draw();};zoomOut.onclick=()=>{zoom=Math.max(.25,zoom-.25);draw();};zoomIn.onclick=()=>{zoom=Math.min(3,zoom+.25);draw();};draw();
 return ()=>host.replaceChildren();
}

export async function mountReader(host,world,initialPlace){
 let timer,controller,version=0,pubId,clear;
 function stop(){clearTimeout(timer);controller?.abort();version++;}
 function denied(){stop();clear?.();host.replaceChildren();make('p',host,ui('Der Zugriff auf diese Welt ist nicht verfügbar.'),{role:'status',id:'atlasDenied'});}
 async function refresh(){
  stop();if(document.hidden)return;controller=new AbortController();const v=version;
  try{const data=await api(`/worlds/${world}/published`,'GET',undefined,controller.signal);if(v!==version)return;
   if(data.publication_id!==pubId){clear?.();pubId=data.publication_id;clear=renderProjection(host,{world,projection:data.projection,initialPlace,imageUrl:id=>`/api/atlas/worlds/${world}/published/maps/${id}.png?version=${data.publication_id}`});}
  }catch(error){if(error.name!=='AbortError'&&v===version){if([401,403,404,409].includes(error.status)){denied();return;}make('p',host,ui('Verbindung unterbrochen. Erneute Prüfung folgt.'),{role:'status'});}}
  finally{if(v===version&&!document.hidden)timer=setTimeout(refresh,5000);}
 }
 const hidden=()=>{stop();if(!document.hidden)refresh();};const leave=()=>{stop();clear?.();host.replaceChildren();};
 document.addEventListener('visibilitychange',hidden);window.addEventListener('pagehide',leave);await refresh();
 return ()=>{leave();document.removeEventListener('visibilitychange',hidden);window.removeEventListener('pagehide',leave);};
}
