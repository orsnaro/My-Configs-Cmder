// vitreus-inhibit: holds a Wayland idle inhibitor until it is killed (Caffeine under pleamar-wm, whose own idle timer hypridle cannot stop).
// Build: wayland-scanner client-header P idle-inhibit.h && wayland-scanner private-code P idle-inhibit.c && gcc -O2 -o ~/.local/bin/vitreus-inhibit vitreus-inhibit.c idle-inhibit.c $(pkg-config --cflags --libs wayland-client)
// with P = /usr/share/wayland-protocols/unstable/idle-inhibit/idle-inhibit-unstable-v1.xml
#include <wayland-client.h>
#include <string.h>
#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include "idle-inhibit.h"
static struct wl_compositor *comp; static struct zwp_idle_inhibit_manager_v1 *mgr;
static void reg(void *d, struct wl_registry *r, uint32_t n, const char *i, uint32_t v) {
    if (!strcmp(i, "wl_compositor")) comp = wl_registry_bind(r, n, &wl_compositor_interface, 1);
    else if (!strcmp(i, zwp_idle_inhibit_manager_v1_interface.name)) mgr = wl_registry_bind(r, n, &zwp_idle_inhibit_manager_v1_interface, 1);
}
static void rem(void *d, struct wl_registry *r, uint32_t n) {}
static const struct wl_registry_listener rl = { reg, rem };
int main(void) {
    // Not holding on to whoever started it: the shell waits for its output to close before it hears the command is done.
    int null = open("/dev/null", O_RDWR);
    if (null >= 0) { dup2(null, 0); dup2(null, 1); dup2(null, 2); }
    struct wl_display *d = wl_display_connect(NULL);
    if (!d) { fprintf(stderr, "no display\n"); return 1; }
    struct wl_registry *r = wl_display_get_registry(d);
    wl_registry_add_listener(r, &rl, NULL);
    wl_display_roundtrip(d);
    if (!comp || !mgr) { fprintf(stderr, "no idle-inhibit\n"); return 1; }
    struct wl_surface *s = wl_compositor_create_surface(comp);
    zwp_idle_inhibit_manager_v1_create_inhibitor(mgr, s);
    wl_surface_commit(s);
    while (wl_display_dispatch(d) != -1) {}
    return 0;
}
