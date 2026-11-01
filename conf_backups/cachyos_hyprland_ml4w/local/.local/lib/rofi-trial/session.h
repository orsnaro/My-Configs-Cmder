#ifndef ROFI_TRIAL_SESSION_H
#define ROFI_TRIAL_SESSION_H

#include <sys/types.h>

struct launcher_session {
    pid_t pid;
    int pidfd;
    char *pidfile;
    char *runtime;
};

/* 0 = verified, 1 = absent/dead, 2 = invalid; close even unsuccessful outputs. */
int session_from_pid(pid_t pid, struct launcher_session *session);
int session_from_pidfile(const char *pidfile, struct launcher_session *session);
void session_close(struct launcher_session *session);
int session_toggle(const char *mode, const char *runtime);
int session_command(char *const argv[], char *output, size_t capacity);

#endif
