' The tank: plate layers, light (caustics, rays, day/night), drifting motes, and the draw order
' that ties the fish (fish.brs) and the critters (critters.brs) together.
'
' Draw order, back to front:
'   bg plate (opaque) > caustics on the sand (rocks redrawn over them) > far motes
'   > fish behind the reef > light rays > fg plate (the reef) > critters on the reef
'   > near fish, with the anemone at its depth among them > near motes > night overlay

function ReefInit(cfg as object, opts as object) as object
    s = {
        cfg: cfg
        opts: opts
        bg: CreateObject("roBitmap", cfg.plate.bg)
        fg: CreateObject("roBitmap", cfg.plate.fg)
        caustic: [CreateObject("roBitmap", "pkg:/images/caustic_0.png"), CreateObject("roBitmap", "pkg:/images/caustic_1.png")]
        ray: CreateObject("roBitmap", "pkg:/images/ray.png")
        occluder: CreateObject("roBitmap", cfg.caustics.occluder)
        mote: CreateObject("roBitmap", "pkg:/images/mote.png")
        motes: []
        dayK: 1.0
        hourClock: -10.0
        frame: 0
    }
    s.prof = invalid
    if opts.profile <> invalid then s.prof = { clock: CreateObject("roTimespan"), report: CreateObject("roTimespan"), upd: 0, drw: 0, n: 0 }
    FishInit(s)
    CrittersInit(s)
    for i = 1 to cfg.motes.count
        s.motes.Push({ x: Rnd(0) * 1920, y: Rnd(0) * 1080, z: Rnd(0), ph: Rnd(0) * 6.283 })
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
    if s.prof <> invalid then s.prof.upd = s.prof.upd + s.prof.clock.TotalMilliseconds() : s.prof.clock.Mark()

    screen.SetAlphaEnable(false)
    screen.DrawObject(0, 0, s.bg)
    screen.SetAlphaEnable(true)
    DrawCaustics(s, screen, t)
    DrawMotes(s, screen, 0, 0.5)
    ' Fish are kept sorted by depth. Far fish pass behind the reef (fg layer); the critters
    ' live on the reef; near fish and the anemone (with its clownfish) are in front of it.
    fishes = s.fish
    n = fishes.Count()
    i = 0
    while i < n and fishes[i].z < s.cfg.fgZ
        FishDraw(s, screen, fishes[i])
        i = i + 1
    end while
    DrawRays(s, screen, t)
    screen.DrawObject(0, 0, s.fg)
    CrittersDraw(s, screen, t)
    anemDrawn = false
    while i < n
        if not anemDrawn and fishes[i].z >= s.anem.z
            AnemoneDraw(s, screen, t)
            anemDrawn = true
        end if
        FishDraw(s, screen, fishes[i])
        i = i + 1
    end while
    if not anemDrawn then AnemoneDraw(s, screen, t)
    DrawMotes(s, screen, 0.5, 1.01)
    if s.night > 0 then screen.DrawRect(0, 0, 1920, 1080, s.nightRgba)
    if s.opts.pose <> invalid then DrawPoses(s, screen, s.opts.pose)

    if s.opts.trace <> invalid and s.frame mod 15 = 0
        f = s.traced
        if f = invalid
            for each g in s.fish
                if f = invalid and g.name = s.opts.trace then f = g
            end for
            s.traced = f
        end if
        print "TRACE t "; Int(t * 10) / 10.0; " x "; Int(f.x); " y "; Int(f.y); " z "; Int(f.z * 100) / 100.0; " hd "; Int(f.hd * 100) / 100.0; " spd "; Int(f.spd); " amp "; Int(f.amp * 100) / 100.0; " pause "; Int(f.pause * 10) / 10.0
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
end sub

' Two caustic bands scroll over the sand in opposite directions; where they cross, the pattern
' appears to ripple and re-form. Hidden under moonlight.
sub DrawCaustics(s as object, screen as object, t as float)
    a = Int(255 * s.cfg.caustics.alpha * s.dayK)
    if a < 2 then return
    col = &hFFFFFF00 + a
    top = s.cfg.caustics.top
    off = [FMod(t * 13, 1024), FMod(300 - t * 8, 1024)]
    for k = 0 to 1
        for j = 0 to 2
            screen.DrawObject(j * 1024 - off[k], top, s.caustic[k], col)
        end for
    end for
    ' Rocks in the band are redrawn over the light, so it lands on the sand only.
    screen.DrawObject(0, top, s.occluder)
end sub

' Soft shafts of light from the surface, slowly breathing and swaying.
sub DrawRays(s as object, screen as object, t as float)
    if s.dayK < 0.02 then return
    k = 0
    for each r in s.cfg.rays
        a = 255 * 0.16 * r[1] * s.dayK * (0.55 + 0.45 * Sin(t * 0.11 + k * 1.7))
        x = r[0] + 30 * Sin(t * 0.05 + k * 2.3)
        screen.DrawScaledObject(x - 128, -40, 1.6, 1.1, s.ray, &hFFFFFF00 + Int(a))
        k = k + 1
    end for
end sub

' Marine snow: tiny specks sinking slowly on a gentle current. Near ones are larger, brighter
' and faster.
sub UpdateMotes(s as object, t as float, dt as float)
    for each mo in s.motes
        mo.x = mo.x + (4 + 10 * mo.z) * dt + 6 * Sin(t * 0.3 + mo.ph) * dt
        mo.y = mo.y + (2 + 7 * mo.z) * dt
        if mo.x > 1930 then mo.x = -10
        if mo.y > 1090
            mo.y = -10
            mo.x = Rnd(0) * 1920
        end if
    end for
end sub

sub DrawMotes(s as object, screen as object, z0 as float, z1 as float)
    lum = 0.4 + 0.6 * s.dayK
    for each mo in s.motes
        if mo.z >= z0 and mo.z < z1
            sc = 0.3 + 0.7 * mo.z
            screen.DrawScaledObject(mo.x, mo.y, sc, sc, s.mote, &hE0F0FF00 + Int((30 + 90 * mo.z) * lum))
        end if
    end for
end sub
