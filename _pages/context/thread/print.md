---
title: "Printing in thread"
author: Maxim Menshikov
layout: defect
permalink: /context/thread/print
arch:
   - native
vulnerability:
   - None
ddos:
   - Low
group_full: context.thread
group:
   - context
   - thread
---
Printing in a thread is not encouraged

# Impact

Writing to the standard output/error streams from a worker thread is discouraged
because the streams are a shared, serialized resource. Multiple threads printing
concurrently produce interleaved, hard-to-read output, and every call contends on
the stream's internal lock — turning logging into an unintended synchronization
point. If the thread is meant to be a fast hot path, the blocking, lock-protected
I/O can dominate its runtime and stall siblings waiting on the same `FILE`.

This is primarily a quality/design defect: diagnostics belong in a dedicated
logging facility, not scattered `printf` calls inside threads. The functional
risk is garbled logs and surprising latency rather than a crash.

# Vulnerability potential

This has no meaningful security relevance: emitting text to a stream does not
corrupt memory, escalate privilege, or leak data beyond whatever the message
itself contains. The only marginal concern is that heavy per-thread printing
serializes work on the stream lock and adds blocking I/O, which under extreme load
contributes mildly to slowdowns — hence a `Low` DoS rating and `None` for
vulnerability. (If the format string were attacker-controlled, that would be a
separate format-string defect, not this one.)

# Technical details

## Stream-level locking
In C, `stdio` streams are line-buffered or fully buffered and, per POSIX, each
`FILE` operation takes an implicit lock (`flockfile`/`funlockfile`). So individual
`printf` calls are atomic, but a *sequence* of them is not: another thread can
interleave between two calls, splitting a logical message. Mixing `printf` with
direct `write(2)` to the same fd bypasses the buffer and scrambles ordering
further.

## C++ streams
`std::cout` is thread-safe per character but not per `<<` chain; `a << x << y`
from two threads interleaves the tokens. `std::cout` is also synchronized with C
`stdio` by default (`sync_with_stdio`), adding more contention.

## Performance and ordering
Because the lock and the actual I/O syscall are on the critical path, a thread
that prints frequently effectively serializes with every other printing thread.
Output order no longer reflects execution order, which makes the logs misleading
for debugging concurrency.

# Catching the issue

## Static analysis / linters
The analyzer that emits this diagnostic flags direct console I/O (`printf`,
`std::cout`, `puts`) inside functions that run on a non-main thread. Custom
clang-tidy or grep-based review rules can do the same.

## Use a logging library
Replace ad-hoc prints with a thread-aware logger (spdlog, glog, a ring-buffer
logger) that batches, timestamps, tags the thread id, and serializes output in one
place. Prefer a single dedicated I/O thread that other threads feed via a queue.

## Atomicity when you must print
If direct printing is unavoidable, build the whole message in a local buffer and
emit it with a single `fputs`/`write`, or guard the sequence with
`flockfile`/`funlockfile`, so a logical line is never split.

# How to reproduce

Run this and observe that the two threads' messages interleave within a line: the
`<<` chain is not atomic, so output from different threads is mixed.

```cpp
#include <iostream>
#include <thread>

void worker(int id)
{
    for (int i = 0; i < 1000; ++i)
        std::cout << "thread " << id << " line " << i << "\n";
}

int main()
{
    std::thread a(worker, 1), b(worker, 2);
    a.join();
    b.join();
    return 0;
}
```
