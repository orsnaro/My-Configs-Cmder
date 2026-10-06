import QtQml

// Hover opens temporarily; a click pins the metrics panel until a second
// click, an outside click or Escape. Delayed hover-close signals cannot
// dismiss a pinned panel.
QtObject {
    property bool isOpen: false
    property bool pinned: false

    function hoverOpen(): void {
        if (!pinned)
            isOpen = true
    }
    function hoverClose(): void {
        if (!pinned)
            isOpen = false
    }
    function toggle(): void {
        if (pinned) {
            close()
        } else {
            pinned = true
            isOpen = true
        }
    }
    function close(): void {
        pinned = false
        isOpen = false
    }
}
