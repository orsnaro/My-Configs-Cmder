/* On-demand verified compositor registration and blocking PID lifetime watch. */
#define _GNU_SOURCE
#include "session.h"
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

static pid_t parse_pid(const char *value) {
    char *end;
    errno = 0;
    long pid = strtol(value, &end, 10);
    return !errno && *value && !*end && pid > 1 && pid <= INT_MAX ? (pid_t)pid : -1;
}

static int signal_session(const struct launcher_session *session) {
    return syscall(SYS_pidfd_send_signal, session->pidfd, SIGTERM, NULL, 0) == 0 || errno == ESRCH ? 0 : 2;
}

static double seconds(void) {
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    return now.tv_sec + now.tv_nsec/1e9;
}

int main(int argc, char **argv) {
    if (argc == 4 && strcmp(argv[1], "--toggle") == 0) return session_toggle(argv[2], argv[3]);
    if (argc == 3 && (strcmp(argv[1], "--dismiss") == 0 || strcmp(argv[1], "--adopt") == 0)) {
        pid_t pid = parse_pid(argv[2]);
        if (pid < 0) return 2;
        struct launcher_session session;
        int result = session_from_pid(pid, &session);
        if (result == 0) result = strcmp(argv[1], "--dismiss") == 0 ? signal_session(&session) : session_ipc("register", pid);
        else result = 0; /* Invalid, stale and foreign targets are a safe no-op. */
        session_close(&session);
        return result;
    }
    if ((argc != 4 && argc != 5) || !*argv[2] || parse_pid(argv[3]) < 0) {
        fprintf(stderr, "Usage: dismiss-guard PIDFILE OUTPUT OWNER_PID [STARTUP_FD]\n");
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
    int owner = (int)syscall(SYS_pidfd_open, parse_pid(argv[3]), 0);
    if (owner < 0) return errno == ESRCH ? 0 : 2;
    struct launcher_session session = {.pidfd = -1};
    double deadline = seconds()+30;
    int identity = 1;
    while (seconds() < deadline) {
        struct pollfd file = {owner, POLLIN, 0};
        if (poll(&file, 1, 0) > 0) { close(owner); return 0; }
        identity = session_from_pidfile(argv[1], &session);
        if (identity != 1) break;
        session_close(&session);
        if (poll(&file, 1, 10) > 0) { close(owner); return 0; }
    }
    close(owner);
    if (identity != 0) {
        fprintf(stderr, "Dismiss guard: PID file is not this launcher, or startup expired\n");
        session_close(&session);
        return 2;
    }
    if (session_ipc("register", session.pid) != 0) {
        fprintf(stderr, "Dismiss guard: session registration failed; install rofi_session.lua and reload config\n");
        signal_session(&session);
        session_close(&session);
        return 2;
    }
    if (startup_fd >= 0) close(startup_fd);
    struct pollfd file = {session.pidfd, POLLIN, 0};
    int waited;
    do { waited = poll(&file, 1, -1); } while (waited < 0 && errno == EINTR);
    int result = session_ipc("unregister", session.pid);
    session_close(&session);
    return waited < 0 ? 2 : result;
}
