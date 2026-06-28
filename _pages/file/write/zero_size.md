---
title: "Writing 0 symbols is pointless"
author: Maxim Menshikov
layout: defect
permalink: /file/write/zero_size
arch:
   - native
vulnerability:
   - None
ddos:
   - None
group_full: file.write
group:
   - file
   - write
---
Write size is 0 symbol long

# Impact

A write is issued with a length of zero — `fwrite(buf, 1, 0, f)`,
`fwrite(buf, 0, n, f)`, or `write(fd, buf, 0)`. No bytes leave the program. The
call is inert, but it is almost always a symptom of a broken size calculation: a
length that collapsed to `0` where the real number of bytes was meant (a forgotten
`strlen`, a `sizeof` mistake, an off-by-one, or an uninitialized counter). The
caller typically believes the data was persisted when nothing was written, which
leads to truncated files, empty records, or messages that never reach the peer.

The harm is the silent loss of the intended output, not the no-op write itself.

# Vulnerability potential

A zero-length write has no security impact: it emits no data, cannot overflow, and
cannot corrupt anything. The ratings are `None`/`None`. The only indirect note is
that the same miscomputed length, if reused for a buffer copy elsewhere, could be
unsafe — but that would be a separate defect at the copy site, not this write.

# Technical details

## `fwrite` semantics
`fwrite(ptr, size, nmemb, stream)` writes `size * nmemb` bytes and returns the
number of *elements* written. If `size` or `nmemb` is `0`, it writes nothing and
returns `0`. A success check of the form `fwrite(...) == nmemb` then sees
`0 == 0` and wrongly reports success, masking the fact that nothing was stored.

## `write(2)` semantics
`write(fd, buf, 0)` returns `0` with no side effect (for a regular file). Since a
short or zero return from `write` is also how partial writes are signalled, a loop
that advances by the return value can spin or terminate incorrectly when the count
was accidentally zero.

## Where the zero comes from
Common origins: `sizeof(ptr)` instead of the buffer length, writing `strlen(s)`
of an empty/uninitialized string, a length field defaulted to `0`, or
`end - start` with equal bounds.

# Catching the issue

## Compiler warnings
`-Wall -Wextra` flags some constant zero sizes and the `sizeof` confusions that
cause them.

## Static analysis
The analyzer emitting this diagnostic, together with Cppcheck and clang-tidy,
constant-folds the size argument and reports a provably zero-length write, and
catches the usual `sizeof`/`strlen` mistakes behind it.

## Runtime checks and review
Assert that computed write sizes are non-zero on paths that must emit data, and
compare `fwrite`/`write` return values against the requested count (and handle
short writes) instead of assuming the call wrote everything.

# How to reproduce

Run this: the write asks for `0` bytes, returns `0`, the success check passes, yet
the file ends up empty — observe that nothing was written despite the "ok" report.

```c
#include <stdio.h>
#include <string.h>

int main(void)
{
    FILE *f = fopen("/tmp/zw_demo.txt", "w");
    if (!f) return 1;

    const char *msg = "important record\n";
    size_t len = 0;                  /* should be strlen(msg) */

    size_t n = fwrite(msg, 1, len, f);   /* writes nothing */
    if (n == len)                    /* 0 == 0: false success */
        printf("write ok\n");        /* but the file is empty */

    fclose(f);
    return 0;
}
```
