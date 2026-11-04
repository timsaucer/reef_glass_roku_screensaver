' Snowflake moray eel living in the cave under the right-hand rock.
'
' The eel lies in the cave mouth facing left, its body running back behind the cave's right
' wall. It slides slowly out to look around and back, and its mouth opens and closes in a
' slow, uneven breathing rhythm (morays pump water over their gills that way). When a big
' fish swims close it pulls quickly back behind the wall, then creeps out once it is calm.
' Its position follows a damped spring, so it eases into and out of every move.
'
' Sprites: moray.png (head and front body facing left, without the lower jaw) and
' moray_jaw.png (placed at "jaw" in moray.png px), rotated about "jawHinge" to gape.
' cave_shade.png is the plate's rock around the cave opening, drawn over the eel so its body
' disappears behind the real rock edge.

sub MorayInit(s as object)
    c = s.cfg.moray
    s.moray = invalid
    if c = invalid then return
    s.moray = {
        body: CreateObject("roBitmap", "pkg:/images/moray.png")
        jaw: CreateObject("roBitmap", "pkg:/images/moray_jaw.png")
        shade: CreateObject("roBitmap", "pkg:/images/cave_shade.png")
        out: 0.7, v: 0.0, outT: 0.7, mode: "out", wait: RndRange(6, 14), calm: 0
        bph: 0.0, bper: 5.0, threatNow: false
    }
    ' The jaw is drawn rotated about its hinge: a region whose origin is moved onto the hinge.
    jb = s.moray.jaw
    s.moray.jawRegion = CreateObject("roRegion", jb, 0, 0, jb.GetWidth(), jb.GetHeight())
    s.moray.jawRegion.SetPretranslation(c.jaw[0] - c.jawHinge[0], c.jaw[1] - c.jawHinge[1])
end sub

sub MorayUpdate(s as object, t as float, dt as float)
    e = s.moray
    if e = invalid then return
    c = s.cfg.moray
    if s.frame mod 3 = 0
        threat = false
        for each f in s.fish
            if f.big and f.z > s.cfg.fgZ - 0.2
                dx = f.x - c.x : dy = f.y - c.y
                if dx * dx + dy * dy < c.threat * c.threat
                    threat = true
                    exit for
                end if
            end if
        end for
        e.threatNow = threat
    end if
    if e.threatNow
        e.mode = "hide"
        e.calm = RndRange(4, 8)
    end if
    if e.mode = "hide"
        target = 0 : k = 9.0
        if not e.threatNow
            e.calm = e.calm - dt
            if e.calm <= 0
                e.mode = "out"
                e.outT = RndRange(0.4, 0.8)
                e.wait = RndRange(8, 16)
            end if
        end if
    else
        ' Out: every so often ease to a new resting point, sometimes far out, sometimes
        ' half back in.
        e.wait = e.wait - dt
        if e.wait <= 0
            e.outT = RndRange(0.35, 1.0)
            e.wait = RndRange(8, 20)
        end if
        target = e.outT : k = 0.5
    end if
    ' Critically damped spring toward the target.
    e.v = e.v + (k * (target - e.out) - 2 * Sqr(k) * e.v) * dt
    e.out = e.out + e.v * dt
    ' Breathing: each cycle the mouth opens and closes over about 2.5 s, then rests; cycles
    ' last 4 to 6.5 s.
    e.bph = e.bph + dt / e.bper
    if e.bph >= 1
        e.bph = 0
        e.bper = RndRange(4, 6.5)
    end if
end sub

sub MorayDraw(s as object, screen as object, t as float)
    e = s.moray
    if e = invalid then return
    c = s.cfg.moray
    x = Int(c.x + (1 - e.out) * c.reach + 0.5)
    y = Int(c.y + 1.5 * Sin(t * 1.1) + 0.5)
    y0 = y - e.body.GetHeight() \ 2
    ' The cave is in shadow: the eel takes a dim tint.
    col = RGBA(180, 180, 175, 255)
    ' Gape: the lower jaw turns down about its hinge, then closes.
    u = e.bph * e.bper / 2.5
    g = 0
    if u < 1 then g = Sin(3.14159 * u) * Sin(3.14159 * u)
    jh = c.jawHinge
    screen.DrawRotatedObject(x + jh[0], y0 + jh[1], g * c.gape, e.jawRegion, col)
    screen.DrawObject(x, y0, e.body, col)
    sh = c.shade
    screen.DrawObject(sh[0], sh[1], e.shade)
end sub
