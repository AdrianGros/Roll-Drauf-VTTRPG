export const ui=(source,parameters)=>globalThis.VTTUi(source,parameters||{});
export const make=(tag,parent,text,attrs={})=>{
 const element=document.createElement(tag);if(text!==null)element.textContent=text;
 for(const [key,value] of Object.entries(attrs))element.setAttribute(key,value);
 parent.append(element);return element;
};
export async function request(path,method='GET',body,signal,extra={},retry=true){
 const headers={...window.Auth.buildHeaders(method,body!==undefined),...extra};
 const response=await fetch(path.startsWith('/api/')?path:'/api/atlas'+path,{method,headers,credentials:'include',signal,body:body===undefined?undefined:JSON.stringify(body)});
 if(response.status===401&&retry&&await window.Auth.refreshAccessToken())return request(path,method,body,signal,extra,false);
 if(!response.ok){const data=await response.json().catch(()=>({}));const error=new Error(data.error?ui(data.error):ui('Atlas-Anfrage fehlgeschlagen. Bitte erneut versuchen.'));error.status=response.status;error.code=data.code;throw error;}
 return response;
}
export async function api(...args){return (await request(...args)).json();}
export function download(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
export async function restore(file,revision){
 if(file.size>64*1024*1024)throw new Error(ui('Die Sicherung ist größer als 64 MiB.'));
 const headers=window.Auth.buildHeaders('POST',false);headers['Content-Type']=file.name.toLowerCase().endsWith('.zip')?'application/zip':'application/json';if(revision!==undefined)headers['X-Atlas-Revision']=String(revision);
 const response=await fetch('/api/atlas/restore',{method:'POST',headers,credentials:'include',body:file});
 const data=await response.json();if(!response.ok)throw new Error(ui(data.error||'Atlas-Anfrage fehlgeschlagen. Bitte erneut versuchen.'));return data;
}
