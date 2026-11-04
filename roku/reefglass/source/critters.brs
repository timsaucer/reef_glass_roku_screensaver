' Reef critters: the anemone, feather duster worms, the giant clam, a starfish, and the goby and
' pistol shrimp sharing a burrow in the sand.

sub CrittersInit(s as object)
    cfg = s.cfg
    a = cfg.anemone
    s.anem = { x: a.x, y: a.y, z: a.z, fps: a.fps, frames: [] }
    for i = 0 to a.frames - 1
        s.anem.frames.Push(CreateObject("roBitmap", "pkg:/images/anemone_" + i.ToStr() + ".png"))
    end for
    b0 = s.anem.frames[0]
    s.anem.w = b0.GetWidth() : s.anem.h = b0.GetHeight()

    s.crown = CreateObject("roBitmap", "pkg:/images/duster_crown.png")
    s.tube = CreateObject("roBitmap", "pkg:/images/duster_tube.png")
    s.dusters = []
    k = 0
    for each d in cfg.dusters
        s.dusters.Push({ x: d.x, y: d.y, s: d.s, open: 1.0, mode: "open", wait: 0, cool: 0, ph: k * 1.9 })
        k = k + 1
    end for

    if cfg.clam.inPlate = invalid then s.clamBmp = CreateObject("roBitmap", "pkg:/images/clam.png")
    s.clamShimmer = CreateObject("roBitmap", "pkg:/images/clam_shimmer.png")
    s.starBmp = CreateObject("roBitmap", "pkg:/images/starfish.png")
    sf = cfg.starfish
    s.star = { x: RndRange(sf.x0, sf.x1), dir: 1, rest: 0 }

    b = cfg.burrow
    s.burrow = {
        x: b.x, y: b.y, threat: b.threat
        goby: LoadFishSprite("goby", GobyPivot(b))
        shrimpBmp: CreateObject("roBitmap", "pkg:/images/shrimp.png")
        lip: CreateObject("roBitmap", "pkg:/images/lip.png")
        puff: CreateObject("roBitmap", "pkg:/images/puff.png")
        ' Goby: out = 1 sitting at the mouth, 0 down inside. off = sideways hop from the mouth.
        out: 1.0, gmode: "out", calm: 0, off: 0.0, offT: 0.0, hop: RndRange(3, 8), gdir: 1, gface: 1.0, gphase: 0
        ' Shrimp: pos 0 inside .. 1 fully out, bulldozing sand to the right.
        pos: 0.0, smode: "in", swait: RndRange(3, 8), puffClock: 0
        puffs: [], threatNow: false
    }
end sub

function GobyPivot(b as object) as object
    if b.goby <> invalid then return b.goby.pivot
    return [4, 15]
end function

sub CrittersUpdate(s as object, t as float, dt as float)
    UpdateBurrow(s, t, dt)
    UpdateDusters(s, t, dt)
    ' Starfish: a slow crawl back and forth along the sand, resting at each end.
    sf = s.cfg.starfish
    st = s.star
    if st.rest > 0
        st.rest = st.rest - dt
    else
        st.x = st.x + st.dir * sf.speed * s.activity * dt
        if st.x > sf.x1 or st.x < sf.x0
            st.dir = -st.dir
            st.x = Clamp(st.x, sf.x0, sf.x1)
            st.rest = RndRange(20, 60)
        end if
    end if
end sub

sub CrittersDraw(s as object, screen as object, t as float)
    ' Clam with its mantle shimmering as the light plays over it.
    c = s.cfg.clam
    ' With photoreal art the clam is part of the plate and only the shimmer is drawn.
    w = s.clamShimmer.GetWidth() : h = s.clamShimmer.GetHeight()
    if c.inPlate = invalid then screen.DrawObject(c.x - w / 2, c.y - h, s.clamBmp)
    sh = 0.3 + 0.2 * Sin(t * 0.8) + 0.12 * Sin(t * 2.3 + 1)
    screen.DrawObject(c.x - w / 2, c.y - h, s.clamShimmer, &hFFFFFF00 + Int(255 * sh * (0.5 + 0.5 * s.dayK)))

    ' Starfish, with a soft contact shadow so it sits on the sand.
    st = s.star
    sw = s.starBmp.GetWidth() : shh = s.starBmp.GetHeight()
    sy = s.cfg.starfish.y
    screen.DrawScaledObject(st.x - sw * 0.55, sy - shh * 0.2, sw * 1.1 / 24, shh * 0.9 / 24, s.burrow.puff, &h1A140F00 + 90)
    screen.DrawObject(st.x - sw / 2, sy - shh / 2, s.starBmp)

    DrawDusters(s, screen, t)
    DrawBurrow(s, screen, t)
end sub

' The anemone sways through a loop of frames, crossfading between neighbors.
sub AnemoneDraw(s as object, screen as object, t as float)
    a = s.anem
    n = a.frames.Count()
    u = t * a.fps
    i = Int(u)
    frac = u - i
    i = i mod n
    x = a.x - a.w / 2 : y = a.y - a.h
    screen.DrawObject(x, y, a.frames[i])
    screen.DrawObject(x, y, a.frames[(i + 1) mod n], &hFFFFFF00 + Int(255 * frac))
end sub

' Feather dusters snap shut when a fish swims close, then unfurl slowly. A quarter of them are
' checked against the fish each frame.
sub UpdateDusters(s as object, t as float, dt as float)
    for each d in s.dusters
        if d.mode = "closing"
            d.open = d.open - dt / 0.15
            if d.open <= 0.04
                d.open = 0.04
                d.mode = "closed"
                d.wait = RndRange(3, 9)
            end if
        else if d.mode = "closed"
            d.wait = d.wait - dt
            if d.wait <= 0 then d.mode = "opening"
        else if d.mode = "opening"
            d.open = d.open + dt / 3.0
            if d.open >= 1
                d.open = 1
                d.mode = "open"
                ' Once open again it tolerates passing fish for a while.
                d.cool = RndRange(10, 30)
            end if
        else
            d.cool = d.cool - dt
        end if
    end for
    if s.frame mod 4 <> 0 then return
    for each d in s.dusters
        if d.mode = "open" and d.cool <= 0
            for each f in s.fish
                dx = f.x - d.x : dy = f.y - (d.y - 40)
                r = 70 + 60 * f.size * f.z
                if dx * dx + dy * dy < r * r and Rnd(0) < 0.35
                    d.mode = "closing"
                    exit for
                end if
            end for
        end if
    end for
end sub

sub DrawDusters(s as object, screen as object, t as float)
    cw = s.crown.GetWidth() : ch = s.crown.GetHeight()
    tw = s.tube.GetWidth()
    drop = 0
    if s.cfg.duster <> invalid then drop = s.cfg.duster.crownDrop
    for each d in s.dusters
        if d.open > 0.05
            ' Retracting: the crown shrinks down into the tube mouth; open crowns breathe a little.
            k = d.open
            sx = d.s * (0.3 + 0.7 * k) * (1 + 0.04 * Sin(t * 0.9 + d.ph))
            sy = d.s * k
            screen.DrawScaledObject(d.x - sx * cw / 2 + 2 * Sin(t * 0.6 + d.ph), d.y - sy * (ch - drop), sx, sy, s.crown)
        end if
        screen.DrawScaledObject(d.x - d.s * tw / 2, d.y - 4 * d.s, d.s, d.s, s.tube)
    end for
end sub

' Goby and pistol shrimp. The shrimp keeps bulldozing sand out of the burrow while the goby
' stands guard at the mouth. When a big fish comes close the goby dives in and the shrimp
' follows; once things have been calm a while the goby rises back up and work resumes.
sub UpdateBurrow(s as object, t as float, dt as float)
    b = s.burrow
    threat = false
    if s.frame mod 3 = 0
        for each f in s.fish
            if f.big
                dx = f.x - b.x : dy = f.y - b.y
                r = b.threat * (0.5 + 0.5 * f.z)
                if dx * dx + dy * dy < r * r
                    threat = true
                    exit for
                end if
            end if
        end for
        b.threatNow = threat
    else
        threat = (b.threatNow = true)
    end if

    if threat
        b.calm = RndRange(3, 6)
        if b.gmode <> "hidden" then b.gmode = "diving"
    else if b.calm > 0
        b.calm = b.calm - dt
    end if

    ' Goby.
    if b.gmode = "diving"
        b.out = b.out - dt / 0.25
        if b.out <= 0
            b.out = 0
            b.gmode = "hidden"
        end if
    else if b.gmode = "hidden"
        if b.calm <= 0 then b.gmode = "rising"
    else if b.gmode = "rising"
        b.out = b.out + dt / 2.5
        if b.out >= 1
            b.out = 1
            b.gmode = "out"
        end if
    else
        ' Out: small hops to either side of the mouth, turning to look around.
        b.hop = b.hop - dt
        if b.hop <= 0
            b.offT = RndRange(-30, 30)
            b.hop = RndRange(3, 9)
            if b.offT > b.off then b.gdir = 1 else b.gdir = -1
            if Rnd(0) < 0.3 then b.gdir = -b.gdir
        end if
        b.off = b.off + Clamp(b.offT - b.off, -40 * dt, 40 * dt)
    end if
    ' The goby only strays from the mouth when fully out.
    if b.gmode <> "out" then b.off = b.off + Clamp(-b.off, -80 * dt, 80 * dt)
    b.gface = b.gface + Clamp(b.gdir - b.gface, -4 * dt, 4 * dt)
    if b.gface > -0.15 and b.gface < 0.15
        if b.gdir > 0 then b.gface = 0.15 else b.gface = -0.15
    end if
    b.gphase = b.gphase + dt * 6.283 * 1.6

    ' Shrimp: works only while the goby is out on guard.
    if b.gmode <> "out" and b.smode <> "in"
        b.smode = "flee"
    end if
    if b.smode = "flee"
        b.pos = b.pos - dt / 0.3
        if b.pos <= 0
            b.pos = 0
            b.smode = "in"
            b.swait = RndRange(2, 5)
        end if
    else if b.smode = "in"
        if b.gmode = "out"
            b.swait = b.swait - dt
            if b.swait <= 0 then b.smode = "push"
        end if
    else if b.smode = "push"
        b.pos = b.pos + dt / 2.6
        b.puffClock = b.puffClock - dt
        if b.puffClock <= 0 and b.pos > 0.25
            b.puffClock = 0.12
            b.puffs.Push({ x: b.x + 22 + b.pos * 52 + RndRange(-4, 4), y: b.y + RndRange(-6, 4), vx: RndRange(10, 30), vy: RndRange(-14, -4), life: 1.0 })
        end if
        if b.pos >= 1
            b.pos = 1
            b.smode = "hold"
            b.swait = RndRange(0.4, 1.2)
        end if
    else if b.smode = "hold"
        b.swait = b.swait - dt
        if b.swait <= 0 then b.smode = "back"
    else if b.smode = "back"
        b.pos = b.pos - dt / 1.6
        if b.pos <= 0
            b.pos = 0
            b.smode = "in"
            b.swait = RndRange(4, 12)
        end if
    end if

    ' Sand puffs drift up a little and settle out.
    alive = []
    for each p in b.puffs
        p.life = p.life - dt / 1.4
        if p.life > 0
            p.x = p.x + p.vx * dt
            p.y = p.y + p.vy * dt
            p.vy = p.vy + 12 * dt
            p.vx = p.vx * (1 - 1.5 * dt)
            alive.Push(p)
        end if
    end for
    b.puffs = alive
end sub

sub DrawBurrow(s as object, screen as object, t as float)
    b = s.burrow
    ' Shrimp climbs out of the hole over the first third of its path, then pushes along the sand.
    if b.pos > 0
        rise = Clamp(b.pos * 3, 0, 1)
        bw = b.shrimpBmp.GetWidth() : bh = b.shrimpBmp.GetHeight()
        sx = b.x + 4 + b.pos * 52
        sy = b.y - bh + 6 + (1 - rise) * 22
        screen.DrawObject(sx - bw / 2, sy, b.shrimpBmp, &hFFFFFF00 + Int(255 * Clamp(rise * 2, 0, 1)))
    end if
    if b.out > 0.02
        g = b.goby
        gy = b.y - 12 + (1 - b.out) * 34
        DrawFishSprite(screen, g, b.x + b.off, gy + Sin(b.gphase * 0.3), 1.0, b.gface, 0.8 + 0.2 * Cos(b.gphase), &hFFFFFF00 + Int(255 * Clamp(b.out * 2.5, 0, 1)))
    end if
    for each p in b.puffs
        sc = 0.6 + 0.8 * (1 - p.life)
        screen.DrawScaledObject(p.x - 12 * sc, p.y - 12 * sc, sc, sc, b.puff, &hD8CCB000 + Int(140 * p.life))
    end for
    screen.DrawObject(b.x - b.lip.GetWidth() / 2, b.y - 8, b.lip)
end sub
