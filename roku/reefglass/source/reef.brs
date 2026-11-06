' The tank: light (rays, day/night), drifting motes, and the frame that ties the wide tank
' (pan.brs: background, reef pieces, camera), the fish (fish.brs) and the critters
' (critters.brs) together. The draw order is in PanFrame.

function ReefInit(cfg as object, opts as object) as object
    s = {
        cfg: cfg
        opts: opts
        ray: CreateObject("roBitmap", "pkg:/images/ray.png")
        mote: CreateObject("roBitmap", "pkg:/images/mote.png")
        motes: []
        dayK: 1.0
        hourClock: -10.0
        frame: 0
    }
    s.prof = invalid
    if opts.profile <> invalid then s.prof = { clock: CreateObject("roTimespan"), report: CreateObject("roTimespan"), upd: 0, drw: 0, n: 0 }
    s.camX = 0.0
    FishInit(s)
    CrittersInit(s)
    PanInit(s)
    ' Each mote sways with one of four shared phases (four Sin calls a frame, not one each).
    for i = 1 to cfg.motes.count
        z = Rnd(0)
        s.motes.Push({ x: Rnd(0) * 1920, y: Rnd(0) * 1080, z: z, g: i mod 4, sc: 0.3 + 0.7 * z, vx: 4 + 10 * z, vy: 2 + 7 * z, col: 0 })
    end for
    ' Motes, split by depth once: the far ones go behind the fish, the near ones in front.
    s.motesFar = [] : s.motesNear = []
    for each mo in s.motes
        if mo.z < 0.5 then s.motesFar.Push(mo) else s.motesNear.Push(mo)
    end for
    UpdateLight(s, 0)
    return s
end function

sub ReefFrame(s as object, screen as object, t as float, dt as float)
    if s.prof <> invalid then s.prof.clock.Mark()
    s.frame = s.frame + 1
    UpdateLight(s, t)
    FishUpdate(s, t, dt)
    CrittersUpdate(s, t, dt)
    UpdateMotes(s, t, dt)
    PanUpdate(s, t)
    if s.prof <> invalid then s.prof.upd = s.prof.upd + s.prof.clock.TotalMilliseconds() : s.prof.clock.Mark()

    PanFrame(s, screen, t)
    ReefFrameEnd(s, screen, t)
end sub

sub ReefFrameEnd(s as object, screen as object, t as float)
    if s.opts.pose <> invalid then DrawPoses(s, screen, s.opts.pose)

    if s.opts.trace <> invalid and s.frame mod 15 = 0
        f = s.traced
        if f = invalid
            for each g in s.fish
                if f = invalid and g.name = s.opts.trace then f = g
            end for
            s.traced = f
        end if
    end if
    ' No fish of that species: nothing to trace.
    if s.opts.trace <> invalid and s.frame mod 15 = 0 and s.traced <> invalid
        f = s.traced
        tr ="TRACE t " + Str(Int(t * 10) / 10.0) + " x " + Str(Int(f.x)) + " y " + Str(Int(f.y)) + " z " + Str(Int(f.z * 100) / 100.0) + " hd " + Str(Int(f.hd * 100) / 100.0)
        tr = tr + " spd " + Str(Int(f.spd)) + " puff " + Str(Int(f.puff * 100) / 100.0) + " tx " + Str(Int(f.tx)) + " tz " + Str(Int(f.tz * 100) / 100.0) + " td " + Str(f.turnDir) + " bk " + Str(Int(f.blockT * 10) / 10.0)
        print tr
        ' A pair: the other fish too (the male's look is the heading he is drawn at).
        g = f.leader
        if g = invalid and f.followers <> invalid then g = f.followers[0]
        if g <> invalid
            lk = "-"
            if g.look <> invalid then lk = Str(Int(g.look * 100) / 100.0)
            if f.look <> invalid then lk = lk + " (traced look " + Str(Int(f.look * 100) / 100.0) + ")"
            print "  MATE x "; Int(g.x); " z "; Int(g.z * 100) / 100.0; " hd "; Int(g.hd * 100) / 100.0; " look "; lk; " spd "; Int(g.spd)
        end if
    end if
    if s.prof <> invalid
        p = s.prof
        p.drw = p.drw + p.clock.TotalMilliseconds()
        p.n = p.n + 1
        if p.report.TotalMilliseconds() >= 5000
            print "PROF update "; Int(p.upd / p.n * 10) / 10.0; " ms, draw calls "; Int(p.drw / p.n * 10) / 10.0; " ms, hour "; Int(s.hour * 10) / 10.0; " dayK "; Int(s.dayK * 100) / 100.0
            dm = ""
            for each d in s.dusters
                dm = dm + d.mode + " "
            end for
            mm = "none"
            if s.moray <> invalid then mm = s.moray.mode
            print "     moray "; mm; " dusters "; dm
            p.upd = 0 : p.drw = 0 : p.n = 0
            p.report.Mark()
        end if
    end if
end sub

' Tank clock: local time, or a pinned/sweeping hour in dev runs.
function TankHour(s as object, t as float) as float
    if s.opts.daycycle <> invalid then return FMod(12 + t * 24 / s.opts.daycycle, 24)
    if s.opts.hour <> invalid then return s.opts.hour
    d = CreateObject("roDateTime")
    d.ToLocalTime()
    return d.GetHours() + d.GetMinutes() / 60.0 + d.GetSeconds() / 3600.0
end function

' dayK: 1 in daylight, 0 under moonlight, eased through dawn and dusk. The clock is read once
' a second (every frame when sweeping).
sub UpdateLight(s as object, t as float)
    if s.opts.daycycle = invalid and t - s.hourClock < 1 then return
    s.hourClock = t
    lt = s.cfg.light
    h = TankHour(s, t)
    s.hour = h
    s.dayK = SmoothStep(lt.dawn[0], lt.dawn[1], h) * (1 - SmoothStep(lt.dusk[0], lt.dusk[1], h))
    s.night = 1 - s.dayK
    nc = lt.night.rgb
    s.nightRgba = RGBA(nc[0], nc[1], nc[2], Int(lt.night.alpha * s.night))
    ' Fish slow down at night; this scales every cruise speed.
    na = 0.5
    if lt.nightActivity <> invalid then na = lt.nightActivity
    s.activity = na + (1 - na) * s.dayK
    ' Mote colors follow the light; they change slowly, so once a second will do.
    lum = 0.4 + 0.6 * s.dayK
    for each mo in s.motes
        mo.col = &hE0F0FF00 + Int((30 + 90 * mo.z) * lum)
    end for
end sub

' Soft shafts of light from the surface, slowly breathing and swaying.
sub DrawRays(s as object, screen as object, t as float)
    if s.dayK < 0.02 then return
    k = 0
    for each r in s.cfg.rays
        a = 255 * 0.16 * r[1] * s.dayK * (0.55 + 0.45 * Sin(t * 0.11 + k * 1.7))
        x = r[0] + 30 * Sin(t * 0.05 + k * 2.3) - s.camX
        ' The rays repeat every screen width of a wide (panning) tank.
        j0 = Int(s.camX / 1920)
        for j = j0 - 1 to j0 + 1
            xj = x + j * 1920
            if xj > -300 and xj < 2100 then screen.DrawScaledObject(xj - 128, -40, 1.6, 1.1, s.ray, &hFFFFFF00 + Int(a))
        end for
        k = k + 1
    end for
end sub

' Marine snow: tiny specks sinking slowly on a gentle current. Near ones are larger, brighter
' and faster.
sub UpdateMotes(s as object, t as float, dt as float)
    sw = [6 * Sin(t * 0.3) * dt, 6 * Sin(t * 0.3 + 1.57) * dt, 6 * Sin(t * 0.3 + 3.14) * dt, 6 * Sin(t * 0.3 + 4.71) * dt]
    for each mo in s.motes
        mo.x = mo.x + mo.vx * dt + sw[mo.g]
        mo.y = mo.y + mo.vy * dt
        if mo.x > 1930 then mo.x = -10
        if mo.y > 1090
            mo.y = -10
            mo.x = Rnd(0) * 1920
        end if
    end for
end sub

sub DrawMotes(s as object, screen as object, list as object)
    bmp = s.mote
    for each mo in list
        screen.DrawScaledObject(mo.x, mo.y, mo.sc, mo.sc, bmp, mo.col)
    end for
end sub
