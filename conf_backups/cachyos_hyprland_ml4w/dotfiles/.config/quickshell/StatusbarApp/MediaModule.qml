import Quickshell
import Quickshell.Services.Mpris
import Quickshell.Services.Pipewire
import QtQuick
import QtQuick.Layouts
import qs.CustomTheme

// Compact now-playing pill: icon + track text, hidden when nothing audible.
// Left click toggles play/pause (MPRIS) or mute (app-audio fallback), wheel
// cycles every currently-playing source (MPRIS players, then app streams),
// right click opens the dropdown (MediaPanel). A pinned source stays active
// until it vanishes, then selection falls back to auto.
Rectangle {
    id: media

    signal mediaToggleRequested
    signal mediaOpenRequested
    signal mediaCloseRequested

    // De-duplicated MPRIS list (same rule as MediaPanel): drops the
    // playerctld proxy mirror and any same-track duplicate, so one source
    // never shows twice and indices stay aligned with the panel.
    readonly property var players: {
        let out = []
        let seen = ({})
        let all = Mpris.players.values
        for (let i = 0; i < all.length; i++) {
            let p = all[i]
            if (!p)
                continue
            if (p.dbusName !== undefined && ("" + p.dbusName).endsWith("playerctld"))
                continue
            let k = (p.identity || "") + " | " + (p.trackTitle || "") + " | " + (p.trackArtist || "")
            if (seen[k])
                continue
            seen[k] = true
            out.push(p)
        }
        return out
    }
    // Same dedupe as MediaPanel: streams whose app name matches an MPRIS
    // identity are hidden there, so the pill's wheel union must skip them
    // too or it would select invisible rows. One stream per matching player
    // is assumed to back its row; extras (a 2nd Brave tab) stay visible.
    readonly property var mprisNames: players.map(p => ((p.identity || "").toLowerCase()))
    function streamKey(n): string {
        if (n === null || n === undefined)
            return ""
        var viaProps = ""
        if (n.properties !== undefined && n.properties !== null)
            viaProps = n.properties["application.name"] || ""
        return ((viaProps || n.description || n.nickname || n.name || "").toLowerCase())
    }
    readonly property var streams: {
        let all = Pipewire.nodes !== null && Pipewire.nodes.values !== undefined ? Pipewire.nodes.values.filter(n => n && n.isStream && n.isSink && n.audio !== null && n.audio !== undefined) : []
        let dropped = ({})
        return all.filter(n => {
            let k = streamKey(n)
            let allow = 0
            for (let i = 0; i < mprisNames.length; i++)
                if (mprisNames[i] === k)
                    allow++
            let d = dropped[k] || 0
            if (d < allow) {
                dropped[k] = d + 1
                return false
            }
            return true
        })
    }
    readonly property int totalCount: players.length + streams.length
    // Pinned index over the union (-1 = auto): 0..players-1 are MPRIS,
    // players.length..total-1 are app streams. Validated on every read.
    property int pinnedIndex: -1
    readonly property bool pinnedValid: pinnedIndex >= 0 && pinnedIndex < totalCount
    readonly property bool pinnedIsStream: pinnedValid && pinnedIndex >= players.length
    readonly property var autoPlayer: {
        for (let i = 0; i < players.length; i++)
            if (players[i].isPlaying)
                return players[i]
        return players.length > 0 ? players[0] : null
    }
    readonly property var player: !pinnedValid ? autoPlayer : (pinnedIsStream ? null : players[pinnedIndex])
    readonly property var selectedStream: pinnedIsStream ? streams[pinnedIndex - players.length] : null
    readonly property var autoStream: streams.length > 0 ? streams[0] : null
    readonly property var shownStream: selectedStream !== null ? selectedStream : (!hasPlayer ? autoStream : null)
    PwObjectTracker { objects: shownStream !== null ? [shownStream] : [] }
    readonly property string streamLabel: {
        let s = shownStream
        if (s === null)
            return ""
        var viaProps = ""
        if (s.properties !== undefined && s.properties !== null)
            viaProps = s.properties["application.name"] || ""
        return viaProps || s.description || s.nickname || s.name || "App audio"
    }
    readonly property bool streamMuted: shownStream !== null && shownStream.audio !== null ? shownStream.audio.muted : false
    readonly property bool hasPlayer: player !== null
    readonly property bool hasAny: hasPlayer || shownStream !== null
    readonly property bool collapsed: !hasAny
    readonly property bool isPlaying: hasPlayer ? player.isPlaying : (shownStream !== null ? !streamMuted : false)
    readonly property string trackText: {
        if (selectedStream !== null)
            return streamLabel
        if (!hasPlayer)
            return streamLabel
        let title = player.trackTitle || player.identity || "No Media"
        let artist = player.trackArtist
            || (player.trackArtists && player.trackArtists.length > 0 ? player.trackArtists[0] : "")
        return artist !== "" ? title + " — " + artist : title
    }

    property bool focused: false
    readonly property bool active: mouseArea.containsMouse || media.focused

    function activate(): void {
        if (selectedStream !== null) {
            if (selectedStream.audio !== null)
                selectedStream.audio.muted = !selectedStream.audio.muted
            return
        }
        if (!hasPlayer && shownStream !== null) {
            if (shownStream.audio !== null)
                shownStream.audio.muted = !shownStream.audio.muted
            return
        }
        togglePlayer(player)
    }
    // Toggle any player (pill or panel row) through the PlayPause method,
    // with a play()/pause() fallback when the player does not advertise it.
    function togglePlayer(p): void {
        if (!p)
            return
        if (p.canTogglePlaying)
            p.togglePlaying()
        else if (p.isPlaying)
            p.pause()
        else
            p.play()
    }
    function next(): void {
        if (hasPlayer)
            player.next()
    }
    function previous(): void {
        if (hasPlayer)
            player.previous()
    }
    // Pin a source by union index (panel row click). Out-of-range pins are
    // ignored by the pinnedValid guard above.
    function selectPlayer(i: int): void {
        pinnedIndex = i
    }
    function selectStream(i: int): void {
        pinnedIndex = players.length + i
    }
    // Wheel steps through every currently-playing source (MPRIS, then app
    // streams). -1 (auto) is one step above the last source so scrolling
    // wraps through everything and back to auto.
    function stepPlayer(dir: int): void {
        let n = totalCount
        if (n === 0)
            return
        // Auto is represented as n so the cycle runs
        // auto -> 0 -> ... -> n-1 -> auto in either direction.
        let cur = pinnedValid ? pinnedIndex : n
        let nxt = (cur + dir + n + 1) % (n + 1)
        pinnedIndex = (nxt >= n) ? -1 : nxt
    }

    visible: !collapsed
    // Fixed width no matter the title: the track slot is always trackWidth,
    // so the pill never jumps when tracks change. Overlong titles elide
    // (step 2 adds hover marquee to reveal them).
    readonly property int trackWidth: 224
    implicitWidth: collapsed ? 0 : trackWidth + 36
    implicitHeight: 30
    radius: 15
    color: active ? Theme.primary : "transparent"
    Behavior on color { ColorAnimation { duration: 500; easing.type: Easing.OutQuint } }

    RowLayout {
        id: row
        anchors.centerIn: parent
        spacing: 6

        Text {
            Layout.alignment: Qt.AlignVCenter
            text: media.isPlaying ? "󰏤" : "󰐊"
            color: media.active ? Theme.background : Theme.primary
            font.family: "monospace"
            font.pixelSize: 16
        }

        // Fixed-width slot with hover marquee: short titles sit still and
        // elided, long titles scroll there-and-back while hovered so the
        // full name shows. Animation runs only in that state (no timers,
        // no cost otherwise); leaving resets to the elided head.
        Item {
            id: trackBox
            Layout.alignment: Qt.AlignVCenter
            Layout.preferredWidth: media.trackWidth
            Layout.maximumWidth: media.trackWidth
            Layout.minimumWidth: media.trackWidth
            Layout.preferredHeight: trackLabel.implicitHeight
            clip: true

            Text {
                id: trackLabel
                anchors.verticalCenter: parent.verticalCenter
                width: scrolling ? implicitWidth : parent.width
                text: media.trackText
                elide: scrolling ? Text.ElideNone : Text.ElideRight
                color: media.active ? Theme.background : Theme.primary
                font.family: Theme.fontFamily
                font.pixelSize: 14
                font.bold: true

                readonly property bool scrolling: mouseArea.containsMouse
                    && implicitWidth > trackBox.width
                onScrollingChanged: {
                    if (!scrolling)
                        x = 0
                }
            }

            SequentialAnimation {
                id: marquee
                running: trackLabel.scrolling
                loops: Animation.Infinite
                PauseAnimation { duration: 700 }
                NumberAnimation {
                    target: trackLabel
                    property: "x"
                    from: 0
                    to: -(trackLabel.implicitWidth - trackBox.width)
                    duration: Math.max(1800, (trackLabel.implicitWidth - trackBox.width) * 35)
                    easing.type: Easing.Linear
                }
                PauseAnimation { duration: 700 }
                NumberAnimation {
                    target: trackLabel
                    property: "x"
                    from: -(trackLabel.implicitWidth - trackBox.width)
                    to: 0
                    duration: 900
                    easing.type: Easing.Linear
                }
            }
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        cursorShape: Qt.PointingHandCursor
        onClicked: mouse => {
            if (mouse.button === Qt.RightButton)
                media.mediaToggleRequested()
            else
                media.activate()
        }
        onWheel: wheel => media.stepPlayer(wheel.angleDelta.y > 0 ? -1 : 1)
        // Dwell-to-open: hovering still for 500ms opens the dropdown.
        // Any movement restarts the clock; leaving cancels it.
        onEntered: {
            closeTimer.stop()
            dwellTimer.start()
        }
        onPositionChanged: dwellTimer.restart()
        // Leaving the pill schedules a hide; reaching the panel in time
        // cancels it (see the card HoverHandler), so the 26px gap between
        // pill and panel stays crossable.
        onExited: {
            dwellTimer.stop()
            closeTimer.start()
        }
    }

    Timer {
        id: dwellTimer
        interval: 250
        onTriggered: media.mediaOpenRequested()
    }

    Timer {
        id: closeTimer
        interval: 1000
        onTriggered: media.mediaCloseRequested()
    }

    // Called by the panel while it is hovered so the scheduled hide above
    // does not fire mid-reach. Leaving the panel re-arms it.
    function cancelClose(): void {
        closeTimer.stop()
    }
    function scheduleClose(): void {
        closeTimer.restart()
    }
}
