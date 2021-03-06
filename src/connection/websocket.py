import struct

import select

DEBUG = 1

def debugmsg(msg):
    if DEBUG:
        print(msg)

class WebSocket:
    def __init__(self, s):
        self.s = s
        self.buf = b""

    def write(self, data, file_transfer=False):
        ft = 0x82 if file_transfer else 0x81

        if type(data) is str:
            data = data.encode("utf-8")

        l = len(data)
        if l < 126:
            hdr = struct.pack(">BB", ft, l)
        else:
            hdr = struct.pack(">BBH", ft, 126, l)
        self.s.send(hdr)
        self.s.send(data)

    def recvexactly(self, sz, timeout=5):
        res = b""
        while sz:
            read_sockets, _, _ = select.select([self.s], [], [], timeout)
            if not read_sockets:
                raise TimeoutError()
            data = self.s.recv(sz)
            if not data:
                raise ConnectionAbortedError()
            res += data
            sz -= len(data)
        return res

    def read(self, size):
        if not self.buf:
            while True:
                hdr = self.recvexactly(2)
                assert len(hdr) == 2
                fl, sz = struct.unpack(">BB", hdr)
                if sz == 126:
                    hdr = self.recvexactly(2)
                    assert len(hdr) == 2
                    (sz,) = struct.unpack(">H", hdr)
                if fl == 0x82 or fl == 0x81:
                    break
                debugmsg("Got unexpected websocket record of type %x, skipping it" % fl)
                while sz:
                    skip = self.s.recv(sz)
                    debugmsg("Skip data: %s" % skip)
                    sz -= len(skip)
            data = self.recvexactly(sz)
            assert len(data) == sz
            self.buf = data

        d = self.buf[:size]
        self.buf = self.buf[size:]
        assert len(d) == size, len(d)
        return d

    def read_all(self, timeout=5):
        read_sockets, _, _ = select.select([self.s], [], [], timeout)
        while read_sockets:
            while True:
                hdr = self.recvexactly(2)
                if len(hdr) != 2:
                    raise ConnectionAbortedError()

                assert len(hdr) == 2
                fl, sz = struct.unpack(">BB", hdr)
                if sz == 126:
                    hdr = self.recvexactly(2)
                    assert len(hdr) == 2
                    (sz,) = struct.unpack(">H", hdr)
                if fl == 0x82 or fl == 0x81:
                    break
                debugmsg("Got unexpected websocket record of type %x, skipping it" % fl)
                while sz:
                    skip = self.s.recv(sz)
                    debugmsg("Skip data: %s" % skip)
                    sz -= len(skip)

            data = self.recvexactly(sz)
            assert len(data) == sz
            self.buf += data
            read_sockets, _, _ = select.select([self.s], [], [], 0)

        ret, self.buf = self.buf, b""
        return ret

    def ioctl(self, req, val):
        assert req == 9 and val == 2