import aiohttp
import requests
import ssl
from requests.models import Response, Request
from aiohttp import ClientResponse

async def aiohttp_to_requests_response(aio_resp: ClientResponse) -> Response:
    req_resp = Response()

    # Status & URL
    req_resp.status_code = aio_resp.status
    req_resp.url = str(aio_resp.url)
    req_resp.reason = aio_resp.reason

    req_resp.headers = {k: v for k, v in aio_resp.headers.items()}

    req_resp.encoding = aio_resp.charset or "utf-8"

    req_resp._content = await aio_resp.read()

    for k, v in aio_resp.cookies.items():
        req_resp.cookies.set(k, v.value)

    dummy_req = Request(method=aio_resp.method, url=str(aio_resp.url))
    req_resp.request = dummy_req.prepare()

    return req_resp


def convert_requests_to_aiohttp(session: requests.Session) -> aiohttp.ClientSession:
    headers = dict(session.headers)

    cookie_jar = aiohttp.CookieJar()
    for cookie in session.cookies:
        cookie_jar.update_cookies({cookie.name: cookie.value})

    auth = None
    if session.auth:
        auth = aiohttp.BasicAuth(*session.auth)

    ssl_context = None
    if session.verify is False:
        ssl_context = False  # disable SSL verification
    elif isinstance(session.verify, str):
        ssl_context = ssl.create_default_context(cafile=session.verify)
    elif session.cert:
        # cert may be a path or (cert, key) tuple
        ssl_context = ssl.create_default_context()
        if isinstance(session.cert, tuple):
            ssl_context.load_cert_chain(*session.cert)
        else:
            ssl_context.load_cert_chain(session.cert)

    trust_env = bool(session.proxies)

    return aiohttp.ClientSession(
        headers=headers,
        cookie_jar=cookie_jar,
        auth=auth,
        trust_env=trust_env,
        connector=aiohttp.TCPConnector(ssl=ssl_context),
    )
