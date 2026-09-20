"""Fail-closed HTTP transport for ARBM SIST.

No implicit redirects. Public remote calls require HTTPS. Plain HTTP is accepted
only for explicit loopback communication used by local OSWorld services.
"""
from __future__ import annotations

import http.client
import ipaddress
import json
import socket
import ssl
from dataclasses import dataclass
from urllib.parse import urlsplit


class SafeHTTPError(RuntimeError):
    def __init__(self, status: int, body: bytes = b"", url: str = ""):
        self.status = int(status)
        self.code = self.status
        self.body = bytes(body or b"")
        self.url = str(url or "")
        super().__init__(f"HTTP {self.status}")

    def read(self) -> bytes:
        return self.body


@dataclass(frozen=True)
class SafeResponse:
    status: int
    body: bytes
    headers: dict

    def read(self) -> bytes:
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def _is_loopback(host: str) -> bool:
    host = str(host or "").strip("[]").casefold()
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _literal_ip_is_public(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(str(host or "").strip("[]"))
    except ValueError:
        return True
    return not (
        ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast
        or ip.is_reserved or ip.is_unspecified
    )


def validate_url(url: str, *, allowed_hosts=(), allow_loopback_http=False, allow_private_http=False):
    parsed = urlsplit(str(url or ""))
    scheme = parsed.scheme.casefold()
    host = (parsed.hostname or "").casefold().rstrip(".")
    if not host or parsed.username is not None or parsed.password is not None:
        raise ValueError("SAFE_HTTP_AUTHORITY_INVALID")
    if parsed.fragment:
        raise ValueError("SAFE_HTTP_FRAGMENT_FORBIDDEN")
    if scheme not in {"https", "http"}:
        raise ValueError("SAFE_HTTP_SCHEME_FORBIDDEN")
    loopback = _is_loopback(host)
    literal_public = _literal_ip_is_public(host)
    literal_private = (not loopback and not literal_public)
    if scheme == "http":
        if loopback and allow_loopback_http:
            pass
        elif literal_private and allow_private_http:
            pass
        else:
            raise ValueError("SAFE_HTTP_PLAINTEXT_FORBIDDEN")
    if scheme == "https" and literal_private:
        raise ValueError("SAFE_HTTP_PRIVATE_IP_FORBIDDEN")
    allowed = tuple(str(x).casefold().rstrip(".") for x in (allowed_hosts or ()) if str(x).strip())
    if allowed and not any(host == item or host.endswith("." + item) for item in allowed):
        raise ValueError("SAFE_HTTP_HOST_NOT_ALLOWLISTED")
    port = parsed.port or (443 if scheme == "https" else 80)
    if not 1 <= int(port) <= 65535:
        raise ValueError("SAFE_HTTP_PORT_INVALID")
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    return scheme, host, int(port), path


def request(url: str, *, method="GET", data=None, headers=None, timeout=30,
            allowed_hosts=(), allow_loopback_http=False, allow_private_http=False,
            max_bytes=8_000_000, raise_for_status=True):
    scheme, host, port, path = validate_url(
        url, allowed_hosts=allowed_hosts, allow_loopback_http=allow_loopback_http,
        allow_private_http=allow_private_http)
    timeout = max(1.0, min(float(timeout), 180.0))
    max_bytes = max(1, min(int(max_bytes), 32_000_000))
    payload = None if data is None else bytes(data)
    safe_headers = {str(k): str(v) for k, v in dict(headers or {}).items()}
    safe_headers.setdefault("User-Agent", "arbm-sist-safe-http/1")
    connection = None
    try:
        if scheme == "https":
            connection = http.client.HTTPSConnection(
                host, port, timeout=timeout, context=ssl.create_default_context())
        else:
            connection = http.client.HTTPConnection(host, port, timeout=timeout)
        connection.request(str(method or "GET").upper(), path, body=payload, headers=safe_headers)
        response = connection.getresponse()
        body = response.read(max_bytes + 1)
        if len(body) > max_bytes:
            raise ValueError("SAFE_HTTP_RESPONSE_TOO_LARGE")
        result = SafeResponse(
            status=int(response.status), body=body,
            headers={str(k).casefold(): str(v) for k, v in response.getheaders()})
        if 300 <= result.status < 400:
            raise ValueError("SAFE_HTTP_REDIRECT_FORBIDDEN")
        if raise_for_status and result.status >= 400:
            raise SafeHTTPError(result.status, result.body, url)
        return result
    except (socket.timeout, TimeoutError):
        raise TimeoutError("SAFE_HTTP_TIMEOUT")
    finally:
        if connection is not None:
            connection.close()


def json_request(url: str, *, method="GET", payload=None, headers=None, timeout=30,
                 allowed_hosts=(), allow_loopback_http=False, allow_private_http=False,
                 max_bytes=8_000_000, raise_for_status=True):
    merged = dict(headers or {})
    data = None
    if payload is not None:
        data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        merged.setdefault("Content-Type", "application/json")
    response = request(
        url, method=method, data=data, headers=merged, timeout=timeout,
        allowed_hosts=allowed_hosts, allow_loopback_http=allow_loopback_http,
        allow_private_http=allow_private_http, max_bytes=max_bytes,
        raise_for_status=raise_for_status)
    try:
        decoded = json.loads(response.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("SAFE_HTTP_JSON_INVALID") from exc
    return response.status, decoded
