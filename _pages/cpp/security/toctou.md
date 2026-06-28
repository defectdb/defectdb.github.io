---
title: "Time-of-check / time-of-use race"
author: Maxim Menshikov
layout: defect
permalink: /cpp/security/toctou
arch:
   - native
vulnerability:
   - High
ddos:
   - Medium
group_full: cpp.security
group:
   - cpp
   - security
---
A filesystem property was checked (access / stat / exists) and the same path was used in a subsequent open / read / unlink call; an attacker can swap the file between the two operations

# Impact

The program decides whether an operation is safe by inspecting a path
(`access`, `stat`, `std::filesystem::exists`, an ownership/permission check)
and then performs the real operation (`open`, `read`, `unlink`, `chmod`,
`exec`) on that **same path** a moment later. Between the check and the use the
binding from name to inode is not held: in a shared or attacker-writable
directory the adversary can replace the path — swap a regular file for a
symlink, or point it at `/etc/passwd` — so the check passes on a benign target
while the action lands on a sensitive one. The result is reading, writing,
deleting, or executing a file the program never validated.

# Vulnerability potential

This is a real, frequently exploited security flaw (CWE-367).

1. **Privilege escalation via symlink.** A setuid or daemon process checks
   `access(path, W_OK)` (which uses the real UID) and then `open`s the path. An
   attacker swaps `path` for a symlink to a root-owned file between the calls,
   and the privileged `open` writes where the check never looked.
2. **Arbitrary file overwrite / disclosure.** Predictable temp-file names in
   `/tmp` plus an exists-then-create pattern let an attacker pre-create or
   redirect the target, causing the program to truncate or reveal an arbitrary
   file.
3. **Deletion / unlink races.** Check-then-`unlink` lets an attacker steer the
   removal at a different file, enabling tampering or denial of service.
4. **Repeated forced failures** of the privileged operation (or filling the
   raced directory) give a denial-of-service angle, hence the non-trivial DoS
   rating; the integrity/privilege impact is the dominant one.

# Technical details

## Why the race exists

A pathname is resolved fresh on every syscall. `stat("p")` and `open("p")` each
walk the directory tree independently, so nothing guarantees they resolve to
the same inode. The attacker's job is only to win the timing window, which can
be widened with filesystem-contention tricks and retried indefinitely.

## The fix: operate on handles, not names

Resolve the name **once** to a kernel object and operate on that object:
`open` the file first, then `fstat`/`fchmod`/`fchown` the returned descriptor
so check and use refer to the identical inode. Use `O_NOFOLLOW` to reject
symlinks, `O_EXCL | O_CREAT` for exclusive creation, and the `*at` family
(`openat`, `unlinkat`, `fstatat` with `AT_SYMLINK_NOFOLLOW`) anchored to a
directory descriptor to defeat path-component swaps. `access()` for an
authorization decision is essentially always wrong — that is what CWE-367
exists to flag.

## std::filesystem caveat

`std::filesystem::exists`/`is_regular_file` followed by `std::ifstream(path)`
is the same anti-pattern in modern dress; the portable library offers no atomic
check-and-open, so the descriptor-based POSIX primitives are still required for
security-sensitive code.

# Catching the issue

## Static analysis

clang-tidy `android-cloexec-*` and the CERT checks (`cert-fio01-c`,
"be careful using functions that use file names for identification"), Coverity's
TOCTOU checker, and CodeQL's `cpp/toctou-race-condition` query flag
check-then-use pairs on the same path.

## Compiler / fortify

GCC's `-Wformat`/`_FORTIFY_SOURCE` will not catch this, but
`-Wanalyzer-fd-*`-style GCC static analyzer warnings and `clang --analyze`
report some patterns.

## Review rule

Treat any `access()`/`stat()`/`exists()` whose result gates a later
filesystem operation on the same name as a defect; require descriptor-based
re-checks (`fstat` on an already-open fd) and `O_NOFOLLOW`/`openat` instead.

# How to reproduce

The check and use race; run the loop under contention (a second process
swapping `data.txt` between a regular file and a symlink to a protected file)
and the privileged open follows the attacker's symlink.

```cpp
#include <unistd.h>
#include <fcntl.h>
#include <cstdio>

// Runs with elevated privileges. BUG: access() checks one inode,
// open() may resolve the name to a different inode an instant later.
void write_user_file(const char* path, const char* data, size_t n) {
    if (access(path, W_OK) != 0)       // time of check (real UID)
        return;                        // attacker swaps `path` here
    int fd = open(path, O_WRONLY);     // time of use -> may be a symlink
    if (fd >= 0) { write(fd, data, n); close(fd); }
}

// Correct: resolve once, reject symlinks, act on the descriptor.
void write_user_file_safe(const char* path, const char* data, size_t n) {
    int fd = open(path, O_WRONLY | O_NOFOLLOW);
    if (fd < 0) return;
    if (faccessat(fd, "", W_OK, AT_EMPTY_PATH) == 0)
        write(fd, data, n);
    close(fd);
}

int main() {
    write_user_file("data.txt", "x", 1);
}
```
