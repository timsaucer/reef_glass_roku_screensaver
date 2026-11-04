' Snowflake moray eel living in the cave under the right-hand rock.
'
' The eel lies in the cave mouth facing left, its body running back into the dark. It slowly
' slides out to look around and back in, its head bobs, and its mouth gapes in a steady
' breathing rhythm (as morays do: they pump water over their gills). When a big fish swims
' close it pulls back into the cave, and creeps out again once things are calm.
'
' Sprites: moray.png (head and front body, facing left, the lower jaw cut away) and
' moray_jaw.png (placed at "jaw" in moray.png px), rotated about "jawHinge" to gape. cave_shade.png is the plate's own dark cave interior with alpha rising
' toward the back, drawn over the eel so its body fades into the cave.

sub MorayInit(s as object)
    c = s.cfg.moray
    s.moray = invalid
    if c = invalid then return
    s.moray = {
        body: CreateObject("roBitmap", "pkg:/images/moray.png")
        jaw: CreateObject("roBitmap", "pkg:/images/moray_jaw.png")
        shade: CreateObject("roBitmap", "pkg:/images/cave_shade.png")
        out: 0.6, outT: 0.6, mode: "out", wait: RndRange(6, 14), calm: 0
        breath: 0.0, threatNow: false
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
        e.out = e.out - dt / 0.6
        if e.out < 0 then e.out = 0
        if not e.threatNow
            e.calm = e.calm - dt
            if e.calm <= 0
                e.mode = "out"
                e.outT = RndRange(0.4, 0.8)
                e.wait = RndRange(8, 16)
            end if
        end if
    else
        ' Out: every so often slide to a new resting point, sometimes far out, sometimes
        ' nearly back inside.
        e.wait = e.wait - dt
        if e.wait <= 0
            e.outT = RndRange(0.25, 1.0)
            e.wait = RndRange(6, 18)
        end if
        e.out = e.out + Clamp(e.outT - e.out, -dt / 6, dt / 6)
    end if
    ' Breathing: gape opens and closes about every 2.5 s, quicker after a scare.
    e.breath = e.breath + dt * 6.283 / 2.5 * (1 + 0.5 * (1 - e.out))
end sub

sub MorayDraw(s as object, screen as object, t as float)
    e = s.moray
    if e = invalid then return
    c = s.cfg.moray
    x = Int(c.x + (1 - e.out) * c.reach + 3 * Sin(t * 0.37))
    y = Int(c.y + 3 * Sin(t * 0.53 + 1) + 2 * Sin(t * 1.1))
    y0 = y - e.body.GetHeight() \ 2
    ' The cave is in shadow: the eel takes a dim tint.
    col = RGBA(180, 180, 175, 255)
    ' Gape: the lower jaw turns down about its hinge, then closes.
    g = 0.5 - 0.5 * Cos(e.breath)
    jh = c.jawHinge
    screen.DrawRotatedObject(x + jh[0], y0 + jh[1], g * c.gape, e.jawRegion, col)
    screen.DrawObject(x, y0, e.body, col)
    sh = c.shade
    screen.DrawObject(sh[0], sh[1], e.shade)
end sub
