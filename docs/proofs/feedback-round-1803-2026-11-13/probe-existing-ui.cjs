const fs=require('fs');
const vm=require('vm');
const acorn=require('internal/deps/acorn/acorn/dist/acorn');
function walk(node,fn){if(!node||typeof node!=='object')return;fn(node);for(const [key,value] of Object.entries(node)){if(key==='loc')continue;if(Array.isArray(value))value.forEach(n=>walk(n,fn));else if(value&&typeof value==='object')walk(value,fn);}}
function parsed(path){const text=fs.readFileSync(path,'utf8');return {text,ast:acorn.parse(text,{ecmaVersion:'latest',sourceType:'module'})};}
const play=parsed('/app/vtt/static/js/play-ui.js');let method;
walk(play.ast,n=>{if(n.type==='MethodDefinition'&&n.key.name==='_normalizeBookReturnTarget')method=n.value;});
if(!method)throw Error('Current return-target method missing');
const normalize=new Function('window','targetHref',play.text.slice(method.body.start+1,method.body.end-1));
const cases=['/dashboard','/characters','/mapmaker','/api/ce/authoring'].map(target=>({target,result:normalize({location:{origin:'https://vtt.roll-drauf.de'}},target)}));
if(cases[2].result!==null||!cases[0].result||!cases[1].result)throw Error('Unexpected baseline; re-evaluate finding');
const cal=parsed('/app/vtt/static/js/session-calendar.js');let render;
walk(cal.ast,n=>{if(n.type==='FunctionDeclaration'&&n.id?.name==='renderGrid')render=n;});
const wanted=new Set(['ui','esc','language','intlLocale','parseDay','isoDay','shiftDays','dayLabel','todayIn']);
const declarations=cal.ast.body.filter(n=>n.type==='VariableDeclaration'&&n.declarations.some(d=>wanted.has(d.id.name))).map(n=>cal.text.slice(n.start,n.end)).join('\n');
const calendars=[];
for(const [lang,start,end,days] of [['de','2026-11-01','2026-12-01',30],['en','2028-02-01','2028-03-01',29]]){
 const box={innerHTML:'',replaceChildren(){this.innerHTML='';}};
 const context={document:{documentElement:{lang}},Intl,Date,root:{querySelector(){return box;}},state:{scope:'month',data:{start,end},entries:[],day:''},timezone:'UTC'};
 vm.runInNewContext(declarations+'\n('+cal.text.slice(render.start,render.end)+')();',context);
 const dayCount=(box.innerHTML.match(/class="sc-day/g)||[]).length,weekdayCount=(box.innerHTML.match(/class="sc-weekday/g)||[]).length;
 if(dayCount!==days||weekdayCount!==7)throw Error('Empty calendar did not render its whole month');
 calendars.push({lang,start,end,entries:0,days:dayCount,weekdays:weekdayCount});
}
console.log(JSON.stringify({scope:'Actual source methods evaluated without browser, server, DB or production writes; these are diagnostic facts, not live UI acceptance.',back_menu_maps:{finding:'Confirmed: /mapmaker normalizes to null although the app menu advertises that target; control routes are accepted.',cases},empty_month_renderer:{result:'pass',cases:calendars}},null,2));
