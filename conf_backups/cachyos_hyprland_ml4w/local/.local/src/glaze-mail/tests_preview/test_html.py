from __future__ import annotations

from html.parser import HTMLParser
from io import BytesIO
from unittest import TestCase
import base64
import importlib
import importlib.util
import random
import re

from PIL import Image


class Elements(HTMLParser):
    def __init__(self, text: str) -> None:
        super().__init__()
        self.items: list[tuple[str, dict[str, str | None]]] = []
        self.feed(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.items.append((tag, dict(attrs)))


def raster(width: int = 1, height: int = 1, noise: bool = False) -> bytes:
    image = (Image.frombytes('RGB', (width, height), random.Random(7).randbytes(width * height * 3))
             if noise else Image.new('RGB', (width, height), 'green'))
    stream = BytesIO()
    image.save(stream, format='PNG')
    return stream.getvalue()


def data_image(data: bytes, mime: str = 'image/png') -> str:
    return f'data:{mime};base64,' + base64.b64encode(data).decode('ascii')


class HtmlTests(TestCase):
    def setUp(self) -> None:
        self.assertIsNotNone(importlib.util.find_spec('preview_html'), 'The HTML safety engine is missing')
        self.module = importlib.import_module('preview_html')

    def test_scripts_and_active_content_removed_with_arabic_preserved(self) -> None:
        source = ('<script>alert(1)</script><style>@import "https://bad.invalid/x";</style>'
                  '<form>private form<input></form><iframe src="https://bad.invalid"></iframe>'
                  '<svg><script>bad</script></svg><math><mi>x</mi></math>'
                  '<meta http-equiv="refresh" content="0;url=https://bad.invalid">'
                  '<base href="https://bad.invalid"><p onclick="bad()" id="header" class="header" dir="rtl">مرحبا</p>')
        result = self.module.sanitize_fragment(source.encode())
        self.assertEqual(result, '<p dir="rtl">مرحبا</p>')

    def test_links_only_allow_deliberate_web_navigation(self) -> None:
        links = ''.join(f'<a href="{url}" ping="https://tracker.invalid">link</a>' for url in (
            'https://example.invalid/a', 'http://example.invalid/', '/relative', '//else.invalid/path',
            'file:///etc/passwd', 'javascript:alert(1)', 'data:text/html,bad', 'mailto:a@example.invalid'))
        elements = Elements(self.module.sanitize_fragment(links.encode())).items
        hrefs = [attrs['href'] for tag, attrs in elements if tag == 'a' and 'href' in attrs]
        self.assertEqual(hrefs, ['https://example.invalid/a', 'http://example.invalid/'])
        self.assertTrue(all('ping' not in attrs for _, attrs in elements))
        self.assertTrue(all(attrs.get('rel') == 'noopener noreferrer' for tag, attrs in elements if tag == 'a'))

    def test_css_only_preserves_bounded_non_fetch_formatting(self) -> None:
        source = b'<p style="color:red;position:fixed;background-image:url(https://bad.invalid);width:999999px">text</p>'
        attrs = Elements(self.module.sanitize_fragment(source)).items[0][1]
        self.assertNotIn('position', attrs.get('style', ''))
        self.assertNotIn('url(', attrs.get('style', ''))
        self.assertNotIn('999999', attrs.get('style', ''))
        safe = self.module.sanitize_fragment(b'<p style="color:red;font-weight:bold;width:80%">text</p>')
        self.assertIn('color:red', safe)
        self.assertIn('font-weight:bold', safe)

    def test_charset_decoding_and_input_limit(self) -> None:
        self.assertEqual(self.module.decode_html('مرحبا'.encode('utf-8-sig')), 'مرحبا')
        self.assertEqual(self.module.decode_html('مرحبا'.encode('utf-16')), 'مرحبا')
        source = b'<meta charset="windows-1256">' + 'مرحبا'.encode('cp1256')
        self.assertIn('مرحبا', self.module.decode_html(source))
        self.assertNotIn('<script', self.module.decode_html(b'<meta charset="utf-7">+ADw-script+AD4-'))
        self.assertIn('\ufffd', self.module.decode_html(b'bad\xffutf8'))
        with self.assertRaises(ValueError):
            self.module.decode_html(b'x' * (16 * 1024 * 1024 + 1))

    def test_embedded_raster_validated_and_spoofs_rejected(self) -> None:
        good = data_image(raster())
        for url, retained in ((good, True), (data_image(raster(), 'image/jpeg'), False),
                              (data_image(b'<svg/>', 'image/svg+xml'), False), ('data:image/png;base64,!!!!', False)):
            with self.subTest(url=url[:35]):
                result = self.module.sanitize_fragment(f'<img alt="readable" src="{url}">'.encode())
                attrs = Elements(result).items[0][1]
                self.assertEqual('src' in attrs, retained)
                self.assertEqual(attrs['alt'], 'readable')

    def test_remote_images_are_explicit_https_only_opt_in(self) -> None:
        urls = ['https://images.example.invalid/x.png', '//images.example.invalid/y.png',
                'http://images.example.invalid/x.png', 'https://127.0.0.1/x', 'https://[::1]/x',
                'https://localhost/x', 'https://192.168.1.1/x', 'https://host.local/x', 'file:///tmp/x']
        source = ''.join(f'<img src="{url}" alt="image">' for url in urls).encode()
        blocked = Elements(self.module.sanitize_fragment(source)).items
        self.assertTrue(all('src' not in attrs for _, attrs in blocked))
        allowed = Elements(self.module.sanitize_fragment(source, allow_remote_images=True)).items
        self.assertEqual([attrs['src'] for _, attrs in allowed if 'src' in attrs],
                         ['https://images.example.invalid/x.png', 'https://images.example.invalid/y.png'])

    def test_image_byte_pixel_and_total_limits(self) -> None:
        for image in (raster(1024, 1024, noise=True), raster(2001, 2000)):
            result = self.module.sanitize_fragment(f'<img src="{data_image(image)}" alt="large">'.encode())
            self.assertNotIn('src', Elements(result).items[0][1])
        medium = data_image(raster(750, 700, noise=True))
        source = ('<img src="' + medium + '">') * 6
        result = Elements(self.module.sanitize_fragment(source.encode())).items
        kept = [attrs['src'] for _, attrs in result if 'src' in attrs]
        self.assertEqual(len(kept), 5)
        self.assertLessEqual(sum(len(base64.b64decode(url.split(',', 1)[1])) for url in kept), 8 * 1024 * 1024)

    def test_malformed_markup_cannot_restore_active_attributes(self) -> None:
        source = b'<p><img src=x onerror=alert(1)><div><a href="java&#x09;script:alert(1)">link</a></p>'
        result = Elements(self.module.sanitize_fragment(source)).items
        self.assertTrue(all(not key.lower().startswith('on') for _, attrs in result for key in attrs))
        self.assertTrue(all('href' not in attrs and 'src' not in attrs for _, attrs in result))

    def test_browser_documents_have_distinct_image_policies_and_trusted_controls(self) -> None:
        self.assertTrue(hasattr(self.module, 'build_documents'), 'Private browser documents are not implemented')
        source = b'<p id="preview-controls" class="preview-controls">Body</p><img src="https://images.example.invalid/x">'
        pages = self.module.build_documents(source, blocked_uri='file:///private/blocked.html', images_uri='file:///private/images.html')
        self.assertEqual(pages.remote_images, 1)
        self.assertNotEqual(pages.blocked, pages.images)
        policies: list[str] = []
        for document in (pages.blocked, pages.images):
            policy = next(attrs['content'] for tag, attrs in Elements(document).items
                          if tag == 'meta' and attrs.get('http-equiv') == 'Content-Security-Policy')
            self.assertIsNotNone(policy)
            policies.append(policy)
            self.assertIn("script-src 'none'", policy)
            self.assertIn("connect-src 'none'", policy)
            self.assertIn('no-referrer', document)
            self.assertLess(document.index('Content-Security-Policy'), document.index('<p>Body</p>'))
            self.assertEqual(document.count('class="preview-controls"'), 1)
        self.assertIn('img-src data:;', policies[0])
        self.assertIn('img-src data: https:;', policies[1])
        self.assertIn('href="file:///private/images.html"', pages.blocked)
        self.assertIn('Load images', pages.blocked)
        self.assertIn('href="file:///private/blocked.html"', pages.images)
        self.assertIn('Block images', pages.images)
        self.assertIn('track opens', pages.blocked)
        with self.assertRaises(ValueError):
            self.module.build_documents(b'body', blocked_uri='javascript:alert(1)', images_uri='file:///private/images.html')

    def test_image_notice_is_one_short_line_with_working_local_toggle(self) -> None:
        pages = self.module.build_documents(b'<p>Body</p>', blocked_uri='file:///private/blocked.html',
                                            images_uri='file:///private/images.html')
        for page, destination in ((pages.images, 'file:///private/blocked.html'),
                                  (pages.blocked, 'file:///private/images.html')):
            footer = page.split('<footer class="preview-controls">', 1)[1].split('</footer>', 1)[0] if '<footer' in page else ''
            self.assertTrue(footer, 'Compact image controls belong after the message, at the window bottom')
            self.assertGreater(page.index('<footer'), page.index('</main>'))
            self.assertLessEqual(len(re.sub('<[^>]+>', '', footer)), 80)
            self.assertNotIn('<br', footer)
            self.assertIn('may track opens.', footer)
            links = [attrs['href'] for tag, attrs in Elements(footer).items if tag == 'a']
            self.assertEqual(links, [destination])
        self.assertIn('Images on · may track opens.', pages.images)

    def test_terminal_rendering_preserves_readable_text_not_active_sequences(self) -> None:
        self.assertTrue(hasattr(self.module, 'html_to_text'), 'Safe terminal HTML text is not implemented')
        source = ('<h2>مرحبا</h2><p>ikIK &amp; useful</p><ul><li>first</li></ul>'
                  '<table><tr><td>A</td><td>B</td></tr></table>'
                  '<a href="https://example.invalid/">website</a><img alt="logo" src="https://bad.invalid/">'
                  '<script>bad()</script>\x1b]52;c;ZXZpbA==\x07\x9b31m\r\nend')
        result = self.module.html_to_text(source.encode())
        for text in ('مرحبا', 'ikIK & useful', 'first', 'A\tB', 'website', 'https://example.invalid/', 'logo', 'end'):
            self.assertIn(text, result)
        self.assertNotIn('bad()', result)
        self.assertNotIn('\r', result)
        self.assertTrue(all(c in '\t\n' or not (ord(c) < 32 or 127 <= ord(c) <= 159) for c in result))

    def test_browser_page_limit_is_enforced_after_rendering(self) -> None:
        self.assertTrue(hasattr(self.module, 'build_documents'), 'Private browser documents are not implemented')
        source = b'x' * (16 * 1024 * 1024)
        with self.assertRaises(ValueError):
            self.module.build_documents(source, blocked_uri='file:///private/blocked.html', images_uri='file:///private/images.html')

    def test_browser_title_is_unique_to_generated_preview_not_email_subject(self) -> None:
        identifier = '7' * 32
        pages = self.module.build_documents(b'<title>fake</title><p>body</p>',
                                            blocked_uri=f'file:///private/{identifier}/blocked.html',
                                            images_uri=f'file:///private/{identifier}/images.html')
        for page in (pages.blocked, pages.images):
            self.assertIn('<title>aerc Mail preview ' + identifier + '</title>', page)
            self.assertNotIn('<title>fake', page)
