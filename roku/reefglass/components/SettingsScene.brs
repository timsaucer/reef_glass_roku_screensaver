' One radio list of lighting choices; picking one reports it at once (the main thread saves it),
' and Back reports done.

sub init()
    ' Keep in step with LightingChoices() in source/settings.brs.
    m.ids = ["auto", "day", "dusk", "night"]
    labels = ["Follow the Roku's clock", "Daytime", "Dusk", "Night"]
    m.list = m.top.findNode("lighting")
    root = CreateObject("roSGNode", "ContentNode")
    for each l in labels
        item = root.createChild("ContentNode")
        item.title = l
    end for
    m.list.content = root
    m.list.checkedItem = 0
    m.list.observeField("checkedItem", "onChecked")
    m.list.setFocus(true)
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
    if i >= 0 and m.top.lighting <> m.ids[i] then m.top.lighting = m.ids[i]
end sub

function onKeyEvent(key as string, press as boolean) as boolean
    if press and key = "back"
        m.top.done = true
        return true
    end if
    return false
end function
