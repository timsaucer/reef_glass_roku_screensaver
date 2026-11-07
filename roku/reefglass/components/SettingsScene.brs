' One radio list of lighting choices; picking one reports it at once (the main thread saves it),
' and Back reports done.

sub init()
    m.ids = []
    m.list = m.top.findNode("lighting")
    m.list.setFocus(true)
end sub

' The choices (LightingChoices() in source/settings.brs) arrive from the main thread, before
' the saved choice. The list reports picks only once it is filled and set to the saved choice,
' so filling it never reports (and saves) the first entry.
sub onChoicesSet()
    m.ids = []
    root = CreateObject("roSGNode", "ContentNode")
    for each c in m.top.choices
        m.ids.Push(c.id)
        item = root.createChild("ContentNode")
        item.title = c.label
    end for
    m.list.unobserveField("checkedItem")
    m.list.content = root
    m.list.checkedItem = 0
    onLightingSet()
    m.list.observeField("checkedItem", "onChecked")
    ' The screen is fully shown: tell Roku the launch is complete (certification 3.2 measures
    ' launch time with this beacon).
    if m.launched <> true
        m.top.signalBeacon("AppLaunchComplete")
        m.launched = true
    end if
end sub

' The saved choice arrives from the main thread after init, once the screen is shown; focus
' set in init can be lost by then, so the list takes it again here.
sub onLightingSet()
    if not m.list.hasFocus() then m.list.setFocus(true)
    for i = 0 to m.ids.Count() - 1
        if m.ids[i] = m.top.lighting and m.list.checkedItem <> i
            m.list.checkedItem = i
            m.list.jumpToItem = i
        end if
    end for
end sub

sub onChecked()
    i = m.list.checkedItem
    if i >= 0 and i < m.ids.Count() and m.top.lighting <> m.ids[i] then m.top.lighting = m.ids[i]
end sub

function onKeyEvent(key as string, press as boolean) as boolean
    if press and key = "back"
        m.top.done = true
        return true
    end if
    return false
end function
