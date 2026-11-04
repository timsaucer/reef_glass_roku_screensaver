' Fish: behavior, swimming animation and depth.
'
' Each fish swims forward along a heading hd, an angle in the horizontal plane: 0 is toward
' screen right, pi toward screen left, +pi/2 toward the glass. It never slides sideways or
' backward. Screen x moves with cos(hd), depth z with sin(hd).
'
' Turning: a fish turns on a circle about sp.radius px across at its swimming speed, so a
' U-turn takes a few seconds and the fish keeps swimming through it. A U-turn always swings
' the head toward the glass: the side view narrows, crossfades into the head-on view
' (<name>_front.png) as the fish faces the viewer, then widens again mirrored.
'
' Sprites: a right-facing body plus a separate tail hinged at the body's tail pivot. The tail
' beat squashes the tail horizontally; its amplitude follows swimming effort.
'
' Depth z (0 far .. 1 near) sets scale, on-screen speed, haze tint and draw order. Fish change
' depth freely in open water, but never cross the reef layer (fgZ) or the anemone's depth
' while over coral (reef.json "coral" map): that would flip them from in front of the coral
' to behind it in a single frame. Over open water the same change is invisible.
'
' Behaviors (reef.json "species"):
'   roam  cruise between waypoints across the whole tank, often leaving the frame
'   home  wander slowly around a home point (the anemone, a ledge, a coral head); "dart"
'         adds short fast bursts, as damselfish do; "hover" is the chance of resting a while

sub FishInit(s as object)
    cfg = s.cfg
    s.sprites = {}
    s.fish = []
    ' Depth units per pixel of travel along the heading.
    s.kz = 1.0 / 800
    ' Depth per px along a fish's body, for its perspective when angled: exaggerated, since a
    ' real camera this close to the glass would show more taper than z alone gives.
    s.cardKz = 1.6 * s.kz
    ' Coral map: rows of '#' (coral) and '.' (open water), one char per cell px square.
    s.coral = invalid
    if cfg.coral <> invalid
        s.coral = { cell: cfg.coral.cell, rows: [] }
        for each r in cfg.coral.rows
            row = []
            for i = 0 to Len(r) - 1
                row.Push(Mid(r, i + 1, 1) = "#")
            end for
            s.coral.rows.Push(row)
        end for
    end if
    s.zWalls = [cfg.fgZ, cfg.anemone.z]
    ' Haze tint by depth, precomputed in 21 steps: far fish take on the water color and some
    ' transparency, so they sit back in the blue.
    hz = cfg.haze
    s.tints = []
    for i = 0 to 20
        z = i / 20.0
        k = (1 - z) * hz.far
        r = Int(255 * (1 - k) + hz.rgb[0] * k)
        g = Int(255 * (1 - k) + hz.rgb[1] * k)
        b = Int(255 * (1 - k) + hz.rgb[2] * k)
        s.tints.Push(RGBA(r, g, b, Int(255 * (1 - 0.3 * k))))
    end for
    for each name in cfg.species
        sp = cfg.species[name]
        if sp.count > 0
            spr = LoadFishSprite(name, sp.pivot)
            if sp.front = true then spr.front = CreateObject("roBitmap", "pkg:/images/" + name + "_front.png")
            s.sprites[name] = spr
            for i = 0 to sp.count - 1
                f = NewFish(s, sp, spr, i)
                f.name = name
                s.fish.Push(f)
            end for
        end if
    end for
    SortFish(s.fish)
end sub

function LoadFishSprite(name as string, pivot as object) as object
    body = CreateObject("roBitmap", "pkg:/images/" + name + "_body.png")
    tail = CreateObject("roBitmap", "pkg:/images/" + name + "_tail.png")
    spr = {
        body: body, tail: tail
        bw: body.GetWidth(), bh: body.GetHeight(), tw: tail.GetWidth(), th: tail.GetHeight()
        px: pivot[0], py: pivot[1], strips: [], su: []
    }
    ' Vertical strips of the body, drawn each at its own depth when the fish swims at an angle
    ' to the glass. Each overlaps the next by a pixel so no seams open.
    n = 6
    for i = 0 to n - 1
        u0 = Int(i * spr.bw / n)
        u1 = Int((i + 1) * spr.bw / n)
        w = u1 - u0 + 1
        if u0 + w > spr.bw then w = spr.bw - u0
        spr.strips.Push(CreateObject("roRegion", body, u0, 0, w, spr.bh))
        spr.su.Push(u0)
    end for
    spr.su.Push(spr.bw)
    return spr
end function

function NewFish(s as object, sp as object, spr as object, idx as integer) as object
    f = {
        sp: sp, spr: spr
        x: 0.0, y: 0.0, z: 0.5
        hd: 0.0, spd: 0.0, vy: 0.0, turnRate: 0.0
        tx: 0.0, ty: 0.0, tz: 0.5
        face: 1.0, amp: 0.1
        phase: Rnd(0) * 6.283
        mul: 1.0, timer: 0.0, pause: 0.0
        size: sp.len / spr.bw
        cruise: sp.speed * RndRange(0.85, 1.15)
        big: false, turnDir: 0, blockT: 0.0
        radius: 0.5 * sp.len
    }
    if sp.radius <> invalid then f.radius = sp.radius
    if sp.big <> invalid then f.big = sp.big
    fgZ = s.cfg.fgZ
    if sp.behavior = "home"
        if sp.home <> invalid
            ' Clownfish: in front of their anemone, never behind its tentacles.
            a = s.cfg.anemone
            f.hx = a.home[0] : f.hy = a.home[1]
            f.z0 = a.z + 0.015 : f.z1 = 0.99
        else
            h = sp.homes[idx mod sp.homes.Count()]
            f.hx = h[0] : f.hy = h[1]
            f.z0 = h[2] - 0.04 : f.z1 = h[2] + 0.06
            if f.z0 < fgZ + 0.02 then f.z0 = fgZ + 0.02
            if f.z1 > 0.99 then f.z1 = 0.99
            if sp.zr <> invalid then f.z0 = sp.zr[0] : f.z1 = sp.zr[1]
        end if
    else
        r = s.cfg.roam
        f.z0 = r.back[0] : f.z1 = r.front[1]
    end if
    PickTarget(s, f)
    f.x = f.tx : f.y = f.ty : f.z = f.tz
    f.hd = Rnd(0) * 6.283
    f.spd = f.cruise * 0.6
    PickTarget(s, f)
    return f
end function

sub PickTarget(s as object, f as object)
    sp = f.sp
    f.mul = 1.0
    if sp.behavior = "roam"
        r = s.cfg.roam
        ' Now and then a cruiser drops down to graze over the open sand (and spooks the goby).
        area = r
        low = (r.low <> invalid and Rnd(0) < r.low.chance)
        if low then area = r.low
        f.tx = RndRange(area.x0, area.x1)
        if not low
            ' Keep cruising the way it faces, at least 500 px on; past the far edge it turns
            ' round out of sight. Only a fish already near that edge comes back the other way.
            if Cos(f.hd) >= 0
                if f.x < area.x1 - 150 then f.tx = RndRange(Min(f.x + 500, area.x1), area.x1) else f.tx = RndRange(area.x0, f.x - 500)
            else
                if f.x > area.x0 + 150 then f.tx = RndRange(area.x0, Max(f.x - 500, area.x0)) else f.tx = RndRange(f.x + 500, area.x1)
            end if
        end if
        f.ty = RndRange(area.y0, area.y1)
        ' Depth: either well behind the reef or out in front of it, near the glass.
        if Rnd(0) < r.frontChance then f.tz = RndRange(r.front[0], r.front[1]) else f.tz = RndRange(r.back[0], r.back[1])
        ' Now and then a fish far back comes up close to the glass on a steep course, or one at
        ' the glass heads off steeply into the distance.
        if not low and Rnd(0) < 0.3
            dirx = 1
            if Cos(f.hd) < 0 then dirx = -1
            f.tx = f.x + dirx * RndRange(200, 400)
            if f.z < 0.6 then f.tz = RndRange(r.front[0], r.front[1]) else f.tz = RndRange(r.back[0], r.back[0] + 0.3)
        end if
        f.timer = RndRange(20, 40)
    else
        ' Keep going roughly the way it faces; only when that would leave the home range does
        ' it pick a point back inside (and so turn around). Fewer, decisive turns look natural.
        dirx = 1
        if Cos(f.hd) < 0 then dirx = -1
        f.tx = f.x + dirx * RndRange(0.4, 1.0) * sp.r
        if Abs(f.tx - f.hx) > sp.r then f.tx = f.hx - dirx * RndRange(0.2, 0.9) * sp.r
        f.ty = f.hy + (Rnd(0) * 2 - 1) * sp.r * 0.4
        f.tz = RndRange(f.z0, f.z1)
        f.timer = RndRange(8, 16)
        if sp.dart <> invalid and Rnd(0) < sp.dart then f.mul = 2.6
        if sp.hover <> invalid and Rnd(0) < sp.hover then f.pause = RndRange(2, 5)
    end if
end sub

sub FishUpdate(s as object, t as float, dt as float)
    act = s.activity
    kz = s.kz
    kPi = 3.14159265
    for each f in s.fish
        sp = f.sp
        f.timer = f.timer - dt
        ' Distance to the waypoint in the swimming plane (depth converted to pixels).
        dx = f.tx - f.x
        dzp = (f.tz - f.z) / kz
        ' Move on to the next waypoint before arriving, so the path flows instead of stopping.
        ' Arrival counts across-the-screen distance only; depth is picked up on the way.
        if Abs(dx) < sp.near or f.timer < 0
            PickTarget(s, f)
            dx = f.tx - f.x
            dzp = (f.tz - f.z) / kz
        end if

        ' Steer toward the waypoint, through depth as well as across. A fish may angle up to
        ' ~70 degrees toward the glass, or ~55 degrees away from it (it is never seen from
        ' straight behind).
        if dzp > 0 then lim = 3.0 * Abs(dx) else lim = 1.4 * Abs(dx)
        if f.blockT > 0
            f.blockT = f.blockT - dt
            lim = 0
        end if
        diff = Atan2(Clamp(dzp, -lim, lim), dx) - f.hd
        while diff > kPi
            diff = diff - 2 * kPi
        end while
        while diff < -kPi
            diff = diff + 2 * kPi
        end while
        ' Turn rate from a turning circle at swimming speed; a slow fish still turns.
        w = Clamp(f.spd / f.radius, 0.7, sp.turn)
        if f.turnDir = 0 and Abs(diff) > 1.6
            ' A U-turn: swing the head toward the glass, whichever way that is.
            if Cos(f.hd) >= 0 then f.turnDir = 1 else f.turnDir = -1
        end if
        if f.turnDir <> 0
            turn = f.turnDir * w * dt
            if Abs(diff) < 0.3 then f.turnDir = 0
        else
            turn = Clamp(diff, -w * dt, w * dt)
        end if
        f.hd = f.hd + turn
        if f.hd > kPi then f.hd = f.hd - 2 * kPi
        if f.hd < -kPi then f.hd = f.hd + 2 * kPi
        if dt > 0 then f.turnRate = Abs(turn) / dt

        ' Speed: cruise, easing off only a little through turns; nearly still while hovering.
        want = f.cruise * f.mul * act * (0.8 + 0.2 * Cos(diff))
        if f.pause > 0
            f.pause = f.pause - dt
            want = f.cruise * 0.12
        end if
        rate = 1.2
        if f.mul > 1 then rate = 5.0
        f.spd = f.spd + (want - f.spd) * Clamp(rate * dt, 0, 1)

        ' Move along the heading. Far fish cover less screen for the same swimming speed.
        sc = 0.4 + 0.6 * f.z
        c = Cos(f.hd)
        f.x = f.x + c * f.spd * sc * dt
        zn = Clamp(f.z + Sin(f.hd) * f.spd * kz * dt, f.z0, f.z1)
        ' Over coral a fish holds its side of the reef, and swims side-on until clear of it.
        if CrossesCoral(s, f, zn) then f.blockT = 1.5 else f.z = zn
        ' Gentle climbs and dives toward the waypoint's height.
        vyWant = Clamp((f.ty - f.y) * 0.6, -0.35 * f.spd, 0.35 * f.spd)
        f.vy = f.vy + (vyWant - f.vy) * Clamp(1.5 * dt, 0, 1)
        f.y = f.y + f.vy * sc * dt


        ' Tail: amplitude follows effort (speed relative to cruise, plus turning); frequency
        ' rises a little with speed.
        effort = f.spd / sp.speed
        a = 0.04 + 0.2 * Clamp(effort, 0, 1.5) + 0.06 * Clamp(f.turnRate / sp.turn, 0, 1)
        f.amp = f.amp + (a - f.amp) * Clamp(3 * dt, 0, 1)
        f.phase = f.phase + dt * 6.283 * sp.beat * (0.5 + 0.5 * Clamp(effort, 0, 2))

        ' Cruisers well off-screen may jump to a new depth; nobody can see it.
        if sp.behavior = "roam" and (f.x < -120 or f.x > 2040) and f.timer > 0 and Rnd(0) < 0.004
            r = s.cfg.roam
            if Rnd(0) < r.frontChance then f.z = RndRange(r.front[0], r.front[1]) else f.z = RndRange(r.back[0], r.back[1])
            f.tz = f.z
        end if
    end for
    SortFish(s.fish)
end sub

' True when moving to depth zn would take the fish across the reef layer or the anemone while
' coral is behind or in front of it.
function CrossesCoral(s as object, f as object, zn as float) as boolean
    cross = false
    for each w in s.zWalls
        if (f.z - w) * (zn - w) <= 0 and f.z <> zn then cross = true
    end for
    if not cross or s.coral = invalid then return false
    c = s.coral
    sc = f.size * (0.4 + 0.6 * f.z)
    hl = 0.5 * sc * f.spr.bw + 0.3 * sc * f.spr.tw
    hh = 0.4 * sc * f.spr.bh
    nr = c.rows.Count()
    gy0 = Int((f.y - hh) / c.cell) : gy1 = Int((f.y + hh) / c.cell)
    gx0 = Int((f.x - hl) / c.cell) : gx1 = Int((f.x + hl) / c.cell)
    for gy = gy0 to gy1
        if gy >= 0 and gy < nr
            row = c.rows[gy]
            for gx = gx0 to gx1
                if gx >= 0 and gx < row.Count()
                    if row[gx] then return true
                end if
            end for
        end if
    end for
    return false
end function

function Atan2(y as float, x as float) as float
    if x > 0 then return Atn(y / x)
    if x < 0
        if y >= 0 then return Atn(y / x) + 3.14159265
        return Atn(y / x) - 3.14159265
    end if
    if y > 0 then return 1.5707963
    if y < 0 then return -1.5707963
    return 0
end function

' Insertion sort by depth: the order barely changes between frames, so this is near-linear.
sub SortFish(a as object)
    n = a.Count()
    for i = 1 to n - 1
        f = a[i]
        j = i - 1
        while j >= 0 and a[j].z > f.z
            a[j + 1] = a[j]
            j = j - 1
        end while
        a[j + 1] = f
    end for
end sub

sub FishDraw(s as object, screen as object, f as object)
    col = s.tints[Int(f.z * 20 + 0.5)]
    spr = f.spr
    c = Cos(f.hd)
    ac = Abs(c)
    ' Close to head-on the body is nearly edge-on: the head-on sprite fades in over it.
    wf = 0
    if spr.front <> invalid and Sin(f.hd) > 0 then wf = SmoothStep(0.36, 0.12, ac)
    if ac > 0.04
        wb = 1
        if spr.front <> invalid then wb = 1 - SmoothStep(0.22, 0.05, ac)
        tailK = 1 - f.amp * (0.5 + 0.5 * Cos(f.phase))
        DrawFishCard(s, screen, spr, f.x, f.y, f.z, f.size, f.hd, tailK, FadeCol(col, wb))
    end if
    if wf > 0
        ' Head-on view, centered a little toward the head and sized by the head's depth.
        g = f.size
        a = 0.2 * spr.bw * g
        zf = f.z + a * Sin(f.hd) * s.cardKz
        sc = g * (0.4 + 0.6 * zf)
        fb = spr.front
        fw = fb.GetWidth() : fh = fb.GetHeight()
        sx = sc * (0.8 + 0.2 * Sin(f.hd)) * (1 + 0.04 * Sin(f.phase))
        if c < 0 then sx = -sx
        x = f.x + a * c * sc / g + 1.2 * sc * Sin(f.phase)
        screen.DrawScaledObject(x - sx * fw / 2, f.y - sc * fh / 2, sx, sc, fb, FadeCol(col, wf))
    end if
end sub

' Draws the body+tail sprite as a card turned to heading hd, in perspective: each vertical
' strip of the body is scaled by its own depth, so a fish angled toward the glass has its head
' end larger than its tail. Side-on (hd 0 or pi) it is the plain sprite, mirrored for pi.
sub DrawFishCard(s as object, screen as object, spr as object, x as float, y as float, z as float, g as float, hd as float, tailK as float, col as integer)
    c = Cos(hd) : sn = Sin(hd)
    kd = s.cardKz * sn
    half = spr.bw / 2
    n = spr.strips.Count()
    ' Tail, hinged at the pivot, at the depth of the tail end.
    ap = (spr.px - half) * g
    zp = z + ap * kd
    xp = x + ap * c * (0.4 + 0.6 * zp)
    zt = z + (ap - 0.5 * spr.tw * g) * kd
    stt = g * (0.4 + 0.6 * zt)
    sxt = stt * c * tailK
    screen.DrawScaledObject(xp - sxt * spr.tw, y + stt * (spr.py - spr.bh / 2 - spr.th / 2), sxt, stt, spr.tail, col)
    ' Nearly side-on the taper is invisible: one draw for the whole body.
    if Abs(sn) < 0.1
        sm = g * (0.4 + 0.6 * z)
        sx = sm * c
        screen.DrawScaledObject(x - sx * half, y - sm * spr.bh / 2, sx, sm, spr.body, col)
        return
    end if
    ' Body strips over it, tail end first. a = offset along the body in px at z = 1.
    a = (spr.su[0] - half) * g
    zz = z + a * kd
    xa = x + a * c * (0.4 + 0.6 * zz)
    for i = 0 to n - 1
        b = (spr.su[i + 1] - half) * g
        zb = z + b * kd
        xb = x + b * c * (0.4 + 0.6 * zb)
        sm = g * (0.4 + 0.6 * (z + 0.5 * (a + b) * kd))
        sx = (xb - xa) / (spr.su[i + 1] - spr.su[i])
        screen.DrawScaledObject(xa, y - sm * spr.bh / 2, sx, sm, spr.strips[i], col)
        a = b : xa = xb
    end for
end sub

' Dev: one fish of a species drawn at headings from 0 to pi (a U-turn through the glass side),
' side by side at z = 1, over a dark band.
sub DrawPoses(s as object, screen as object, name as string)
    if s.poseA0 = invalid
        s.poseA0 = 0.0 : s.poseA1 = 3.14159265
        if s.opts.poseFine <> invalid then s.poseA0 = 0.785 : s.poseA1 = 1.571
    end if
    for each g in s.fish
        if g.name = name
            screen.DrawRect(0, 380, 1920, 320, &h102030FF)
            f = { sp: g.sp, spr: g.spr, size: g.size, z: 1.0, hd: 0.0, amp: 0.1, phase: 0.0, x: 0.0, y: 540.0 }
            for i = 0 to 8
                f.hd = s.poseA0 + (s.poseA1 - s.poseA0) * i / 8
                f.x = 120 + i * 210
                FishDraw(s, screen, f)
            end for
            return
        end if
    end for
end sub

' The tint with its alpha scaled by k.
function FadeCol(col as integer, k as float) as integer
    a = col and &hFF
    return (col and &hFFFFFF00) + Int(a * k)
end function

function Min(a as float, b as float) as float
    if a < b then return a
    return b
end function

function Max(a as float, b as float) as float
    if a > b then return a
    return b
end function
