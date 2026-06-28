---
title: "File is closed twice"
author: Maxim Menshikov
layout: defect
permalink: /file/state/double_close
arch:
   - native
vulnerability:
   - Medium
ddos:
   - Medium
group_full: file.state
group:
   - file
   - state
---
It is possible that file is closed twice or more times

# Impact

The same file handle is passed to `close`/`fclose` more than once. The first call
releases the descriptor; the second operates on a handle that is no longer valid.
The danger is not the wasted call — it is that the OS aggressively recycles file
descriptor numbers. Between the two closes, another thread (or the same thread)
may have opened a new file, socket, or pipe and been given the *same* numeric fd.
The stray second close then silently shuts down that unrelated resource.

With `FILE*` the situation is worse: the second `fclose` reads a freed `FILE`
object, which is undefined behaviour and can corrupt the heap or crash. The bug is
intermittent and timing-dependent, so it tends to escape testing and surface in
production.

# Vulnerability potential

Double-close is a recognized weakness class (CWE-1341) with concrete security
impact.

1. **Wrong-resource close / fd confusion.** After fd reuse, the duplicate close
   tears down a descriptor now owned by other code — a security-relevant socket,
   an audit log, an authenticated connection — causing it to fail or silently fall
   back to an insecure path. An attacker who can influence open/close timing may
   steer which descriptor gets closed.
2. **Use-after-free via `fclose`.** The second `fclose` dereferences and frees an
   already-freed `FILE`, a classic double-free/use-after-free. With heap grooming
   this is potentially exploitable for memory corruption and, in the worst case,
   code execution.
3. **Denial of service.** The simplest outcome — abort or crash on the second
   close — terminates the process.

The memory-corruption and resource-confusion potential gives a `Medium`
vulnerability rating; the crash potential gives a `Medium` DoS rating.

# Technical details

## File-descriptor reuse
POSIX requires `open`/`socket`/etc. to return the lowest-numbered unused
descriptor. Once `close(fd)` succeeds, that number is immediately eligible for
reuse, so a concurrent `open` can hand it straight back. A delayed second
`close(fd)` then hits whatever now lives at that number. EINTR handling makes this
worse: retrying `close` after `EINTR` on Linux can double-close because Linux
closes the fd even when it returns `EINTR`.

## `fclose` and the FILE object
`fclose` frees the `FILE` structure. A second `fclose` (or any `f*` call) on the
same pointer is undefined behaviour: it may read freed memory, double-free the
buffer, or abort. The C standard explicitly leaves the handle dangling after
`fclose`.

## Common code shapes
- An error path closes the handle, then the normal cleanup path closes it again.
- A handle closed inside a helper and again by the caller.
- A struct destructor closing a handle that was already closed elsewhere, or two
  copies of a struct each closing the same fd.

# Catching the issue

## Sanitizers and tooling
Build with AddressSanitizer to catch the `FILE*` use-after-free/double-free.
Valgrind/Memcheck and `-fsanitize=address` both report the invalid second free.
On Linux, fd sanitizers and `strace` reveal `close()` returning `EBADF`.

## Static analysis
Cppcheck, clang-tidy, Coverity and the analyzer emitting this diagnostic track
handle state across paths and report a close on an already-closed handle.

## Defensive coding
After closing, set the handle to a sentinel (`fd = -1`, `fp = NULL`) and guard
closes (`if (fd >= 0)`), so a second cleanup is a no-op. Give each resource a
single owner (RAII: `std::fstream`, `std::unique_ptr` with a closing deleter) so
ownership — and therefore the close — is unambiguous. Never retry `close` on
`EINTR` on Linux.

# How to reproduce

Build with `-fsanitize=address`. The second `fclose` operates on a freed `FILE`,
and ASan reports a heap use-after-free / double free.

```c
#include <stdio.h>

int main(void)
{
    FILE *f = fopen("/tmp/dc_demo.txt", "w");
    if (!f)
        return 1;

    fputs("hello\n", f);
    fclose(f);

    /* f is now a dangling handle; closing it again is undefined behaviour. */
    fclose(f);

    return 0;
}
```
