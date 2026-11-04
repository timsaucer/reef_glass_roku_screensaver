' Development entry point: lets the package run as a sideloaded app so it can be launched and
' inspected over ECP. Release builds leave this file out and drop "title" from the manifest
' (see tools/sideload.sh --release).
'
' Launch parameters (ECP: POST :8060/launch/dev?hour=22&profile=1):
'   hour=<h>       pin the tank clock to this hour (e.g. 21.5) instead of local time
'   daycycle=<s>   sweep a full 24 h day every <s> seconds, to check the lighting ramps
'   profile=1      print per-section frame timings every 5 s
'   pose=<name>    draw that species through a U-turn, in 9 steps across the screen
'                  (fine=1: only 45 to 90 degrees; pp=<0..1>: that much puffed up)
'   puff=1         the pufferfish puffs up as soon as its cooldown allows (set short)
'   trace=<name>   print the motion of one fish of that species (e.g. trace=clown) (x, y, z, heading, speed, puff,
'                  waypoint, U-turn direction, coral block) twice a second

sub Main(args as dynamic)
    if type(args) <> "roAssociativeArray" then args = {}
    opts = {}
    if args.hour <> invalid then opts.hour = Val(args.hour)
    if args.daycycle <> invalid then opts.daycycle = Val(args.daycycle)
    if args.profile <> invalid then opts.profile = true
    if args.trace <> invalid then opts.trace = args.trace
if args.pose <> invalid then opts.pose = args.pose
if args.fine <> invalid then opts.poseFine = true
if args.puff <> invalid then opts.puff = true
if args.pp <> invalid then opts.posePuff = Val(args.pp)
    RunReef(opts, true)
end sub
