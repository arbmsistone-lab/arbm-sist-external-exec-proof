import http.server
import json
import threading
import unittest

from arbm_safe_http import SafeHttpError, _target, request_json


class _Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*_):
        pass
    def do_POST(self):
        length=int(self.headers.get('Content-Length','0'))
        raw=self.rfile.read(length)
        self.send_response(200)
        self.send_header('Content-Type','application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'ok':True,'bytes':len(raw)}).encode())


class SafeHttpTests(unittest.TestCase):
    def test_rejects_non_http_schemes(self):
        for value in ('file:///etc/passwd','ftp://example.com/x','data:text/plain,x'):
            with self.subTest(value=value), self.assertRaisesRegex(SafeHttpError,'HTTP_SCHEME_FORBIDDEN'):
                _target(value)

    def test_rejects_embedded_credentials(self):
        with self.assertRaisesRegex(SafeHttpError,'HTTP_EMBEDDED_CREDENTIALS_FORBIDDEN'):
            _target('https://user:password@example.com/path')

    def test_rejects_plain_http_by_default(self):
        with self.assertRaisesRegex(SafeHttpError,'HTTP_SCHEME_FORBIDDEN'):
            _target('http://127.0.0.1:8080/path')

    def test_https_target_is_normalized(self):
        scheme,host,port,path=_target('https://example.com:8443/a?b=1')
        self.assertEqual((scheme,host,port,path),('https','example.com',8443,'/a?b=1'))

    def test_plain_http_requires_explicit_local_control_plane_opt_in(self):
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),_Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            status,data,_=request_json(
                f'http://127.0.0.1:{server.server_port}/execute',
                method='POST',data=b'abc',headers={'Content-Type':'application/octet-stream'},
                timeout=5,allow_plain_http=True)
            self.assertEqual(status,200)
            self.assertEqual(data,{'ok':True,'bytes':3})
        finally:
            server.shutdown();server.server_close();thread.join()


if __name__=='__main__':
    unittest.main()
