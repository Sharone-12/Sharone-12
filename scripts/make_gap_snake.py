import re, sys
from PIL import Image, ImageDraw

HTML_PATH = sys.argv[1] if len(sys.argv) > 1 else "contrib.html"
OUT = sys.argv[2] if len(sys.argv) > 2 else "gap-snake.gif"

html = open(HTML_PATH, encoding="utf-8").read()
cells = re.findall(
    r'id="contribution-day-component-(\d+)-(\d+)" data-level="(\d)"', html
)

grid = {}
max_col = 0
for row, col, lvl in cells:
    row, col, lvl = int(row), int(col), int(lvl)
    grid[(col, row)] = lvl
    max_col = max(max_col, col)

W = max_col + 1
H = 7

LEVEL_COLOR = {
    0: (22, 27, 34),
    1: (14, 68, 41),
    2: (0, 109, 50),
    3: (38, 166, 65),
    4: (57, 211, 83),
}

CELL = 11
GAP = 3
STEP = CELL + GAP
MARGIN = 6
PAD = 1  # thin margin the snake only uses as a last resort when fully blocked

IMG_W = MARGIN * 2 + (W + 2 * PAD) * STEP - GAP
IMG_H = MARGIN * 2 + (H + 2 * PAD) * STEP - GAP

def cell_box(w, h):
    x0 = MARGIN + (w + PAD) * STEP
    y0 = MARGIN + (h + PAD) * STEP
    return [x0, y0, x0 + CELL, y0 + CELL]

base = Image.new("RGBA", (IMG_W, IMG_H), (13, 17, 23, 255))
bd = ImageDraw.Draw(base)
for w in range(W):
    for h in range(H):
        lvl = grid.get((w, h), 0)
        bd.rounded_rectangle(cell_box(w, h), radius=2, fill=LEVEL_COLOR[lvl])

# walkable space = every real grid cell with no contributions, PLUS a ring of open
# space around the whole grid, so the snake can go above/below/past a blocked run
# of columns instead of being trapped in whichever pocket it started in
def is_free(w, h):
    if 0 <= w < W and 0 <= h < H:
        return grid.get((w, h), 0) == 0
    return -PAD <= w < W + PAD and -PAD <= h < H + PAD

space = {
    (w, h)
    for w in range(-PAD, W + PAD)
    for h in range(-PAD, H + PAD)
    if is_free(w, h)
}

def neighbors(cell):
    w, h = cell
    for dw, dh in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nb = (w + dw, h + dh)
        if nb in space:
            yield nb

# connected components of the walkable space; the snake can only ever roam within one
seen = set()
components = []
for start in space:
    if start in seen:
        continue
    stack = [start]
    comp = set()
    while stack:
        cur = stack.pop()
        if cur in comp:
            continue
        comp.add(cur)
        seen.add(cur)
        stack.extend(nb for nb in neighbors(cur) if nb not in comp)
    components.append(comp)

largest = max(components, key=len) if components else {(0, 0)}

def in_grid(cell):
    w, h = cell
    return 0 <= w < W and 0 <= h < H

def comp_neighbors(cell):
    # prefer staying inside the real grid; only step into the margin when every
    # in-grid neighbor is already visited (i.e. genuinely blocked)
    nbs = [nb for nb in neighbors(cell) if nb in largest]
    inside = [nb for nb in nbs if in_grid(nb)]
    outside = [nb for nb in nbs if not in_grid(nb)]
    return inside + outside

# full DFS "Euler tour" of the connected gap region: every consecutive step is a
# real orthogonal move (forward into a new cell, or backtracking to the parent)
start = min(largest)
visited = {start}
stack = [start]
iters = {start: iter(comp_neighbors(start))}
walk = [start]

while stack:
    node = stack[-1]
    advanced = False
    for nb in iters[node]:
        if nb not in visited:
            visited.add(nb)
            stack.append(nb)
            iters[nb] = iter(comp_neighbors(nb))
            walk.append(nb)
            advanced = True
            break
    if not advanced:
        stack.pop()
        if stack:
            walk.append(stack[-1])

path = walk

# ping-pong: forward then back, excluding duplicated endpoints
pingpong = path + path[-2::-1]

SNAKE_LEN = 9       # path points included in the body
LINE_WIDTH = 9
BODY_COLOR = (147, 51, 234)   # purple
HEAD_COLOR = (168, 85, 247)
SUBSTEPS = 2        # interpolated sub-frames per cell-to-cell move, for a smooth glide

def center(cell):
    w, h = cell
    box = cell_box(w, h)
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)

# a 1-deep dead end forces the walk to retrace the exact same cell (A, B, A) on
# its way back out; rendered as a thick line that overlaps itself perfectly,
# that pinch reads as a glitch. Nudge the tip sideways so it's a small rounded
# hook instead of a perfect retrace.
TIP_NUDGE = STEP * 0.3
path_centers = [list(center(c)) for c in path]
for i in range(1, len(path) - 1):
    if path[i - 1] == path[i + 1]:
        aw, ah = path[i - 1]
        bw, bh = path[i]
        dw, dh = bw - aw, bh - ah
        perp = (-dh, dw)
        path_centers[i][0] += perp[0] * TIP_NUDGE
        path_centers[i][1] += perp[1] * TIP_NUDGE
path_centers = [tuple(p) for p in path_centers]
pingpong_centers = path_centers + path_centers[-2::-1]
path_centers = pingpong_centers
last_idx = len(pingpong) - 1

def lerp(a, b, t):
    return (a[0] + (b[0]-a[0])*t, a[1] + (b[1]-a[1])*t)

def point_at(t):
    t = max(0.0, min(last_idx, t))
    f = int(t)
    frac = t - f
    c = min(f + 1, last_idx)
    return lerp(path_centers[f], path_centers[c], frac)

total_frames = last_idx * SUBSTEPS + 1

frames = []
for frame_i in range(total_frames):
    t = frame_i / SUBSTEPS
    frame = base.copy()
    fd = ImageDraw.Draw(frame)

    points = [point_at(t - k) for k in range(SNAKE_LEN - 1, -1, -1)]

    r = LINE_WIDTH / 2
    if len(points) >= 2:
        fd.line(points, fill=BODY_COLOR, width=LINE_WIDTH, joint="curve")
        for p in points:
            fd.ellipse([p[0]-r, p[1]-r, p[0]+r, p[1]+r], fill=BODY_COLOR)
    else:
        p = points[0]
        fd.ellipse([p[0]-r, p[1]-r, p[0]+r, p[1]+r], fill=BODY_COLOR)

    # head + eyes, facing the direction of travel
    hx, hy = points[-1]
    px, py = point_at(t - 0.6)
    dx, dy = hx - px, hy - py
    mag = (dx*dx + dy*dy) ** 0.5 or 1.0
    dx, dy = dx / mag, dy / mag
    fd.ellipse([hx-r-1, hy-r-1, hx+r+1, hy+r+1], fill=HEAD_COLOR)

    perp = (-dy, dx)
    fwd = 2.6
    gap = 2.6
    ex, ey = hx + dx * fwd, hy + dy * fwd
    for sign in (1, -1):
        exx, eyy = ex + perp[0]*gap*sign, ey + perp[1]*gap*sign
        fd.ellipse([exx-1.6, eyy-1.6, exx+1.6, eyy+1.6], fill=(255, 255, 255))
        fd.ellipse([exx-0.7, eyy-0.7, exx+0.7, eyy+0.7], fill=(15, 10, 20))

    frames.append(frame)

p_frames = [f.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=64) for f in frames]

p_frames[0].save(
    OUT,
    save_all=True,
    append_images=p_frames[1:],
    duration=75,
    loop=0,
    optimize=True,
)
print("frames:", len(p_frames), "size:", IMG_W, IMG_H, "gap cells:", len(path))
