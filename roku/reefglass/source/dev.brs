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
    RunReef(opts, true)
end sub
