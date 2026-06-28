---
title: "Scanning in thread"
author: Maxim Menshikov
layout: defect
permalink: /context/thread/scan
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
Scanning in a thread is not encouraged

# Impact

Reading interactive input (`scanf`, `std::cin`, `fgets` on `stdin`) from a worker
thread is discouraged. The standard input stream is a single shared resource with
no notion of "which thread the line belongs to": if more than one thread reads it,
input is split between them non-deterministically, and a blocking read parks the
thread indefinitely with no clean way to cancel it. A pool worker that blocks on
`scanf` is effectively removed from the pool until a line arrives, which may be
never.

This is mainly a design defect — input handling belongs in one place (usually the
main thread or a dedicated reader) — but it also creates real liveness problems:
threads stuck in a blocking read at shutdown prevent the program from exiting
cleanly.

# Vulnerability potential

There is no direct security exposure here: consuming bytes from `stdin` does not
corrupt memory or cross a trust boundary by itself. The only practical risk is
liveness — a thread blocked forever on input ties up a worker and can stall
shutdown or exhaust the pool — which is why the DoS rating is `Low` and the
vulnerability rating is `None`. (A `scanf("%s", buf)` with no width would be a
separate buffer-overflow defect, not this one.)

# Technical details

## Blocking, uncancellable reads
`scanf`/`cin` on a terminal or pipe block until data arrives or EOF. A blocked
thread holds its stack and any resources it owns; there is no portable way to
interrupt a thread parked in a blocking `read(2)` other than closing the fd or
sending a signal, both of which are awkward and racy.

## Shared stream, split input
Per POSIX the `FILE` is locked per call, so a single `scanf` is internally
consistent, but two threads each calling `scanf` race for whatever the user types:
one gets some fields, the other gets the rest, so neither parses what the user
intended. The buffered nature of `stdio` makes the split even less predictable.

## Format/state hazards
A failed conversion leaves the offending characters in the buffer; with several
threads reading, recovering from a parse error (clearing the stream) becomes
unreliable because another thread may consume the very characters you tried to
discard.

# Catching the issue

## Static analysis / linters
The analyzer emitting this diagnostic flags `scanf`/`fscanf(stdin, …)`/`std::cin`
usage in functions executed off the main thread. Review rules can forbid console
input outside a single designated reader.

## Centralize input
Read all interactive input in one place (the main thread or one reader thread) and
hand parsed values to workers through a queue. Workers should never touch
`stdin`.

## Make reads cancellable
Where a thread must wait on input, use non-blocking I/O with `poll`/`select` plus
a self-pipe or `eventfd` so the wait can be woken at shutdown, instead of a bare
blocking `scanf`.

# How to reproduce

Run this with two threads reading `stdin`: type several numbers and observe that
the values are split between the threads unpredictably, and that the program will
not exit until both blocking reads happen to receive input.

```cpp
#include <iostream>
#include <thread>

void reader(int id)
{
    int x;
    while (std::cin >> x)            // blocking read on the shared stream
        std::cout << "thread " << id << " got " << x << "\n";
}

int main()
{
    std::thread a(reader, 1), b(reader, 2);
    a.join();
    b.join();
    return 0;
}
```
