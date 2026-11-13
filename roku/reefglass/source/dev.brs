' Development entry point: lets the package run as a sideloaded app so it can be launched and
' inspected over ECP. Release builds leave this file out and drop "title" from the manifest
' (see tools/sideload.sh --release).
'
' Launch parameters (ECP: POST :8060/launch/dev?hour=22&profile=1):
'   hour=<h>       pin the tank clock to this hour (e.g. 21.5); without it, the saved lighting
'                  setting applies, as in the screensaver
'   settings=1     open the settings screen instead
'   lighting=<id>  save this lighting setting (auto, day, dusk, night) first, as the settings
'                  screen would
'   daycycle=<s>   sweep a full 24 h day every <s> seconds, to check the lighting ramps
'   profile=1      print per-section frame timings every 5 s
'   pose=<name>    draw that species through a U-turn, in 9 steps across the screen
'                  (fine=1: only 45 to 90 degrees; pp=<0..1>: that much puffed up;
'                  pitch=<deg>: climbing at that angle)
'   puff=1         the pufferfish puffs up as soon as its cooldown allows (set short)
'   scene=<name>   load scenes/<name>.json (default tank)
'   pan=<s>        <s> seconds per back-and-forth; cam=<x> pins the camera at
'                  tank x
'   fps=<n>        override the frame cap (0: uncapped, to measure headroom)
'   nofish=1       no fish (the moray and other critters stay), to look closely at the scene
'   mirror=flat    left-facing fish drawn level, as when no scratch bitmap fits (FishMirrorMode)
'   failbmp=<text> fail every bitmap load whose path contains <text> (e.g. wide_bg1, puffer)
'   fliptest=1     draw a grid of one sprite flipped and rotated (FlipTest), to check how the device mirrors
'   trace=<name>   print the motion of one fish of that species (e.g. trace=clown) (x, y, z, heading, speed, puff,
'                  waypoint, U-turn direction, coral block) twice a second

sub Main(args as dynamic)
    if type(args) <> "roAssociativeArray" then args = {}
    if args.lighting <> invalid then SaveLighting(args.lighting)
    if args.settings <> invalid
        RunScreenSaverSettings()
        return
    end if
    opts = {}
    h = LightingHour(LoadLighting())
    if h <> invalid then opts.hour = h
    if args.hour <> invalid then opts.hour = Val(args.hour)
    if args.daycycle <> invalid then opts.daycycle = Val(args.daycycle)
    if args.profile <> invalid then opts.profile = true
    if args.trace <> invalid then opts.trace = args.trace
    if args.pose <> invalid then opts.pose = args.pose
    if args.fine <> invalid then opts.poseFine = true
    if args.puff <> invalid then opts.puff = true
    if args.pp <> invalid then opts.posePuff = Val(args.pp)
    if args.pitch <> invalid then opts.posePitch = Val(args.pitch)
    if args.scene <> invalid then opts.scene = args.scene
    if args.pan <> invalid then opts.pan = Val(args.pan)
    if args.cam <> invalid then opts.cam = Val(args.cam)
    if args.fps <> invalid then opts.fps = Val(args.fps)
    if args.nofish <> invalid then opts.nofish = true
    if args.mirror <> invalid then opts.mirror = args.mirror
    if args.failbmp <> invalid then m.failBmp = args.failbmp
    if args.fliptest <> invalid
        FlipTest()
        return
    end if
    RunReef(opts, true)
end sub

' Dev: fliptest=1. A grid of one asymmetric sprite (gray 100x60, red top-left, green
' top-right, blue bottom-left) drawn with DrawTransformedObject at angles across the columns
' and scale signs (sx, sy) down the rows: rows 0-3 from a region with its origin moved to its
' center (SetPretranslation), rows 4-7 from the bitmap itself (origin top-left). Each cell is
' centered on its draw point, marked by a small white cross. Stays up until Back.
sub FlipTest()
    screen = CreateObject("roScreen", true, 1920, 1080)
    port = CreateObject("roMessagePort")
    screen.SetMessagePort(port)
    bmp = CreateObject("roBitmap", { width: 100, height: 60, AlphaEnable: true })
    bmp.Clear(0)
    bmp.DrawRect(0, 0, 100, 60, &h808080FF)
    bmp.DrawRect(0, 0, 30, 20, &hFF0000FF)
    bmp.DrawRect(70, 0, 30, 20, &h00FF00FF)
    bmp.DrawRect(0, 40, 30, 20, &h0000FFFF)
    bmp.Finish()
    reg = CreateObject("roRegion", bmp, 0, 0, 100, 60)
    reg.SetPretranslation(-50, -30)
    angles = [0, 20, 45, 90, 135, 180, 270, 340]
    signs = [[1, 1], [-1, 1], [1, -1], [-1, -1]]
    for frame = 1 to 2
        screen.Clear(&h101010FF)
        for r = 0 to 7
            sg = signs[r mod 4]
            src = reg
            if r >= 4 then src = bmp
            y = 67 + r * 135
            for c = 0 to 7
                x = 120 + c * 240
                screen.DrawTransformedObject(x, y, angles[c], sg[0], sg[1], src)
                screen.DrawRect(x - 4, y, 9, 1, &hFFFFFFFF)
                screen.DrawRect(x, y - 4, 1, 9, &hFFFFFFFF)
            end for
        end for
        screen.SwapBuffers()
    end for
    print "FLIPTEST drawn"
    ' Can a region itself mirror its source (negative width, or offset/scale tricks)?
    neg = CreateObject("roRegion", bmp, 100, 0, -100, 60)
    print "FLIPTEST negative-width region: "; type(neg)
    if neg <> invalid
        screen.Clear(&h101010FF)
        ok1 = screen.DrawObject(300, 300, neg)
        ok2 = screen.DrawTransformedObject(700, 300, 20, 1, 1, neg)
        print "FLIPTEST negative-width draws: "; ok1; " "; ok2
        screen.SwapBuffers()
    end if
    while true
        msg = wait(0, port)
        if type(msg) = "roUniversalControlEvent" and msg.GetInt() = 0 then return
    end while
end sub
