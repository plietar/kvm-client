import http
import re
import ssl
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
ctx.options |= 0x4  # OP_LEGACY_SERVER_CONNECT
ctx.set_ciphers("ALL:@SECLEVEL=0")


def login(host: str, username: str, password: str) -> bytes:
    url = f"https://{host}/rpc/WEBSES/create.asp"
    response = urlopen(
        url,
        context=ctx,
        data=urlencode(
            {
                "WEBVAR_USERNAME": username,
                "WEBVAR_PASSWORD": password,
            }
        ).encode("ascii"),
    )

    data = response.read()
    m = re.search(rb"'SESSION_COOKIE'\s*:\s*'([a-zA-Z0-9]*)'", data)
    if not m:
        raise ValueError("Web portal authentication failed")
    return m.group(1)


@dataclass
class ConnectionParameters:
    hostname: str
    port: int
    token: bytes


def get_kvm_parameters(host: str, cookie: bytes) -> ConnectionParameters:
    url = f"https://{host}/Java/jviewer.jnlp"
    request = Request(
        url, headers={"Cookie": f"SessionCookie={cookie.decode('ascii')}"}
    )
    response = urlopen(request, context=ctx)
    try:
        data = response.read()
    except http.client.IncompleteRead as e:
        data = e.partial

    root = ET.fromstring(data)
    args = [a.text for a in root.findall("./application-desc/argument")]

    assert args[0] is not None
    assert args[1] is not None
    assert args[2] is not None
    return ConnectionParameters(
        hostname=args[0], port=int(args[1]), token=args[2].encode("ascii")
    )
