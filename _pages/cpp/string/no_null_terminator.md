---
title: "Buffer not guaranteed null-terminated"
author: Maxim Menshikov
layout: defect
permalink: /cpp/string/no_null_terminator
arch:
   - native
vulnerability:
   - High
ddos:
   - Low
group_full: cpp.string
group:
   - cpp
   - string
---
strncpy / strncat does not write a terminating NUL when the source reaches the size limit; subsequent strlen / printf-style use can read past the buffer

# Impact

`strncpy(dst, src, n)` copies at most `n` bytes and writes a terminating `'\0'`
**only if** `src` is shorter than `n`. When the source is `n` bytes or longer,
the destination is filled but left **without** a terminator. Any later use that
relies on a terminator — `strlen`, `printf("%s")`, `strcat`, passing the buffer
to a C API — then reads past the end of the buffer, scanning memory until it
happens upon a zero byte. The consequences are an out-of-bounds read that
returns adjacent stack/heap contents, a wrong (too-long) length, or a crash
when the scan walks into an unmapped page.

# Vulnerability potential

This is a real memory-safety defect (CWE-170 missing null termination / CWE-125
out-of-bounds read).

1. **Information disclosure.** `printf`/`send` of a non-terminated buffer emits
   everything from the buffer up to the next zero byte, leaking adjacent stack
   or heap memory — other variables, pointers (defeating ASLR), or secrets — to
   an output the attacker can observe.
2. **Secondary overflow.** A bogus over-long `strlen` result fed into a
   subsequent `memcpy`/allocation size turns the over-read into an over-write,
   i.e. a buffer overflow on the next operation.
3. **Crash.** When the unterminated scan reaches an unmapped page it segfaults,
   an availability impact (the secondary DoS weight); the disclosure/corruption
   risk is the dominant one, hence the high rating.

# Technical details

## strncpy is not a safe strcpy

`strncpy` was designed for fixed-width fields (old UNIX directory entries), not
for safe string copying. Its two documented hazards are: it does **not**
NUL-terminate on truncation, and it **zero-pads** the entire remainder when the
source is short (a performance, not safety, surprise). `strncat` has a related
trap: its `n` is the number of bytes to append, not the destination size, so it
always writes a terminator but can still overflow if `n` is miscomputed.

## Correct alternatives

- Explicitly terminate: `strncpy(dst, src, n - 1); dst[n - 1] = '\0';`.
- Use size-aware copies that always terminate: `snprintf(dst, n, "%s", src)`,
  or the bounded `strlcpy`/`strscpy` (BSD/Linux) which guarantee a terminator.
- In C++, avoid raw buffers entirely: `std::string`/`std::string_view` carry
  their own length and never depend on a terminator.

## Why it passes tests

With short test inputs the source is always under the limit, so the terminator
*is* written and the bug is invisible; it only triggers at exactly the boundary
length, which fuzzing or adversarial input reaches but unit tests rarely do.

# Catching the issue

## Sanitizers

AddressSanitizer reports the out-of-bounds read when `strlen`/`printf` scans
past the buffer (especially with a heap-allocated destination). Valgrind
Memcheck flags the invalid read similarly.

## Fortify / compiler

`_FORTIFY_SOURCE=2/3` with optimization adds runtime checks to the `str*`
family; GCC/Clang `-Wstringop-truncation` warns specifically about a `strncpy`
whose result may be unterminated, and `-Wstringop-overflow` covers `strncat`
miscalculations.

## Static analysis

clang-tidy `bugprone-not-null-terminated-result` and the CERT rules
(`cert-str32-c`, "do not pass a non-null-terminated character sequence to a
library function") flag the pattern; Coverity has a dedicated
STRING_NULL checker.

# How to reproduce

Build with `-fsanitize=address`; the `name` exactly fills `dst` so no
terminator is written, and `printf("%s")` over-reads (ASan reports
stack-buffer-overflow / heap-buffer-overflow).

```cpp
#include <cstring>
#include <cstdio>
#include <cstdlib>

int main() {
    const char* name = "0123456789ABCDEF";   // 16 chars, no room for NUL
    char* dst = (char*)malloc(16);
    strncpy(dst, name, 16);                   // BUG: fills 16 bytes, no '\0'
    printf("%s\n", dst);                      // over-reads past dst
    free(dst);
    // Fix: char* dst = malloc(17); strncpy(dst, name, 16); dst[16] = '\0';
}
```
