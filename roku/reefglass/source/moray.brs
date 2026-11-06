' Snowflake moray eel living in the cave under the right-hand rock.
'
' The eel lies in the cave mouth facing left, its body running back behind the cave's right
' wall. It slides slowly out to look around and back, and its mouth opens and closes in a
' slow, uneven breathing rhythm (morays pump water over their gills that way). When a big
' fish swims close it pulls quickly back behind the wall, then creeps out once it is calm.
' Its slow moves are timed glides that ease in and out (a spring's long, slow tail showed as
' the eel creeping a pixel at a time); the quick retreat follows a stiff damped spring.
'
' Sprites: moray.png (head and front body facing left, without the lower jaw) and
' moray_jaw.png (placed at "jaw" in moray.png px), rotated about "jawHinge" to gape.
' cave_shade.png is the reef's rock around the cave opening plus the cave's shadow deepening
' toward the back, drawn over the eel so its body fades into the dark and disappears behind the
' real rock edge. The body is clipped at the shade's right edge ("clip").

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
        from: 0.7, tw: 0.0, dur: 1.0
    }
    ' The jaw is drawn rotated about its hinge: a region whose origin is moved onto the hinge.
    s.moray.bw = s.moray.body.GetWidth() : s.moray.vis = -1
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
                MorayGlideTo(e, c, RndRange(0.4, 0.8))
                e.wait = RndRange(8, 16)
            end if
        end if
    else
        ' Out: every so often ease to a new resting point, sometimes far out, sometimes
        ' half back in.
        e.wait = e.wait - dt
        if e.wait <= 0
            MorayGlideTo(e, c, RndRange(0.35, 1.0))
            e.wait = RndRange(8, 20)
        end if
    end if
    if e.mode = "hide"
        ' Critically damped spring toward the target.
        e.v = e.v + (k * (target - e.out) - 2 * Sqr(k) * e.v) * dt
        e.out = e.out + e.v * dt
    else
        e.tw = e.tw + dt
        u = e.tw / e.dur
        if u > 1 then u = 1
        e.out = e.from + (e.outT - e.from) * (0.5 - 0.5 * Cos(3.14159 * u))
        e.v = (e.outT - e.from) * 1.5708 * Sin(3.14159 * u) / e.dur
    end if
    ' Breathing: each cycle the mouth opens and closes over about 2.5 s, then rests; cycles
    ' last 4 to 6.5 s.
    e.bph = e.bph + dt / e.bper
    if e.bph >= 1
        e.bph = 0
        e.bper = RndRange(4, 6.5)
    end if
end sub

' Starts a glide from where the eel is to the given reach, at up to ~40 px/s (fast enough
' that it moves at least a pixel a frame through the middle of the move).
sub MorayGlideTo(e as object, c as object, target as float)
    e.from = e.out
    e.outT = target
    e.tw = 0
    e.dur = 1.5708 * Abs(target - e.out) * c.reach / 40
    if e.dur < 2 then e.dur = 2
end sub

sub MorayDraw(s as object, screen as object, t as float)
    e = s.moray
    if e = invalid then return
    c = s.cfg.moray
    x = Int(c.x - s.camX + (1 - e.out) * c.reach + 0.5)
    y = c.y
    y0 = y - e.body.GetHeight() \ 2
    ' The cave is in shadow: the eel takes a dim tint.
    col = RGBA(180, 180, 175, 255)
    ' Gape: the lower jaw turns down about its hinge, then closes.
    u = e.bph * e.bper / 2.5
    g = 0
    if u < 1 then g = Sin(3.14159 * u) * Sin(3.14159 * u)
    jh = c.jawHinge
    screen.DrawRotatedObject(x + jh[0], y0 + jh[1], g * c.gape, e.jawRegion, col)
    ' Clip the body where the cave shade ends, so the part behind the wall never shows past
    ' the rock it hides behind.
    vis = Int(c.clip - s.camX - x)
    if vis > 0
        if vis > e.bw then vis = e.bw
        if vis <> e.vis
            e.bodyRegion = CreateObject("roRegion", e.body, 0, 0, vis, e.body.GetHeight())
            e.vis = vis
        end if
        screen.DrawObject(x, y0, e.bodyRegion, col)
    end if
    sh = c.shade
    screen.DrawObject(sh[0] - s.camX, sh[1], e.shade)
end sub
