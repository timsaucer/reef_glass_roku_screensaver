' Fish: behavior, swimming animation and depth.
'
' Each fish is a right-facing body sprite plus a separate tail sprite hinged at the body's tail
' pivot. The tail beat is a horizontal squash of the tail (in side view a beating tail fin
' narrows and widens). Facing left is a negative x scale; a turn eases the x scale through a
' narrow minimum, which reads as the fish swinging round toward the glass.
'
' Depth z (0 far .. 1 near) sets scale, on-screen speed, haze tint and draw order.
'
' Behaviors (reef.json "species"):
'   roam  cruise between random points across the whole tank, often leaving the frame
'   home  stay near a home point (the anemone, a rock ledge, a coral head); "dart" adds short
'         fast bursts, as damselfish do

sub FishInit(s as object)
    cfg = s.cfg
    s.sprites = {}
    s.fish = []
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
        spr = LoadFishSprite(name, sp.pivot)
        s.sprites[name] = spr
        for i = 0 to sp.count - 1
            s.fish.Push(NewFish(s, sp, spr, i))
        end for
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
        vx: 0.0, vy: 0.0
        tx: 0.0, ty: 0.0, tz: 0.5
        dir: 1, face: 1.0, turnT: -1.0, turnFrom: 1
        phase: Rnd(0) * 6.283
        mul: 1.0, timer: 0.0, pause: 0.0
        size: sp.len / spr.bw
        big: false
    }
    if sp.big <> invalid then f.big = sp.big
    ' Home point: the anemone, or one of the species' listed homes (spread over the fish).
    if sp.behavior = "home"
        if sp.home <> invalid
            a = s.cfg.anemone
            f.hx = a.x : f.hy = a.y - 60 : f.hz = a.z
        else
            h = sp.homes[idx mod sp.homes.Count()]
            f.hx = h[0] : f.hy = h[1] : f.hz = h[2]
        end if
    end if
    PickTarget(s, f)
    f.x = f.tx : f.y = f.ty : f.z = f.tz
    if Rnd(2) = 1 then f.dir = -1
    f.face = f.dir
    PickTarget(s, f)
    return f
end function

sub PickTarget(s as object, f as object)
    sp = f.sp
    f.mul = 1.0
    f.pause = 0
    if sp.behavior = "roam"
        r = s.cfg.roam
        ' Now and then a cruiser drops down to graze over the open sand (and spooks the goby).
        if r.low <> invalid and Rnd(0) < r.low.chance then r = r.low
        f.tx = RndRange(r.x0, r.x1)
        f.ty = RndRange(r.y0, r.y1)
        f.tz = RndRange(r.z0, r.z1)
        ' Long enough to arrive; the timer only rescues a fish that gets stuck.
        dx = f.tx - f.x : dy = f.ty - f.y
        f.timer = Sqr(dx * dx + dy * dy) / (sp.speed * 0.5) + 4
    else
        f.tx = f.hx + (Rnd(0) * 2 - 1) * sp.r
        f.ty = f.hy + (Rnd(0) * 2 - 1) * sp.r * 0.5
        f.tz = Clamp(f.hz + (Rnd(0) - 0.5) * 0.16, 0.02, 0.98)
        f.timer = RndRange(3, 8)
        if sp.dart <> invalid and Rnd(0) < sp.dart then f.mul = 2.4
        ' Home fish often just hover in place for a while.
        if Rnd(0) < 0.3 then f.pause = RndRange(1, 4)
    end if
end sub

sub FishUpdate(s as object, t as float, dt as float)
    act = s.activity
    for each f in s.fish
        sp = f.sp
        f.timer = f.timer - dt
        dx = f.tx - f.x
        dy = f.ty - f.y
        d = Sqr(dx * dx + dy * dy)
        if f.pause > 0
            f.pause = f.pause - dt
            dvx = 0 : dvy = 0
        else
            if d < 25 or f.timer < 0
                PickTarget(s, f)
                dx = f.tx - f.x : dy = f.ty - f.y
                d = Sqr(dx * dx + dy * dy)
            end if
            ' Speed on screen shrinks with distance; ease in near the target.
            spd = sp.speed * f.mul * act * (0.45 + 0.55 * f.z)
            if d < 90 then spd = spd * (0.3 + 0.7 * d / 90)
            if d > 0.01
                dvx = dx / d * spd
                dvy = dy / d * spd * 0.55
            else
                dvx = 0 : dvy = 0
            end if
        end if
        k = 1.4 * dt
        if f.mul > 1 then k = 4 * dt
        f.vx = f.vx + (dvx - f.vx) * k
        f.vy = f.vy + (dvy - f.vy) * k
        f.x = f.x + f.vx * dt
        f.y = f.y + f.vy * dt
        f.z = f.z + Clamp(f.tz - f.z, -0.04 * dt, 0.04 * dt)

        ' Turn when the swim direction reverses.
        if f.turnT < 0
            want = f.dir
            if f.vx > 6 then want = 1
            if f.vx < -6 then want = -1
            if want <> f.dir
                f.turnFrom = f.dir
                f.dir = want
                f.turnT = 0
            end if
        else
            f.turnT = f.turnT + dt / 0.5
            if f.turnT >= 1 then f.turnT = -1
        end if
        if f.turnT < 0
            f.face = f.dir
        else
            c = Cos(3.14159 * f.turnT) * f.turnFrom
            if c > -0.15 and c < 0.15
                if f.turnT < 0.5 then c = 0.15 * f.turnFrom else c = 0.15 * f.dir
            end if
            f.face = c
        end if

        ' Tail beat speeds up with swimming speed; hovering fish still fan slowly.
        v = Sqr(f.vx * f.vx + f.vy * f.vy) / (sp.speed * (0.45 + 0.55 * f.z))
        f.phase = f.phase + dt * 6.283 * sp.beat * (0.35 + 0.9 * v)
    end for
    SortFish(s.fish)
end sub

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
    tailK = 0.7 + 0.3 * Cos(f.phase)
    DrawFishSprite(screen, f.spr, f.x, f.y + 1.5 * Sin(f.phase * 0.5), sc, f.face, tailK, s.tints[Int(f.z * 20 + 0.5)])
end sub

' Draws a body+tail sprite centered at (x, y). face is the signed x scale factor (1 right,
' -1 left, in between while turning). A negative scale mirrors the sprite about the draw x,
' so screen x = x0 + sx * u holds for either sign.
sub DrawFishSprite(screen as object, spr as object, x as float, y as float, sc as float, face as float, tailK as float, col as integer)
    sx = sc * face
    x0 = x - sx * spr.bw / 2
    y0 = y - sc * spr.bh / 2
    stx = sx * tailK
    screen.DrawScaledObject(x0 + sx * spr.px - stx * spr.tw, y0 + sc * (spr.py - spr.th / 2), stx, sc, spr.tail, col)
    screen.DrawScaledObject(x0, y0, sx, sc, spr.body, col)
end sub
