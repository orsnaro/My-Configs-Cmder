/* On-demand pointer-only guards for outputs not occupied by the Rofi picker. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <poll.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>
#include <signal.h>
#include <wayland-client.h>
#include "wlr-layer-shell-client.h"
#include "viewporter-client.h"
#include "session.h"

struct App;
struct Output {
    struct App *app;
    struct Output *next;
    uint32_t global;
    struct wl_output *wl;
    char *name;
    struct wl_surface *surface;
    struct zwlr_layer_surface_v1 *layer;
    struct wp_viewport *viewport;
};
struct App {
    struct wl_display *display;
    struct wl_registry *registry;
    struct wl_compositor *compositor;
    struct wl_shm *shm;
    struct wl_buffer *buffer;
    struct wl_seat *seat;
    struct wl_pointer *pointer;
    struct zwlr_layer_shell_v1 *shell;
    struct wp_viewporter *viewporter;
    struct Output *outputs;
    const char *excluded;
    int pidfd;
    bool initialized, running, failed;
};

static int pidfd_open_for(pid_t pid) { return (int)syscall(SYS_pidfd_open, pid, 0); }
static double seconds(void) {
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    return (double)now.tv_sec + now.tv_nsec / 1e9;
}
static pid_t parse_pid(const char *value) {
    char *end;
    errno = 0;
    long number = strtol(value, &end, 10);
    while (*end == '\n' || *end == ' ') end++;
    return !errno && !*end && number > 1 && number <= INT_MAX ? (pid_t)number : -1;
}

/* Open the descriptor before checking /proc, so a reused PID is never signaled. */
static int launcher_pidfd(const char *pidfile) {
    FILE *file = fopen(pidfile, "re");
    if (!file) return errno == ENOENT ? -1 : -2;
    char value[64] = {0};
    char *read = fgets(value, sizeof(value), file);
    fclose(file);
    if (!read || !*value) return -1;
    pid_t pid = parse_pid(value);
    if (pid < 0) return -2;
    int descriptor = pidfd_open_for(pid);
    if (descriptor < 0) return errno == ESRCH ? -1 : -2;
    char path[128], executable[PATH_MAX], arguments[32768];
    struct stat status;
    snprintf(path, sizeof(path), "/proc/%d", pid);
    bool valid = stat(path, &status) == 0 && status.st_uid == getuid();
    snprintf(path, sizeof(path), "/proc/%d/exe", pid);
    ssize_t size = readlink(path, executable, sizeof(executable)-1);
    if (size < 0) { close(descriptor); return -1; }
    executable[size] = '\0';
    const char *base = strrchr(executable, '/');
    valid = valid && base && strcmp(base+1, "rofi") == 0;
    snprintf(path, sizeof(path), "/proc/%d/cmdline", pid);
    file = fopen(path, "re");
    size_t length = file ? fread(arguments, 1, sizeof(arguments), file) : 0;
    if (file) fclose(file);
    bool matched = false;
    for (size_t offset = 0; offset < length && length < sizeof(arguments);) {
        size_t n = strnlen(arguments+offset, length-offset);
        if (n == 4 && memcmp(arguments+offset, "-pid", 4) == 0) {
            size_t next = offset+n+1;
            if (next < length && strnlen(arguments+next, length-next) == strlen(pidfile)
                && memcmp(arguments+next, pidfile, strlen(pidfile)) == 0) matched = true;
        }
        offset += n+1;
    }
    if (valid && matched) return descriptor;
    close(descriptor);
    fprintf(stderr, "Dismiss guard: PID file is not this launcher; refusing to signal it\n");
    return -2;
}

static void destroy_guard(struct Output *output) {
    if (output->layer) zwlr_layer_surface_v1_destroy(output->layer);
    if (output->viewport) wp_viewport_destroy(output->viewport);
    if (output->surface) wl_surface_destroy(output->surface);
    output->layer = NULL;
    output->viewport = NULL;
    output->surface = NULL;
}
static void configured(void *data, struct zwlr_layer_surface_v1 *layer,
                       uint32_t serial, uint32_t width, uint32_t height) {
    struct Output *output = data;
    if (!width || !height || width > INT_MAX || height > INT_MAX) {
        output->app->failed = true;
        output->app->running = false;
        return;
    }
    zwlr_layer_surface_v1_ack_configure(layer, serial);
    wp_viewport_set_destination(output->viewport, (int32_t)width, (int32_t)height);
    wl_surface_attach(output->surface, output->app->buffer, 0, 0);
    wl_surface_damage(output->surface, 0, 0, INT_MAX, INT_MAX);
    wl_surface_commit(output->surface);
}
static void closed(void *data, struct zwlr_layer_surface_v1 *layer) {
    destroy_guard(data);
}
static const struct zwlr_layer_surface_v1_listener layer_listener = {configured, closed};
static void create_guard(struct Output *output) {
    struct App *app = output->app;
    if (output->layer || !output->name || strcmp(output->name, app->excluded) == 0) return;
    output->surface = wl_compositor_create_surface(app->compositor);
    output->viewport = wp_viewporter_get_viewport(app->viewporter, output->surface);
    output->layer = zwlr_layer_shell_v1_get_layer_surface(
        app->shell, output->surface, output->wl,
        ZWLR_LAYER_SHELL_V1_LAYER_OVERLAY, "rofi-dismiss-guard");
    zwlr_layer_surface_v1_add_listener(output->layer, &layer_listener, output);
    zwlr_layer_surface_v1_set_size(output->layer, 0, 0);
    zwlr_layer_surface_v1_set_anchor(output->layer,
        ZWLR_LAYER_SURFACE_V1_ANCHOR_TOP | ZWLR_LAYER_SURFACE_V1_ANCHOR_BOTTOM |
        ZWLR_LAYER_SURFACE_V1_ANCHOR_LEFT | ZWLR_LAYER_SURFACE_V1_ANCHOR_RIGHT);
    zwlr_layer_surface_v1_set_exclusive_zone(output->layer, -1);
    zwlr_layer_surface_v1_set_keyboard_interactivity(output->layer, ZWLR_LAYER_SURFACE_V1_KEYBOARD_INTERACTIVITY_NONE);
    wl_surface_commit(output->surface);
}
static void output_geometry(void *data, struct wl_output *wl, int32_t x, int32_t y,
                            int32_t pw, int32_t ph, int32_t subpixel, const char *make,
                            const char *model, int32_t transform) {}
static void output_mode(void *data, struct wl_output *wl, uint32_t flags,
                        int32_t width, int32_t height, int32_t refresh) {}
static void output_done(void *data, struct wl_output *wl) {}
static void output_scale(void *data, struct wl_output *wl, int32_t scale) {}
static void output_name(void *data, struct wl_output *wl, const char *name) {
    struct Output *output = data;
    free(output->name);
    output->name = strdup(name);
    if (output->app->initialized) create_guard(output);
}
static void output_description(void *data, struct wl_output *wl, const char *description) {}
static const struct wl_output_listener output_listener = {
    output_geometry, output_mode, output_done, output_scale, output_name, output_description
};

static void pointer_enter(void *data, struct wl_pointer *pointer, uint32_t serial,
                          struct wl_surface *surface, wl_fixed_t x, wl_fixed_t y) {}
static void pointer_leave(void *data, struct wl_pointer *pointer, uint32_t serial, struct wl_surface *surface) {}
static void pointer_motion(void *data, struct wl_pointer *pointer, uint32_t time, wl_fixed_t x, wl_fixed_t y) {}
static void pointer_button(void *data, struct wl_pointer *pointer, uint32_t serial,
                           uint32_t time, uint32_t button, uint32_t state) {
    struct App *app = data;
    if (state == WL_POINTER_BUTTON_STATE_PRESSED) {
        if (syscall(SYS_pidfd_send_signal, app->pidfd, SIGTERM, NULL, 0) < 0 && errno != ESRCH)
            app->failed = true;
        app->running = false;
    }
}
static void pointer_axis(void *data, struct wl_pointer *pointer, uint32_t time, uint32_t axis, wl_fixed_t value) {}
static void pointer_frame(void *data, struct wl_pointer *pointer) {}
static void pointer_axis_source(void *data, struct wl_pointer *pointer, uint32_t source) {}
static void pointer_axis_stop(void *data, struct wl_pointer *pointer, uint32_t time, uint32_t axis) {}
static void pointer_axis_discrete(void *data, struct wl_pointer *pointer, uint32_t axis, int32_t discrete) {}
static const struct wl_pointer_listener pointer_listener = {
    .enter = pointer_enter, .leave = pointer_leave, .motion = pointer_motion,
    .button = pointer_button, .axis = pointer_axis, .frame = pointer_frame,
    .axis_source = pointer_axis_source, .axis_stop = pointer_axis_stop, .axis_discrete = pointer_axis_discrete
};
static void seat_capabilities(void *data, struct wl_seat *seat, uint32_t capabilities) {
    struct App *app = data;
    if ((capabilities & WL_SEAT_CAPABILITY_POINTER) && !app->pointer) {
        app->pointer = wl_seat_get_pointer(seat);
        wl_pointer_add_listener(app->pointer, &pointer_listener, app);
    } else if (!(capabilities & WL_SEAT_CAPABILITY_POINTER) && app->pointer) {
        wl_pointer_release(app->pointer);
        app->pointer = NULL;
    }
}
static void seat_name(void *data, struct wl_seat *seat, const char *name) {}
static const struct wl_seat_listener seat_listener = {seat_capabilities, seat_name};
static void global_added(void *data, struct wl_registry *registry, uint32_t name,
                         const char *interface, uint32_t version) {
    struct App *app = data;
    if (strcmp(interface, wl_compositor_interface.name) == 0)
        app->compositor = wl_registry_bind(registry, name, &wl_compositor_interface, 1);
    else if (strcmp(interface, wl_shm_interface.name) == 0)
        app->shm = wl_registry_bind(registry, name, &wl_shm_interface, 1);
    else if (strcmp(interface, zwlr_layer_shell_v1_interface.name) == 0)
        app->shell = wl_registry_bind(registry, name, &zwlr_layer_shell_v1_interface, version < 4 ? version : 4);
    else if (strcmp(interface, wp_viewporter_interface.name) == 0)
        app->viewporter = wl_registry_bind(registry, name, &wp_viewporter_interface, 1);
    else if (strcmp(interface, wl_seat_interface.name) == 0 && version >= 5 && !app->seat) {
        app->seat = wl_registry_bind(registry, name, &wl_seat_interface, 5);
        wl_seat_add_listener(app->seat, &seat_listener, app);
    } else if (strcmp(interface, wl_output_interface.name) == 0 && version >= 4) {
        struct Output *output = calloc(1, sizeof(*output));
        if (!output) { app->failed = true; app->running = false; return; }
        output->app = app;
        output->global = name;
        output->wl = wl_registry_bind(registry, name, &wl_output_interface, 4);
        output->next = app->outputs;
        app->outputs = output;
        wl_output_add_listener(output->wl, &output_listener, output);
    }
}
static void global_removed(void *data, struct wl_registry *registry, uint32_t name) {
    struct App *app = data;
    for (struct Output **next = &app->outputs; *next; next = &(*next)->next) {
        struct Output *output = *next;
        if (output->global != name) continue;
        *next = output->next;
        destroy_guard(output);
        wl_output_release(output->wl);
        free(output->name);
        free(output);
        return;
    }
}
static const struct wl_registry_listener registry_listener = {global_added, global_removed};
static void buffer_release(void *data, struct wl_buffer *buffer) {}
static const struct wl_buffer_listener buffer_listener = {buffer_release};
static bool create_buffer(struct App *app) {
    int fd = memfd_create("rofi-dismiss-transparent", MFD_CLOEXEC);
    if (fd < 0) return false;
    uint32_t transparent = 0;
    if (write(fd, &transparent, sizeof(transparent)) != sizeof(transparent)) { close(fd); return false; }
    struct wl_shm_pool *pool = wl_shm_create_pool(app->shm, fd, sizeof(transparent));
    app->buffer = wl_shm_pool_create_buffer(pool, 0, 1, 1, 4, WL_SHM_FORMAT_ARGB8888);
    wl_buffer_add_listener(app->buffer, &buffer_listener, app);
    wl_shm_pool_destroy(pool);
    close(fd);
    return true;
}

static void run(struct App *app) {
    int display_fd = wl_display_get_fd(app->display);
    while (app->running) {
        while (wl_display_prepare_read(app->display) != 0) {
            if (wl_display_dispatch_pending(app->display) < 0) { app->failed = true; return; }
            if (!app->running) return;
        }
        struct pollfd files[] = {{display_fd, POLLIN, 0}, {app->pidfd, POLLIN, 0}};
        if (wl_display_flush(app->display) < 0) {
            if (errno == EAGAIN) files[0].events |= POLLOUT;
            else { wl_display_cancel_read(app->display); app->failed = true; return; }
        }
        int result = poll(files, 2, -1);
        if (result < 0) {
            wl_display_cancel_read(app->display);
            if (errno == EINTR) continue;
            app->failed = true;
            return;
        }
        if (files[1].revents) { wl_display_cancel_read(app->display); return; }
        if (files[0].revents & POLLIN) {
            if (wl_display_read_events(app->display) < 0) { app->failed = true; return; }
        } else wl_display_cancel_read(app->display);
        if (files[0].revents & (POLLERR | POLLHUP | POLLNVAL)) { app->failed = true; return; }
        if (wl_display_dispatch_pending(app->display) < 0) { app->failed = true; return; }
    }
}
static void cleanup(struct App *app) {
    while (app->outputs) global_removed(app, app->registry, app->outputs->global);
    if (app->pointer) wl_pointer_release(app->pointer);
    if (app->seat) wl_seat_release(app->seat);
    if (app->buffer) wl_buffer_destroy(app->buffer);
    if (app->viewporter) wp_viewporter_destroy(app->viewporter);
    if (app->shell) {
        if (wl_proxy_get_version((struct wl_proxy *)app->shell) >= 3) zwlr_layer_shell_v1_destroy(app->shell);
        else wl_proxy_destroy((struct wl_proxy *)app->shell);
    }
    if (app->shm) wl_shm_destroy(app->shm);
    if (app->compositor) wl_compositor_destroy(app->compositor);
    if (app->registry) wl_registry_destroy(app->registry);
    if (app->display) wl_display_disconnect(app->display);
    close(app->pidfd);
}
int main(int argc, char **argv) {
    if (argc == 4 && strcmp(argv[1], "--toggle") == 0) return session_toggle(argv[2], argv[3]);
    if ((argc != 4 && argc != 5) || !*argv[2] || parse_pid(argv[3]) < 0) {
        fprintf(stderr, "Usage: dismiss-guard PIDFILE EXCLUDED_OUTPUT OWNER_PID [STARTUP_FD]\n");
        return 2;
    }
    int startup_fd = -1;
    if (argc == 5) {
        char *end;
        errno = 0;
        long value = strtol(argv[4], &end, 10);
        if (errno || end == argv[4] || *end || value < 3 || value > INT_MAX || fcntl((int)value, F_GETFD) < 0) {
            fprintf(stderr, "Dismiss guard: invalid startup descriptor\n");
            return 2;
        }
        startup_fd = (int)value;
    }
    int owner = pidfd_open_for(parse_pid(argv[3]));
    if (owner < 0) return errno == ESRCH ? 0 : 2;
    struct App app = {.excluded = argv[2], .pidfd = -1, .running = true};
    double deadline = seconds()+30;
    while (seconds() < deadline) {
        struct pollfd watched = {owner, POLLIN, 0};
        if (poll(&watched, 1, 20) > 0) { close(owner); return 0; }
        app.pidfd = launcher_pidfd(argv[1]);
        if (app.pidfd >= 0 || app.pidfd == -2) break;
    }
    close(owner);
    if (app.pidfd < 0) return 2;
    /* The wrapper closed its copy before launching Rofi. No picker/app inherits
       the lock, and later requests can toggle only after PID identity is known. */
    if (startup_fd >= 0) close(startup_fd);
    app.display = wl_display_connect(NULL);
    if (!app.display) { close(app.pidfd); return 2; }
    app.registry = wl_display_get_registry(app.display);
    wl_registry_add_listener(app.registry, &registry_listener, &app);
    if (wl_display_roundtrip(app.display) < 0 || wl_display_roundtrip(app.display) < 0) app.failed = true;
    bool found = false;
    for (struct Output *output = app.outputs; output; output = output->next)
        if (output->name && strcmp(output->name, app.excluded) == 0) found = true;
    if (!found || !app.compositor || !app.shm || !app.shell || !app.viewporter || !app.seat) app.failed = true;
    if (!app.failed && !create_buffer(&app)) app.failed = true;
    if (!app.failed) {
        app.initialized = true;
        for (struct Output *output = app.outputs; output; output = output->next) create_guard(output);
        run(&app);
    }
    if (app.failed) fprintf(stderr, "Dismiss guard: required Wayland output/protocol unavailable or connection failed\n");
    cleanup(&app);
    return app.failed ? 2 : 0;
}
