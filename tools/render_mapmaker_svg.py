#!/usr/bin/env python3
"""Offline technical SVG rasterization using an existing Playwright Chromium.
No AI, network requests, script content or external SVG resources are allowed.
"""
import argparse,base64,os,re
from pathlib import Path
from playwright.sync_api import sync_playwright

def render_svg(data, output):
    text=data.decode('utf-8-sig')
    if re.search(r'<(?:script|foreignObject|iframe)\b|<!ENTITY|<!DOCTYPE|\bon\w+\s*=',text,re.I):
        raise ValueError('Active SVG content is not allowed')
    for ref in re.findall(r'(?:href|src)\s*=\s*["\']([^"\']+)',text,re.I):
        if not ref.startswith(('#','data:image/')):raise ValueError('External SVG reference: '+ref)
    for ref in re.findall(r'url\(\s*["\']?([^\s)"\']+)',text):
        if not ref.startswith(('#','data:image/')):raise ValueError('External SVG CSS reference')
    with sync_playwright() as p:
        opts={'headless':True,'args':['--no-sandbox']}
        if os.environ.get('MAPMAKER_CHROMIUM'):opts['executable_path']=os.environ['MAPMAKER_CHROMIUM']
        browser=p.chromium.launch(**opts);page=browser.new_page();page.route('**/*',lambda route:route.abort())
        result=page.evaluate('''async (text) => {
            const svg = new DOMParser().parseFromString(text, 'image/svg+xml').documentElement;
            if (svg.localName !== 'svg') throw new Error('Invalid SVG');
            document.body.appendChild(document.importNode(svg, true));
            const mounted = document.querySelector('svg');
            const b = mounted.getBBox();
            if (!(b.width > 0 && b.height > 0)) throw new Error('Empty SVG');
            const scale = Math.min(1, 4092 / Math.max(b.width, b.height));
            mounted.setAttribute('viewBox', `${b.x-2} ${b.y-2} ${b.width+4} ${b.height+4}`);
            const w = Math.ceil((b.width+4)*scale), h = Math.ceil((b.height+4)*scale);
            mounted.setAttribute('width', w); mounted.setAttribute('height', h);
            const xml = new XMLSerializer().serializeToString(mounted);
            const img = new Image(); img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(xml)));
            await img.decode();
            const c = document.createElement('canvas'); c.width=w; c.height=h;
            c.getContext('2d').drawImage(img,0,0,w,h);return c.toDataURL('image/png').split(',')[1];
        }''',text)
        browser.close()
    Path(output).write_bytes(base64.b64decode(result))
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('input',type=Path);a.add_argument('output',type=Path);v=a.parse_args();render_svg(v.input.read_bytes(),v.output)
