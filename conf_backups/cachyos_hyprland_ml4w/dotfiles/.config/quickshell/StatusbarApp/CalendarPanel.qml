import Quickshell
import Quickshell.Io
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import QtQuick.Effects
import qs.CustomTheme

// The month calendar that drops out of the clock module.
//
// This is a plain Item living inside the statusbar's own window, not a separate
// PanelWindow or a PopupWindow: while the bar holds a Hyprland focus grab (which
// is what closes the panel on an outside click), pointer input only reaches the
// grabbed layer surface, so a separate surface renders but never receives the
// clicks on its buttons. StatusbarWindow reserves room for it below the bar and
// opens its input mask while it is showing.
//
// The panel is positioned by the parent (see StatusbarWindow): `openY` is where
// it sits when open, and it slides up out of the window when closed.
Item {
    id: panel

    // Open/closed, driven by the clock module and the "calendar" IPC handler.
    property bool isOpen: false

    // Where the panel sits when open, in window coordinates. Set by the parent
    // so the panel hangs below the pill.
    property real openY: 0

    // Guard that keeps the item rendered until the closing slide has finished.
    // Without it the panel would vanish the instant isOpen went false instead of
    // sliding away.
    property bool showPanel: false

    // The card is inset inside the item so the drop shadow has room, which is
    // why the panel is 2 * cardInset wider and taller than the card itself.
    // The parent reads this to line the card up with the bar.
    readonly property int cardInset: 20
    implicitWidth: 660
    implicitHeight: 420
    width: implicitWidth
    height: implicitHeight
    visible: showPanel

    // --- GOOGLE AGENDA (events + tasks from gcal-sync.py) ---
    property var agendaEvents: []
    property var agendaTasks: []
    property bool manageAgendaBackground: false
    property var agendaRawEvents: []
    property string agendaUpdated: ""
    property string agendaError: ""
    property string agendaErrorUpdated: ""
    property bool agendaStale: false

    function parseLocalDate(s) {
        let m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s)
        if (!m)
            return null
        let d = new Date(+m[1], +m[2] - 1, +m[3])
        if (isNaN(d.getTime()) || d.getFullYear() !== +m[1]
                || d.getMonth() !== +m[2] - 1 || d.getDate() !== +m[3])
            return null
        return d
    }

    function agendaStamp(raw) {
        if (typeof raw !== "string" || raw === "")
            return null
        let d = /^\d{4}-\d{2}-\d{2}$/.test(raw) ? panel.parseLocalDate(raw) : new Date(raw)
        if (!d || isNaN(d.getTime()))
            return null
        return d
    }

    function agendaUsable(entry, now) {
        if (!entry || typeof entry !== "object")
            return false
        if (typeof entry.summary !== "string" || entry.summary === "")
            return false
        let start = panel.agendaStamp(entry.start)
        let end = panel.agendaStamp(entry.end)
        if (start === null || end === null || end < start)
            return false
        return end > now
    }

    function refreshAgenda(): void {
        let now = new Date()
        let kept = []
        for (let i = 0; i < panel.agendaRawEvents.length; i++) {
            let e = panel.agendaRawEvents[i]
            if (panel.agendaUsable(e, now))
                kept.push(e)
        }
        panel.agendaEvents = kept
        if (typeof panel.agendaUpdated === "string" && panel.agendaUpdated !== "") {
            let stamp = new Date(panel.agendaUpdated)
            panel.agendaStale = !isNaN(stamp.getTime()) && (now - stamp) > 1800000
        } else {
            panel.agendaStale = false
        }
    }

    function allDayLabel(raw): string {
        let d = panel.parseLocalDate(raw)
        if (d === null)
            return "All day"
        return "All day · " + Qt.formatDateTime(d, "d MMM")
    }

    function agendaIsNewer(raw) {
        if (typeof raw !== "string" || raw === "")
            return false
        let incoming = new Date(raw)
        if (isNaN(incoming.getTime()))
            return false
        if (panel.agendaErrorUpdated === "")
            return true
        let base = new Date(panel.agendaErrorUpdated)
        return isNaN(base.getTime()) || incoming > base
    }

    function parseAgenda(src): void {
        try {
            let d = JSON.parse(src)
            panel.agendaRawEvents = Array.isArray(d.events) ? d.events : []
            panel.agendaTasks = d.tasks || []
            if (typeof d.updated === "string")
                panel.agendaUpdated = d.updated
            if (panel.agendaError !== "" && panel.agendaIsNewer(d.updated)) {
                panel.agendaError = ""
                panel.agendaErrorUpdated = ""
            }
            panel.refreshAgenda()
        } catch (e) {
            // Ignore malformed cache; the next sync rewrites it.
        }
    }

    FileView {
        id: agendaFile
        path: Quickshell.env("HOME") + "/.config/gcal/cache.json"
        blockLoading: true
        printErrors: false
        watchChanges: true
        onLoaded: panel.parseAgenda(text())
        onFileChanged: agendaFile.reload()
    }

    // Sync on every open; the timer keeps it fresh in the background.
    Process {
        id: agendaSync
        command: [Quickshell.env("HOME") + "/.config/gcal/.venv/bin/python",
            Quickshell.env("HOME") + "/.config/gcal/gcal-sync.py"]
        stderr: StdioCollector { id: agendaSyncErr }
        onExited: (exitCode, exitStatus) => {
            if (exitCode === 0 && exitStatus === 0) {
                panel.agendaError = ""
                panel.agendaErrorUpdated = ""
                agendaFile.reload()
            } else if (exitStatus === 0) {
                panel.agendaErrorUpdated = panel.agendaUpdated
                if (agendaSyncErr.text.indexOf("invalid_grant") !== -1)
                    panel.agendaError = "Calendar sync failed · sign-in expired"
                else
                    panel.agendaError = "Calendar sync failed · cached data shown"
                panel.refreshAgenda()
            } else if (exitCode !== 15) {
                panel.agendaErrorUpdated = panel.agendaUpdated
                panel.agendaError = "Calendar sync failed · cached data shown"
                panel.refreshAgenda()
            }
        }
    }
    Timer {
        interval: 900000
        repeat: true
        running: panel.manageAgendaBackground
        onTriggered: {
            panel.refreshAgenda()
            agendaSync.running = true
        }
    }
    // Reminder daemon: notify + sound for imminent events / due tasks.
    Process {
        id: agendaRemind
        command: [Quickshell.env("HOME") + "/.config/gcal/.venv/bin/python",
            Quickshell.env("HOME") + "/.config/gcal/gcal-remind.py"]
    }
    Timer {
        interval: 300000
        repeat: true
        running: panel.manageAgendaBackground
        triggeredOnStart: true
        onTriggered: agendaRemind.running = true
    }

    // Parked above the window (and so off-screen) when closed.
    readonly property real hiddenY: -height - 20
    y: isOpen ? openY : hiddenY

    Behavior on y {
        NumberAnimation {
            duration: 350
            easing.type: Easing.OutQuint
            // Stop rendering the panel only once the closing slide is done.
            onRunningChanged: {
                if (!running && !panel.isOpen)
                    panel.showPanel = false
            }
        }
    }

    onIsOpenChanged: {
        if (!isOpen)
            return
        showPanel = true
        // Fresh agenda for every open.
        agendaFile.reload()
        panel.refreshAgenda()
        if (!agendaSync.running)
            agendaSync.running = true

        // Auto-refresh "Today" if the date changed while Quickshell was running
        let now = new Date()
        if (now.getDate() !== todayDate || now.getMonth() !== todayMonth) {
            todayDate = now.getDate()
            todayMonth = now.getMonth()
            todayYear = now.getFullYear()

            currentMonth = todayMonth
            currentYear = todayYear
            updateCalendar(currentYear, currentMonth)
        }
    }

    // Swallow clicks that land on the card but not on one of its buttons, so
    // they do not fall through to the window-level MouseArea that closes the
    // panel.
    MouseArea {
        anchors.fill: parent
        anchors.margins: panel.cardInset
        acceptedButtons: Qt.LeftButton | Qt.RightButton
    }

    // --- REUSABLE COMPONENTS ---
    component ActionIcon: Button {
        property string iconTxt: ""
        property string iconSrc: ""
        implicitWidth: 28
        implicitHeight: 28
        background: Rectangle { color: "transparent" }
        contentItem: Item {
            Text {
                anchors.centerIn: parent
                text: iconTxt
                visible: iconSrc === ""
                color: Theme.primary
                font.family: "monospace"
                font.pixelSize: 18
                verticalAlignment: Text.AlignVCenter
                horizontalAlignment: Text.AlignHCenter
            }
            Image {
                anchors.centerIn: parent
                source: iconSrc
                width: 18
                height: 18
                sourceSize.width: 18
                sourceSize.height: 18
                visible: iconSrc !== ""
                fillMode: Image.PreserveAspectFit
                layer.enabled: iconSrc !== ""
                layer.effect: MultiEffect {
                    colorization: 1.0
                    colorizationColor: Theme.primary
                }
            }
        }
    }

    // Styled ML4W Button for the "Today" action
    component ML4WButton: Button {
        background: Rectangle {
            color: "transparent"
            border.color: Theme.primary
            border.width: 1
            radius: 8
        }
        contentItem: Text {
            text: parent.text
            font.family: Theme.fontFamily
            font.pixelSize: 12
            color: Theme.primary
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            padding: 4
            leftPadding: 10
            rightPadding: 10
        }
    }

    // --- CALENDAR LOGIC & DATA ---
    property var monthNames: ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    property var dayNames: ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]

    property int currentMonth: new Date().getMonth()
    property int currentYear: new Date().getFullYear()

    property int todayDate: new Date().getDate()
    property int todayMonth: new Date().getMonth()
    property int todayYear: new Date().getFullYear()

    ListModel { id: dayModel }
    ListModel { id: weekModel }

    Component.onCompleted: updateCalendar(currentYear, currentMonth)

    function prevMonth() {
        if (currentMonth === 0) {
            currentMonth = 11;
            currentYear--;
        } else {
            currentMonth--;
        }
        updateCalendar(currentYear, currentMonth);
    }

    function nextMonth() {
        if (currentMonth === 11) {
            currentMonth = 0;
            currentYear++;
        } else {
            currentMonth++;
        }
        updateCalendar(currentYear, currentMonth);
    }

    function updateCalendar(year, month) {
        dayModel.clear()
        weekModel.clear()

        let firstDay = new Date(year, month, 1)
        let startingDayOfWeek = firstDay.getDay()
        let startCell = startingDayOfWeek === 0 ? 6 : startingDayOfWeek - 1

        let daysInMonth = new Date(year, month + 1, 0).getDate()
        let daysInPrevMonth = new Date(year, month, 0).getDate()

        for (let row = 0; row < 6; row++) {
            let dateInRow = new Date(year, month, 1 + (row * 7) - startCell)
            let d = new Date(Date.UTC(dateInRow.getFullYear(), dateInRow.getMonth(), dateInRow.getDate()));
            d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay()||7));
            let yearStart = new Date(Date.UTC(d.getUTCFullYear(),0,1));
            let weekNo = Math.ceil(( ( (d - yearStart) / 86400000) + 1)/7);

            weekModel.append({ weekNumber: weekNo })
        }

        for (let i = 0; i < 42; i++) {
            if (i < startCell) {
                dayModel.append({ day: daysInPrevMonth - startCell + i + 1, isCurrentMonth: false, isToday: false })
            } else if (i >= startCell && i < startCell + daysInMonth) {
                let dayNum = i - startCell + 1
                let isTod = (dayNum === todayDate && month === todayMonth && year === todayYear)
                dayModel.append({ day: dayNum, isCurrentMonth: true, isToday: isTod })
            } else {
                dayModel.append({ day: i - startCell - daysInMonth + 1, isCurrentMonth: false, isToday: false })
            }
        }
    }

    // ==========================================
    // MAIN PANEL BACKGROUND
    // ==========================================
    Item {
        anchors.fill: parent
        anchors.margins: panel.cardInset

        RectangularShadow {
            id: shadow
            anchors.fill: mainBgRect
            radius: mainBgRect.radius
            blur: 15
            color: Qt.rgba(Theme.shadow.r, Theme.shadow.g, Theme.shadow.b, 0.4)
        }

        Rectangle {
            id: mainBgRect
            anchors.fill: parent
            radius: 10
            opacity: 0.95 // Only the background is transparent

            // Gradient border (outer)
            gradient: Gradient {
                orientation: Gradient.Vertical
                GradientStop { position: 0.0; color: Theme.primary }
                GradientStop { position: 1.0; color: Theme.on_primary }
            }

            // Background fill (inner), inset by the border thickness
            Rectangle {
                anchors.fill: parent
                anchors.margins: 2
                radius: parent.radius - anchors.margins
                color: Theme.background
            }
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 15

            // --- HEADER: MONTH NAVIGATION & TODAY BUTTON ---
            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 30

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 5

                    ActionIcon {
                        iconSrc: "../shared/icons/chevron-left.svg"
                        onClicked: prevMonth()
                    }

                    Text {
                        Layout.preferredWidth: 120
                        text: monthNames[currentMonth] + " " + currentYear
                        color: Theme.primary
                        font.family: Theme.fontFamily
                        font.pixelSize: 18
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                    }

                    ActionIcon {
                        iconSrc: "../shared/icons/chevron-right.svg"
                        onClicked: nextMonth()
                    }
                }

                ML4WButton {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Today"

                    opacity: (currentMonth !== todayMonth || currentYear !== todayYear) ? 1.0 : 0.0
                    enabled: opacity > 0

                    Behavior on opacity { NumberAnimation { duration: 250; easing.type: Easing.InOutQuad } }

                    onClicked: {
                        currentMonth = todayMonth;
                        currentYear = todayYear;
                        updateCalendar(currentYear, currentMonth);
                    }
                }
            }

            Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.primary; opacity: 0.3 }

            // --- CALENDAR BODY ---
            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 15

                ColumnLayout {
                    Layout.fillHeight: true
                    spacing: 5

                    Text {
                        Layout.fillWidth: true
                        text: "Wk"
                        color: Theme.on_background
                        opacity: 0.5
                        font.family: Theme.fontFamily
                        font.pixelSize: 13
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        Layout.bottomMargin: 5
                    }

                    Repeater {
                        model: weekModel
                        Text {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            text: model.weekNumber
                            color: Theme.primary
                            opacity: 0.7
                            font.family: Theme.fontFamily
                            font.pixelSize: 13
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }

                Rectangle { Layout.fillHeight: true; implicitWidth: 1; color: Theme.primary; opacity: 0.3 }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 300
                    spacing: 5

                    RowLayout {
                        Layout.fillWidth: true
                        Repeater {
                            model: panel.dayNames
                            Text {
                                Layout.fillWidth: true
                                text: modelData
                                color: Theme.primary
                                font.family: Theme.fontFamily
                                font.pixelSize: 14
                                font.bold: true
                                horizontalAlignment: Text.AlignHCenter
                            }
                        }
                    }

                    GridLayout {
                        columns: 7
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        rowSpacing: 5
                        columnSpacing: 5

                        Repeater {
                            model: dayModel

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                radius: width / 2
                                color: model.isToday ? Theme.primary : "transparent"

                                Text {
                                    anchors.centerIn: parent
                                    text: model.day
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 14
                                    font.bold: model.isToday
                                    color: model.isToday ? Theme.background : Theme.on_background
                                    opacity: (model.isCurrentMonth || model.isToday) ? 1.0 : 0.3
                                }
                            }
                        }
                    }
                }

                Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.primary; opacity: 0.3 }

                // --- AGENDA: upcoming Google events + open tasks ---
                ColumnLayout {
                    Layout.preferredWidth: 270
                    Layout.fillHeight: true
                    spacing: 4

                    Text {
                        text: "Upcoming"
                        color: Theme.primary
                        font.family: Theme.fontFamily
                        font.pixelSize: 14
                        font.bold: true
                    }

                    Text {
                        Layout.fillWidth: true
                        visible: panel.agendaError !== "" || panel.agendaStale
                        text: panel.agendaError !== "" ? panel.agendaError : "Calendar cache stale · refresh pending"
                        color: Theme.on_background
                        font.family: Theme.fontFamily
                        font.pixelSize: 12
                        elide: Text.ElideRight
                    }

                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 60
                        clip: true
                        model: panel.agendaEvents.slice(0, 8)
                        delegate: RowLayout {
                            width: ListView.view.width
                            spacing: 8
                            Text {
                                Layout.preferredWidth: 118
                                text: {
                                    if (modelData.allDay)
                                        return panel.allDayLabel(modelData.start)
                                    return Qt.formatDateTime(new Date(modelData.start), "ddd d MMM · hh:mm")
                                }
                                color: Theme.on_background
                                font.family: Theme.fontFamily
                                font.pixelSize: 12
                                elide: Text.ElideRight
                            }
                            Text {
                                Layout.fillWidth: true
                                text: modelData.summary
                                color: Theme.primary
                                font.family: Theme.fontFamily
                                font.pixelSize: 13
                                elide: Text.ElideRight
                                HoverHandler { id: eventTitleHover }
                                ToolTip.text: modelData.summary
                                ToolTip.visible: eventTitleHover.hovered
                            }
                        }
                    }
                    Text {
                        visible: panel.agendaEvents.length === 0 && panel.agendaError === ""
                        text: "No upcoming events"
                        color: Theme.on_background
                        font.family: Theme.fontFamily
                        font.pixelSize: 12
                    }

                    Text {
                        text: "Tasks"
                        color: Theme.primary
                        font.family: Theme.fontFamily
                        font.pixelSize: 14
                        font.bold: true
                    }

                    ListView {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.min(3, panel.agendaTasks.length) * 24
                        clip: true
                        model: panel.agendaTasks.slice(0, 6)
                        delegate: RowLayout {
                            width: ListView.view.width
                            height: 24
                            spacing: 8
                            Text {
                                text: "○"
                                color: Theme.on_background
                                font.family: Theme.fontFamily
                                font.pixelSize: 12
                            }
                            Text {
                                Layout.fillWidth: true
                                text: modelData.title
                                    + (modelData.due ? "  ·  " + Qt.formatDate(new Date(modelData.due), "d MMM") : "")
                                color: Theme.primary
                                font.family: Theme.fontFamily
                                font.pixelSize: 13
                                elide: Text.ElideRight
                                HoverHandler { id: taskTitleHover }
                                ToolTip.text: modelData.title
                                ToolTip.visible: taskTitleHover.hovered
                            }
                        }
                    }
                    Text {
                        visible: panel.agendaTasks.length === 0
                        text: "No open tasks"
                        color: Theme.on_background
                        font.family: Theme.fontFamily
                        font.pixelSize: 12
                    }
                }
            }
        }
    }
}
