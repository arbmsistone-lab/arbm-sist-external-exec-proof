"""Strict HTTP transport for ARBM SIST.

Rejects non-HTTP(S) schemes, embedded credentials and hostless URLs.
HTTPS uses Python's default certificate-verifying TLS context. Plain HTTP
must be explicitly opted in by the caller for trusted local/provider control
planes.
"""
from __future__ import annotations

import http.client
import json
from urllib.parse import urlsplit


class SafeHttpError(RuntimeError):
    pass


def _target(url: str, *, allow_plain_http: bool = False):
    parts=urlsplit(str(url or ""))
    if parts.scheme not in ({"https","http"} if allow_plain_http else {"https"}):
        raise SafeHttpError("HTTP_SCHEME_FORBIDDEN")
    if not parts.hostname:
        raise SafeHttpError("HTTP_HOST_REQUIRED")
    if parts.username is not None or parts.password is not None:
        raise SafeHttpError("HTTP_EMBEDDED_CREDENTIALS_FORBIDDEN")
    if parts.fragment:
        raise SafeHttpError("HTTP_FRAGMENT_FORBIDDEN")
    port=parts.port
    host=parts.hostname
    path=parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    return parts.scheme, host, port, path


def request_bytes(url: str, *, method: str = "GET", headers=None, data=None,
                  timeout: float = 30, allow_plain_http: bool = False):
    scheme,host,port,path=_target(url,allow_plain_http=allow_plain_http)
    connection_cls=http.client.HTTPSConnection if scheme=="https" else http.client.HTTPConnection
    connection=connection_cls(host,port=port,timeout=timeout)
    try:
        connection.request(str(method or "GET").upper(),path,body=data,headers=dict(headers or {}))
        response=connection.getresponse()
        raw=response.read()
        return int(response.status),raw,dict(response.getheaders())
    finally:
        connection.close()


def request_json(url: str, *, method: str = "GET", headers=None, data=None,
                 timeout: float = 30, allow_plain_http: bool = False):
    status,raw,response_headers=request_bytes(
        url,method=method,headers=headers,data=data,timeout=timeout,
        allow_plain_http=allow_plain_http)
    try:
        payload=json.loads(raw)
    except (json.JSONDecodeError,UnicodeDecodeError,TypeError):
        payload={}
    return status,payload,response_headers
