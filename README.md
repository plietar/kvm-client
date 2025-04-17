# A client for remote KVM

This client remotely connects to the BMC on rack-mounted server and displays
the server's video output locally. It also allows keystrokes to be sent to the
server for remote control. The BMC exists outside of the operating system and
main CPU, making this suitable for remote administration of the BIOS
configuration and supervision of the early boot stages, before and SSH server
is available.

Typically these servers expose a web interface, from which a Java applet called
JViewer can be run. Unfortunately the web interface uses an old TLS version,
causing modern browsers to refuse to connect to it.

This has only been tested on a PowerEdge C6100. Other Dell (and possibly
non-Dell) servers may be supported.

## Usage
### KVM mode

```
kvm-client connect 10.0.0.1 --username root --password itsme
```

Once the client is connected to the remote machine, it will open up a console
mirroring the machine's video output.

### Proxy mode

```
kvm-client proxy 10.0.0.1 --port 8080
```

This sets up a simple proxy on the specified port, and forwards any connection
to the given IP address using TLSv1.0. It can be used to workaround the
security restrictions of modern browsers that refuse to connect to such an
outdated and insecure protocol version. You can visit
`http://localhost:8080/login.asp` to access the BMC administration page.

The proxy is very dumb and does not perform any rewritting of the responses,
which makes it particularly brittle. The BMC uses absolute redirects, using
`https://localhost:8080/...` as the destination URL and overriding the
protocol. Additionally, the `.jnlp` of the Java Applet includes the URL of the
Java `.jar` files, but these will start with `https://localhost/Java/...`

The proxy does not improve the security of the connection in any way. The
connections between the server and the proxy still uses an outdated TLS
version, and the connection between the proxy and your browser uses plain HTTP.
It just serves as a workaround for browser restrictions.

## Limitations

A lot of auixiliary controls are not implemented, such as remote mounting of
ISOs, bandwidth control, mouse inputs, ...

The video feed packet format suggests that RC4 encryption may optionally be
used. Since I did not encounter any encrypted packets, I did not implement
decryption.

The video feed decoder only supports one of two compression modes. If the video
card uses the unsupported mode, the client will crash. It's not clear when
exactly does the card switch modes. In my experience, WebBIOS, GRUB and Wayland
compositors cause this to happen.

There exists [an open source decoder written in C][aspeed_codec], targetting
WebAssembly for the other compression mode. It should be possible to port it to
Python, or to link to the relevant parts of the C code.

[aspeed_codec]: https://github.com/AspeedTech-BMC/aspeed_codec

## Protocol details

The BMC has its own IP address, running an HTTP server. In addition to basic
sensor reading and control over chassis power, the web page hosts a Java
applet that can act as a remote video console.

The Java Applet connects to the BMC over port 7578. The protocol uses a simple
[type-length-value][TLV] style encoding. The 7-byte header is composed of the
type (1 byte), the length (4 bytes, litte endian) and two additional unknown
bytes. The header is immediately followed by the payload. The length field only
includes the payload bytes, not the 7 header bytes.

[TLV]: https://en.wikipedia.org/wiki/Type%E2%80%93length%E2%80%93value

| Type |   Direction   | Description | Payload |
|------|---------------|-------------|---------|
| 0x23 | Client to BMC | Authentication request | ASCII-encoded authentication token |
| 0x24 | BMC to Client | Authentication result  | A single byte, 1 for success and 0 for a failure |
| 0x05 | BMC to Client | Video feed | See below |
| 0x05 | Client to BMC | Keyboard and Mouse input | See below |

### Video feed

As soon as the client is authenticated, the BMC will start sending out regular
video packets. Each video packet starts with its own header which includes a
lot of information, including the display resolution, frame number,
encryptions, ...

The rest of the packet is a bit stream. Each block of 4 bytes should be read as
a little-endian word (least significant byte first). From that word, bitfields
of varying lengths may be read starting with the most-significant bits. A
bitfield may straddle two bytes or even two words.

Packets only include parts of the image that have changed. The change described
by the packet should be applies to the in-memory frame buffer maintained by the
receiver. The bitstreams describes a sequence of groups, each group
representing an 8 by 8 grid of pixels.

Each group may optionally include its coordinates. If not specified, the
coordinates increment automatically from the previous received group.

There are two broad compression modes:

- In the "basic" mode, each group defines a palette of 2^k colours, where k
    ranges from 0 to 2, inclusive. Each of the 64 pixels in the group is
    then represented as k bits, which are used to index into the palette.
    The colours are represented in [YUV-space][YUV], using one byte per
    component.

- The secondary mode is much more complicated and seems to be inspired from
    JPEG encoding. It uses Huffman encoding and discrete cosine transforms
    (DCT).

[YUV]: https://en.wikipedia.org/wiki/Y%E2%80%B2UV

### Keyboard and Mouse

TBD

## Future directions

Ideally I would like to make this a web-based client instead of a Python
desktop application. From one instance of the server one should be able to
access any number of machines. The server can be hosted on a small device (eg.
a Raspberry Pi) located on the BMCs network.

The video decoding could either remain implemented in Python server-side, and
re-encoded into a standard video format that can easily be displayed in a
modern browser, or the decoder could be reimplemented in a client friendly
language (JavaScript or compiled to WebAssembly). The server would merely act
as a tunnel between a WebSocket and a TCP connection to the BMC.
