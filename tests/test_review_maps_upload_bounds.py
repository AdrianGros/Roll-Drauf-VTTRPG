"""Bound image allocation before decode and reject stale upload completions."""
import io
import struct

from PIL import Image
import pytest
from playwright.sync_api import expect
from tests.test_mapmaker_browser import browser, open_editor, preview_origin  # noqa: F401


def raster(format_, size=(32, 16), color="red"):
    output = io.BytesIO()
    Image.new("RGB", size, color).save(output, format=format_)
    return output.getvalue()


def open_upload(open_editor):
    ed = open_editor(choose_template=False)
    ed.page.locator("#newEmpty").click()
    ed.tool("stamp")
    ed.page.locator("#ownUploadBtn").click()
    return ed


def file(name, data, mime="image/png"):
    return dict(name=name, buffer=data, mimeType=mime)


def png_header(width, height):
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I4sIIBBBBBI", 13, b"IHDR", width, height, 8, 6, 0, 0, 0, 0)


def jpeg_header(width, height):
    return b"\xff\xd8\xff\xc0" + struct.pack(">HBHHB", 8, 8, height, width, 0)


def webp_header(width, height, extended=False):
    if extended:
        data = b"\0" * 4 + (width - 1).to_bytes(3, "little") + (height - 1).to_bytes(3, "little")
        chunk = b"VP8X" + struct.pack("<I", len(data)) + data
    else:
        data = b"\x2f" + struct.pack("<I", (width - 1) | (height - 1) << 14)
        chunk = b"VP8L" + struct.pack("<I", len(data)) + data + b"\0"
    return b"RIFF" + struct.pack("<I", 4 + len(chunk)) + b"WEBP" + chunk


def test_large_or_ambiguous_headers_never_reach_bitmap_decoder(open_editor):
    ed = open_upload(open_editor)
    page = ed.page
    page.evaluate("() => {window.__decodeCalls=0;window.createImageBitmap=async()=>{window.__decodeCalls++;throw new Error('decoder must not run');}}")
    inputs = [
        file("wide.png", png_header(8193, 1)),
        file("many.png", png_header(4096, 4096)),
        file("wide.jpg", jpeg_header(8193, 1), "image/jpeg"),
        file("many.jpg", jpeg_header(4096, 4096), "image/jpeg"),
        file("wide.webp", webp_header(8193, 1), "image/webp"),
        file("many.webp", webp_header(4096, 4096, True), "image/webp"),
        file("spoof.png", b"<svg onload='alert(1)'/>"),
        file("short.jpg", b"\xff\xd8\xff\xe1\x00\x20x", "image/jpeg"),
        file("short.webp", b"RIFF\0\0\0\0WEBP", "image/webp"),
    ]
    for candidate in inputs:
        page.locator("#ownUploadFile").set_input_files(candidate)
        expect(page.locator("#ownUploadError")).to_be_visible()
        expect(page.locator("#ownUploadSave")).to_be_disabled()
    assert page.evaluate("window.__decodeCalls") == 0
    assert page.locator("#ownUploadPreview").evaluate("c=>[c.width,c.height]") == [1, 1]
    # JPEG metadata segments longer than the bounded header also fail before
    # decode. The reader must never load the full 32MiB input into JS memory.
    result = page.evaluate("""async()=>{const {uploadDimensions}=await import('/mapmaker/js/asset-dialogs.js');let read=0;const f={type:'image/jpeg',size:32*1024*1024,slice:(a,b)=>{read=b-a;return new Blob([new Uint8Array(b-a)]);}};return [await uploadDimensions(f),read];}""")
    assert result == [None, 256 * 1024]
    ed.assert_clean()


@pytest.mark.parametrize("format_,mime,extension", [("PNG", "image/png", "png"), ("JPEG", "image/jpeg", "jpg"), ("WEBP", "image/webp", "webp")])
def test_real_bounded_formats_still_load(open_editor, format_, mime, extension):
    ed = open_upload(open_editor)
    page = ed.page
    page.locator("#ownUploadFile").set_input_files(file("small." + extension, raster(format_), mime))
    expect(page.locator("#ownUploadSave")).to_be_enabled()
    expect(page.locator("#ownCropW")).to_have_value("32")
    expect(page.locator("#ownCropH")).to_have_value("16")
    assert page.locator("#ownUploadError").is_hidden()
    ed.assert_clean()


def test_out_of_order_decode_close_and_reopen_discard_and_close_stale_bitmaps(open_editor):
    ed = open_upload(open_editor)
    page = ed.page
    page.evaluate("""()=>{const decode=window.createImageBitmap.bind(window);window.__pending=[];window.__closed=[];
      window.createImageBitmap=async(file)=>{const bitmap=await decode(file),close=bitmap.close.bind(bitmap);bitmap.close=()=>{window.__closed.push(file.name);close();};return new Promise(resolve=>window.__pending.push({name:file.name,finish:()=>resolve(bitmap)}));};}""")
    page.locator("#ownUploadFile").set_input_files(file("older.png", raster("PNG", (16, 8))))
    page.wait_for_function("() => window.__pending.length===1")
    page.locator("#ownUploadFile").set_input_files(file("newer.png", raster("PNG", (32, 16), "blue")))
    page.wait_for_function("() => window.__pending.length===2")
    page.evaluate("window.__pending[1].finish()")
    expect(page.locator("#ownCropW")).to_have_value("32")
    page.evaluate("window.__pending[0].finish()")
    page.wait_for_function("() => window.__closed.includes('older.png')")
    expect(page.locator("#ownCropW")).to_have_value("32")
    expect(page.locator("#ownUploadLabel")).to_have_value("newer")
    expect(page.locator("#ownUploadSave")).to_be_enabled()
    page.locator("#ownUploadFile").set_input_files(file("closed.png", raster("PNG")))
    page.wait_for_function("() => window.__pending.length===3")
    page.locator("#ownUploadCancel").click()
    page.locator("#ownUploadBtn").click()
    page.evaluate("window.__pending[2].finish()")
    page.wait_for_function("() => window.__closed.includes('closed.png')")
    expect(page.locator("#ownUploadSave")).to_be_disabled()
    expect(page.locator("#ownUploadLabel")).to_have_value("Eigenes Bild")
    assert page.locator("#ownUploadPreview").evaluate("c=>[c.width,c.height]") == [1, 1]
    ed.assert_clean()


def test_stale_header_completion_does_not_start_decode(open_editor):
    ed = open_upload(open_editor)
    page = ed.page
    page.evaluate("""()=>{const slice=File.prototype.slice,decode=window.createImageBitmap.bind(window);window.__decodeNames=[];
      File.prototype.slice=function(...args){const blob=slice.apply(this,args);if(this.name==='slow.png')return {arrayBuffer:()=>new Promise(resolve=>window.__finishHeader=async()=>resolve(await blob.arrayBuffer()))};return blob;};
      window.createImageBitmap=(file)=>{window.__decodeNames.push(file.name);return decode(file);};}""")
    page.locator("#ownUploadFile").set_input_files(file("slow.png", raster("PNG")))
    page.wait_for_function("() => typeof window.__finishHeader==='function'")
    page.locator("#ownUploadFile").set_input_files(file("fast.png", raster("PNG", (24, 12))))
    expect(page.locator("#ownCropW")).to_have_value("24")
    page.evaluate("window.__finishHeader()")
    assert page.evaluate("window.__decodeNames") == ["fast.png"]
    ed.assert_clean()
