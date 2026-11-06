' Reef Glass screensaver: a photoreal reef-tank plate with procedurally animated fish, critters
' and light drawn over it.
'
' Entry points:
'   RunScreenSaver          the system screensaver
'   RunScreenSaverSettings  its settings screen: the lighting (settings.brs)
'   Main                    dev.brs; development builds only (see tools/sideload.sh)

sub RunScreenSaver()
    opts = {}
    h = LightingHour(LoadLighting())
    if h <> invalid then opts.hour = h
    RunReef(opts, false)
end sub

' Runs the tank until the system stops the screensaver (or Back is pressed in the dev app).
sub RunReef(opts as object, isApp as boolean)
    screen = CreateObject("roScreen", true, 1920, 1080)
    screen.SetAlphaEnable(true)
    port = CreateObject("roMessagePort")
    screen.SetMessagePort(port)
    ' Held for the whole run: the monitor's objects must stay alive to deliver their events.
    mon = StartMemoryMonitor(port)

    scene = "reef"
    if opts.scene <> invalid then scene = opts.scene
    cfg = ParseJson(ReadAsciiFile("pkg:/scenes/" + scene + ".json"))
    s = ReefInit(cfg, opts)

    ' Frame cap: a steady 30 judders less than an uneven 35-45 on low-end sticks.
    frameMs = 0
    if cfg.fps <> invalid then frameMs = 1000 / cfg.fps
    if opts.fps <> invalid
        frameMs = 0
        if opts.fps > 0 then frameMs = 1000 / opts.fps
    end if
    fade = 2.0
    frameClock = CreateObject("roTimespan")
    fpsClock = CreateObject("roTimespan")
    frames = 0
    late = 0
    ' Run time in integer ms: dt comes from the difference of two exact counts (in float
    ' seconds it would quantize as the run grows long and make motion uneven). roTimespan's
    ' 32-bit ms count overflows after ~24.8 days, so it is restarted daily and what it had
    ' counted carried forward in a 64-bit total.
    clock = CreateObject("roTimespan")
    baseMs = 0&
    lastMs = 0&
    nextMs = 0#
    while true
        elapsed = clock.TotalMilliseconds()
        if elapsed >= 86400000
            baseMs = baseMs + elapsed
            clock.Mark()
            elapsed = 0
        end if
        ms = baseMs + elapsed
        dt = (ms - lastMs) / 1000.0
        if dt > 0.1 then dt = 0.1
        lastMs = ms
        now = ms / 1000.0
        ReefFrame(s, screen, now, dt)

        if now < fade then screen.DrawRect(0, 0, 1920, 1080, &h00000000 + Int(255 * (1 - now / fade)))

        if frameMs > 0
            ' Frames on a fixed schedule (frame n at n * frameMs), not timed from the last one:
            ' timed from the last swap, the small error of each wait added up and every so
            ' often a frame came out a vsync early (30.6 fps), a visible hitch in the pan.
            nextMs = nextMs + frameMs
            nowMs = baseMs + clock.TotalMilliseconds()
            if nextMs < nowMs - frameMs then nextMs = nowMs
            left = Int(nextMs - nowMs) - 2
            if left > 0 then sleep(left)
        end if
        screen.SwapBuffers()
        if frameMs > 0 and frameClock.TotalMilliseconds() > frameMs * 1.4 then late = late + 1
        frameClock.Mark()

        frames = frames + 1
        if fpsClock.TotalMilliseconds() >= 10000
            print "FPS "; frames / 10.0; " late "; late
            frames = 0
            late = 0
            fpsClock.Mark()
        end if

        msg = port.GetMessage()
        if type(msg) = "roDeviceInfoEvent" or type(msg) = "roAppMemoryNotificationEvent" then HandleMemoryEvent(msg)
        if isApp and type(msg) = "roUniversalControlEvent" and msg.GetInt() = 0 then return
    end while
end sub

' Memory monitoring, as Roku certification asks for. The texture budget is modest, so these
' events are not expected; if one arrives, collect garbage and log the levels.
function StartMemoryMonitor(port as object) as object
    mon = { di: CreateObject("roDeviceInfo"), app: CreateObject("roAppMemoryMonitor") }
    ' Not every Roku OS has every call, so each is guarded on its own.
    try
        mon.di.SetMessagePort(port)
        mon.di.EnableLowGeneralMemoryEvent(true)
    catch e
    end try
    try
        mon.app.SetMessagePort(port)
        mon.app.EnableMemoryWarningEvent(true)
    catch e
    end try
    LogMemory("start")
    return mon
end function

sub HandleMemoryEvent(msg as object)
    ' roDeviceInfoEvent also reports unrelated changes (HDMI, power, audio); act only on memory.
    info = invalid
    try
        info = msg.GetInfo()
    catch e
    end try
    if type(msg) = "roDeviceInfoEvent" and (info = invalid or info.generalMemoryLevel = invalid) then return
    RunGarbageCollector()
    detail = ""
    if info <> invalid then detail = FormatJson(info)
    LogMemory("event " + type(msg) + " " + detail)
end sub

sub LogMemory(label as string)
    app = CreateObject("roAppMemoryMonitor")
    limit = "n/a" : avail = "n/a" : pct = "n/a"
    try
        limit = app.GetChannelMemoryLimit().ToStr()
    catch e
    end try
    try
        avail = app.GetChannelAvailableMemory().ToStr()
    catch e
    end try
    try
        pct = app.GetMemoryLimitPercent().ToStr()
    catch e
    end try
    print "MEMORY "; label; ": limit "; limit; " available "; avail; " used% "; pct
end sub

' Float modulo with a non-negative result (BrightScript's mod works on integers).
function FMod(a as float, m as float) as float
    return a - Int(a / m) * m
end function

' Packs a color for draw calls. Colors are signed 32-bit, so r * &h1000000 would overflow for
' r >= 128; the top byte is folded into the negative range instead.
function RGBA(r as integer, g as integer, b as integer, a as integer) as integer
    if r >= 128 then r = r - 256
    return r * &h1000000 + g * &h10000 + b * &h100 + a
end function

function Clamp(v as float, lo as float, hi as float) as float
    if v < lo then return lo
    if v > hi then return hi
    return v
end function

function SmoothStep(a as float, b as float, v as float) as float
    u = Clamp((v - a) / (b - a), 0, 1)
    return u * u * (3 - 2 * u)
end function

function RndRange(lo as float, hi as float) as float
    return lo + Rnd(0) * (hi - lo)
end function
