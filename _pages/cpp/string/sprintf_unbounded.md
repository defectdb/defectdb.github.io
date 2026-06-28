---
title: "sprintf with %s — output is unbounded"
author: Maxim Menshikov
layout: defect
permalink: /cpp/string/sprintf_unbounded
arch:
   - native
vulnerability:
   - High
ddos:
   - Medium
group_full: cpp.string
group:
   - cpp
   - string
---
sprintf cannot truncate; an attacker-controlled string can overflow the destination buffer. Use snprintf with explicit destination size

# Impact

`sprintf(dst, fmt, ...)` writes as many bytes as the formatted output requires
plus a terminator, with **no knowledge of the size of `dst`**. If any
conversion — most commonly `%s`, but also wide `%d`/`%f` or `%g` — produces more
characters than `dst` can hold, `sprintf` writes past the end of the buffer.
When `dst` is a fixed stack array, this is a classic stack buffer overflow:
local variables, the saved frame pointer, and the return address are
overwritten. The immediate effect is corruption and a crash; the dangerous
effect is that an attacker who controls the formatted string controls what
overwrites the stack.

# Vulnerability potential

This is a textbook, high-severity memory-corruption vulnerability (CWE-787
out-of-bounds write / CWE-120 classic buffer overflow).

1. **Remote code execution.** An attacker-controlled `%s` argument overflowing
   a stack buffer can overwrite the saved return address; with a crafted
   payload this redirects execution to attacker-chosen code (or, with
   mitigations, a ROP chain). This is the canonical stack-smashing exploit.
2. **Control-data / adjacent-variable corruption.** Even without reaching the
   return address, the overflow can clobber a length, a flag, or a pointer used
   later, enabling logic bypasses or further corruption.
3. **Denial of service.** The overflow reliably crashes the process (stack
   canary abort or segfault), and an attacker can trigger it at will — hence the
   non-trivial DoS weight in addition to the dominant code-execution risk.

# Technical details

## Why sprintf is unfixable in place

`sprintf` has no size parameter; the only way to use it safely is to *prove*
the output can never exceed the buffer, which is fragile and breaks the moment
an input becomes attacker-influenced. The standard replacement is
`snprintf(dst, sizeof dst, fmt, ...)`, which never writes more than `size`
bytes (including the terminator) and returns the number of characters that
*would* have been written, so truncation is detectable.

## Modern C++ replacements

Prefer the type-safe, self-sizing facilities: `std::format`/`std::format_to_n`
(C++20), `std::ostringstream`, or `fmt::format`. These compute the required
size and allocate or bound it, removing the fixed-buffer hazard entirely.

## A note on snprintf size

A frequent secondary bug is passing the size of a *pointer* (`sizeof dst` when
`dst` is a `char*`) instead of the real buffer length; pass the actual capacity.

# Catching the issue

## Compiler / fortify

`_FORTIFY_SOURCE=2/3` redirects `sprintf` to a checked variant that aborts on
overflow when the destination size is known at compile time. GCC/Clang
`-Wformat-security` and `-Wformat-overflow` warn when `sprintf` may overflow a
fixed buffer. `-fstack-protector-strong` adds a canary that turns many
overflows into a controlled abort rather than silent corruption.

## Sanitizers

AddressSanitizer reports the stack-buffer-overflow at the write, with the exact
buffer and overflow size.

## Static analysis

clang-tidy `cppcoreguidelines-pro-type-vararg` and CERT `FIO47-C`/`STR31-C`
flag unbounded `sprintf` use; Coverity (OVERRUN) and CodeQL
(`cpp/unbounded-write`) detect it. A simple, enforceable review rule is to ban
`sprintf`/`vsprintf` outright in favor of `snprintf`/`std::format`.

# How to reproduce

Build with `-fsanitize=address`; the long `user` string overflows the 16-byte
stack buffer and ASan reports a stack-buffer-overflow.

```cpp
#include <cstdio>

void greet(const char* user) {
    char msg[16];
    sprintf(msg, "Hello, %s!", user);   // BUG: no bound on output size
    printf("%s\n", msg);
}

int main() {
    greet("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");   // 32 chars -> overflow
    // Fix: snprintf(msg, sizeof msg, "Hello, %s!", user);
}
```
