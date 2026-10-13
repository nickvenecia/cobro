"""Talking to a web address safely (the AI providers; the updater has its own in core/update.py).

An API key in a request's headers must never be sent on to wherever a redirect points, so redirects are never
followed: a redirect comes back as an error instead. Certificates are always checked (core/net.py).
"""

from __future__ import annotations

import urllib.request

from cobro.core.net import ssl_context


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # redirects are never followed with an API key on board


_opener = urllib.request.build_opener(_NoRedirect(), urllib.request.HTTPSHandler(context=ssl_context()))
_direct = urllib.request.build_opener(  # for this computer: never through a proxy
    _NoRedirect(), urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=ssl_context())
)


def open_no_redirect(req: urllib.request.Request, timeout: float, direct: bool = False):
    """Open `req` without following redirects. A redirect comes back as an HTTPError. `direct`: skip any
    proxy (a model on this computer: its key must not travel through a proxy in plain http)."""
    return (_direct if direct else _opener).open(req, timeout=timeout)
