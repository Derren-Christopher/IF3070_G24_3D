from __future__ import annotations

import itertools
import os
import re
import shutil
import sys
import textwrap
import threading
import time

try:  # biar karakter box-drawing aman di Windows
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _color_enabled() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return sys.stdout.isatty()


USE_COLOR = _color_enabled()
ANIMATE = USE_COLOR and sys.stdout.isatty()
if USE_COLOR and os.name == "nt":
    os.system("")  # aktifkan ANSI di cmd/PowerShell lama

WIDTH = 73

RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"

# palet 256-color
ACCENT, PINK, GOLD, GREEN, RED, BLUE = 51, 213, 221, 84, 203, 75
GREY, GREY2, WHITE, BLACK = 245, 238, 255, 16

VEHICLE_PALETTE = [203, 215, 221, 156, 87, 111, 183, 213, 180, 114,
                   81, 147, 217, 229, 121, 159, 225, 222]

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def fgc(n: int) -> str:
    return f"\x1b[38;5;{n}m"


def bgc(n: int) -> str:
    return f"\x1b[48;5;{n}m"


def paint(text, *codes: str) -> str:
    if not USE_COLOR or not codes:
        return str(text)
    return "".join(codes) + str(text) + RESET


def strip(s: str) -> str:
    return _ANSI.sub("", s)


def vlen(s: str) -> int:
    return len(strip(s))


def ljust(s: str, w: int) -> str:
    return s + " " * max(0, w - vlen(s))


def center(s: str, w: int) -> str:
    total = max(0, w - vlen(s))
    left = total // 2
    return " " * left + s + " " * (total - left)


# ---------- gaya kecil ----------
def bold(s) -> str: return paint(s, BOLD)
def dim(s) -> str: return paint(s, fgc(GREY))
def good(s) -> str: return paint(s, BOLD, fgc(GREEN))
def bad(s) -> str: return paint(s, BOLD, fgc(RED))
def accent(s) -> str: return paint(s, BOLD, fgc(ACCENT))
def gold(s) -> str: return paint(s, fgc(GOLD))


def vcolor(vid: str) -> int:
    digits = re.sub(r"\D", "", vid)
    return VEHICLE_PALETTE[int(digits or 0) % len(VEHICLE_PALETTE)]


def vtag(vid: str) -> str:
    return paint(vid, BOLD, fgc(vcolor(vid)))


# ---------- pesan ----------
def info(msg: str) -> None:
    print(paint("  ℹ ", fgc(BLUE)) + msg)


def success(msg: str) -> None:
    print(paint("  ✔ ", BOLD, fgc(GREEN)) + msg)


def warn(msg: str) -> None:
    print(paint("  ⚠ ", BOLD, fgc(GOLD)) + msg)


def error(msg: str) -> None:
    print(paint("  ✘ ", BOLD, fgc(RED)) + msg)


def prompt(text: str) -> str:
    return paint("  ❯ ", BOLD, fgc(PINK)) + text


# ---------- layout ----------
def banner(art: list[str], title: str, credits: list[str], tagline: str) -> None:
    inner = WIDTH - 2
    frame = fgc(39)
    gradient = [51, 45, 39, 33, 63, 99]

    def row(s: str = "") -> None:
        print(paint("║", frame) + center(s, inner) + paint("║", frame))
        if ANIMATE:
            time.sleep(0.03)

    print()
    print(paint("╔" + "═" * inner + "╗", frame))
    row()
    for i, line in enumerate(art):
        row(paint(line, BOLD, fgc(gradient[i % len(gradient)])))
    row()
    row(paint(title, BOLD, fgc(PINK)))
    row(paint("─" * 20, fgc(GREY2)))
    row(paint(tagline, fgc(ACCENT)))
    row()
    for c in credits:
        row(paint(c, fgc(GREY)))
    row()
    print(paint("╚" + "═" * inner + "╝", frame))
    print()


def section(title: str) -> None:
    rest = max(3, WIDTH - vlen(title) - 4)
    print()
    print(paint("━━ ", BOLD, fgc(ACCENT)) + paint(title, BOLD, fgc(WHITE))
          + " " + paint("━" * rest, fgc(GREY2)))


def box(title: str, rows: list[str], color: int = ACCENT) -> None:
    inner = WIDTH - 2
    t = f" {title} "
    c = fgc(color)
    print(paint("╭─", c) + paint(t, BOLD, c) + paint("─" * (inner - 1 - len(t)) + "╮", c))
    for r in rows:
        print(paint("│", c) + " " + ljust(r, inner - 2) + " " + paint("│", c))
    print(paint("╰" + "─" * inner + "╯", c))


def kv_lines(pairs: list[tuple[str, str]], kw: int = 26) -> list[str]:
    vw = WIDTH - 2 - 2 - kw - 2
    out: list[str] = []
    for key, val in pairs:
        val = str(val)
        chunks = [val] if vlen(val) <= vw else (textwrap.wrap(strip(val), vw) or [""])
        for i, chunk in enumerate(chunks):
            k = paint(key.ljust(kw), fgc(GREY)) if i == 0 else " " * kw
            out.append(f"{k}  {chunk}")
    return out


def menu(items: list[tuple[str, str, str]]) -> None:
    for key, label, desc in items:
        if USE_COLOR:
            badge = paint(f" {key} ", BOLD, fgc(BLACK), bgc(ACCENT))
        else:
            badge = f"[{key}]"
        print(f"  {badge}  {paint(label.ljust(22), BOLD)}{dim(desc)}")


def table(headers: list[str], rows: list[list], aligns: list[str] | None = None) -> None:
    aligns = aligns or ["l"] * len(headers)
    head = [paint(h, BOLD, fgc(ACCENT)) for h in headers]
    cols = [max(vlen(str(x)) for x in [head[i]] + [r[i] for r in rows]) for i in range(len(headers))]

    def fmt(cells: list) -> str:
        out = []
        for i, c in enumerate(cells):
            c = str(c)
            pad = " " * (cols[i] - vlen(c))
            out.append(pad + c if aligns[i] == "r" else c + pad)
        return "  " + "   ".join(out)

    print(fmt(head))
    print("  " + paint("─" * (sum(cols) + 3 * (len(cols) - 1)), fgc(GREY2)))
    for r in rows:
        print(fmt(r))


def bar(frac: float, width: int = 24) -> str:
    frac = max(0.0, min(1.0, frac))
    n = round(frac * width)
    col = GREEN if frac < 0.7 else GOLD if frac < 0.95 else PINK
    return paint("█" * n, fgc(col)) + paint("░" * (width - n), fgc(GREY2)) + f" {frac * 100:5.1f}%"


_BLOCKS = "▁▂▃▄▅▆▇█"


def spark(values, width: int = 44) -> str:
    vals = list(values)
    if not vals:
        return ""
    if len(vals) > width:
        step = len(vals) / width
        vals = [vals[int(i * step)] for i in range(width)]
    lo, hi = min(vals), max(vals)
    if hi == lo:
        s = _BLOCKS[3] * len(vals)
    else:
        s = "".join(_BLOCKS[int((v - lo) / (hi - lo) * (len(_BLOCKS) - 1))] for v in vals)
    return paint(s, fgc(GREEN))


def trend(label: str, values, fmt: str = "{:g}") -> None:
    vals = list(values)
    if not vals:
        return
    rng = dim(f"{fmt.format(min(vals))} → {fmt.format(max(vals))}")
    print(f"  {paint(label.ljust(8), fgc(GREY))} {spark(vals)}  {rng}")


def ok_line(name: str, ok: bool) -> None:
    if ok:
        print(paint("  ✔ ", BOLD, fgc(GREEN)) + name)
    else:
        print(paint("  ✘ ", BOLD, fgc(RED)) + paint(name, fgc(RED)))


# ---------- grid kapal ----------
def _cell(c, w: int) -> str:
    if c is None:
        return paint("·".center(w), DIM) if USE_COLOR else ".".center(w)
    vid, origin = c
    if not USE_COLOR:
        return vid[:w].center(w)
    text = vid[:w].ljust(w) if origin else " " * w
    return paint(text, BOLD, fgc(BLACK), bgc(vcolor(vid)))


def grid(cells: list[list]) -> None:
    rows = len(cells)
    cols = len(cells[0]) if rows else 0
    term = shutil.get_terminal_size((100, 20)).columns
    w = 4 if cols * 4 + 6 <= term else 3
    g = fgc(GREY)
    print("     " + "".join(paint(f"{j:^{w}}", g) for j in range(cols)))
    print("    " + paint("╭" + "─" * (w * cols) + "╮", g))
    for i, row in enumerate(cells):
        line = paint(f"{i:>3} ", g) + paint("│", g)
        line += "".join(_cell(c, w) for c in row)
        print(line + paint("│", g))
    print("    " + paint("╰" + "─" * (w * cols) + "╯", g))


# ---------- spinner ----------
class Spinner:
    FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, text: str) -> None:
        self.text = text
        self.elapsed = 0.0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "Spinner":
        self._t0 = time.perf_counter()
        if ANIMATE:
            self._thread = threading.Thread(target=self._spin, daemon=True)
            self._thread.start()
        else:
            print(f"  ◌ {self.text}...")
        return self

    def _spin(self) -> None:
        for frame in itertools.cycle(self.FRAMES):
            if self._stop.is_set():
                break
            el = time.perf_counter() - self._t0
            sys.stdout.write(f"\r  {paint(frame, BOLD, fgc(ACCENT))} {self.text} "
                             f"{paint(f'{el:5.1f}s', fgc(GREY))}  ")
            sys.stdout.flush()
            time.sleep(0.08)

    def __exit__(self, et, ev, tb) -> bool:
        self.elapsed = time.perf_counter() - self._t0
        if self._thread:
            self._stop.set()
            self._thread.join()
            sys.stdout.write("\r\x1b[2K")
        if et is None:
            success(f"{self.text} selesai dalam {self.elapsed:.2f}s")
        else:
            error(f"{self.text} gagal")
        return False