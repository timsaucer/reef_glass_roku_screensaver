' Fish: behavior, swimming animation and depth.
'
' Each fish swims forward along a heading hd, an angle in the horizontal plane: 0 is toward
' screen right, pi toward screen left, +/-pi/2 straight away from / toward the glass. It never
' slides sideways or backward. Screen x moves with cos(hd), depth z with sin(hd), so a turn is
' a real U-turn through depth: on the way round the fish points toward or away from the
' glass, and its side-view length shrinks with |cos(hd)| before it reappears mirrored.
'
' Sprites: a right-facing body plus a separate tail hinged at the body's tail pivot. The tail
' beat squashes the tail horizontally; its amplitude follows swimming effort (speed and
' turning), so a hovering fish only fans gently.
'
' Depth z (0 far .. 1 near) sets scale, on-screen speed, haze tint and draw order. Every fish
' keeps to a depth lane, so it never crosses the reef layer (fgZ) or the anemone while in
' view: crossing those boundaries would flip it from in front of the coral to behind it in a
' single frame. Cruisers change lanes only while off-screen.
'
' Behaviors (reef.json "species"):
'   roam  cruise between waypoints across the whole tank, often leaving the frame
'   home  wander slowly around a home point (the anemone, a ledge, a coral head); "dart"
'         adds short fast bursts, as damselfish do; "hover" is the chance of resting a while

sub FishInit(s as object)
    cfg = s.cfg
    s.sprites = {}
    s.fish = []
    ' Depth units per pixel of travel. Large, so depth changes need little heading: fish stay
    ' close to side-on except while actually turning round.
    s.kz = 1.0 / 450
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
    return {
        body: body, tail: tail
        bw: body.GetWidth(), bh: body.GetHeight(), tw: tail.GetWidth(), th: tail.GetHeight()
        px: pivot[0], py: pivot[1]
    }
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
        big: false
    }
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
        end if
    else
        SetLane(s, f, Rnd(0) < s.cfg.roam.frontChance)
    end if
    PickTarget(s, f)
    f.x = f.tx : f.y = f.ty : f.z = f.tz
    f.hd = Rnd(0) * 6.283
    f.spd = f.cruise * 0.6
    PickTarget(s, f)
    return f
end function

' Cruiser depth lanes: behind the reef layer, or close to the glass in front of everything.
sub SetLane(s as object, f as object, front as boolean)
    r = s.cfg.roam
    if front
        f.z0 = r.front[0] : f.z1 = r.front[1]
    else
        f.z0 = r.back[0] : f.z1 = r.back[1]
    end if
end sub

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
        f.tz = RndRange(f.z0, f.z1)
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

        ' Turn toward the waypoint at a limited rate. Depth is gained gradually: the course
        ' stays within ~24 degrees of side-on, so only a real turn shows a foreshortened fish.
        lim = 0.45 * Abs(dx)
        diff = Atan2(Clamp(dzp, -lim, lim), dx) - f.hd
        while diff > kPi
            diff = diff - 2 * kPi
        end while
        while diff < -kPi
            diff = diff + 2 * kPi
        end while
        maxTurn = sp.turn * dt
        turn = Clamp(diff, -maxTurn, maxTurn)
        f.hd = f.hd + turn
        if f.hd > kPi then f.hd = f.hd - 2 * kPi
        if f.hd < -kPi then f.hd = f.hd + 2 * kPi
        if dt > 0 then f.turnRate = Abs(turn) / dt

        ' Speed: cruise, slower through sharp turns, nearly still while hovering.
        want = f.cruise * f.mul * act * (0.55 + 0.45 * Cos(diff))
        if f.pause > 0
            f.pause = f.pause - dt
            want = f.cruise * 0.12
        end if
        rate = 1.2
        if f.mul > 1 then rate = 5.0
        f.spd = f.spd + (want - f.spd) * Clamp(rate * dt, 0, 1)

        ' Move along the heading. Far fish cover less screen for the same swimming speed.
        sc = 0.45 + 0.55 * f.z
        c = Cos(f.hd)
        f.x = f.x + c * f.spd * sc * dt
        f.z = Clamp(f.z + Sin(f.hd) * f.spd * kz * dt, f.z0, f.z1)
        ' Gentle climbs and dives toward the waypoint's height.
        vyWant = Clamp((f.ty - f.y) * 0.6, -0.35 * f.spd, 0.35 * f.spd)
        f.vy = f.vy + (vyWant - f.vy) * Clamp(1.5 * dt, 0, 1)
        f.y = f.y + f.vy * sc * dt

        ' Side-view length follows the heading. Head-on a fish still shows its thickness.
        if c >= 0
            if c < 0.22 then c = 0.22
        else
            if c > -0.22 then c = -0.22
        end if
        f.face = c

        ' Tail: amplitude follows effort (speed relative to cruise, plus turning); frequency
        ' rises a little with speed.
        effort = f.spd / sp.speed
        a = 0.04 + 0.2 * Clamp(effort, 0, 1.5) + 0.06 * Clamp(f.turnRate / sp.turn, 0, 1)
        f.amp = f.amp + (a - f.amp) * Clamp(3 * dt, 0, 1)
        f.phase = f.phase + dt * 6.283 * sp.beat * (0.5 + 0.5 * Clamp(effort, 0, 2))

        ' Cruisers well off-screen may change depth lane; nobody can see the jump.
        if sp.behavior = "roam" and (f.x < -120 or f.x > 2040) and f.timer > 0 and Rnd(0) < 0.004
            SetLane(s, f, Rnd(0) < s.cfg.roam.frontChance)
            f.z = RndRange(f.z0, f.z1)
            f.tz = RndRange(f.z0, f.z1)
        end if
    end for
    SortFish(s.fish)
end sub

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
    sc = f.size * (0.4 + 0.6 * f.z)
    tailK = 1 - f.amp * (0.5 + 0.5 * Cos(f.phase))
    DrawFishSprite(screen, f.spr, f.x, f.y, sc, f.face, tailK, s.tints[Int(f.z * 20 + 0.5)])
end sub

' Draws a body+tail sprite centered at (x, y). face is the signed x scale factor (1 right,
' -1 left, smaller while turning). A negative scale mirrors the sprite about the draw x, so
' screen x = x0 + sx * u holds for either sign.
sub DrawFishSprite(screen as object, spr as object, x as float, y as float, sc as float, face as float, tailK as float, col as integer)
    sx = sc * face
    x0 = x - sx * spr.bw / 2
    y0 = y - sc * spr.bh / 2
    stx = sx * tailK
    screen.DrawScaledObject(x0 + sx * spr.px - stx * spr.tw, y0 + sc * (spr.py - spr.th / 2), stx, sc, spr.tail, col)
    screen.DrawScaledObject(x0, y0, sx, sc, spr.body, col)
end sub

function Min(a as float, b as float) as float
    if a < b then return a
    return b
end function

function Max(a as float, b as float) as float
    if a > b then return a
    return b
end function
