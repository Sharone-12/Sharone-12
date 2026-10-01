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
PAD = 2  # extra rows/cols of open space around the grid the snake can travel through

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
STEP_PX = 2  # advance this many path-points per frame

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
    duration=70,
    loop=0,
    optimize=True,
)
print("frames:", len(p_frames), "size:", IMG_W, IMG_H, "gap cells:", len(path))
