---
title: "No timeout handling"
author: Maxim Menshikov
layout: defect
permalink: /fn/timing/unbound
arch:
   - native
vulnerability:
   - Low
ddos:
   - Medium
group_full: fn.timing
group:
   - fn
   - timing
---
The operation might block forever

# Impact

A blocking operation is performed with no upper bound on how long it may wait. A
socket `recv`, a `connect`, a lock acquisition, a `read` from a pipe, a condition
variable wait, or a `join` is issued in its indefinitely-blocking form. If the
event it waits for never arrives — a peer that stops sending, a connection that
hangs half-open, a producer that died, a lock whose holder never releases — the
calling thread is parked forever. It makes no progress, never returns, and holds
whatever resources it owns (a connection slot, a mutex, a thread from the pool) for
the lifetime of the process.

In a server this silently consumes a worker per stuck operation; enough of them
and the service stops accepting work even though nothing has "crashed."

# Vulnerability potential

The unbounded wait is a denial-of-service primitive.

1. **Resource exhaustion.** An attacker who can make operations hang — opening
   connections and never completing the handshake (slowloris-style), or sending a
   request and stalling mid-stream — pins one worker per connection. With a bounded
   thread/connection pool, a handful of stalled peers can exhaust it and block all
   legitimate clients.
2. **Deadlock amplification.** An unbounded lock wait behind a resource the
   attacker can hold (or that another stuck thread holds) can cascade into a
   system-wide stall.

It does not itself corrupt memory or cross a trust boundary, so the vulnerability
rating is `Low`; the hang/exhaustion behaviour gives a `Medium` DoS rating.

# Technical details

## Blocking calls without a deadline
By default, sockets are blocking: `recv`/`accept`/`connect` wait until data, a
connection, or a (long, OS-dependent) TCP timeout. `pthread_mutex_lock`,
`pthread_cond_wait`, and `std::condition_variable::wait` (no-predicate, no
timeout) wait forever. `read` on a pipe/FIFO blocks until a writer appears.

## The timed alternatives exist
Almost every blocking primitive has a bounded variant that this defect ignores:
`SO_RCVTIMEO`/`SO_SNDTIMEO` and `poll`/`select`/`epoll` with a timeout for sockets;
`pthread_mutex_timedlock`, `pthread_cond_timedwait`,
`cv.wait_for`/`wait_until` for synchronization; `O_NONBLOCK` plus a timed `poll`
for pipes. Using the unbounded form where external/peer input controls completion
is the flagged condition.

## TCP nuance
Even "blocking" sockets eventually time out at the TCP layer, but the keep-alive /
retransmission timeout is minutes-long and not application-controlled, so it does
not bound application latency in any useful way — a half-open connection can wedge
a worker for a very long time.

# Catching the issue

## Static analysis
The analyzer emitting this diagnostic flags blocking calls reachable from
request-handling code that lack a timeout/deadline. Review rules can require every
external wait to carry an explicit timeout.

## Design
Set socket timeouts (`SO_RCVTIMEO`/`SO_SNDTIMEO`) or drive all I/O through
`poll`/`epoll`/`select` with a deadline. Use timed lock/condition-variable
variants and handle the timeout branch (back off, abort, log). Apply an overall
per-request deadline and cancel work that exceeds it.

## Runtime observability
A watchdog that samples worker liveness, plus metrics on operation latency, expose
threads stuck in unbounded waits before the pool is fully drained.

# How to reproduce

Run this against a port where nothing ever sends data (e.g. a peer that accepts
then stays silent). The blocking `recv` has no timeout and the program hangs
forever instead of returning.

```c
#include <stdio.h>
#include <string.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <unistd.h>

int main(void)
{
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in a = {0};
    a.sin_family = AF_INET;
    a.sin_port   = htons(9);              /* discard port: accepts, never replies */
    inet_pton(AF_INET, "127.0.0.1", &a.sin_addr);

    if (connect(fd, (struct sockaddr *)&a, sizeof a) == 0) {
        char buf[256];
        /* No SO_RCVTIMEO and no poll(): this recv blocks indefinitely. */
        ssize_t n = recv(fd, buf, sizeof buf, 0);
        printf("got %zd bytes\n", n);     /* never reached */
    }
    close(fd);
    return 0;
}
```
