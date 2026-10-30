"""qr.py -- a QR code for the classroom address, standard library only.

Pupils join the lesson server from a school PC or a phone. Typing
"http://192.168.0.23:5173" on a phone keyboard is the single slowest step of a
lesson start, so the teacher's screen shows the address as a QR code as well.

There is no package to install on a school laptop and the classroom may have no
internet, so the encoder is written out here: byte mode, error-correction level
M, versions 1-10 (up to 213 bytes, far more than an address needs), all eight
masks scored by the standard penalty rules. The tables and the construction
follow ISO/IEC 18004; `test_qr.py` checks the Reed-Solomon arithmetic against
the standard's worked example and, where a decoder is available, decodes the
symbol back.

    svg = qr.svg("http://192.168.0.23:5173/")
"""
from __future__ import annotations

# ECC level M, index = version (0 unused)
_ECC_PER_BLOCK_M = [-1, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26]
_BLOCKS_M = [-1, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5]
_FORMAT_ECL_M = 0          # format-information bits for level M
MAX_VERSION = 10


def _gf_mul(x: int, y: int) -> int:
    z = 0
    for i in reversed(range(8)):
        z = (z << 1) ^ ((z >> 7) * 0x11D)
        z ^= ((y >> i) & 1) * x
    return z


def rs_divisor(degree: int) -> list[int]:
    out = [0] * (degree - 1) + [1]
    root = 1
    for _ in range(degree):
        for j in range(degree):
            out[j] = _gf_mul(out[j], root)
            if j + 1 < degree:
                out[j] ^= out[j + 1]
        root = _gf_mul(root, 0x02)
    return out


def rs_remainder(data: list[int], divisor: list[int]) -> list[int]:
    out = [0] * len(divisor)
    for b in data:
        factor = b ^ out.pop(0)
        out.append(0)
        for i, coef in enumerate(divisor):
            out[i] ^= _gf_mul(coef, factor)
    return out


def _raw_modules(ver: int) -> int:
    n = (16 * ver + 128) * ver + 64
    if ver >= 2:
        k = ver // 7 + 2
        n -= (25 * k - 10) * k - 55
        if ver >= 7:
            n -= 36
    return n


def _data_codewords(ver: int) -> int:
    return _raw_modules(ver) // 8 - _ECC_PER_BLOCK_M[ver] * _BLOCKS_M[ver]


def _alignment_positions(ver: int) -> list[int]:
    if ver == 1:
        return []
    k = ver // 7 + 2
    size = ver * 4 + 17
    step = (ver * 8 + k * 3 + 5) // (k * 4 - 4) * 2
    return list(reversed([size - 7 - i * step for i in range(k - 1)] + [6]))


class _Symbol:
    def __init__(self, ver: int):
        self.ver = ver
        self.size = ver * 4 + 17
        self.m = [[False] * self.size for _ in range(self.size)]
        self.fn = [[False] * self.size for _ in range(self.size)]

    def set_fn(self, x: int, y: int, dark: bool) -> None:
        self.m[y][x] = dark
        self.fn[y][x] = True

    def draw_function_patterns(self) -> None:
        s = self.size
        for i in range(s):
            self.set_fn(6, i, i % 2 == 0)
            self.set_fn(i, 6, i % 2 == 0)
        for cx, cy in ((3, 3), (s - 4, 3), (3, s - 4)):
            for dy in range(-4, 5):
                for dx in range(-4, 5):
                    x, y = cx + dx, cy + dy
                    if 0 <= x < s and 0 <= y < s:
                        self.set_fn(x, y, max(abs(dx), abs(dy)) not in (2, 4))
        pos = _alignment_positions(self.ver)
        n = len(pos)
        for i in range(n):
            for j in range(n):
                if (i == 0 and j == 0) or (i == 0 and j == n - 1) or (i == n - 1 and j == 0):
                    continue
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        self.set_fn(pos[i] + dx, pos[j] + dy, max(abs(dx), abs(dy)) != 1)
        self.draw_format(0)
        if self.ver >= 7:
            rem = self.ver
            for _ in range(12):
                rem = (rem << 1) ^ ((rem >> 11) * 0x1F25)
            bits = self.ver << 12 | rem
            for i in range(18):
                bit = (bits >> i) & 1 == 1
                a, b = s - 11 + i % 3, i // 3
                self.set_fn(a, b, bit)
                self.set_fn(b, a, bit)

    def draw_format(self, mask: int) -> None:
        data = _FORMAT_ECL_M << 3 | mask
        rem = data
        for _ in range(10):
            rem = (rem << 1) ^ ((rem >> 9) * 0x537)
        bits = (data << 10 | rem) ^ 0x5412
        s = self.size

        def bit(i):
            return (bits >> i) & 1 == 1
        for i in range(6):
            self.set_fn(8, i, bit(i))
        self.set_fn(8, 7, bit(6))
        self.set_fn(8, 8, bit(7))
        self.set_fn(7, 8, bit(8))
        for i in range(9, 15):
            self.set_fn(14 - i, 8, bit(i))
        for i in range(8):
            self.set_fn(s - 1 - i, 8, bit(i))
        for i in range(8, 15):
            self.set_fn(8, s - 15 + i, bit(i))
        self.set_fn(8, s - 8, True)

    def draw_codewords(self, data: list[int]) -> None:
        s, i = self.size, 0
        right = s - 1
        while right >= 1:
            if right == 6:
                right = 5
            for vert in range(s):
                for j in range(2):
                    x = right - j
                    upward = ((right + 1) & 2) == 0
                    y = (s - 1 - vert) if upward else vert
                    if not self.fn[y][x] and i < len(data) * 8:
                        self.m[y][x] = (data[i >> 3] >> (7 - (i & 7))) & 1 == 1
                        i += 1
            right -= 2

    def apply_mask(self, mask: int) -> None:
        f = _MASKS[mask]
        for y in range(self.size):
            for x in range(self.size):
                if not self.fn[y][x] and f(x, y):
                    self.m[y][x] = not self.m[y][x]

    def penalty(self) -> int:
        s, m, score = self.size, self.m, 0
        lines = [m[y] for y in range(s)] + [[m[y][x] for y in range(s)] for x in range(s)]
        for line in lines:
            run, prev = 0, None
            for v in line:
                if v == prev:
                    run += 1
                else:
                    if run >= 5:
                        score += 3 + run - 5
                    run, prev = 1, v
            if run >= 5:
                score += 3 + run - 5
            txt = "".join("1" if v else "0" for v in line)
            for pat in ("10111010000", "00001011101"):
                start = txt.find(pat)
                while start != -1:
                    score += 40
                    start = txt.find(pat, start + 1)
        for y in range(s - 1):
            for x in range(s - 1):
                c = m[y][x]
                if c == m[y][x + 1] == m[y + 1][x] == m[y + 1][x + 1]:
                    score += 3
        dark = sum(sum(1 for v in row if v) for row in m)
        total = s * s
        k = (abs(dark * 20 - total * 10) + total - 1) // total - 1
        return score + max(k, 0) * 10


_MASKS = [
    lambda x, y: (x + y) % 2 == 0,
    lambda x, y: y % 2 == 0,
    lambda x, y: x % 3 == 0,
    lambda x, y: (x + y) % 3 == 0,
    lambda x, y: (x // 3 + y // 2) % 2 == 0,
    lambda x, y: x * y % 2 + x * y % 3 == 0,
    lambda x, y: (x * y % 2 + x * y % 3) % 2 == 0,
    lambda x, y: ((x + y) % 2 + x * y % 3) % 2 == 0,
]


def _codewords(payload: bytes, ver: int) -> list[int]:
    cap = _data_codewords(ver)
    bits: list[int] = []

    def put(val: int, n: int) -> None:
        bits.extend((val >> i) & 1 for i in reversed(range(n)))
    put(0b0100, 4)                                   # byte mode
    put(len(payload), 8 if ver <= 9 else 16)
    for b in payload:
        put(b, 8)
    put(0, min(4, cap * 8 - len(bits)))              # terminator
    put(0, (-len(bits)) % 8)
    data = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
    pad = 0xEC
    while len(data) < cap:
        data.append(pad)
        pad ^= 0xEC ^ 0x11
    # split into blocks, append ECC, interleave
    nblocks, ecclen = _BLOCKS_M[ver], _ECC_PER_BLOCK_M[ver]
    raw = _raw_modules(ver) // 8
    nshort = nblocks - raw % nblocks
    shortlen = raw // nblocks
    div = rs_divisor(ecclen)
    blocks, k = [], 0
    for i in range(nblocks):
        take = shortlen - ecclen + (0 if i < nshort else 1)
        dat = data[k:k + take]
        k += take
        ecc = rs_remainder(dat, div)
        if i < nshort:
            dat = dat + [0]
        blocks.append(dat + ecc)
    out = []
    for i in range(len(blocks[0])):
        for j, blk in enumerate(blocks):
            if i != shortlen - ecclen or j >= nshort:
                out.append(blk[i])
    return out


def matrix(text: str) -> list[list[bool]]:
    """The module matrix for `text`, True = dark. Raises ValueError if too long."""
    payload = text.encode("utf-8")
    for ver in range(1, MAX_VERSION + 1):
        header_bits = 4 + (8 if ver <= 9 else 16)
        if header_bits + 8 * len(payload) <= _data_codewords(ver) * 8:
            break
    else:
        raise ValueError(f"text too long for a version-{MAX_VERSION} QR code")
    sym = _Symbol(ver)
    sym.draw_function_patterns()
    sym.draw_codewords(_codewords(payload, ver))
    best, best_score = 0, None
    for mask in range(8):
        sym.apply_mask(mask)
        sym.draw_format(mask)
        score = sym.penalty()
        if best_score is None or score < best_score:
            best, best_score = mask, score
        sym.apply_mask(mask)                         # undo (XOR)
    sym.apply_mask(best)
    sym.draw_format(best)
    return sym.m


def svg(text: str, border: int = 4, dark: str = "#111827",
        light: str = "#ffffff") -> str:
    m = matrix(text)
    n = len(m) + 2 * border
    path = []
    for y, row in enumerate(m):
        for x, v in enumerate(row):
            if v:
                path.append(f"M{x + border},{y + border}h1v1h-1z")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n} {n}" '
            f'shape-rendering="crispEdges" role="img" aria-label="QR kód">'
            f'<rect width="{n}" height="{n}" fill="{light}"/>'
            f'<path d="{"".join(path)}" fill="{dark}"/></svg>')
