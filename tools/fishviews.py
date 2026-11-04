"""Render a fish mesh (tools/fish3d.py) into turn views for the screensaver.

Usage (TripoSR's env, which has moderngl and trimesh):
  ext/venv/bin/python tools/fishviews.py axes <mesh.ply> <out.png>
      six axis-aligned views side by side, for finding the mesh's orientation
  ext/venv/bin/python tools/fishviews.py strip <mesh.ply> <out.png> [--photo keyed.png]
      the fish at headings -60..180 in 30 degree steps, for review
  ext/venv/bin/python tools/fishviews.py views <mesh.ply> <name> --photo keyed.png [--fat 1.0]
      the screensaver's turn views: images/<name>_<k>b.png (body) and <name>_<k>t.png (tail)
      for the headings in ANGLES, -60..90 deg (the rest are mirrors), sized so the side view
      is "sideLen" px long (first time: as long as the old <name>_body/tail sprites, whose
      tail split also gives "ped", where the tail joins), and the "views" block of the species in
      scenes/reef.json (per view: body anchor, tail anchor, tail hinge; see fish.brs)

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
out vec3 vcol;
out vec3 vn;
out vec3 mpos;
out vec3 mn;
void main() {
    gl_Position = mvp * vec4(pos, 1.0);
    vcol = col;
    vn = rot * nrm;
    mpos = pos;
    mn = nrm;
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
out vec4 frag;
void main() {
    vec3 n = normalize(vn);
    vec3 base = vcol;
    // The side photo, projected straight across onto both flanks (fish are symmetric).
    vec2 uv = vec2((mpos.y - box.x) / (box.y - box.x), (box.w - mpos.z) / (box.w - box.z));
    vec4 ph = texture(photo, uv);
    float side = smoothstep(0.25, 0.6, abs(normalize(mn).x)) * ph.a * usePhoto;
    base = mix(base, ph.rgb, side);
    // Mostly the photo's own shading (baked into the colors); a little light from above
    // the camera keeps the thickness readable when the fish faces the viewer.
    float l = 0.82 + 0.18 * max(dot(n, normalize(vec3(0.0, 0.6, 0.8))), 0.0);
    frag = vec4(base * l, 1.0);
}
"""


ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "roku/reefglass/images"
SCENE = ROOT / "roku/reefglass/scenes/reef.json"
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
        data = np.hstack([v, c, n]).astype("f4")
        self.vbo = self.ctx.buffer(data.tobytes())
        self.faces = np.asarray(m.faces, np.int32)
        self.vao = self.part(np.ones(len(self.faces), bool))
        self.fbo = self.ctx.simple_framebuffer((size, size), components=4)
        self.verts = v
        self.prog["usePhoto"].value = 0.0

    def set_photo(self, path):
        """The keyed side photo (RGBA, head right): its fish's bounding box is matched to the
        mesh's extent along its length (y) and height (z)."""
        im = Image.open(path).convert("RGBA")
        a = np.array(im)[..., 3]
        ys, xs = np.nonzero(a > 128)
        im = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
        tex = self.ctx.texture(im.size, 4, im.tobytes())
        tex.build_mipmaps()
        tex.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
        tex.repeat_x = tex.repeat_y = False
        tex.use(0)
        self.prog["photo"].value = 0
        v = self.verts
        self.prog["box"].value = (float(v[:, 1].min()), float(v[:, 1].max()), float(v[:, 2].min()), float(v[:, 2].max()))
        self.prog["usePhoto"].value = 1.0

    def part(self, sel):
        ibo = self.ctx.buffer(self.faces[sel].tobytes())
        return self.ctx.vertex_array(self.prog, [(self.vbo, "3f 3f 3f", "pos", "col", "nrm")], ibo)

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


# View headings (deg): wide steps side-on and away, narrow ones nearing head-on, where the face
# and eyes move fastest and a blend of distant views would show double.
ANGLES = [-60, -45, -30, -15, 0, 12, 24, 35, 45, 54, 62, 69, 75, 80, 84, 87, 90]


def export_views(r, name, S=1024):
    from imgio import save_rgba
    cfg = json.loads(SCENE.read_text())
    sp = cfg["species"][name]
    # Old side sprites give the length on screen and where the tail joins.
    # (Recorded in reef.json as "sideLen" and "ped" on the first export.)
    if "sideLen" not in sp:
        bw = Image.open(IMAGES / f"{name}_body.png").width
        tw = Image.open(IMAGES / f"{name}_tail.png").width
        ov = sp["pivot"][0]
        sp["sideLen"] = bw + tw - ov
        sp["ped"] = round((tw - ov) / sp["sideLen"], 3)
    total, frac = sp["sideLen"], sp["ped"]
    v = r.verts
    y0, y1 = float(v[:, 1].min()), float(v[:, 1].max())
    yp = y0 + frac * (y1 - y0)
    near = np.abs(v[:, 1] - yp) < 0.02 * (y1 - y0)
    zp = float(v[near, 2].mean()) if near.any() else 0.0
    fy = v[r.faces, 1].mean(axis=1)
    body, tail = r.part(fy >= yp), r.part(fy < yp)
    r.size = S
    r.fbo = r.ctx.simple_framebuffer((S, S), components=4)
    ppu = S / 2 / r.radius  # render px per mesh unit
    k = total / ((y1 - y0) * ppu)  # render px to sprite px
    views = []
    for i, deg in enumerate(ANGLES):
        R = rot_y(-math.radians(deg)) @ SIDE
        out = []
        for part, tag in ((body, "b"), (tail, "t")):
            im, (cx0, cy0) = crop_alpha(premul_resize(r.render(R, part), k))
            save_rgba(im, IMAGES / f"{name}_{i}{tag}.png")
            # Where the mesh's center (the render's center) falls in this sprite.
            out += [round(S / 2 * k - cx0, 1), round(S / 2 * k - cy0, 1)]
        h = R @ np.array([0, yp, zp], np.float32)
        out += [round(float(h[0]) * ppu * k, 1), round(float(-h[1]) * ppu * k, 1)]
        views.append(out)
    sp["views"] = {"deg": ANGLES, "v": views}
    SCENE.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"{name}: {len(views)} views, side length {total}px, peduncle at {frac:.2f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("mesh")
    ap.add_argument("out")
    ap.add_argument("--size", type=int, default=256)
    ap.add_argument("--photo")
    ap.add_argument("--fat", type=float, default=1.0)
    a = ap.parse_args()
    r = Renderer(a.mesh, a.size, a.fat)
    if a.photo:
        r.set_photo(a.photo)
    if a.cmd == "upright":
        # Candidate side-on frames: head (mesh +y) to the right, dorsal up as +z or -z.
        A = np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], np.float32)
        B = np.array([[0, 1, 0], [0, 0, -1], [-1, 0, 0]], np.float32)
        label_row([r.render(A), r.render(B)], a.out)
    if a.cmd == "strip":
        R0 = SIDE
        imgs = [r.render(rot_y(-math.radians(d)) @ R0) for d in range(-60, 181, 30)]
        label_row(imgs, a.out)
    if a.cmd == "views":
        export_views(r, a.out)
    if a.cmd == "axes":
        label_row([r.render(R) for R in AXES.values()], a.out)
        print("order:", " ".join(AXES))
