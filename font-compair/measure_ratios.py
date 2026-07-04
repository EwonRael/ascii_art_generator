"""Measure monospace character-cell width/height ratios from the font-compair
SVG references.

Each reference SVG holds a block of text: a font-name label line, followed by
several lines of U+2588 (FULL BLOCK) characters with a space between every
pair, and every other line indented by one extra leading space -- producing a
checkerboard of blocks. When the font is available and Inkscape has converted
the text to path outlines, every U+2588 glyph becomes its own perfectly
axis-aligned rectangle subpath within one big <path> element, with exact
vector corner coordinates -- so instead of rasterizing and hunting for corners
in pixels, we can read the corners directly out of the path data.

For each rectangle we know its exact (minx, miny, maxx, maxy). Because of the
checkerboard layout, the same corner (e.g. bottom-right) of a block and the
bottom-right corner of the "next" block one row up is offset by exactly one
character cell horizontally and one line vertically -- so decomposing that
corner-to-corner measurement into its x and y components directly gives the
cell width and line height, without needing a diagonal/pixel measurement.
We do the equivalent thing more robustly: measure every within-row gap
(which spans one block + one space = 2 cells) for cell width, and every
between-row gap for line height, then take the median across all samples.

Usage: python measure_ratios.py
"""

import re
from pathlib import Path
from statistics import median
from xml.etree import ElementTree as ET

FONT_DIR = Path(__file__).parent
SVG_NS = "{http://www.w3.org/2000/svg}"

# Command letters that mean "this subpath has a curve in it" -- i.e. it's an
# actual letterform (from the font-name label), not a block rectangle.
CURVE_CMDS = set("CcSsQqTtAa")

# Number of arguments each command consumes per repetition, and how many of
# the trailing values are the endpoint (x, y) used to advance current point.
ARG_COUNTS = {
    "M": 2, "L": 2, "H": 1, "V": 1,
    "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7,
    "Z": 0,
}

TOKEN_RE = re.compile(r"[MLHVCSQTAZ]|-?\d*\.?\d+(?:[eE][-+]?\d+)?", re.IGNORECASE)


def _numbers_for(cmd_upper, tokens, i):
    """Pull the numeric args for one repetition of cmd_upper starting at tokens[i]."""
    n = ARG_COUNTS[cmd_upper]
    vals = [float(tokens[i + k]) for k in range(n)]
    return vals, i + n


def parse_path_rectangles(d):
    """Walk an SVG path 'd' string; return (minx, miny, maxx, maxy) for every
    subpath that is a plain axis-aligned rectangle (the block glyphs).

    Curved subpaths (letterforms) are skipped for rectangle-extraction, but
    we still track the current point through them so later relative
    'm' commands (which chain off wherever the pen last was) stay correct.
    """
    tokens = TOKEN_RE.findall(d)
    i = 0
    cur_cmd = None
    cx = cy = 0.0
    start_x = start_y = 0.0
    subpath_has_curve = False
    subpath_verts = []
    have_current_point = False
    rects = []

    def flush():
        if not subpath_has_curve and len(subpath_verts) >= 4:
            xs = sorted({round(x, 3) for x, y in subpath_verts})
            ys = sorted({round(y, 3) for x, y in subpath_verts})
            if len(xs) == 2 and len(ys) == 2:
                rects.append((xs[0], ys[0], xs[1], ys[1]))

    n = len(tokens)
    while i < n:
        tok = tokens[i]
        if tok.upper() in ARG_COUNTS or tok in "Zz":
            cur_cmd = tok
            i += 1
        cmd_upper = cur_cmd.upper()
        is_relative = cur_cmd.islower()

        if cmd_upper == "Z":
            cx, cy = start_x, start_y
            flush()
            subpath_has_curve = False
            subpath_verts = []
            continue

        if cmd_upper == "M":
            vals, i = _numbers_for("M", tokens, i)
            x, y = vals
            if is_relative and have_current_point:
                x += cx
                y += cy
            flush()
            subpath_has_curve = False
            cx, cy = x, y
            start_x, start_y = x, y
            subpath_verts = [(cx, cy)]
            have_current_point = True
            # subsequent bare coordinate pairs after an M are implicit L
            cur_cmd = "l" if is_relative else "L"
            continue

        if cmd_upper == "H":
            vals, i = _numbers_for("H", tokens, i)
            (x,) = vals
            cx = cx + x if is_relative else x
            subpath_verts.append((cx, cy))
        elif cmd_upper == "V":
            vals, i = _numbers_for("V", tokens, i)
            (y,) = vals
            cy = cy + y if is_relative else y
            subpath_verts.append((cx, cy))
        elif cmd_upper == "L":
            vals, i = _numbers_for("L", tokens, i)
            x, y = vals
            if is_relative:
                x += cx
                y += cy
            cx, cy = x, y
            subpath_verts.append((cx, cy))
        else:
            # Curve command: consume its args, advance current point to the
            # endpoint (last coordinate pair), but mark subpath as curved.
            vals, i = _numbers_for(cmd_upper, tokens, i)
            x, y = vals[-2], vals[-1]
            if is_relative:
                x += cx
                y += cy
            cx, cy = x, y
            subpath_has_curve = True
            subpath_verts.append((cx, cy))

    flush()
    return rects


def cluster_rows(rects, tol=0.5):
    """Group rectangles into text rows by their vertical center, tolerant of
    small float noise."""
    rows = []
    for r in sorted(rects, key=lambda r: (r[1] + r[3]) / 2):
        cy = (r[1] + r[3]) / 2
        if rows and abs(cy - rows[-1][0]) <= tol:
            rows[-1][1].append(r)
        else:
            rows.append([cy, [r]])
    return [sorted(row_rects, key=lambda r: r[0]) for _, row_rects in rows]


def measure_font(svg_path):
    tree = ET.parse(svg_path)
    root = tree.getroot()
    paths = root.findall(f".//{SVG_NS}path")
    if not paths:
        return None  # e.g. SF Mono.svg: live <text>, never converted to paths

    all_rects = []
    for p in paths:
        d = p.get("d")
        if d:
            all_rects.extend(parse_path_rectangles(d))

    rows = cluster_rows(all_rects)
    # Drop any "row" that isn't a full block row (10 blocks) -- guards against
    # stray rectangle-shaped letter subpaths (e.g. capital "I" serifs) sneaking in.
    rows = [row for row in rows if len(row) == 10]
    if len(rows) < 2:
        return None

    width_samples = []
    for row in rows:
        lefts = [r[0] for r in row]
        gaps = [b - a for a, b in zip(lefts, lefts[1:])]
        # consecutive blocks in a row are separated by one space -> 2 cells
        width_samples.extend(g / 2 for g in gaps)

    row_ys = [row[0][1] for row in rows]  # top-y is consistent within a row
    height_samples = [b - a for a, b in zip(row_ys, row_ys[1:])]

    cell_width = median(width_samples)
    line_height = median(height_samples)
    return cell_width, line_height, len(rows), len(width_samples)


def main():
    print(f"{'Font':<20}{'Cell width':>12}{'Line height':>14}{'H:W ratio':>12}   rows/samples")
    print("-" * 78)
    results = {}
    for svg_path in sorted(FONT_DIR.glob("*.svg")):
        name = svg_path.stem
        measurement = measure_font(svg_path)
        if measurement is None:
            print(f"{name:<20}{'--':>12}{'--':>14}{'--':>12}   (no path glyph data -- see note)")
            continue
        cell_width, line_height, n_rows, n_samples = measurement
        ratio = line_height / cell_width
        results[name] = ratio
        print(f"{name:<20}{cell_width:>12.4f}{line_height:>14.4f}{ratio:>12.4f}   {n_rows} rows / {n_samples} samples")

    if results:
        avg = sum(results.values()) / len(results)
        print("-" * 78)
        print(f"{'Average H:W ratio':<20}{'':>12}{'':>14}{avg:>12.4f}")


if __name__ == "__main__":
    main()
