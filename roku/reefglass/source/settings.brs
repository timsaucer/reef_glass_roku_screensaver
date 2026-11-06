' Screensaver settings: the tank's lighting, held at daytime (the default), dusk or night, or
' following the Roku's clock. Roku opens RunScreenSaverSettings from the screensaver's
' "Change screensaver settings" entry. That context only shows SceneGraph screens, so the UI is
' components/SettingsScene.xml; this side loads the saved choice into it and saves it back to
' the registry as soon as it changes.

' Lighting choices, in list order, with the tank hour each one holds (auto: the clock).
function LightingChoices() as object
    return [
        { id: "auto", label: "Follow the Roku's clock" }
        { id: "day", label: "Daytime", hour: 12.0 }
        { id: "dusk", label: "Dusk", hour: 20.7 }
        { id: "night", label: "Night", hour: 23.0 }
    ]
end function

function LoadLighting() as string
    reg = CreateObject("roRegistrySection", "reefglass")
    id = "day"
    if reg.Exists("lighting") then id = reg.Read("lighting")
    for each c in LightingChoices()
        if c.id = id then return id
    end for
    return "day"
end function

' The hour to hold the tank at for a lighting choice, or invalid to follow the clock.
function LightingHour(id as string) as dynamic
    for each c in LightingChoices()
        if c.id = id and c.hour <> invalid then return c.hour
    end for
    return invalid
end function

sub SaveLighting(id as string)
    reg = CreateObject("roRegistrySection", "reefglass")
    reg.Write("lighting", id)
    reg.Flush()
end sub

sub RunScreenSaverSettings()
    screen = CreateObject("roSGScreen")
    port = CreateObject("roMessagePort")
    screen.SetMessagePort(port)
    mon = StartMemoryMonitor(port)
    ui = screen.CreateScene("SettingsScene")
    screen.Show()
    ui.choices = LightingChoices()
    ui.lighting = LoadLighting()
    ui.ObserveField("lighting", port)
    ui.ObserveField("done", port)
    while true
        msg = wait(0, port)
        t = type(msg)
        if t = "roDeviceInfoEvent" or t = "roAppMemoryNotificationEvent" then HandleMemoryEvent(msg)
        if t = "roSGNodeEvent" and msg.GetField() = "lighting"
            SaveLighting(ui.lighting)
            print "SETTINGS saved lighting="; ui.lighting
        end if
        if (t = "roSGNodeEvent" and msg.GetField() = "done") or (t = "roSGScreenEvent" and msg.IsScreenClosed())
            SaveLighting(ui.lighting)
            return
        end if
    end while
end sub
