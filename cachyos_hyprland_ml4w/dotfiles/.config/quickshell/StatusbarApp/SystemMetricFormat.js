function memory(used, total) {
    if (used === null || used === undefined || total === null || total === undefined)
        return "—"
    return Number(used).toFixed(1) + " / " + Number(total).toFixed(1) + " GiB"
}
function memoryUsed(used) {
    if (used === null || used === undefined)
        return "—"
    return Number(used).toFixed(1) + " GiB"
}
