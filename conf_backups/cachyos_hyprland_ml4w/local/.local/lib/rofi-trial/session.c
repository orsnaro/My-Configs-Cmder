/* Shared identity verification and on-demand launch/toggle; no desktop surfaces. */
#define _GNU_SOURCE
#include "session.h"
#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <json-c/json.h>
#include <limits.h>
#include <poll.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static void initialize(struct launcher_session *session) {
    *session = (struct launcher_session){.pidfd = -1};
}

void session_close(struct launcher_session *session) {
    if (session->pidfd >= 0) close(session->pidfd);
    free(session->pidfile);
    free(session->runtime);
    initialize(session);
}

static bool valid_mode(const char *mode) {
    const char *modes[] = {"apps", "run", "calc", "emoji", "files", "clipboard"};
    for (size_t i = 0; i < sizeof(modes)/sizeof(*modes); i++)
        if (strcmp(mode, modes[i]) == 0) return true;
    return false;
}

static pid_t parse_pid(const char *value) {
    if (!isdigit((unsigned char)*value)) return -1;
    char *end;
    errno = 0;
    long number = strtol(value, &end, 10);
    return !errno && !*end && number > 1 && number <= INT_MAX ? (pid_t)number : -1;
}

static int private_directory(const char *path) {
    if (!path || path[0] != '/' || path[strlen(path)-1] == '/') return -1;
    int fd = open(path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    struct stat status;
    if (fd >= 0 && fstat(fd, &status) == 0 && status.st_uid == getuid() && !(status.st_mode & 077)) return fd;
    if (fd >= 0) close(fd);
    return -1;
}

/* Nonblocking + no-follow prevents FIFOs and symlinks from becoming reads/writes. */
static int regular_file(int directory, const char *name, int flags) {
    int fd = openat(directory, name, flags | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC, 0600);
    if (fd < 0) return -1;
    struct stat status;
    if (fstat(fd, &status) == 0 && S_ISREG(status.st_mode) && status.st_uid == getuid() && status.st_nlink == 1) return fd;
    close(fd);
    errno = EINVAL;
    return -1;
}

static int read_text(int directory, const char *name, char *value, size_t capacity) {
    int fd = regular_file(directory, name, O_RDONLY);
    if (fd < 0) return errno == ENOENT ? 1 : 2;
    ssize_t length = read(fd, value, capacity);
    close(fd);
    if (length < 0 || (size_t)length == capacity || memchr(value, '\0', (size_t)length)) return 2;
    while (length > 0 && (value[length-1] == '\n' || value[length-1] == ' ')) length--;
    value[length] = '\0';
    return 0;
}

static bool valid_monitor(const char *value) {
    if (!*value || strlen(value) > 255) return false;
    for (; *value; value++) if (iscntrl((unsigned char)*value)) return false;
    return true;
}

static bool alive(int pidfd) {
    struct pollfd file = {pidfd, POLLIN, 0};
    return poll(&file, 1, 0) == 0;
}

int session_from_pid(pid_t pid, struct launcher_session *session) {
    initialize(session);
    if (pid <= 1) return 2;
    session->pidfd = (int)syscall(SYS_pidfd_open, pid, 0);
    if (session->pidfd < 0) return errno == ESRCH ? 1 : 2;
    session->pid = pid;
    char path[64], executable[PATH_MAX], arguments[32768];
    struct stat status;
    snprintf(path, sizeof(path), "/proc/%d", pid);
    if (stat(path, &status) < 0) return 1;
    if (status.st_uid != getuid()) return 2;
    snprintf(path, sizeof(path), "/proc/%d/exe", pid);
    ssize_t size = readlink(path, executable, sizeof(executable)-1);
    if (size < 0) return errno == ENOENT ? 1 : 2;
    executable[size] = '\0';
    const char *base = strrchr(executable, '/');
    if (!base || strcmp(base+1, "rofi") != 0) return 2;
    snprintf(path, sizeof(path), "/proc/%d/cmdline", pid);
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    size = fd < 0 ? -1 : read(fd, arguments, sizeof(arguments));
    if (fd >= 0) close(fd);
    if (size <= 0 || size == sizeof(arguments) || arguments[size-1] != '\0') return 2;
    const char *pidfile = NULL;
    for (size_t offset = 0; offset < (size_t)size;) {
        const char *argument = arguments+offset;
        offset += strlen(argument)+1;
        if (strcmp(argument, "-pid") != 0) continue;
        if (pidfile || offset >= (size_t)size || arguments[offset] != '/') return 2;
        pidfile = arguments+offset;
        offset += strlen(pidfile)+1;
    }
    if (!pidfile) return 2;
    const char *slash = strrchr(pidfile, '/');
    if (!slash || strcmp(slash+1, "rofi.pid") != 0) return 2;
    session->runtime = strndup(pidfile, (size_t)(slash-pidfile));
    session->pidfile = strdup(pidfile);
    if (!session->runtime || !session->pidfile) return 2;
    int directory = private_directory(session->runtime);
    if (directory < 0) return 2;
    char value[4096];
    bool valid = read_text(directory, "rofi.pid", value, sizeof(value)) == 0 && parse_pid(value) == pid;
    valid = valid && read_text(directory, "mode", value, sizeof(value)) == 0 && valid_mode(value);
    valid = valid && read_text(directory, "monitor", value, sizeof(value)) == 0 && valid_monitor(value);
    close(directory);
    if (!alive(session->pidfd)) return 1;
    return valid ? 0 : 2;
}

int session_from_pidfile(const char *pidfile, struct launcher_session *session) {
    initialize(session);
    const char *slash = pidfile ? strrchr(pidfile, '/') : NULL;
    if (!slash || pidfile[0] != '/' || strcmp(slash+1, "rofi.pid") != 0) return 2;
    char *runtime = strndup(pidfile, (size_t)(slash-pidfile));
    if (!runtime) return 2;
    int directory = private_directory(runtime);
    free(runtime);
    if (directory < 0) return 2;
    char value[64];
    int result = read_text(directory, "rofi.pid", value, sizeof(value));
    close(directory);
    if (result) return result;
    if (!*value) return 1; /* Rofi may still be writing its just-created file. */
    pid_t pid = parse_pid(value);
    if (pid < 0) return 2;
    result = session_from_pid(pid, session);
    if (result == 0 && strcmp(session->pidfile, pidfile) != 0) return 2;
    return result;
}

static long milliseconds(void) {
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    return now.tv_sec*1000 + now.tv_nsec/1000000;
}

/* Drain bounded output while waiting; a wedged IPC child cannot hold startup. */
int session_command(char *const argv[], char *output, size_t capacity) {
    int pipefd[2];
    if (capacity < 2 || pipe2(pipefd, O_CLOEXEC) < 0) return 2;
    pid_t child = fork();
    if (child == 0) {
        if (dup2(pipefd[1], STDOUT_FILENO) < 0) _exit(127);
        close(pipefd[0]);
        close(pipefd[1]);
        close(9); /* The startup lock belongs to the wrapper/watcher only. */
        execvp(argv[0], argv);
        _exit(127);
    }
    close(pipefd[1]);
    if (child < 0) { close(pipefd[0]); return 2; }
    fcntl(pipefd[0], F_SETFL, O_NONBLOCK);
    int childfd = (int)syscall(SYS_pidfd_open, child, 0);
    size_t used = 0;
    int status = 0, result = 2;
    long deadline = milliseconds()+3000;
    while (milliseconds() < deadline) {
        ssize_t size;
        while ((size = read(pipefd[0], output+used, capacity-1-used)) > 0) {
            used += (size_t)size;
            if (used == capacity-1) goto done;
        }
        if (waitpid(child, &status, WNOHANG) == child) {
            child = -1;
            /* The child's last write may have raced the preceding read. */
            while ((size = read(pipefd[0], output+used, capacity-1-used)) > 0) {
                used += (size_t)size;
                if (used == capacity-1) goto done;
            }
            if (WIFEXITED(status) && WEXITSTATUS(status) == 0) result = 0;
            break;
        }
        struct pollfd files[] = {{pipefd[0], POLLIN, 0}, {childfd, POLLIN, 0}};
        long remaining = deadline-milliseconds();
        if (poll(files, 2, remaining > 0 ? (int)remaining : 0) < 0 && errno != EINTR) break;
    }
done:
    if (child > 0) {
        kill(child, SIGKILL);
        while (waitpid(child, &status, 0) < 0 && errno == EINTR) {}
    }
    if (childfd >= 0) close(childfd);
    close(pipefd[0]);
    output[used] = '\0';
    return result;
}

int session_ipc(const char *action, pid_t pid) {
    if (pid <= 1 || (strcmp(action, "register") != 0 && strcmp(action, "unregister") != 0)) return 2;
    char code[256], output[4096];
    snprintf(code, sizeof(code), "assert(rofi_trial_session and rofi_trial_session.%s(%d) ~= false, 'Rofi session integration missing; reload config')", action, pid);
    char *command[] = {"hyprctl", "eval", code, NULL};
    if (session_command(command, output, sizeof(output)) != 0) return 2;
    size_t length = strlen(output);
    while (length && isspace((unsigned char)output[length-1])) output[--length] = '\0';
    return strcmp(output, "ok") == 0 ? 0 : 2;
}

static int write_metadata(int directory, const char *name, const char *value) {
    int fd = regular_file(directory, name, O_WRONLY | O_CREAT);
    if (fd < 0) return 2;
    size_t length = strlen(value);
    int result = ftruncate(fd, 0) == 0 && write(fd, value, length) == (ssize_t)length && write(fd, "\n", 1) == 1 ? 0 : 2;
    close(fd);
    return result;
}

int session_toggle(const char *mode, const char *runtime) {
    int result = 2;
    if (!valid_mode(mode)) return 2;
    int directory = private_directory(runtime);
    if (directory < 0) return 2;
    char *pidfile = NULL;
    if (asprintf(&pidfile, "%s/rofi.pid", runtime) < 0) { close(directory); return 2; }
    struct launcher_session session;
    int identity = session_from_pidfile(pidfile, &session);
    char value[4096];
    if (identity == 2) goto done;
    if (identity == 0) {
        bool same = read_text(directory, "mode", value, sizeof(value)) == 0 && strcmp(value, mode) == 0;
        if (syscall(SYS_pidfd_send_signal, session.pidfd, SIGTERM, NULL, 0) < 0 && errno != ESRCH) goto done;
        struct pollfd file = {session.pidfd, POLLIN, 0};
        int waited;
        do { waited = poll(&file, 1, 4000); } while (waited < 0 && errno == EINTR);
        if (waited <= 0) goto done;
        if (same) { result = 0; goto done; }
    }
    /* Refuse unsafe existing files before starting IPC or touching metadata. */
    const char *names[] = {"mode", "monitor"};
    for (size_t i = 0; i < sizeof(names)/sizeof(*names); i++)
        if (read_text(directory, names[i], value, sizeof(value)) == 2) goto done;
    char output[65536];
    char *command[] = {"hyprctl", "-j", "monitors", NULL};
    if (session_command(command, output, sizeof(output)) != 0) goto done;
    struct json_object *monitors = json_tokener_parse(output);
    char *monitor = NULL;
    if (monitors && json_object_is_type(monitors, json_type_array)) {
        for (size_t i = 0; i < json_object_array_length(monitors); i++) {
            struct json_object *row = json_object_array_get_idx(monitors, i), *focused, *name;
            if (json_object_object_get_ex(row, "focused", &focused) && json_object_is_type(focused, json_type_boolean)
                && json_object_get_boolean(focused) && json_object_object_get_ex(row, "name", &name)
                && json_object_is_type(name, json_type_string) && valid_monitor(json_object_get_string(name))) {
                monitor = strdup(json_object_get_string(name));
                break;
            }
        }
    }
    if (monitors) json_object_put(monitors);
    if (monitor) {
        if (write_metadata(directory, "monitor", monitor) == 0 && write_metadata(directory, "mode", mode) == 0) {
            puts(pidfile);
            result = 10;
        }
        free(monitor);
    }
done:
    if (result == 2) fprintf(stderr, "Launcher session: invalid/unsafe metadata, foreign process, or failed compositor IPC\n");
    session_close(&session);
    free(pidfile);
    close(directory);
    return result;
}
