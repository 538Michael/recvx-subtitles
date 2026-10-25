#!/usr/bin/env python3
"""make-ps3-font: the subtitle font of recvx-enhanced-port (mods/subtitles/fonts/cvx.otf), made from
your own copy of Resident Evil Code: Veronica X HD for PlayStation 3 as installed in the RPCS3
emulator. Nothing of the game is included here: the tool reads your installed game, traces the HD
lettering of its message font and writes a font file for your own use.

Use it with the window (double-click, or drop your RPCS3 folder, the game's folder or syseff.arc on
the program) or from a terminal:

    make-ps3-font [PATH] [--game RECVX_FOLDER] [--out FILE.otf] [--cli]

PATH: the RPCS3 folder, the installed game (dev_hdd0/game/NPUB30467), its USRDIR, or syseff.arc.
--game: the folder with recvx.exe (default: the folder this program is in, if recvx is there).
--out: write the font here instead of <game>/mods/subtitles/fonts/cvx.otf.
--cli: no window; messages on the terminal, exit status 0 on success.
"""
import argparse, glob, math, os, queue, shutil, struct, sys, threading, zlib
import numpy as np
from PIL import Image

INSTALL_HELP = ("The PS3 game has to be installed in the RPCS3 emulator first: in RPCS3, choose\n"
                "File > Install Packages/Raps/Edats and select your game's .pkg (and its .rap licence).\n"
                "Then give this tool the RPCS3 folder, or the installed game in dev_hdd0/game/NPUB30467.")


class ToolError(Exception):
    pass


# ---------------------------------------------------------------- finding the game

def find_arc(path):
    """syseff.arc of the installed game: the file itself, or searched for under a folder"""
    path = os.path.abspath(path)
    low = path.lower()
    if os.path.isfile(path):
        if low.endswith(".arc"):
            return path
        if low.endswith((".pkg", ".iso", ".rap", ".edat")):
            raise ToolError("That is a package or disc image, which is encrypted.\n\n" + INSTALL_HELP)
        raise ToolError("That file is not syseff.arc. Give the RPCS3 folder or the installed game's folder.")
    if not os.path.isdir(path):
        raise ToolError("Not found: %s" % path)
    tail = os.path.join("BHCV", "nativePS3", "biocv_disc", "*", "system", "syseff.arc")
    roots = [path, os.path.join(path, "USRDIR")]
    for pattern in ("*", os.path.join("dev_hdd0", "game", "*"), os.path.join("game", "*")):
        roots += glob.glob(os.path.join(path, pattern, "USRDIR"))
    found = []
    for r in roots:
        found += glob.glob(os.path.join(r, tail))
        found += glob.glob(os.path.join(r, "system", "syseff.arc")) + glob.glob(os.path.join(r, "syseff.arc"))
    if not found:   # a folder deeper or shallower than expected: look a few levels down
        base = path.rstrip(os.sep).count(os.sep)
        for dirpath, dirnames, filenames in os.walk(path):
            if dirpath.count(os.sep) - base >= 8:
                dirnames[:] = []
            if "syseff.arc" in filenames and os.path.basename(dirpath).lower() == "system":
                found.append(os.path.join(dirpath, "syseff.arc"))
                break
    found = sorted(set(os.path.realpath(f) for f in found))
    if not found:
        raise ToolError("Resident Evil Code: Veronica X HD was not found in that folder.\n\n" + INSTALL_HELP)
    usa = [f for f in found if os.sep + "usa" + os.sep in f.lower()]
    return (usa or found)[0]


# ---------------------------------------------------------------- the game's files

def arc_texture(data, suffix="syseff/tex0000_bm"):
    """the texture entry ending in `suffix` of an MT Framework archive (in its "SFH" wrapper)"""
    if data[:4] == b"\0SFH":   # a 16-byte header, then 0x20000-byte blocks each ending in a 16-byte trailer
        body = data[16:]
        data = b"".join(body[i:i + 0x20000 - 16] for i in range(0, len(body), 0x20000))
    if data[:4] != b"\0CRA":
        raise ToolError("syseff.arc is not in the expected format (is it from the PS3 version?)")
    n = struct.unpack(">H", data[6:8])[0]
    for i in range(n):
        e = data[8 + i * 80:8 + (i + 1) * 80]
        name = e[:64].split(b"\0")[0].decode("ascii", "replace").replace("\\", "/").lower()
        kind, csize, _, off = struct.unpack(">IIII", e[64:80])
        if name.endswith(suffix) and kind == 0x241F5DEB:
            return zlib.decompress(data[off:off + csize])
    raise ToolError("The font page was not found in syseff.arc.")


def dxt5(data, w, h):
    """DXT5 (BC3) blocks to RGBA, h x w x 4 uint8"""
    nb = (w // 4) * (h // 4)
    b = np.frombuffer(data, np.uint8)[:nb * 16].reshape(nb, 16)
    a0, a1 = b[:, 0].astype(np.int32), b[:, 1].astype(np.int32)
    pal_a = np.zeros((nb, 8), np.int32)
    pal_a[:, 0], pal_a[:, 1] = a0, a1
    gt = a0 > a1
    for i in range(2, 8):
        pal_a[:, i] = ((8 - i) * a0 + (i - 1) * a1) // 7
    for i in range(2, 6):
        pal_a[:, i] = np.where(gt, pal_a[:, i], ((6 - i) * a0 + (i - 1) * a1) // 5)
    pal_a[:, 6] = np.where(gt, pal_a[:, 6], 0)
    pal_a[:, 7] = np.where(gt, pal_a[:, 7], 255)
    abits = np.zeros(nb, np.uint64)
    for k in range(6):
        abits |= b[:, 2 + k].astype(np.uint64) << np.uint64(8 * k)
    c = [b[:, 8].astype(np.int32) | b[:, 9].astype(np.int32) << 8, b[:, 10].astype(np.int32) | b[:, 11].astype(np.int32) << 8]
    rgb = []
    for v in c:
        r, g, bl = (v >> 11) & 31, (v >> 5) & 63, v & 31
        rgb.append(np.stack([(r << 3) | (r >> 2), (g << 2) | (g >> 4), (bl << 3) | (bl >> 2)], 1))
    pal_c = np.stack([rgb[0], rgb[1], (2 * rgb[0] + rgb[1]) // 3, (rgb[0] + 2 * rgb[1]) // 3], 1)   # nb x 4 x 3
    cbits = b[:, 12].astype(np.uint32) | b[:, 13].astype(np.uint32) << 8 | b[:, 14].astype(np.uint32) << 16 | b[:, 15].astype(np.uint32) << 24
    out = np.zeros((nb, 16, 4), np.uint8)
    rows = np.arange(nb)
    for t in range(16):
        out[:, t, :3] = pal_c[rows, (cbits >> (2 * t)) & 3]
        out[:, t, 3] = pal_a[rows, ((abits >> np.uint64(3 * t)) & np.uint64(7)).astype(np.int64)]
    return out.reshape(h // 4, w // 4, 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(h, w, 4)


def tex_rgba(d):
    """an MT Framework texture (PS3, "TEX", DXT5) to RGBA"""
    if d[:4] != b"\0XET":
        raise ToolError("The font page is not a texture of the expected kind.")
    _, w2, w3 = struct.unpack(">III", d[4:16])
    mips, w, h, fmt = w2 & 0x3F, (w2 >> 6) & 0x1FFF, (w2 >> 19) & 0x1FFF, (w3 >> 8) & 0xFF
    if fmt not in (0x17, 0x18, 0x19) or w % 4 or h % 4:
        raise ToolError("The font page has an unexpected format (%#x, %dx%d)." % (fmt, w, h))
    off = struct.unpack(">I", d[16:20])[0] if mips else 20
    return dxt5(d[off:off + (w // 4) * (h // 4) * 16], w, h)


# ---------------------------------------------------------------- tracing

CELL, UP, PAD = 28, 8, 2   # a cell in font pixels; samples per pixel; empty pixels around while tracing
LEVEL = 115.0              # the letters' fill (about 180-200) against their dark outline (60-80)


def trace_cell(page, code, ck):
    """the fill of cell `code` (18 per row) as polygons in cell pixels (y down): [(points, is_hole)]"""
    r, c = divmod(code, 18)
    cell = page[r * ck:(r + 1) * ck, c * ck:(c + 1) * ck]
    if cell.max() <= LEVEL:
        return []
    p = int(round(PAD * ck / CELL))                 # (ck = 42 on the PS3 page: 3 page pixels)
    padded = np.zeros((ck + 2 * p, ck + 2 * p), np.float32)
    padded[p:p + ck, p:p + ck] = cell
    m = (CELL + 2 * PAD) * UP
    f = np.array(Image.fromarray(padded, "F").resize((m, m), Image.BICUBIC), np.float64)
    f[f == LEVEL] = LEVEL - 1e-3
    inside = f > LEVEL
    a, b, cc, d = inside[:-1, :-1], inside[:-1, 1:], inside[1:, 1:], inside[1:, :-1]
    case = a * 1 | b * 2 | cc * 4 | d * 8
    H, W = f.shape
    pts, adj = {}, {}

    def edge(x0, y0, x1, y1, eid):   # the level's crossing on the edge between two samples
        if eid not in pts:
            f0, f1 = f[y0, x0], f[y1, x1]
            t = (LEVEL - f0) / (f1 - f0)
            pts[eid] = ((x0 + t * (x1 - x0) + 0.5) / UP - PAD, (y0 + t * (y1 - y0) + 0.5) / UP - PAD)
        return eid

    def link(e0, e1):
        adj.setdefault(e0, []).append(e1)
        adj.setdefault(e1, []).append(e0)

    for y, x in zip(*np.nonzero((case != 0) & (case != 15))):
        k = case[y, x]
        top = edge(x, y, x + 1, y, y * W + x) if (k & 1) != (k >> 1 & 1) else None
        right = edge(x + 1, y, x + 1, y + 1, H * W + y * W + x + 1) if (k >> 1 & 1) != (k >> 2 & 1) else None
        bottom = edge(x, y + 1, x + 1, y + 1, (y + 1) * W + x) if (k >> 3 & 1) != (k >> 2 & 1) else None
        left = edge(x, y, x, y + 1, H * W + y * W + x) if (k & 1) != (k >> 3 & 1) else None
        es = [e for e in (top, right, bottom, left) if e is not None]
        if len(es) == 2:
            link(*es)
        else:   # a saddle: the centre decides which corners the inside joins
            centre = (f[y, x] + f[y, x + 1] + f[y + 1, x + 1] + f[y + 1, x]) / 4
            if (centre > LEVEL) == bool(k & 1):
                link(top, right); link(bottom, left)
            else:
                link(left, top); link(right, bottom)
    loops, seen = [], set()
    for s in adj:
        if s in seen:
            continue
        loop, prev, cur = [], None, s
        while cur not in seen:
            seen.add(cur)
            loop.append(pts[cur])
            nxt = [e for e in adj[cur] if e != prev]
            prev, cur = cur, (nxt[0] if nxt else s)
        if len(loop) >= 3 and abs(area(loop)) >= 0.25:   # specks and pinholes dropped
            loops.append(simplify(smooth(loop), 0.03))
    out = []
    for i, lp in enumerate(loops):   # holes: inside an odd number of other outlines
        depth = sum(1 for j, other in enumerate(loops) if j != i and inside_poly(lp[0], other))
        out.append((lp, depth % 2 == 1))
    return out


def area(p):
    return sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p))) / 2


def inside_poly(pt, poly):
    x, y, hit = pt[0], pt[1], False
    for i in range(len(poly)):
        (x0, y0), (x1, y1) = poly[i], poly[i - 1]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            hit = not hit
    return hit


def smooth(p, passes=3):
    """the sampling steps evened out (a closed moving average); sharp corners kept"""
    p = np.array(p)
    for _ in range(passes):
        prv, nxt = np.roll(p, 1, 0), np.roll(p, -1, 0)
        u, v = p - prv, nxt - p
        lu, lv = np.hypot(*u.T), np.hypot(*v.T)
        cos = np.where((lu > 0) & (lv > 0), (u * v).sum(1) / np.maximum(lu * lv, 1e-12), 1)
        q = (prv + 2 * p + nxt) / 4
        p = np.where((cos < -0.2)[:, None], p, q)
    return [tuple(v) for v in p]


def simplify(p, eps):
    """Douglas-Peucker on a closed outline, split at the point farthest from the first"""
    n = len(p)
    far = max(range(n), key=lambda i: (p[i][0] - p[0][0]) ** 2 + (p[i][1] - p[0][1]) ** 2)
    keep = {0, far}
    ring = p + [p[0]]
    stack = [(0, far), (far, n)]
    while stack:
        a, b = stack.pop()
        (ax, ay), (bx, by) = ring[a], ring[b]
        dx, dy = bx - ax, by - ay
        ll = dx * dx + dy * dy
        best, bi = 0.0, -1
        for i in range(a + 1, b):
            px, py = ring[i]
            t = ((px - ax) * dx + (py - ay) * dy) / ll if ll else 0
            t = 0 if t < 0 else 1 if t > 1 else t
            dd = math.hypot(ax + t * dx - px, ay + t * dy - py)
            if dd > best:
                best, bi = dd, i
        if bi >= 0 and best > eps:
            keep.add(bi)
            stack += [(a, bi), (bi, b)]
    return [p[i] for i in sorted(keep) if i < n]


# ---------------------------------------------------------------- the letters

SKIP = set('#$&*<=>@[\\]^`{|}')            # their cells hold the game's own symbols
EXTRA = {2: "”", 7: "’", 60: "×", 62: "·", 91: "α", 92: "Σ", 95: "®"}
GRAVE, ACUTE, CIRC, TILDE, DIAER, RING, CARON, DOT, CEDIL, OGON = range(10)
MARK_OF = {"̀": GRAVE, "́": ACUTE, "̂": CIRC, "̃": TILDE, "̈": DIAER, "̊": RING,
           "̌": CARON, "̇": DOT, "̧": CEDIL, "̨": OGON}


def bbox(cs):
    xs = [x for p, _ in cs for x, _ in p]
    ys = [y for p, _ in cs for _, y in p]
    return (min(xs), min(ys), max(xs), max(ys)) if xs else (0, 0, 0, 0)


def moved(cs, f):
    return [([f(pt) for pt in p], hole) for p, hole in cs]


def poly(xy, cx, y, hole=False):
    return ([(cx + xy[i], y + xy[i + 1]) for i in range(0, len(xy), 2)], hole)


def circle(cx, cy, r, n=16, hole=False):
    return ([(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)], hole)


def mark(m, cx, y):
    """a mark centred on cx, sitting on y (above a letter) or hanging from it (cedilla, ogonek)"""
    if m == ACUTE: return [poly((-1.4, 0, 0.2, 0, 2.6, -3.4, 0.6, -3.8), cx, y)]
    if m == GRAVE: return [poly((1.4, 0, -0.2, 0, -2.6, -3.4, -0.6, -3.8), cx, y)]
    if m == CIRC: return [poly((-3.2, 0, -1.7, 0, 0, -2.0, 1.7, 0, 3.2, 0, 0.9, -3.6, -0.9, -3.6), cx, y)]
    if m == CARON: return [poly((-3.2, -3.6, -1.7, -3.6, 0, -1.6, 1.7, -3.6, 3.2, -3.6, 0.9, 0, -0.9, 0), cx, y)]
    if m == CEDIL: return [poly((-0.6, -0.6, 0.6, -0.6, 0.6, 1.0, 2.2, 1.8, 1.8, 3.5, -1.8, 3.7, -1.8, 2.9, 0.4, 2.7, 0.6, 2.1, -0.6, 1.5), cx, y)]
    if m == OGON: return [poly((0.2, -0.6, 1.6, -0.6, 0.6, 1.4, 1.0, 2.5, 2.6, 2.6, 2.4, 3.5, -0.4, 3.4, -1.0, 2.0), cx, y)]
    if m == TILDE:   # a wave, up on the left, down on the right
        top, bot = [], []
        for i in range(13):
            t = -1 + i / 6.0
            w = -1.9 + 1.1 * math.sin(math.pi * t)
            top.append((cx + 3.2 * t, y + w - 0.75)); bot.append((cx + 3.2 * t, y + w + 0.75))
        return [(top + bot[::-1], False)]
    if m == DIAER: return [circle(cx - 2.2, y - 1.6, 1.25), circle(cx + 2.2, y - 1.6, 1.25)]
    if m == DOT: return [circle(cx, y - 1.6, 1.35)]
    if m == RING: return [circle(cx, y - 2.2, 2.0, 20), circle(cx, y - 2.2, 0.95, 20, True)]
    return []


def letters(page, log):
    """the page's letters and the ones composed from them: {character: (polygons, advance)}"""
    import unicodedata
    ck = round(CELL * page.shape[1] / 512)
    g = {}
    codes = [(code, chr(code + 32)) for code in range(1, 95) if chr(code + 32) not in SKIP and code not in EXTRA]
    codes += sorted(EXTRA.items())
    for i, (code, ch) in enumerate(codes):
        cs = trace_cell(page, code, ck)
        if cs:
            g[ch] = (cs, 0.0)
        if i % 10 == 0:
            log("tracing the letters... %d%%" % (100 * i // len(codes)))
    for need in "HIEFTxzvwOil-.,":
        if need not in g:
            raise ToolError("The font page looks wrong (letter %r missing)." % need)
    base = max(bbox(g[c][0])[3] for c in "HIEFLT" if c in g)
    xh = min(bbox(g[c][0])[1] for c in "xzvw" if c in g)
    cap = min(bbox(g[c][0])[1] for c in "HIEFT" if c in g)
    for dotless, src in (("ı", "i"), ("ȷ", "j")):   # without the dot (wholly above the x-height)
        if src in g:
            g[dotless] = ([c for c in g[src][0] if bbox([c])[3] > xh + 1.0], 0.0)
    made = 0
    for cp in list(range(0xC0, 0x180)) + [0x178]:
        d = unicodedata.normalize("NFD", chr(cp))
        if len(d) != 2 or d[1] not in MARK_OF:
            continue
        m, b = MARK_OF[d[1]], d[0]
        src = {"i": "ı", "j": "ȷ"}.get(b, b) if m not in (CEDIL, OGON) else b
        if src not in g:
            continue
        cs = g[src][0]
        x0, y0, x1, y1 = bbox(cs)
        if m == CEDIL: marks = mark(m, (x0 + x1) / 2, base)
        elif m == OGON: marks = mark(m, x1 - 1.6, base)
        else:
            top = (cap if b.isupper() else xh) - 1.2
            if b in "bdfhklt":
                top = y0 - 1.0
            marks = mark(m, (x0 + x1) / 2 + (0.4 if m == ACUTE else 0), top)
        g[chr(cp)] = (cs + marks, 0.0); made += 1
    for ch, b in (("ł", "l"), ("Ł", "L")):   # l and L with a stroke
        cs = g[b][0] if b in g else None
        if cs:
            x0, y0, x1, y1 = bbox(cs)
            stem = x0 + (x1 - x0) * (0.5 if b == "l" else 0.3)
            g[ch] = (cs + [poly((-3.0, 1.9, -3.0, 0.5, 3.0, -1.9, 3.0, -0.5), stem, (y0 + base) / 2 + (1 if b == "L" else 0))], 0.0)
    for a, b in (("¡", "!"), ("¿", "?")):   # turned, under the baseline
        if b in g:
            x0, y0, x1, y1 = bbox(g[b][0])
            g[a] = (moved(g[b][0], lambda q, x0=x0, x1=x1, y0=y0, y1=y1: (x0 + x1 - q[0], y0 + y1 - q[1] + (base - y1) + 3.0)), 0.0)
    for a, b in (("“", "”"), ("‘", "’")):   # opening quotes: the closing ones turned
        if b in g:
            x0, y0, x1, y1 = bbox(g[b][0])
            g[a] = (moved(g[b][0], lambda q, x0=x0, x1=x1, y0=y0, y1=y1: (x0 + x1 - q[0], y0 + y1 - q[1])), 0.0)
    if "”" in g:
        x0, y0, x1, y1 = bbox(g["”"][0])
        g["„"] = (moved(g["”"][0], lambda q: (q[0], q[1] + base + 3.0 - y1)), 0.0)
        g['"'] = g["”"]
    if "’" in g:
        g["'"] = g["’"]
    x0, y0, x1, y1 = bbox(g["-"][0])
    for a, w in (("–", 9.0), ("—", 16.0)):
        g[a] = (moved(g["-"][0], lambda q, w=w: (1.0 + (q[0] - x0) * w / (x1 - x0), q[1])), 0.0)
    x0, y0, x1, y1 = bbox(g["."][0])
    g["…"] = ([c for k in range(3) for c in moved(g["."][0], lambda q, k=k: (q[0] - x0 + 1.0 + k * (x1 - x0 + 1.6), q[1]))], 0.0)
    mid = (xh + base) / 2

    def chevron(cx, d):
        return poly((d * 1.6, -2.6, d * 2.8, -2.6, d * 1.0, 0, d * 2.8, 2.6, d * 1.6, 2.6, -d * 0.4, 0), cx, mid)
    g["«"] = ([chevron(3.0, 1), chevron(6.6, 1)], 0.0)
    g["»"] = ([chevron(9.0, -1), chevron(5.4, -1)], 0.0)
    for lig, a, b in (("œ", "o", "e"), ("Œ", "O", "E")):   # oe / OE run together
        if a in g and b in g:
            xa0, _, xa1, _ = bbox(g[a][0]); xb0, _, _, _ = bbox(g[b][0])
            shift = xa1 - xb0 - (1.4 if a == "o" else 2.2)
            g[lig] = (g[a][0] + moved(g[b][0], lambda q, d=shift: (q[0] + d, q[1])), 0.0)
    side = 0.9   # spaced by the ink, a little on each side
    for ch, (cs, _) in list(g.items()):
        if cs:
            x0, y0, x1, y1 = bbox(cs)
            g[ch] = (moved(cs, lambda q, d=side - x0: (q[0] + d, q[1])), x1 - x0 + 2 * side)
    g[" "] = ([], 6.5)
    g[" "] = ([], 6.5)
    log("%d letters (%d with accents)" % (len(g), made))
    return g, base


# ---------------------------------------------------------------- the font file

def font_bytes(g, base):
    from io import BytesIO
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    U = 1000.0 / CELL
    asc, desc = round(base * U), round((CELL - base) * U)
    order, cmap, glyphs, metrics = [".notdef"], {}, {".notdef": TTGlyphPen(None).glyph()}, {".notdef": (500, 0)}
    for ch in sorted(g):
        cs, adv = g[ch]
        name = "uni%04X" % ord(ch)
        pen = TTGlyphPen(None)
        for pts, hole in cs:
            q = [(x * U, (base - y) * U) for x, y in pts]
            if (area(q) > 0) != hole:   # TrueType: outlines clockwise, holes counter-clockwise (y up)
                q = q[::-1]
            pen.moveTo(q[0])
            for v in q[1:]:
                pen.lineTo(v)
            pen.closePath()
        glyphs[name] = pen.glyph()
        order.append(name); cmap[ord(ch)] = name
        metrics[name] = (round(adv * U), round(bbox(cs)[0] * U) if cs else 0)
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=asc, descent=-desc)
    fb.setupNameTable({"familyName": "CVX Subtitles", "styleName": "Regular"})
    fb.setupOS2(sTypoAscender=asc, sTypoDescender=-desc, sTypoLineGap=0, usWinAscent=asc + 200, usWinDescent=desc)
    fb.setupPost()
    out = BytesIO()
    fb.save(out)
    return out.getvalue()


def make_font(source, log):
    """the font file's bytes from the installed game at `source`"""
    arc = find_arc(source)
    log("found %s" % arc)
    with open(arc, "rb") as f:
        rgba = tex_rgba(arc_texture(f.read())).astype(np.float32)
    page = rgba[..., 3] * rgba[..., :3].mean(2) / 255   # how much of the light letter each texel shows
    log("font page %dx%d" % (page.shape[1], page.shape[0]))
    g, base = letters(page, log)
    return font_bytes(g, base)


# ---------------------------------------------------------------- where it goes

def default_game_dir():
    here = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
    for d in (here, os.getcwd()):
        if is_game_dir(d):
            return d
    return ""


def is_game_dir(d):
    return bool(d) and any(os.path.isfile(os.path.join(d, n)) for n in ("recvx.exe", "recvx"))


def install(data, game=None, out=None):
    """write the font; an existing one is kept as .bak; the path written"""
    if not out:
        if not is_game_dir(game or ""):
            raise ToolError("Choose the recvx-enhanced-port folder (the one with recvx.exe).")
        out = os.path.join(game, "mods", "subtitles", "fonts", "cvx.otf")
    out = os.path.normpath(os.path.abspath(out))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out):
        shutil.copy2(out, out + ".bak")
    with open(out, "wb") as f:
        f.write(data)
    return out


DONE = ("In the game, the subtitles use it with Settings > DISPLAY > Subtitle font: Game.\n"
        "Keep the font for yourself: it is made from the game, so please don't share it.")


# ---------------------------------------------------------------- the window

def gui(source="", game=""):
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    root = tk.Tk()
    root.title("Make PS3 subtitle font - recvx-enhanced-port")
    root.minsize(640, 420)
    frm = ttk.Frame(root, padding=14)
    frm.pack(fill="both", expand=True)
    frm.columnconfigure(1, weight=1)
    ttk.Label(frm, text="Makes the subtitle font from your own PS3 copy of Resident Evil Code: Veronica X HD,\n"
                        "installed in the RPCS3 emulator.", justify="left").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 12))
    src_var, game_var = tk.StringVar(value=source), tk.StringVar(value=game)
    ttk.Label(frm, text="PS3 game:").grid(row=1, column=0, sticky="w")
    ttk.Entry(frm, textvariable=src_var).grid(row=1, column=1, sticky="ew", padx=6)
    ttk.Button(frm, text="Folder...", command=lambda: src_var.set(filedialog.askdirectory(title="The RPCS3 folder or the installed game") or src_var.get())).grid(row=1, column=2)
    ttk.Button(frm, text="File...", command=lambda: src_var.set(filedialog.askopenfilename(title="syseff.arc", filetypes=[("syseff.arc", "*.arc"), ("All files", "*.*")]) or src_var.get())).grid(row=1, column=3, padx=(4, 0))
    ttk.Label(frm, text="recvx folder:").grid(row=2, column=0, sticky="w", pady=6)
    ttk.Entry(frm, textvariable=game_var).grid(row=2, column=1, sticky="ew", padx=6, pady=6)
    ttk.Button(frm, text="Choose...", command=lambda: game_var.set(filedialog.askdirectory(title="The folder with recvx.exe") or game_var.get())).grid(row=2, column=2, columnspan=2, sticky="ew", pady=6)
    run_btn = ttk.Button(frm, text="Make font")
    run_btn.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(6, 8))
    logw = tk.Text(frm, height=10, wrap="word", state="disabled")
    logw.grid(row=4, column=0, columnspan=4, sticky="nsew")
    frm.rowconfigure(4, weight=1)
    status = ttk.Label(frm, text="Drop your RPCS3 folder on this program, or choose it above.", foreground="#555")
    status.grid(row=5, column=0, columnspan=4, sticky="w", pady=(8, 0))
    q = queue.Queue()

    def say(msg):
        logw.configure(state="normal"); logw.insert("end", msg + "\n"); logw.see("end"); logw.configure(state="disabled")

    def work(src, gdir):
        try:
            data = make_font(src, lambda m: q.put(("log", m)))
            q.put(("done", install(data, gdir)))
        except ToolError as e:
            q.put(("error", str(e)))
        except Exception as e:   # (reported in plain words too)
            q.put(("error", "Something went wrong: %s: %s" % (type(e).__name__, e)))

    def poll():
        try:
            while True:
                kind, msg = q.get_nowait()
                if kind == "log":
                    say(msg)
                    continue
                run_btn.configure(state="normal")
                if kind == "done":
                    say("Font written to %s" % msg)
                    status.configure(text="Done!", foreground="#060")
                    messagebox.showinfo("Font made", "The font was written to:\n%s\n\n%s" % (msg, DONE))
                else:
                    say(msg)
                    status.configure(text="Not done - see above.", foreground="#a00")
                    messagebox.showerror("Could not make the font", msg)
        except queue.Empty:
            pass
        root.after(100, poll)

    def start():
        src, gdir = src_var.get().strip(), game_var.get().strip()
        if not src:
            messagebox.showwarning("PS3 game", "Choose the RPCS3 folder, the installed game or syseff.arc first.")
            return
        if not is_game_dir(gdir):
            messagebox.showwarning("recvx folder", "Choose the recvx-enhanced-port folder (the one with recvx.exe).")
            return
        run_btn.configure(state="disabled")
        status.configure(text="Working...", foreground="#555")
        say("Making the font from %s" % src)
        threading.Thread(target=work, args=(src, gdir), daemon=True).start()

    run_btn.configure(command=start)
    root.after(100, poll)
    if source and is_game_dir(game):   # dropped on the program, next to recvx: go
        root.after(300, start)
    elif source:
        status.configure(text="Now choose the recvx folder (the one with recvx.exe), then Make font.")
    return root


def main(argv=None):
    ap = argparse.ArgumentParser(description="Make recvx-enhanced-port's subtitle font from your own PS3 copy (installed in RPCS3).")
    ap.add_argument("source", nargs="?", default="", help="the RPCS3 folder, the installed game, or syseff.arc")
    ap.add_argument("--game", default="", help="the recvx-enhanced-port folder (with recvx.exe)")
    ap.add_argument("--out", default="", help="write the font here instead")
    ap.add_argument("--cli", action="store_true", help="no window")
    a = ap.parse_args(argv)
    game = a.game or default_game_dir()
    if not a.cli:
        gui(a.source, game).mainloop()
        return 0

    def say(m):
        for s in (sys.stdout, sys.stderr):
            if s:
                print(m, file=s)
                break
    if not a.source:
        say("Give the RPCS3 folder, the installed game or syseff.arc.")
        return 2
    try:
        say("Font written to %s\n%s" % (install(make_font(a.source, say), game, a.out or None), DONE))
        return 0
    except ToolError as e:
        say(str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
