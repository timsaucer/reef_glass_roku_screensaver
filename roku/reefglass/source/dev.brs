' Development entry point: lets the package run as a sideloaded app so it can be launched and
' inspected over ECP. Release builds leave this file out and drop "title" from the manifest
' (see tools/sideload.sh --release).
'
' Launch parameters (ECP: POST :8060/launch/dev?hour=22&profile=1):
'   hour=<h>       pin the tank clock to this hour (e.g. 21.5) instead of local time
'   daycycle=<s>   sweep a full 24 h day every <s> seconds, to check the lighting ramps
'   profile=1      print per-section frame timings every 5 s
'   pose=<name>    draw that species through a U-turn, in 9 steps across the screen
'   trace=<name>   print the motion of one fish of that species (e.g. trace=clown) (x, y, z, heading, speed, face, tail) twice a second

sub Main(args as dynamic)
    if type(args) <> "roAssociativeArray" then args = {}
    opts = {}
    if args.hour <> invalid then opts.hour = Val(args.hour)
    if args.daycycle <> invalid then opts.daycycle = Val(args.daycycle)
    if args.profile <> invalid then opts.profile = true
    if args.trace <> invalid then opts.trace = args.trace
if args.pose <> invalid then opts.pose = args.pose
    RunReef(opts, true)
end sub
