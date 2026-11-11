"""Development source-position annotations; never translates runtime/user DOM text."""
import argparse,hashlib,html,json,pathlib,re
from html.parser import HTMLParser
ROOT=pathlib.Path(__file__).resolve().parents[2]
SOURCES=ROOT/'tools/i18n/ui-sources.json'
SKIP={'script','style','textarea','pre','code','kbd','samp'}
VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
ATTRS={'title','placeholder','aria-label','alt'}
REGISTRY={}


def eligible(value):
    return isinstance(value,str) and 0<len(value.strip())<1600 and re.search(r'[A-Za-zÄÖÜäöüß]',value) and not re.search(r'\{\{|\{%|\$\{|__VT_EXPR_|\{p\d+\}',value) and not re.fullmatch(r'[a-z0-9_-]+',value.strip()) and not re.fullmatch(r'[A-Z_]+',value.strip())


def register(value,ref):
    key='u_'+hashlib.sha1(value.encode()).hexdigest()[:12]
    row=REGISTRY.setdefault(key,{'key':key,'source':value,'de':value,'refs':[]})
    if ref not in row['refs']:row['refs'].append(ref)
    return key


class Marker(HTMLParser):
    def __init__(self,ref,expression=False):
        super().__init__(convert_charrefs=False);self.ref=ref;self.expression=expression;self.out=[];self.stack=[];self.markers={}
    def replacement(self,value):
        key=register(value,self.ref)
        if not self.expression:return key
        marker=f'__VT_UI_{len(self.markers)}__';self.markers[marker]=value;return marker
    def start(self,tag,attrs):
        raw=self.get_starttag_text()
        def attribute(match):
            value=html.unescape(match[3])
            if not eligible(value):return match[0]
            key=self.replacement(value)
            if self.expression:return f'{match[1]}={match[2]}{key}{match[2]}'
            return match[0]+f' data-ui-{match[1].lower()}="{key}"'
        raw=re.sub(r'\b(title|placeholder|aria-label|alt)\s*=\s*([\'"])(.*?)\2',attribute,raw,flags=re.I|re.S)
        index=len(self.out);self.out.append(raw)
        if tag not in VOID:self.stack.append({'tag':tag,'start':index,'parts':[]})
    def handle_starttag(self,tag,attrs):self.start(tag,attrs)
    def handle_startendtag(self,tag,attrs):
        self.start(tag,attrs)
        if tag not in VOID and self.stack and self.stack[-1]['tag']==tag:self.stack.pop()
    def handle_endtag(self,tag):
        frame=None
        if self.stack and self.stack[-1]['tag']==tag:frame=self.stack.pop()
        if frame and tag in ('option','title') and not self.expression:
            value=html.unescape(''.join(frame['parts'])).strip()
            if eligible(value):
                key=self.replacement(value);raw=self.out[frame['start']]
                if 'data-ui-key=' not in raw:self.out[frame['start']]=raw[:-1]+f' data-ui-key="{key}">'
        self.out.append(f'</{tag}>')
    def handle_data(self,data):
        for frame in self.stack:
            if frame['tag'] in ('option','title'):frame['parts'].append(data)
        tag=self.stack[-1]['tag'] if self.stack else None
        if any(frame['tag'] in SKIP for frame in self.stack) or tag in ('option','title') and not self.expression:
            self.out.append(data);return
        value=data.strip()
        if not eligible(value):self.out.append(data);return
        marker=self.replacement(value)
        prefix=data[:len(data)-len(data.lstrip())];suffix=data[len(data.rstrip()):]
        if self.expression:self.out.append(prefix+marker+suffix)
        else:self.out.append(prefix+f'<span data-ui-key="{marker}">'+data.strip()+'</span>'+suffix)
    def handle_entityref(self,name):
        value='&'+name+';';self.out.append(value)
        for frame in self.stack:
            if frame['tag'] in ('option','title'):frame['parts'].append(value)
    def handle_charref(self,name):
        value='&#'+name+';';self.out.append(value)
        for frame in self.stack:
            if frame['tag'] in ('option','title'):frame['parts'].append(value)
    def handle_comment(self,data):self.out.append('<!--'+data+'-->')
    def handle_decl(self,decl):self.out.append('<!'+decl+'>')
    def handle_pi(self,data):self.out.append('<?'+data+'>')
    def unknown_decl(self,data):self.out.append('<!['+data+']>')
    def result(self):return ''.join(self.out)


def html_mark(source,ref,expression=False):
    parser=Marker(ref,expression);parser.feed(source);parser.close();return parser.result(),parser.markers


def js_quote(value):return json.dumps(value,ensure_ascii=False)

def quasi(value):return value.replace('\\','\\\\').replace('`','\\`').replace('${','\\${').replace('</script','<\\/script')


FALLBACK="""globalThis.VTTUi ||= (source,parameters={}) => globalThis.VTTI18n?.literal(source,parameters) ?? source.replace(/\\{([a-zA-Z0-9_]+)\\}/g,(m,k)=>Object.prototype.hasOwnProperty.call(parameters,k)?String(parameters[k]):m);
globalThis.VTTUiHTML ||= source => globalThis.VTTUi(source).replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[c]));
"""


def prepare(rows):
    items={};files={}
    for row in rows:
        if not row.get('html'):
            key=register(row['de'],row['refs'][0]['file'])
            for ref in row['refs']:
                register(row['de'],ref['file'])
                if not ref.get('explicit'):items.setdefault(ref['file'],[]).append({'source':row['de'],**ref})
        else:
            for ref in row['refs']:
                pattern=row['de']
                for index in range(len(ref['expressions'])):pattern=pattern.replace('{p'+str(index)+'}',f'__VT_EXPR_{index}__')
                marked,markers=html_mark(pattern,ref['file']+':markup',True)
                if markers:items.setdefault(ref['file'],[]).append({'source':row['de'],'html':marked,'markers':markers,**ref})
    for relative,refs in items.items():
        source=(ROOT/relative).read_text();unique={(r['start'],r['end']):r for r in refs};refs=list(unique.values())
        def replace_range(start,end,exclude=None):
            within=[r for r in refs if start<=r['start'] and r['end']<=end and r is not exclude]
            tops=[r for r in within if not any(o['start']<=r['start'] and o['end']>=r['end'] and o is not r for o in within)]
            output=source[start:end]
            for ref in sorted(tops,key=lambda r:r['start'],reverse=True):
                output=output[:ref['start']-start]+render(ref)+output[ref['end']-start:]
            return output
        def render(ref):
            expressions=[replace_range(e['start'],e['end']) for e in ref['expressions']]
            if 'html' in ref:
                pattern=ref['html'];tokens={**{m:'globalThis.VTTUiHTML('+js_quote(value)+')' for m,value in ref['markers'].items()},
                    **{f'__VT_EXPR_{i}__':value for i,value in enumerate(expressions)}}
                pieces=re.split(r'(__VT_UI_\d+__|__VT_EXPR_\d+__)',pattern)
                return '`'+''.join('${'+tokens[p]+'}' if p in tokens else quasi(p) for p in pieces)+'`'
            arguments=''
            if expressions:arguments=',{'+','.join(f'p{i}:({value})' for i,value in enumerate(expressions))+'}'
            return 'globalThis.VTTUi('+js_quote(ref['source'])+arguments+')'
        transformed=replace_range(0,len(source))
        if relative.endswith('.js'):transformed=FALLBACK+transformed
        else:
            # Inline scripts execute independently of deferred external app files.
            pattern=re.compile(r'(<script\b(?![^>]*\bsrc=)[^>]*>)',re.I)
            transformed=pattern.sub(lambda match:match[1]+FALLBACK,transformed,count=1)
        files[relative]=transformed
    return files


def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['scan','apply']);parser.add_argument('js_inventory');args=parser.parse_args()
    rows=json.loads(pathlib.Path(args.js_inventory).read_text());files=prepare(rows)
    for relative in json.loads(SOURCES.read_text()):
        if not relative.endswith('.html'):continue
        source=files.get(relative,(ROOT/relative).read_text());files[relative]=html_mark(source,relative)[0]
    fragments=ROOT/'vtt/play/surfaces/dm.json';values=json.loads(fragments.read_text());values={key:html_mark(value,'vtt/play/surfaces/dm.json#'+key)[0] for key,value in values.items()}
    # Preserve the original source wording separately from translated DE/EN.
    output=ROOT/'tools/i18n/ui-inventory.json';output.write_text(json.dumps(list(REGISTRY.values()),ensure_ascii=False,indent=2)+'\n')
    if args.mode=='apply':
        backup=ROOT/'tools/i18n/source-before-marking.json'
        if backup.exists():raise RuntimeError('Source backup exists: review before another migration')
        backup.write_text(json.dumps({relative:(ROOT/relative).read_text() for relative in [*files,'vtt/play/surfaces/dm.json']},ensure_ascii=False))
        for relative,source in files.items():(ROOT/relative).write_text(source)
        fragments.write_text(json.dumps(values,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'messages':len(REGISTRY),'files':len(files),'mode':args.mode}))
if __name__=='__main__':main()
