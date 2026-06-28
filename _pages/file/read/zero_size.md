---
title: "Reading 0 symbols is pointless"
author: Maxim Menshikov
layout: defect
permalink: /file/read/zero_size
arch:
   - native
vulnerability:
   - None
ddos:
   - None
group_full: file.read
group:
   - file
   - read
---
Read size is 0 symbol long

# Impact

A read operation is issued with a length of zero — `fread(buf, 1, 0, f)`,
`fread(buf, 0, n, f)`, or `read(fd, buf, 0)`. The call transfers no data and has no
useful effect. By itself it is harmless, but it almost always signals a logic
mistake: a size computed as `0` where a real length was intended (an off-by-one,
an `n - n`, a forgotten `sizeof`, or an uninitialized length variable). Code that
then assumes the buffer was populated will act on stale or uninitialized contents.

So the defect matters less for what the zero-length read does and more for what it
reveals about a broken size calculation upstream.

# Vulnerability potential

A zero-length read has no security impact on its own: it moves no bytes, cannot
overflow a buffer, and cannot leak data. The ratings are `None`/`None`. The only
indirect concern is that the underlying size bug — if the same miscomputed length
feeds a *write* or a copy elsewhere — could be dangerous, but that would be a
different defect at that site, not this read.

# Technical details

## `fread` semantics
`fread(ptr, size, nmemb, stream)` reads `size * nmemb` bytes. If either `size` or
`nmemb` is `0`, it reads nothing and returns `0`, leaving the file position
unchanged and not touching the buffer. A caller that checks `fread(...) == nmemb`
will see `0 == 0` succeed and wrongly conclude a full read happened.

## `read(2)` semantics
`read(fd, buf, 0)` returns `0` and has no other effect. Critically, a return of
`0` from `read` normally means end-of-file; a zero-length request also returns
`0`, so a loop using "`read` returned 0 ⇒ EOF" may terminate prematurely or
misbehave when the count was accidentally zero.

## Where the zero comes from
Typical sources: `sizeof(ptr)` vs `sizeof(*ptr)` confusion collapsing to a small
or zero value, a length parsed from input that defaulted to `0`, or arithmetic
like `end - start` where the bounds are equal.

# Catching the issue

## Compiler warnings
GCC/Clang with `-Wall -Wextra` warn on some constant zero-size allocations and
suspicious `sizeof` usage. Review any "argument is zero" notes.

## Static analysis
The analyzer emitting this diagnostic, plus Cppcheck/clang-tidy, can constant-fold
the size argument and report when it is provably `0`. They also flag the common
`sizeof` mistakes that produce it.

## Runtime asserts and review
Assert that computed I/O sizes are non-zero where a non-empty transfer is
expected, and always compare `fread`/`read` return values against the *requested*
count and against `0`-means-EOF semantics, rather than assuming success.

# How to reproduce

Run this: `fread` is asked for `0` bytes, returns `0`, leaves `buf` uninitialized,
yet the success check passes — observe that the printed data is garbage.

```c
#include <stdio.h>

int main(void)
{
    FILE *f = fopen("/etc/hostname", "r");
    if (!f) return 1;

    char buf[64] = {0};
    size_t want = 0;                 /* miscomputed length: should be > 0 */

    size_t got = fread(buf, 1, want, f);  /* reads nothing */
    if (got == want)                 /* 0 == 0: looks like success */
        printf("read ok: '%s'\n", buf);   /* but buf was never filled */

    fclose(f);
    return 0;
}
```
