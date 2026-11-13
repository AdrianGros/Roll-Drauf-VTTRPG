// Transient selection and atomic group commands. No document/schema ownership here.
import {cellOf,cellKey,LIMITS} from './document.js';
import {itemBounds,replacedTitleLabel} from './render.js';
const copy = value => JSON.parse(JSON.stringify(value));
const intersects = (a,b) => a.x <= b.x+b.w && a.x+a.w >= b.x && a.y <= b.y+b.h && a.y+a.h >= b.y;
export class Selection {
    constructor(ed) { this.ed=ed;this.reset();this.marquee=null; }
    reset(id=null) { this.ids=id?[id]:[];this.tiles=null; }
    get objects() {
        if(!this.ed.doc)return [];
        const byId=new Map(this.ed.doc.layers.filter(l=>l.visible).flatMap(layer=>(layer.items || []).map((item,index)=>[item.id,{layer,item,index}])));
        return this.ids.map(id=>byId.get(id)).filter(Boolean);
    }
    get count() { if(this.tiles && (!this.tiles.keys.length || !this.ed.doc?.layers.some(l=>l.id===this.tiles.layerId && l.visible)))this.tiles=null;return this.tiles ? this.tiles.keys.length : this.objects.length; }
    sync() { this.ed._selection=this.ids[0] || null;this.ed.ui.refreshInspector();this.ed.ui.refreshPlaces();this.ed.requestFrame(); }
    choose(id,add=false) {
        this.tiles=null;
        if(!add)this.ids=id?[id]:[];
        else if(this.ids.includes(id))this.ids=this.ids.filter(x=>x!==id);
        else if(id)this.ids.push(id);
        this.sync();
    }
    tileAt(p,add=false) {
        const layer=this.ed.doc.layers.find(l=>l.id===this.ed.activeLayerId && l.kind==='tiles' && l.visible);
        if(!layer)return false;
        const key=cellKey(Math.floor(p.x/layer.grid.size),Math.floor(p.y/layer.grid.size));
        if(!layer.cells.has(key))return false;
        if(!add && this.tiles?.layerId===layer.id && this.tiles.keys.includes(key))return true;
        if(!add || this.tiles?.layerId!==layer.id)this.tiles={layerId:layer.id,keys:[]};
        this.tiles.keys=add && this.tiles.keys.includes(key)?this.tiles.keys.filter(k=>k!==key):[...new Set([...this.tiles.keys,key])];
        this.ids=[];this.sync();return true;
    }
    rectangle(a,b,add=false) {
        const rect={x:Math.min(a.x,b.x),y:Math.min(a.y,b.y),w:Math.abs(a.x-b.x),h:Math.abs(a.y-b.y)};
        const layer=this.ed.doc.layers.find(l=>l.id===this.ed.activeLayerId && l.kind==='tiles' && l.visible);
        if(layer){
            const keys=[...layer.cells.keys()].filter(k=>{const p=cellOf(k);return intersects(rect,{x:p.col*layer.grid.size,y:p.row*layer.grid.size,w:layer.grid.size,h:layer.grid.size});});
            this.ids=[];this.tiles={layerId:layer.id,keys:[...new Set([...(add && this.tiles?.layerId===layer.id?this.tiles.keys:[]),...keys])]};
        }else{
            const ids=this.ed.doc.layers.filter(l=>l.visible && ['stamps','labels','paths'].includes(l.kind)).flatMap(l=>l.items.filter(i=>i!==replacedTitleLabel(this.ed.doc) && intersects(rect,itemBounds(i,this.ed.palette))).map(i=>i.id));
            this.tiles=null;this.ids=[...new Set([...(add?this.ids:[]),...ids])];
        }
        this.sync();
    }
    bounds() {
        const boxes=this.tiles ? (()=>{const l=this.ed.doc.layers.find(l=>l.id===this.tiles.layerId);return l?this.tiles.keys.map(k=>{const p=cellOf(k);return {x:p.col*l.grid.size,y:p.row*l.grid.size,w:l.grid.size,h:l.grid.size};}):[];})() : this.objects.map(({item})=>itemBounds(item,this.ed.palette));
        if(!boxes.length)return null;
        const x=Math.min(...boxes.map(b=>b.x)),y=Math.min(...boxes.map(b=>b.y));
        return {x,y,w:Math.max(...boxes.map(b=>b.x+b.w))-x,h:Math.max(...boxes.map(b=>b.y+b.h))-y};
    }
    beginMove() {
        if(this.tiles){const layer=this.ed.doc.layers.find(l=>l.id===this.tiles.layerId);return {layer,keys:this.tiles.keys.slice(),before:new Map(layer.cells),after:null,valid:true};}
        return {objects:this.objects.map(({item})=>({item,before:copy(item)})),moved:false};
    }
    previewMove(g,dx,dy) {
        if(g.layer){
            const grid=g.layer.grid.size,col=Math.round(dx/grid),row=Math.round(dy/grid),positions=g.keys.map(k=>{const p=cellOf(k);return {col:p.col+col,row:p.row+row};}),keys=positions.map(p=>cellKey(p.col,p.row));
            const own=new Set(g.keys),maxCol=Math.ceil(this.ed.doc.size.w/grid),maxRow=Math.ceil(this.ed.doc.size.h/grid);
            g.valid=positions.every((p,i)=>p.col>=0 && p.row>=0 && p.col<maxCol && p.row<maxRow && (!g.before.has(keys[i])||own.has(keys[i])));
            g.layer.cells=new Map(g.before);g.after=null;
            if(g.valid){const values=g.keys.map(k=>g.before.get(k));g.keys.forEach(k=>g.layer.cells.delete(k));keys.forEach((k,i)=>g.layer.cells.set(k,values[i]));g.after={cells:new Map(g.layer.cells),keys};}
        }else if(g.objects.length){
            dx=Math.max(...g.objects.map(o=>-o.before.x),Math.min(dx,...g.objects.map(o=>this.ed.doc.size.w-o.before.x)));
            dy=Math.max(...g.objects.map(o=>-o.before.y),Math.min(dy,...g.objects.map(o=>this.ed.doc.size.h-o.before.y)));
            g.objects.forEach(o=>{o.item.x=o.before.x+dx;o.item.y=o.before.y+dy;});g.moved=dx!==0||dy!==0;
        }
        this.ed.invalidate();
    }
    restoreMove(g) {
        if(g.layer)g.layer.cells=new Map(g.before);
        else g.objects.forEach(o=>Object.assign(o.item,copy(o.before)));
        this.ed.invalidate();
    }
    finishMove(g) {
        if(g.layer){
            if(!g.valid){this.restoreMove(g);this.ed.ui.toast(globalThis.VTTUi('Zielzellen sind belegt oder außerhalb der Karte. Auswahl wurde nicht verschoben.'));return;}
            if(!g.after || g.keys.every((k,i)=>k===g.after.keys[i]))return;
            const set=(cells,keys)=>{g.layer.cells=new Map(cells);this.tiles={layerId:g.layer.id,keys:keys.slice()};this.ids=[];this.ed.invalidate();this.sync();};
            this.tiles={layerId:g.layer.id,keys:g.after.keys};this.ed.commit({label:globalThis.VTTUi('Kachelauswahl verschieben'),bytes:(g.before.size+g.after.cells.size)*32,undo:()=>set(g.before,g.keys),redo:()=>set(g.after.cells,g.after.keys)});
        }else if(g.moved){
            const after=g.objects.map(o=>copy(o.item));const set=values=>{g.objects.forEach((o,i)=>Object.assign(o.item,copy(values[i])));this.ed.invalidate();this.ed.afterItemChange();};
            this.ed.commit({label:globalThis.VTTUi('Auswahl verschieben'),bytes:g.objects.length*512,undo:()=>set(g.objects.map(o=>o.before)),redo:()=>set(after)});
        }
        this.ed.afterItemChange();
    }
    remove() {
        const ed=this.ed;
        if(this.tiles){
            const layer=ed.doc.layers.find(l=>l.id===this.tiles.layerId),entries=this.tiles.keys.map(k=>[k,layer.cells.get(k)]);
            const apply=()=>{entries.forEach(([k])=>layer.cells.delete(k));ed.invalidate();ed.afterItemChange();};
            const undo=()=>{entries.forEach(([k,v])=>layer.cells.set(k,v));ed.invalidate();ed.afterItemChange();};
            this.reset();ed._selection=null;apply();ed.commit({label:globalThis.VTTUi('Kachelauswahl löschen'),bytes:entries.length*64,undo,redo:apply});return;
        }
        const rows=this.objects.map(o=>({...o,index:o.layer.items.indexOf(o.item)}));if(!rows.length)return;
        const apply=()=>{rows.forEach(({layer,item})=>{const i=layer.items.indexOf(item);if(i>=0)layer.items.splice(i,1);});ed.invalidate();ed.afterItemChange();};
        const undo=()=>{rows.slice().sort((a,b)=>a.index-b.index).forEach(({layer,item,index})=>layer.items.splice(index,0,item));ed.invalidate();ed.afterItemChange();};
        this.reset();ed._selection=null;apply();ed.commit({label:globalThis.VTTUi('Auswahl löschen'),bytes:rows.length*512,undo,redo:apply});
    }
    scale(factor) {
        const rows=this.objects;if(!rows.length || rows.some(({item})=>'points' in item))return;
        const range=item=>'asset' in item?LIMITS.stampSize:LIMITS.labelSize;
        factor=Math.max(...rows.map(({item})=>range(item)[0]/item.size),Math.min(factor,...rows.map(({item})=>range(item)[1]/item.size)));
        const before=rows.map(({item})=>copy(item));rows.forEach(({item})=>{item.size*=factor;});
        const after=rows.map(({item})=>copy(item));const set=values=>{rows.forEach(({item},i)=>Object.assign(item,copy(values[i])));this.ed.invalidate();this.ed.afterItemChange();};
        this.ed.invalidate();this.ed.afterItemChange();this.ed.commit({label:globalThis.VTTUi('Auswahl skalieren'),bytes:rows.length*512,undo:()=>set(before),redo:()=>set(after)});
    }
    draw(ctx,zoom) {
        ctx.save();ctx.strokeStyle='#f2c66d';ctx.fillStyle='rgba(242,198,109,.12)';ctx.lineWidth=2/zoom;ctx.setLineDash([6/zoom,4/zoom]);
        const b=this.bounds();if(b && (this.count>1||this.tiles))ctx.strokeRect(b.x,b.y,b.w,b.h);
        if(this.marquee){const {a,b}=this.marquee,x=Math.min(a.x,b.x),y=Math.min(a.y,b.y),w=Math.abs(a.x-b.x),h=Math.abs(a.y-b.y);ctx.fillRect(x,y,w,h);ctx.strokeRect(x,y,w,h);}
        ctx.restore();
    }
}
