' The wide tank (a scene with a "pan" section, e.g. scenes/wide.json): reef pieces placed
' along a tank several screens wide over an empty-tank background, with the camera sliding
' slowly left and right. Everything in the scene is in tank coordinates; s.camX is the tank x
' at the screen's left edge, and every draw subtracts it.
'
' Parallax is optional and kept mild if used (a real tank is not deep enough for much): the
' background can be drawn in horizontal bands (pan.bgBands: [y0, y1, par]), each scrolling at
' its own fraction of the camera's speed, and pieces with par < 1 are drawn behind the far
' fish at their own fraction. The wide tank uses neither: everything moves with the camera.
'
' Dev launch parameters: pan=<s> seconds per back-and-forth, cam=<x> pins the camera.

sub PanInit(s as object)
    pc = s.cfg.pan
    s.pan = { w: pc.width, period: pc.period, ease: 0.15, far: [], near: [], bands: [] }
    if pc.ease <> invalid then s.pan.ease = pc.ease
    if s.opts.pan <> invalid and s.opts.pan > 0 then s.pan.period = s.opts.pan
    ' Background: tiles side by side (each at most 2048 px wide, a Roku bitmap's limit),
    ' repeating if the tank is wider than they are. Each band cuts a region from every tile.
    tiles = []
    for each path in pc.bg
        tiles.Push(CreateObject("roBitmap", path))
    end for
    s.pan.tileW = tiles[0].GetWidth()
    for each b in pc.bgBands
        regs = []
        for each tb in tiles
            regs.Push(CreateObject("roRegion", tb, 0, b[0], tb.GetWidth(), b[1] - b[0]))
        end for
        s.pan.bands.Push({ regs: regs, y: b[0], par: b[2] })
    end for
    bmps = {}
    for each p in pc.pieces
        if bmps[p.img] = invalid then bmps[p.img] = CreateObject("roBitmap", p.img)
        b = bmps[p.img]
        tint = &hFFFFFFFF
        if p.tint <> invalid then tint = RGBA(p.tint[0], p.tint[1], p.tint[2], p.tint[3])
        sc = 1.0
        if p.sc <> invalid then sc = p.sc
        par = 1.0
        if p.par <> invalid then par = p.par
        q = { bmp: b, x: p.x, y: p.y, sc: sc, par: par, w: b.GetWidth() * sc, h: b.GetHeight() * sc, mir: (p.mir = true), tint: tint, shadow: (p.shadow <> false) }
        if par < 1 then s.pan.far.Push(q) else s.pan.near.Push(q)
    end for
    s.camX = 0.0
    s.camDx = 0.0
end sub

sub PanUpdate(s as object, t as float)
    pn = s.pan
    if s.opts.cam <> invalid
        x = s.opts.cam
    else
        ' On the 30 fps frame grid (the clock's jitter within a frame would otherwise make
        ' the steps uneven), and in whole pixels: the Roku draws at whole pixels, so every
        ' layer that moves with the camera then steps on the same frame.
        tq = Int(t * 30 + 0.5) / 30.0
        x = Int((pn.w - 1920) * PanSweep(tq / pn.period, pn.ease) + 0.5)
    end if
    s.camDx = x - s.camX
    s.camX = x
    ' Marine snow drifts past at its own depth's parallax.
    for each mo in s.motes
        mo.x = mo.x - s.camDx * (0.4 + 0.6 * mo.z)
        if mo.x < -10 then mo.x = mo.x + 1940
        if mo.x > 1930 then mo.x = mo.x - 1940
    end for
end sub

' Where the camera is (0 .. 1 across the tank) at phase u of a back-and-forth: a steady glide,
' speeding up over the first fraction e of each sweep and slowing down over the last (constant
' acceleration), so it turns round at each end without lingering there.
function PanSweep(u as float, e as float) as float
    u = 2 * (u - Int(u))
    if u > 1 then u = 2 - u
    if u > 0.5 then return 1 - PanGlide(1 - u, e)
    return PanGlide(u, e)
end function

' The first half of a sweep (u = 0 .. 0.5 of it): speeding up, then gliding.
function PanGlide(u as float, e as float) as float
    if u < e then return u * u / (2 * e * (1 - e))
    return (u - 0.5 * e) / (1 - e)
end function

sub PanDrawBg(s as object, screen as object)
    tw = s.pan.tileW
    for each b in s.pan.bands
        n = b.regs.Count()
        ox = Int(s.camX * b.par + 0.5)
        k = Int(ox / tw)
        x = k * tw - ox
        while x < 1920
            screen.DrawObject(x, b.y, b.regs[k mod n])
            x = x + tw
            k = k + 1
        end while
    end for
end sub

sub PanDrawPieces(s as object, screen as object, list as object)
    puff = s.puff
    for each q in list
        sx = Int(q.x - s.camX * q.par + 0.5)
        if sx < 1920 and sx + q.w > 0
            ' A soft contact shadow on the sand under the piece.
            if q.shadow then screen.DrawScaledObject(sx + q.w * 0.08, q.y + q.h * 0.94, q.w * 0.84 / 24, q.h * 0.08 / 24, puff, &h0A141E00 + Int(90 * q.par))
            if q.mir
                screen.DrawScaledObject(sx + q.w, q.y, -q.sc, q.sc, q.bmp, q.tint)
            else
                screen.DrawScaledObject(sx, q.y, q.sc, q.sc, q.bmp, q.tint)
            end if
        end if
    end for
end sub

sub PanFrame(s as object, screen as object, t as float)
    screen.SetAlphaEnable(false)
    PanDrawBg(s, screen)
    screen.SetAlphaEnable(true)
    DrawCaustics(s, screen, t)
    PanDrawPieces(s, screen, s.pan.far)
    DrawMotes(s, screen, s.motesFar)
    fishes = s.fish
    n = fishes.Count()
    i = 0
    while i < n and fishes[i].z < s.cfg.fgZ
        FishDraw(s, screen, fishes[i])
        i = i + 1
    end while
    DrawRays(s, screen, t)
    PanDrawPieces(s, screen, s.pan.near)
    CrittersDraw(s, screen, t)
    while i < n
        FishDraw(s, screen, fishes[i])
        i = i + 1
    end while
    DrawMotes(s, screen, s.motesNear)
    if s.night > 0 then screen.DrawRect(0, 0, 1920, 1080, s.nightRgba)
end sub
