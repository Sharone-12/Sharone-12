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

# boustrophedon order over gap (zero-contribution) cells only
path = []
for w in range(W):
    rng = range(H) if w % 2 == 0 else range(H - 1, -1, -1)
    for h in rng:
        if grid.get((w, h), 0) == 0:
            path.append((w, h))

if not path:
    path = [(0, 0)]

# ping-pong: forward then back, excluding duplicated endpoints
pingpong = path + path[-2::-1]

SNAKE_LEN = 7
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
    duration=55,
    loop=0,
    optimize=True,
)
print("frames:", len(p_frames), "size:", IMG_W, IMG_H, "gap cells:", len(path))
