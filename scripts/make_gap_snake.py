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

IMG_W = MARGIN * 2 + W * STEP - GAP
IMG_H = MARGIN * 2 + H * STEP - GAP

def cell_box(w, h):
    x0 = MARGIN + w * STEP
    y0 = MARGIN + h * STEP
    return [x0, y0, x0 + CELL, y0 + CELL]

base = Image.new("RGBA", (IMG_W, IMG_H), (13, 17, 23, 255))
bd = ImageDraw.Draw(base)
for w in range(W):
    for h in range(H):
        lvl = grid.get((w, h), 0)
        bd.rounded_rectangle(cell_box(w, h), radius=2, fill=LEVEL_COLOR[lvl])

# gap cells (no contributions) only move orthogonally between them, like a real snake
gaps = {c for c, lvl in grid.items() if lvl == 0}

def neighbors(cell):
    w, h = cell
    for dw, dh in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nb = (w + dw, h + dh)
        if nb in gaps:
            yield nb

# connected components of the gap graph; the snake can only ever walk within one
seen = set()
components = []
for start in gaps:
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

def comp_neighbors(cell):
    return [nb for nb in neighbors(cell) if nb in largest]

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

SNAKE_LEN = 8
SNAKE_COLOR = (255, 140, 60)
STEP_PX = 1  # advance this many path-points per frame (1 = true cell-by-cell crawl)

frames = []
for i in range(0, len(pingpong), STEP_PX):
    frame = base.copy()
    fd = ImageDraw.Draw(frame)
    for k in range(SNAKE_LEN):
        idx = i - k
        if idx < 0 or idx >= len(pingpong):
            continue
        w, h = pingpong[idx]
        alpha = max(40, 255 - k * 32)
        color = SNAKE_COLOR + (alpha,)
        box = cell_box(w, h)
        pad = 1
        fd.rounded_rectangle(
            [box[0]-pad, box[1]-pad, box[2]+pad, box[3]+pad],
            radius=3, fill=color
        )
    frames.append(frame)

p_frames = [f.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=64) for f in frames]

p_frames[0].save(
    OUT,
    save_all=True,
    append_images=p_frames[1:],
    duration=110,
    loop=0,
    optimize=True,
)
print("frames:", len(p_frames), "size:", IMG_W, IMG_H, "gap cells:", len(path))
