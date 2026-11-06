"""Render a fish mesh (tools/fish3d.py) into turn views for the screensaver.

Usage (TripoSR's env, which has moderngl and trimesh):
  ext/venv/bin/python tools/fishviews.py axes <mesh.ply> <out.png>
      six axis-aligned views side by side, for finding the mesh's orientation
  ext/venv/bin/python tools/fishviews.py strip <mesh.ply> <out.png> [--photo keyed.png]
      the fish at headings -60..180 in 30 degree steps, for review
  ext/venv/bin/python tools/fishviews.py views <mesh.ply> <name> --photo keyed.png [--fat 1.0]
      the screensaver's turn views, body and tail sprites packed into images/<name>_atlas<p>.png,
      for the headings in ANGLES, -60..90 deg (the rest are mirrors), sized so the side view
      is "sideLen" px long (first time: as long as the old <name>_body/tail sprites, whose
      tail split also gives "ped", where the tail joins), and the "views" block of the species in
      gen/base_scene.json (per view: body anchor, tail anchor, tail hinge; see fish.brs).
      --len/--ped for a new species; --ball 1.2 exports an inflated form (pufferfish) as the
      species' "ball" block, in images/<name>_ball_atlas<p>.png; --under 0.5 shades the
      underside as if lit from above (the damselfish)

The side photo is projected onto both flanks (--photo) so they keep the photo's detail; the
mesh's own colors show where the surface turns away from the side (face, back, belly).

Rendering is orthographic with vertex colors and a soft key light, on transparency.
"""
import argparse
import math

import json
import sys
from pathlib import Path

import moderngl
import numpy as np
import trimesh
from PIL import Image

VS = """
#version 330
uniform mat4 mvp;
uniform mat3 rot;
in vec3 pos;
in vec3 col;
in vec3 nrm;
in vec3 opos;  // unbent position and normal: the photo stays pinned to the body as it bends
in vec3 onrm;
out vec3 vcol;
out vec3 vn;
out vec3 mpos;
out vec3 mn;
void main() {
    gl_Position = mvp * vec4(pos, 1.0);
    vcol = col;
    vn = rot * nrm;
    mpos = opos;
    mn = onrm;
}
"""
FS = """
#version 330
in vec3 vcol;
in vec3 vn;
in vec3 mpos;
in vec3 mn;
uniform sampler2D photo;
uniform vec4 box;  // mesh y0, y1, z0, z1 that the photo's fish spans
uniform float usePhoto;
uniform float under;
out vec4 frag;
void main() {
    vec3 n = normalize(vn);
    vec3 base = vcol;
    // The side photo, projected straight across onto both flanks (fish are symmetric).
    vec2 uv = vec2((mpos.y - box.x) / (box.y - box.x), (box.w - mpos.z) / (box.w - box.z));
    vec4 ph = texture(photo, uv);
    float side = smoothstep(0.45, 0.8, abs(normalize(mn).x)) * ph.a * usePhoto;
    base = mix(base, ph.rgb, side);
    // Mostly the photo's own shading (baked into the colors); a little light from above
    // the camera keeps the thickness readable when the fish faces the viewer.
    float l = 0.82 + 0.18 * max(dot(n, normalize(vec3(0.0, 0.6, 0.8))), 0.0);
    // Light from above: the fish's underside (surface facing down, mesh -z) and the lowest
    // part of its body are in its own shadow, darkest at the bottom edge.
    float hgt = (mpos.z - box.z) / (box.w - box.z);
    float sh = max(smoothstep(0.0, 0.85, -normalize(mn).z), 1.0 - smoothstep(0.05, 0.4, hgt));
    l *= 1.0 - under * sh;
    frag = vec4(base * l, 1.0);
}
"""


ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "roku/reefglass/images"
SCENE = ROOT / "gen/base_scene.json"
sys.path.insert(0, str(ROOT / "tools"))


class Renderer:
    def __init__(self, mesh_path, size=512, fat=1.0):
        m = trimesh.load(mesh_path, process=False)
        v = np.asarray(m.vertices, np.float32)
        v -= (v.max(0) + v.min(0)) / 2
        v[:, 0] *= fat  # lateral: a little extra thickness reads better head-on
        self.radius = float(np.linalg.norm(v, axis=1).max())
        c = np.asarray(m.visual.vertex_colors, np.float32)[:, :3] / 255
        n = np.asarray(m.vertex_normals, np.float32)
        self.size = size
        self.ctx = moderngl.create_standalone_context()
        self.prog = self.ctx.program(vertex_shader=VS, fragment_shader=FS)
        self.faces = np.asarray(m.faces, np.int32)
        self.v0, self.n0, self.col = v, n, c
        self.verts = v
        self.set_bend(0.0)
        self.fbo = self.ctx.simple_framebuffer((size, size), components=4)
        self.prog["usePhoto"].value = 0.0
        self.prog["under"].value = 0.0

    def set_photo(self, path):
        """The keyed side photo (RGBA, head right): its fish's bounding box is matched to the
        mesh's extent along its length (y) and height (z)."""
        im = Image.open(path).convert("RGBA")
        a = np.array(im)[..., 3]
        ys, xs = np.nonzero(a > 128)
        im = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
        # Use only the photo's interior: its outline (dark rims, keyed edges) would otherwise be
        # projected onto the face and back, where the surface turns away from the side.
        arr = np.array(im)
        import cv2
        al = (arr[..., 3] > 128).astype(np.uint8)
        e = max(2, im.width // 60)
        al = cv2.erode(al, np.ones((2 * e + 1, 2 * e + 1), np.uint8)).astype(np.float32)
        arr[..., 3] = (cv2.GaussianBlur(al, (0, 0), e * 0.7) * 255).astype(np.uint8)
        im = Image.fromarray(arr, "RGBA")
        tex = self.ctx.texture(im.size, 4, im.tobytes())
        tex.build_mipmaps()
        tex.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
        tex.repeat_x = tex.repeat_y = False
        tex.use(0)
        self.prog["photo"].value = 0
        v = self.verts
        self.prog["box"].value = (float(v[:, 1].min()), float(v[:, 1].max()), float(v[:, 2].min()), float(v[:, 2].max()))
        self.prog["usePhoto"].value = 1.0

    def set_bend(self, beta, pivot=0.7):
        """Bends the body sideways (about the vertical) by beta radians in all: the front
        (head) 1 - pivot of the length stays straight, the rest curves on a circle, the tail
        end swinging toward +x for beta > 0."""
        self.beta, self.pivot = beta, pivot
        v = self.bend_points(self.v0)
        n = self.n0 if beta == 0 else np.asarray(trimesh.Trimesh(v, self.faces, process=False).vertex_normals, np.float32)
        data = np.hstack([v, self.col, n, self.v0, self.n0]).astype("f4")
        self.vbo = self.ctx.buffer(data.tobytes())
        self.vao = self.part(np.ones(len(self.faces), bool))

    def bend_points(self, p):
        p = np.array(p, np.float32, ndmin=2)
        if self.beta == 0:
            return p.copy()
        y0, y1 = float(self.v0[:, 1].min()), float(self.v0[:, 1].max())
        yp = y0 + self.pivot * (y1 - y0)
        R = (yp - y0) / self.beta
        out = p.copy()
        rear = p[:, 1] < yp
        s = yp - p[rear, 1]
        phi = s / R
        x = p[rear, 0]
        out[rear, 0] = R - (R - x) * np.cos(phi)
        out[rear, 1] = yp - (R - x) * np.sin(phi)
        return out

    def part(self, sel):
        ibo = self.ctx.buffer(self.faces[sel].tobytes())
        return self.ctx.vertex_array(self.prog, [(self.vbo, "3f 3f 3f 3f 3f", "pos", "col", "nrm", "opos", "onrm")], ibo)

    def render(self, R, vao=None):
        """R: 3x3 rotation taking mesh coords to camera coords (x right, y up, z toward viewer)."""
        s = 1.0 / self.radius
        mvp = np.eye(4, dtype=np.float32)
        mvp[:3, :3] = R * s
        mvp[2, :3] *= -1  # GL clip z points away from the viewer
        self.fbo.use()
        self.fbo.clear(0, 0, 0, 0)
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.prog["mvp"].write(mvp.T.copy().tobytes())
        self.prog["rot"].write(R.T.astype("f4").copy().tobytes())
        (vao or self.vao).render()
        img = Image.frombytes("RGBA", (self.size, self.size), self.fbo.read(components=4))
        return img.transpose(Image.FLIP_TOP_BOTTOM)


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], np.float32)


AXES = {
    "+x": np.array([[0, 0, -1], [0, 1, 0], [1, 0, 0]], np.float32),
    "-x": np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], np.float32),
    "+y": np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], np.float32),
    "-y": np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], np.float32),
    "+z": np.eye(3, dtype=np.float32),
    "-z": np.array([[-1, 0, 0], [0, 1, 0], [0, 0, -1]], np.float32),
}


# Side-on, facing right, dorsal up: the mesh's +y (head) to camera right, +z up, +x toward the
# camera. Heading hd turns it about the vertical: R = rot_y(-hd) @ SIDE (hd = +90 deg faces
# the viewer).
SIDE = np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], np.float32)


def label_row(imgs, out):
    w = sum(i.width for i in imgs)
    row = Image.new("RGBA", (w, imgs[0].height), (20, 30, 48, 255))
    x = 0
    for i in imgs:
        row.alpha_composite(i, (x, 0))
        x += i.width
    row.convert("RGB").save(out)


def premul_resize(im, k):
    im = im.convert("RGBa")
    w, h = max(1, round(im.width * k)), max(1, round(im.height * k))
    return im.resize((w, h), Image.LANCZOS).convert("RGBA")


def crop_alpha(im, pad=2):
    a = np.array(im)[..., 3]
    ys, xs = np.nonzero(a > 3)
    if len(xs) == 0:
        return im.crop((0, 0, 1, 1)), (0, 0)
    x0, y0 = max(xs.min() - pad, 0), max(ys.min() - pad, 0)
    x1, y1 = min(xs.max() + pad + 1, im.width), min(ys.max() + pad + 1, im.height)
    return im.crop((x0, y0, x1, y1)), (int(x0), int(y0))


# View headings (deg). The screensaver snaps to the nearest one (blending two views shows
# double faces), so they are close enough that each change is a small step: wider side-on and
# away, where a fish changes little as it turns, down to 2 degrees nearing head-on, where the
# face and eyes move fastest.
BEND_DEG = 36  # full bend through a turn, head to tail
ANGLES = [-60, -50, -40, -30, -20, -10, 0, 8, 16, 24, 31, 38, 44, 50, 55, 60, 64, 68, 72, 75, 78, 81, 84, 86, 88, 90]


# A ball (the inflated pufferfish) hardly turns while inflated: a few headings, no bends.
BALL_ANGLES = [-60, -40, -20, 0, 20, 40, 60, 75, 90]


def export_views(r, name, S=1024, ball=None, length=None, ped=None):
    """ball: the inflated form of species name, drawn this many times as long as its normal
    side view; stored as the species' "ball" block. length/ped: side length and tail joint for a
    species exported for the first time without old sprites."""
    from imgio import save_rgba
    cfg = json.loads(SCENE.read_text())
    sp = cfg["species"][name]
    if length:
        sp["sideLen"] = length
        sp["ped"] = ped if ped is not None else 0.22
    # Old side sprites give the length on screen and where the tail joins.
    # (Recorded in gen/base_scene.json as "sideLen" and "ped" on the first export.)
    if "sideLen" not in sp:
        bw = Image.open(IMAGES / f"{name}_body.png").width
        tw = Image.open(IMAGES / f"{name}_tail.png").width
        ov = sp["pivot"][0]
        sp["sideLen"] = bw + tw - ov
        sp["ped"] = round((tw - ov) / sp["sideLen"], 3)
    total, frac = sp["sideLen"], sp["ped"]
    angles, prefix = ANGLES, name
    if ball:
        total, frac, angles, prefix = round(sp["sideLen"] * ball), ped if ped is not None else 0.15, BALL_ANGLES, f"{name}_ball"
    v = r.verts
    y0, y1 = float(v[:, 1].min()), float(v[:, 1].max())
    yp = y0 + frac * (y1 - y0)
    near = np.abs(v[:, 1] - yp) < 0.02 * (y1 - y0)
    zp = float(v[near, 2].mean()) if near.any() else 0.0
    fy = v[r.faces, 1].mean(axis=1)
    r.size = S
    r.fbo = r.ctx.simple_framebuffer((S, S), components=4)
    ppu = S / 2 / r.radius  # render px per mesh unit
    k = total / ((y1 - y0) * ppu)  # render px to sprite px

    sprites = []  # every rendered sprite, packed into atlas pages at the end

    def render_set(beta, angles, suffix):
        r.set_bend(beta)
        body, tail = r.part(fy >= yp), r.part(fy < yp)
        hinge = r.bend_points([0, yp, zp])[0]
        out_views = []
        for i, deg in angles:
            R = rot_y(-math.radians(deg)) @ SIDE
            out = []
            for part, tag in ((body, "b"), (tail, "t")):
                im, (cx0, cy0) = crop_alpha(premul_resize(r.render(R, part), k))
                sprites.append(im)
                # Where the mesh's center (the render's center) falls in this sprite; the
                # sprite's atlas place is filled in after packing.
                out += [round(S / 2 * k - cx0, 1), round(S / 2 * k - cy0, 1), len(sprites) - 1]
            h = R @ hinge
            out += [round(float(h[0]) * ppu * k, 1), round(float(-h[1]) * ppu * k, 1)]
            out_views.append(out)
        return out_views

    views = render_set(0.0, list(enumerate(angles)), "")
    # Bent sets for the turn (headings 0..90, where every U-turn passes): a third, two thirds
    # and full bend,
    # tail swinging toward the near flank (p) or the far one (m).
    fwd = [(i, d) for i, d in enumerate(ANGLES) if d >= 0]
    sets = {}
    for key, bf in () if ball else (("p1", 1 / 3), ("p2", 2 / 3), ("p3", 1.0), ("m1", -1 / 3), ("m2", -2 / 3), ("m3", -1.0)):
        sets[key] = render_set(bf * math.radians(BEND_DEG), fwd, key)
    # Pack into atlas pages (shelf packing, tallest first): a few big palette PNGs instead of
    # a thousand small ones, each of which would carry its own palette and zip entry.
    for f in IMAGES.glob(f"{prefix}_atlas*.png"):
        f.unlink()
    order = sorted(range(len(sprites)), key=lambda j: -sprites[j].height)
    place, pages = {}, []
    PW = PH = 2048
    x = y = shelf = 0
    page = None
    for j in order:
        im = sprites[j]
        w, h = im.width + 1, im.height + 1
        if page is None or x + w > PW:
            x, y, shelf = 0, y + shelf, 0
        if page is None or y + h > PH:
            page = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
            pages.append(page)
            x = y = shelf = 0
        page.paste(im, (x, y))
        place[j] = [len(pages) - 1, x, y, im.width, im.height]
        x += w
        shelf = max(shelf, h)
    for pi, pg in enumerate(pages):
        # Trim to the lowest sprite rectangle (not the lowest visible pixel: sprites keep a
        # transparent margin, and a region past the page's edge fails to load).
        bottom = max(pl[2] + pl[4] for pl in place.values() if pl[0] == pi)
        pg = pg.crop((0, 0, PW, bottom + 1))
        save_rgba(pg, IMAGES / f"{prefix}_atlas{pi}.png")

    def fix(vs):
        # [bx, by, bodySprite, tx, ty, tailSprite, hx, hy] -> body/tail atlas places inline
        return [v[0:2] + v[3:5] + v[6:8] + place[v[2]] + place[v[5]] for v in vs]
    views = fix(views)
    sets = {k2: fix(v2) for k2, v2 in sets.items()}
    if ball:
        sp["ball"] = {"deg": angles, "pages": len(pages), "v": views, "scale": ball}
    else:
        sp["views"] = {"deg": ANGLES, "pages": len(pages), "v": views, "bend": {"deg": BEND_DEG, "from": fwd[0][0], "sets": sets}}
    SCENE.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"{name}: {len(views)} views + {len(fwd)}x{len(sets)} bent, {len(pages)} atlas pages, side length {total}px, peduncle at {frac:.2f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("mesh")
    ap.add_argument("out")
    ap.add_argument("--size", type=int, default=256)
    ap.add_argument("--photo")
    ap.add_argument("--fat", type=float, default=1.0)
    ap.add_argument("--bend", type=float, default=0.0, help="strip: bend in degrees")
    ap.add_argument("--ball", type=float, help="views: export as the species' inflated form, this times its length")
    ap.add_argument("--len", type=int, help="views: side length in px (first export of a new species)")
    ap.add_argument("--ped", type=float, help="views: tail joint, fraction of the length from the tail end")
    ap.add_argument("--under", type=float, default=0.0, help="darken the underside (0..1), lit from above")
    a = ap.parse_args()
    r = Renderer(a.mesh, a.size, a.fat)
    r.prog["under"].value = a.under
    if a.photo:
        r.set_photo(a.photo)
    if a.cmd == "upright":
        # Candidate side-on frames: head (mesh +y) to the right, dorsal up as +z or -z.
        A = np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], np.float32)
        B = np.array([[0, 1, 0], [0, 0, -1], [-1, 0, 0]], np.float32)
        label_row([r.render(A), r.render(B)], a.out)
    if a.cmd == "strip":
        r.set_bend(math.radians(a.bend))
        R0 = SIDE
        imgs = [r.render(rot_y(-math.radians(d)) @ R0) for d in range(-60, 181, 30)]
        label_row(imgs, a.out)
    if a.cmd == "views":
        export_views(r, a.out, ball=a.ball, length=a.len, ped=a.ped)
    if a.cmd == "axes":
        label_row([r.render(R) for R in AXES.values()], a.out)
        print("order:", " ".join(AXES))
