"""Bounded, network-free transformations for untrusted HTML email parts."""
from __future__ import annotations

from dataclasses import dataclass
from html import escape
from html.parser import HTMLParser
from io import BytesIO
from urllib.parse import urlsplit
import base64
import binascii
import codecs
import ipaddress
import re

import nh3
from PIL import Image, UnidentifiedImageError


MAX_HTML_BYTES = 16 * 1024 * 1024
MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_IMAGE_BYTES = 8 * 1024 * 1024
MAX_IMAGE_PIXELS = 4_000_000
TAGS = set('a b blockquote br caption code col colgroup dd del div dl dt em h1 h2 h3 h4 h5 h6 hr i img li ol p pre s small span strong sub sup table tbody td th thead tfoot tr u ul'.split())
DROP_CONTENT = set('script style form iframe frame frameset object embed svg math template noscript textarea select button head title'.split())
ATTRIBUTES = {'*': {'title', 'lang', 'dir', 'style'}, 'a': {'href'},
              'img': {'src', 'alt', 'width', 'height'}, 'table': {'width', 'cellpadding', 'cellspacing'},
              'td': {'colspan', 'rowspan', 'width', 'height', 'align', 'valign'},
              'th': {'colspan', 'rowspan', 'width', 'height', 'align', 'valign'}}
CSS = set('color background-color font-family font-size font-style font-weight line-height text-align text-decoration white-space margin margin-top margin-right margin-bottom margin-left padding padding-top padding-right padding-bottom padding-left border border-top border-right border-bottom border-left border-color border-style border-width border-collapse border-spacing table-layout width height max-width max-height'.split())
CHARSETS = {'utf-8': 'utf-8', 'utf8': 'utf-8', 'windows-1256': 'cp1256', 'cp1256': 'cp1256',
            'windows-1252': 'cp1252', 'iso-8859-1': 'latin-1', 'latin1': 'latin-1'}


def decode_html(source: bytes) -> str:
    if len(source) > MAX_HTML_BYTES:
        raise ValueError('HTML part exceeds the preview size limit')
    if source.startswith(codecs.BOM_UTF8):
        return source.decode('utf-8-sig', errors='replace')
    if source.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return source.decode('utf-16', errors='replace')
    # Encoding discovery is not sanitization; nh3 parses the decoded fragment.
    match = re.search(rb'<meta\b[^>]{0,1024}\bcharset\s*=\s*[\s\x22\x27]*([a-zA-Z0-9_-]+)', source[:8192], re.IGNORECASE)
    encoding = CHARSETS.get(match[1].decode('ascii').lower(), 'utf-8') if match else 'utf-8'
    return source.decode(encoding, errors='replace')


def _web_url(value: str, *, images: bool) -> str | None:
    if images and value.startswith('//'):
        value = 'https:' + value
    if any(ord(c) < 32 or ord(c) == 127 for c in value) or '\\' in value:
        return None
    try:
        parts = urlsplit(value)
        host = (parts.hostname or '').encode('idna').decode('ascii').lower().rstrip('.')
        if parts.scheme.lower() not in ({'https'} if images else {'http', 'https'}) or not host:
            return None
        if parts.username is not None or parts.password is not None or '%' in host:
            return None
        if parts.port is not None and not 1 <= parts.port <= 65535:
            return None
        if images:
            if host == 'localhost' or host.endswith(('.localhost', '.local', '.internal')):
                return None
            try:
                if not ipaddress.ip_address(host).is_global:
                    return None
            except ValueError:
                if re.fullmatch(r'(?:0x[0-9a-f]+|[0-9]+)(?:\.(?:0x[0-9a-f]+|[0-9]+))*', host):
                    return None
    except (ValueError, UnicodeError):
        return None
    return value


def _dimension(value: str) -> str | None:
    value = value.strip().lower()
    if value == 'auto':
        return value
    match = re.fullmatch(r'(\d{1,4}(?:\.\d{1,2})?)(px|%)?', value)
    if not match or float(match[1]) > (100 if match[2] == '%' else 4096):
        return None
    return value


def _style(value: str) -> str | None:
    if any(c in value for c in '\\@\x00'):
        return None
    declarations: list[str] = []
    for declaration in value.split(';'):
        prop, separator, val = declaration.partition(':')
        prop, val = prop.strip().lower(), val.strip()
        if not separator or prop not in CSS or re.search(r'url\s*\(|expression\s*\(|var\s*\(|!', val, re.IGNORECASE):
            continue
        if prop in {'width', 'height', 'max-width', 'max-height'} and _dimension(val) is None:
            continue
        declarations.append(prop + ':' + val)
    return ';'.join(declarations) or None


class _Attributes:
    def __init__(self, allow_remote: bool) -> None:
        self.allow_remote = allow_remote
        self.image_bytes = 0

    def raster(self, value: str) -> str | None:
        match = re.fullmatch(r'data:(image/(?:png|jpeg|gif|webp));base64,([A-Za-z0-9+/=]+)', value, re.IGNORECASE)
        if not match or len(match[2]) > ((MAX_IMAGE_BYTES + 2) // 3) * 4:
            return None
        try:
            raw = base64.b64decode(match[2], validate=True)
            if len(raw) > MAX_IMAGE_BYTES:
                return None
            with Image.open(BytesIO(raw)) as image:
                if image.format != {'image/png': 'PNG', 'image/jpeg': 'JPEG', 'image/gif': 'GIF', 'image/webp': 'WEBP'}[match[1].lower()]:
                    return None
                if image.width * image.height > MAX_IMAGE_PIXELS:
                    return None
                image.seek(0)
                mode = 'RGBA' if image.mode == 'RGBA' or 'transparency' in image.info else 'RGB'
                clean = image.convert(mode)
                output = BytesIO()
                clean.save(output, format='PNG')
                data = output.getvalue()
            if len(data) > MAX_IMAGE_BYTES or self.image_bytes + len(data) > MAX_TOTAL_IMAGE_BYTES:
                return None
        except (ValueError, OSError, binascii.Error, UnidentifiedImageError, Image.DecompressionBombError):
            return None
        self.image_bytes += len(data)
        return 'data:image/png;base64,' + base64.b64encode(data).decode('ascii')

    def __call__(self, tag: str, name: str, value: str) -> str | None:
        if name == 'href':
            return _web_url(value, images=False)
        if name == 'src':
            if value.lower().startswith('data:'):
                return self.raster(value)
            return _web_url(value, images=True) if self.allow_remote else None
        if name == 'style':
            return _style(value)
        if name == 'dir':
            return value.lower() if value.lower() in {'ltr', 'rtl', 'auto'} else None
        if name in {'width', 'height'}:
            return _dimension(value)
        if name in {'colspan', 'rowspan', 'cellspacing', 'cellpadding'}:
            return value if value.isascii() and value.isdecimal() and 0 <= int(value) <= 100 else None
        if name == 'align':
            return value.lower() if value.lower() in {'left', 'right', 'center', 'justify'} else None
        if name == 'valign':
            return value.lower() if value.lower() in {'top', 'middle', 'bottom', 'baseline'} else None
        return value


def sanitize_fragment(source: bytes, *, allow_remote_images: bool = False) -> str:
    text = decode_html(source)
    text = ''.join(c for c in text if c in '\t\n\r' or not (ord(c) < 32 or 127 <= ord(c) <= 159))
    return nh3.clean(text, tags=TAGS, clean_content_tags=DROP_CONTENT, attributes=ATTRIBUTES,
                     attribute_filter=_Attributes(allow_remote_images), strip_comments=True,
                     link_rel='noopener noreferrer', url_schemes={'http', 'https', 'data'},
                     url_relative=lambda value: value if allow_remote_images and value.startswith('//') else None,
                     filter_style_properties=CSS)


@dataclass(frozen=True)
class PreviewDocuments:
    blocked: str
    images: str
    remote_images: int


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.links: list[str] = []
        self.remote_images = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag in {'p', 'div', 'blockquote', 'pre', 'tr', 'table', 'ul', 'ol', 'dl', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br', 'hr'}:
            self.parts.append('\n')
        if tag == 'li':
            self.parts.append('\n- ')
        if tag in {'td', 'th'}:
            self.parts.append('\t')
        if tag == 'a':
            self.links.append(attributes.get('href') or '')
        if tag == 'img':
            self.parts.append('[' + (attributes.get('alt') or 'image') + ']')
            if (attributes.get('src') or '').lower().startswith('https:'):
                self.remote_images += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == 'a' and self.links:
            href = self.links.pop()
            if href:
                self.parts.append(' <' + href + '>')
        if tag in {'p', 'div', 'blockquote', 'pre', 'tr', 'table', 'li', 'ul', 'ol', 'dl', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}:
            self.parts.append('\n')

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def html_to_text(source: bytes) -> str:
    parser = _Text()
    parser.feed(sanitize_fragment(source))
    text = ''.join(parser.parts).replace('\r\n', '\n').replace('\r', '\n')
    text = ''.join(c for c in text if c in '\t\n' or not (ord(c) < 32 or 127 <= ord(c) <= 159))
    return re.sub(r'\n{3,}', '\n\n', text).strip() + '\n'


def _local_uri(value: str) -> str:
    parts = urlsplit(value)
    if parts.scheme != 'file' or parts.netloc or parts.query or parts.fragment or not parts.path.startswith('/'):
        raise ValueError('Preview navigation must use generated local files')
    if any(ord(c) < 32 for c in value):
        raise ValueError('Invalid local preview navigation')
    return escape(value, quote=True)


def _document(fragment: str, other_uri: str, *, images: bool, count: int) -> str:
    navigation = _local_uri(other_uri)
    title = 'aerc Mail preview ' + urlsplit(other_uri).path.rsplit('/', 2)[-2]
    policy = ("default-src 'none'; script-src 'none'; object-src 'none'; base-uri 'none'; "
              "form-action 'none'; frame-src 'none'; connect-src 'none'; font-src 'none'; "
              "media-src 'none'; style-src 'unsafe-inline'; img-src data:" + (' https:' if images else '') + ';')
    label = 'Block images' if images else f'Load images ({count})'
    state = 'Images on · may track opens.' if images else 'Images off · loading may track opens.'
    css = ('body{margin:0 auto;padding:1rem 1rem 4rem;max-width:1000px;background:#fff;color:#222;'
           'font:16px/1.5 sans-serif;overflow-wrap:anywhere}img,table{max-width:100%}'
           '.preview-controls{position:fixed;bottom:0;left:0;right:0;background:#f1f3ed;color:#222;'
           'padding:.35rem .75rem;border-top:1px solid #bac0af;z-index:1000;font:14px/1.4 sans-serif}'
           '.preview-controls a{color:#314d10;font-weight:bold}pre{white-space:pre-wrap}'
           '@media(max-width:240px){body{padding-bottom:8rem}}')
    document = ('<!doctype html><html><head><meta charset="utf-8">'
                '<meta http-equiv="Content-Security-Policy" content="' + escape(policy, quote=True) + '">'
                '<meta name="referrer" content="no-referrer"><title>' + escape(title) + '</title>'
                '<style>' + css + '</style></head><body>'
                '<main dir="auto">' + fragment + '</main>'
                '<footer class="preview-controls">' + state + ' '
                '<a href="' + navigation + '" rel="noopener noreferrer">' + label + '</a>'
                '</footer></body></html>')
    if len(document.encode('utf-8')) > MAX_HTML_BYTES:
        raise ValueError('Rendered preview exceeds the size limit')
    return document


def build_documents(source: bytes, *, blocked_uri: str, images_uri: str) -> PreviewDocuments:
    allowed = sanitize_fragment(source, allow_remote_images=True)
    inspector = _Text()
    inspector.feed(allowed)
    blocked = _document(sanitize_fragment(source), images_uri, images=False, count=inspector.remote_images)
    images = _document(allowed, blocked_uri, images=True, count=inspector.remote_images)
    return PreviewDocuments(blocked, images, inspector.remote_images)
