' Fish: behavior, swimming animation and depth.
'
' Each fish swims forward along a heading hd, an angle in the horizontal plane: 0 is toward
' screen right, pi toward screen left, +pi/2 toward the glass. It never slides sideways or
' backward. Screen x moves with cos(hd), depth z with sin(hd).
'
' Turning: a fish turns on a circle about sp.radius px across at its swimming speed, so a
' U-turn takes a few seconds and the fish keeps swimming through it. A U-turn always swings
' the head toward the glass. Every heading is drawn from views rendered off the fish's 3D
' model (LoadFishViews), so it turns with real thickness and shows its face head-on.
'
' Sprites: a right-facing body plus a separate tail hinged at the body's tail pivot. The tail
' beat squashes the tail horizontally; its amplitude follows swimming effort.
'
' Depth z (0 far .. 1 near) sets scale, on-screen speed, haze tint and draw order. Fish change
' depth freely in open water, but never cross the reef layer (fgZ)
' while over coral (reef.json "coral" map): that would flip them from in front of the coral
' to behind it in a single frame. Over open water the same change is invisible.
'
' Behaviors (reef.json "species"):
'   roam  cruise between waypoints across the whole tank, often leaving the frame
'   home  wander slowly around a home point (the anemone, a ledge, a coral head); "dart"
'         adds short fast bursts, as damselfish do; "hover" is the chance of resting a while,
'         "shuffle" makes those rests fidgety; "excursion" is the chance of a short trip off
'         home and back; "follow" ("pair" or "school") makes the second and later fish
'         follow the first (any behavior); "visit" (roam) is the chance of dropping by a
'         spot (its own of "homes", else "visitAt", else the anemone) to hover

sub FishInit(s as object)
    cfg = s.cfg
    s.sprites = {}
    s.fish = []
    ' Depth units per pixel of travel along the heading.
    s.kz = 1.0 / 800
    s.depthMin = 0.72
    if cfg.depthScale <> invalid then s.depthMin = cfg.depthScale
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
    s.zWalls = [cfg.fgZ]
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
            spr = LoadFishViews(name, sp.views)
            spr.ball = invalid
            if sp.ball <> invalid then spr.ball = LoadBallViews(name, sp.ball)
            s.sprites[name] = spr
            lead = invalid
            for i = 0 to sp.count - 1
                f = NewFish(s, sp, spr, i)
                f.name = name
                ' A pair or school ("follow"): the first leads, the rest follow it about, each at
                ' its own place behind and beside it. A pair's follower (the male clownfish) is
                ' smaller.
                if sp.follow <> invalid
                    if lead = invalid
                        lead = f
                    else
                        f.leader = lead
                        L = sp.sideLen
                        if sp.follow = "pair"
                            f.slot = [0.9 * L, 24]
                            f.size = 0.85
                        else
                            f.slot = [RndRange(0.6, 2.2) * L, RndRange(-1, 1) * 0.9 * L]
                            f.size = RndRange(0.85, 1.05)
                        end if
                        f.wob = Rnd(0) * 6.283
                    end if
                end if
                s.fish.Push(f)
            end for
        end if
    end for
    SortFish(s.fish)
end sub

' Turn views rendered from the fish's 3D model (tools/fishviews.py): for the headings in "deg"
' (-60 .. 90, closer together nearing head-on), a body and a tail sprite each, with where the fish's center falls
' in each sprite and where the tail joins the body (relative to the center, px at z = 1).
' Headings beyond 90 degrees are drawn as mirrors of these.
' v: [bx, by, tx, ty, hx, hy, body page, x, y, w, h, tail page, x, y, w, h]
function NewFishView(pages as object, v as object) as object
    b = CreateObject("roRegion", pages[v[6]], v[7], v[8], v[9], v[10])
    t = CreateObject("roRegion", pages[v[11]], v[12], v[13], v[14], v[15])
    return { b: b, t: t, bx: v[0], by: v[1], tx: v[2], ty: v[3], hx: v[4], hy: v[5], w: v[9] }
end function

function LoadFishViews(name as string, vc as object) as object
    spr = { views: [], ang: [] }
    for each d in vc.deg
        spr.ang.Push(d * 3.14159265 / 180)
    end for
    ' The sprites live packed in atlas pages (<name>_atlas<p>.png).
    pages = []
    for p = 0 to vc.pages - 1
        pages.Push(CreateObject("roBitmap", "pkg:/images/" + name + "_atlas" + p.ToStr() + ".png"))
    end for
    for each v in vc.v
        spr.views.Push(NewFishView(pages, v))
    end for
    ' Bent sets, for headings from index "from" on (0..90 degrees, where U-turns pass): p1/p2
    ' half and full bend with the tail swung toward the fish's near flank (as seen at heading
    ' 0), m1/m2 toward the far one.
    spr.bsets = invalid
    if vc.bend <> invalid
        spr.bsets = {}
        spr.bfrom = vc.bend.from
        for each key in vc.bend.sets
            set = []
            for each v in vc.bend.sets[key]
                set.Push(NewFishView(pages, v))
            end for
            spr.bsets[key] = set
        end for
    end if
    ' Side view size, for coral overlap tests.
    side = spr.views[0]
    for k = 0 to spr.ang.Count() - 1
        if Abs(spr.ang[k]) < 0.01 then side = spr.views[k]
    end for
    spr.bw = side.b.GetWidth() : spr.bh = side.b.GetHeight() : spr.tw = side.t.GetWidth()
    return spr
end function

' A pufferfish's inflated form: a few views of the ball (<name>_ball_atlas<p>.png).
function LoadBallViews(name as string, vc as object) as object
    ball = { views: [], ang: [] }
    for each d in vc.deg
        ball.ang.Push(d * 3.14159265 / 180)
    end for
    pages = []
    for p = 0 to vc.pages - 1
        pages.Push(CreateObject("roBitmap", "pkg:/images/" + name + "_ball_atlas" + p.ToStr() + ".png"))
    end for
    for each v in vc.v
        ball.views.Push(NewFishView(pages, v))
    end for
    return ball
end function

function NewFish(s as object, sp as object, spr as object, idx as integer) as object
    f = {
        sp: sp, spr: spr
        x: 0.0, y: 0.0, z: 0.5
        hd: 0.0, spd: 0.0, vy: 0.0, turnRate: 0.0, bend: 0.0
        tx: 0.0, ty: 0.0, tz: 0.5
        face: 1.0, amp: 0.1
        phase: Rnd(0) * 6.283
        mul: 1.0, timer: 0.0, pause: 0.0
        size: 1.0
        cruise: sp.speed * RndRange(0.85, 1.15)
        big: false, turnDir: 0, blockT: 0.0, leader: invalid, away: false, visiting: false, slot: invalid, wob: 0.0, visitAt: invalid
        puff: 0.0, pmode: "none", ptime: 0.0, pcool: RndRange(40, 90)
        radius: 0.5 * sp.sideLen
    }
    if sp.radius <> invalid then f.radius = sp.radius
    if sp.big <> invalid then f.big = sp.big
    fgZ = s.cfg.fgZ
    if sp.behavior = "home"
        if sp.home <> invalid
            ' Clownfish: in front of their anemone (part of the reef layer).
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
        ' A roamer with "homes" visits its own one.
        if sp.homes <> invalid then f.visitAt = sp.homes[idx mod sp.homes.Count()]
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
        ' Now and then a cruiser drops down to graze over the open sand.
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
        ' Roamers with a "visit" chance (the clownfish) now and then drop by the anemone and
        ' hover over it a while, when they are in front of the reef.
        if sp.visit <> invalid
            if f.visiting
                f.visiting = false
                f.pause = RndRange(3, 6)
            else if f.z > s.cfg.fgZ and Rnd(0) < sp.visit
                ' The spot: the species' "visitAt" [x, y, z], or the anemone.
                v = f.visitAt
                if v = invalid then v = sp.visitAt
                if v = invalid then v = [s.cfg.anemone.home[0], s.cfg.anemone.home[1], 0.955]
                f.tx = v[0] + RndRange(-60, 60)
                f.ty = v[1] + RndRange(-30, 30)
                f.tz = Clamp(v[2] + RndRange(-0.025, 0.025), s.cfg.fgZ + 0.02, 0.99)
                f.visiting = true
                f.timer = 25
            end if
        end if
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
        if f.away = true
            ' Back from an excursion: a pause out there, then a quick run home.
            f.away = false
            f.tx = f.hx + RndRange(-0.4, 0.4) * sp.r
            f.ty = f.hy + RndRange(-0.2, 0.2) * sp.r
            f.mul = 1.7
            f.pause = RndRange(1, 2.5)
        else if sp.excursion <> invalid and Rnd(0) < sp.excursion
            ' A short excursion a little way off the anemone.
            if Rnd(0) < 0.5 then dirx = -dirx
            f.tx = f.hx + dirx * RndRange(sp.r + 60, sp.r + 160)
            f.ty = f.hy + RndRange(-100, 30)
            f.mul = 1.5
            f.pause = 0
            f.away = true
        end if
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
        if f.leader <> invalid
            FollowLeader(f, t)
            dx = f.tx - f.x
            dzp = (f.tz - f.z) / kz
        else if (Abs(dx) < sp.near and f.pause <= 0) or f.timer < 0
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
        w = Clamp(f.spd / f.radius, 1.4, sp.turn)
        ' Fish swing through the middle of a turn a little faster than they start and end it.
        ec = 1 - Abs(Cos(f.hd))
        w = w * (1 + 0.6 * ec * ec)
        ' A puffed-up fish barely turns.
        if f.puff > 0 then w = w * (1 - 0.85 * f.puff)
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
        if dt > 0
            f.turnRate = Abs(turn) / dt
            ' Body bend follows the turn: full at the slowest U-turn rate and above, signed by
            ' which way it turns.
            bw = Clamp(turn / dt / 1.4, -1, 1)
            f.bend = f.bend + (bw - f.bend) * Clamp(4 * dt, 0, 1)
        end if

        ' Speed: cruise, easing off only a little through turns; nearly still while hovering.
        want = f.cruise * f.mul * act * (0.8 + 0.2 * Cos(diff))
        if f.spr.ball <> invalid then want = want * (1 - 0.85 * UpdatePuff(s, f, dt))
        if f.pause > 0
            f.pause = f.pause - dt
            want = f.cruise * 0.12
            ' Hovering over home, some fish shuffle a little this way and that, turning in place.
            if sp.shuffle = true and Rnd(0) < dt * 0.5
                f.tx = f.x + RndRange(-35, 35)
                f.ty = f.y + RndRange(-10, 10)
            end if
            if sp.shuffle = true then want = f.cruise * 0.22
        end if
        rate = 1.2
        if f.mul > 1 then rate = 5.0
        f.spd = f.spd + (want - f.spd) * Clamp(rate * dt, 0, 1)

        ' Move along the heading. Far fish cover less screen for the same swimming speed.
        sc = DepthScale(s, f.z)
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
        if sp.behavior = "roam" and f.leader = invalid and (f.x < -120 or f.x > 2040) and f.timer > 0 and Rnd(0) < 0.004
            r = s.cfg.roam
            if Rnd(0) < r.frontChance then f.z = RndRange(r.front[0], r.front[1]) else f.z = RndRange(r.back[0], r.back[1])
            f.tz = f.z
        end if
    end for
    SortFish(s.fish)
end sub

' Pufferfish: swells into a spiny ball when a big fish comes close (or, rarely, on its own),
' hangs there drifting, then slowly deflates; then it cannot puff again for a while.
' Returns how puffed it is (0 .. 1).
function UpdatePuff(s as object, f as object, dt as float) as float
    if f.pmode = "none"
        if s.opts.puff <> invalid and f.pcool > 3 then f.pcool = 3
        f.pcool = f.pcool - dt
        if f.pcool <= 0
            ' On its own only where it can be seen: on screen, in front of the reef.
            go = (Rnd(0) < dt / 150 and f.z > s.cfg.fgZ and f.x > 150 and f.x < 1770)
            if s.opts.puff <> invalid then go = true
            if not go and s.frame mod 6 = 0
                for each o in s.fish
                    if o.big and Abs(o.z - f.z) < 0.2
                        dx = o.x - f.x : dy = o.y - f.y
                        if dx * dx + dy * dy < 170 * 170 then go = true
                    end if
                end for
            end if
            if go then f.pmode = "inflate"
        end if
    else if f.pmode = "inflate"
        f.puff = f.puff + dt / 0.5
        if f.puff >= 1
            f.puff = 1
            f.pmode = "ball"
            f.ptime = RndRange(6, 12)
        end if
    else if f.pmode = "ball"
        f.ptime = f.ptime - dt
        if f.ptime <= 0 then f.pmode = "deflate"
    else
        f.puff = f.puff - dt / 1.8
        if f.puff <= 0
            f.puff = 0
            f.pmode = "none"
            f.pcool = RndRange(90, 180)
            if s.opts.puff <> invalid then f.pcool = 3
        end if
    end if
    return f.puff
end function

' A follower keeps to its place (slot: distance behind, height beside) by its leader, the
' place drifting slowly so a school never moves as a rigid block. It matches the leader's
' pace: faster when it falls back, nearly still when the leader hovers, and straight on (no
' fussing turns) when close.
sub FollowLeader(f as object, t as float)
    L = f.leader
    gap = f.slot[0] * (1 + 0.15 * Sin(t * 0.3 + f.wob))
    px = L.x - Cos(L.hd) * gap
    py = L.y + f.slot[1] + 12 * Sin(t * 0.21 + 2 * f.wob)
    d = Sqr((px - f.x) * (px - f.x) + (py - f.y) * (py - f.y))
    if d > gap * 0.5 then f.tx = px else f.tx = f.x + Cos(f.hd) * 60
    f.ty = py
    f.tz = Clamp(L.z - 0.01, f.z0, f.z1)
    f.mul = Clamp(d / gap, 0.3, 2.2)
    if L.pause > 0 and d < gap then f.mul = 0.15
    f.pause = 0
    f.timer = 10
end sub

' Size (and on-screen speed) by depth: the back of the tank is only a little farther from
' the viewer than the front glass, so far fish are only somewhat smaller (cfg.depthScale at
' z = 0, full size at z = 1).
function DepthScale(s as object, z as float) as float
    return s.depthMin + (1 - s.depthMin) * z
end function

' True when moving to depth zn would take the fish across the reef layer while
' coral is behind or in front of it.
function CrossesCoral(s as object, f as object, zn as float) as boolean
    cross = false
    for each w in s.zWalls
        if (f.z - w) * (zn - w) <= 0 and f.z <> zn then cross = true
    end for
    if not cross or s.coral = invalid then return false
    c = s.coral
    sc = f.size * DepthScale(s, f.z)
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
    tailK = 1 - f.amp * (0.5 + 0.5 * Cos(f.phase))
    sc = f.size * DepthScale(s, f.z)
    spr = f.spr
    ' Heading to a rendered view: facing right (cos >= 0) directly; facing left as the mirror
    ' of the matching right-facing heading.
    hd = f.hd
    mir = 1.0
    if Cos(hd) < 0
        hd = 3.14159265 - hd
        if hd > 3.14159265 then hd = hd - 6.2831853
        mir = -1.0
    end if
    away = (Sin(f.hd) < 0)
    p = f.puff
    if p < 0.99
        ' Normal form; while swelling it stretches (taller more than longer) and fades out
        ' as the ball takes over.
        aN = 1 - SmoothStep(0.45, 0.95, p)
        DrawNormalView(s, screen, f, spr, hd, mir, away, sc * (1 + 0.25 * p), sc * (1 + 0.7 * p), tailK, FadeCol(col, aN))
    end if
    if p > 0.01 and spr.ball <> invalid
        ' The ball: nearest of its few views, growing from smaller than the fish to full.
        bl = spr.ball
        i = 0
        while i < bl.ang.Count() - 1 and hd > 0.5 * (bl.ang[i] + bl.ang[i + 1])
            i = i + 1
        end while
        v = bl.views[i]
        bs = sc * (0.5 + 0.5 * SmoothStep(0, 1, p))
        bsx = bs * mir
        cb = FadeCol(col, SmoothStep(0.15, 0.6, p))
        DrawFishTail(screen, v, f.x, f.y, bsx, bs, 1, cb)
        screen.DrawScaledObject(f.x - bsx * v.bx, f.y - bs * v.by, bsx, bs, v.b, cb)
    end if
end sub

' The tint with its alpha scaled by k.
function FadeCol(col as integer, k as float) as integer
    a = col and &hFF
    return (col and &hFFFFFF00) + Int(a * k)
end function

' The fish's normal form at heading hd (already mapped to -60..90, mirrored by mir): nearest
' rendered view, bent while turning, with its outline width interpolated between views.
sub DrawNormalView(s as object, screen as object, f as object, spr as object, hd as float, mir as float, away as boolean, scx as float, sc as float, tailK as float, col as integer)
    ' Nearest rendered view (no blending: two views a few degrees apart show double faces).
    ang = spr.ang
    n = ang.Count()
    i = 0
    while i < n - 1 and hd > 0.5 * (ang[i] + ang[i + 1])
        i = i + 1
    end while
    ' Between views the outline still changes smoothly: the nearest view is stretched to the
    ' width interpolated from its neighbours at this exact heading.
    kx = 1.0
    j = i
    if hd < ang[i] and i > 0 then j = i - 1
    if hd > ang[i] and i < n - 1 then j = i + 1
    if j <> i
        fr = (hd - ang[i]) / (ang[j] - ang[i])
        kx = 1 + fr * (spr.views[j].w / spr.views[i].w - 1)
        if kx < 0.8 or kx > 1.25 then kx = 1
    end if
    v = spr.views[i]
    ' Bent view while turning: a third, two thirds or full bend, tail toward the turn's
    ' inside. Mirroring swaps the fish's flanks, so the set flips with it.
    ab = Abs(f.bend)
    if spr.bsets <> invalid and ab > 0.17 and i >= spr.bfrom
        lv = "1"
        if ab > 0.5 then lv = "2"
        if ab > 0.83 then lv = "3"
        if f.bend * mir > 0 then key = "p" + lv else key = "m" + lv
        v = spr.bsets[key][i - spr.bfrom]
    end if
    sx = scx * mir * kx
    ' Tail behind the body, or in front when the fish swims away (tail nearer the glass).
    if not away then DrawFishTail(screen, v, f.x, f.y, sx, sc, tailK, col)
    screen.DrawScaledObject(f.x - sx * v.bx, f.y - sc * v.by, sx, sc, v.b, col)
    if away then DrawFishTail(screen, v, f.x, f.y, sx, sc, tailK, col)
end sub

' A view's tail, hinged at its joint and beating (squashed toward the hinge). sx is negative
' for a mirrored (left-facing) fish.
sub DrawFishTail(screen as object, v as object, x as float, y as float, sx as float, sc as float, tailK as float, col as integer)
    stx = sx * tailK
    screen.DrawScaledObject(x + sx * v.hx - stx * (v.tx + v.hx), y - sc * v.ty, stx, sc, v.t, col)
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
            f = { sp: g.sp, spr: g.spr, size: g.size, z: 1.0, hd: 0.0, amp: 0.1, phase: 0.0, x: 0.0, y: 540.0, bend: 0.8, puff: 0.0 }
            if s.opts.posePuff <> invalid then f.puff = s.opts.posePuff : f.bend = 0
            for i = 0 to 8
                f.hd = s.poseA0 + (s.poseA1 - s.poseA0) * i / 8
                f.x = 120 + i * 210
                FishDraw(s, screen, f)
            end for
            return
        end if
    end for
end sub

function Min(a as float, b as float) as float
    if a < b then return a
    return b
end function

function Max(a as float, b as float) as float
    if a > b then return a
    return b
end function
