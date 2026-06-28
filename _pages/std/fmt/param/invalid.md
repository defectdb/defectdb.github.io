---
title: "Format parameter is invalid"
author: Maxim Menshikov
layout: defect
permalink: /std/fmt/param/invalid
arch:
   - native
vulnerability:
   - Low
ddos:
   - Low
group_full: std.fmt.param
group:
   - std
   - fmt
   - param
---
Format parameter is invalid with respect to format standard

# Impact

The format string itself contains a conversion specification that the standard
does not define — an unknown conversion letter (``%y``), a nonsensical
flag/length/conversion combination (``%#s``, ``%lc`` misuse), a length modifier
attached to a conversion that does not accept it, or a stray ``%`` followed by
something that is not a valid specifier. The C standard says the behavior is
undefined. In practice most C libraries fall back to printing the offending
specifier literally or skip it, but the result is unreliable and
implementation-defined: output differs between glibc, musl, the BSD libc and the
Windows CRT, and a malformed directive can desynchronize the argument cursor so
that every following conversion reads the wrong argument.

# Vulnerability potential

On its own an invalid specifier is mostly a correctness and portability defect,
but it is not fully benign.

1. If the bad directive causes the library to mis-advance through the argument
   list, a later ``%s``/``%n`` can read or write through a wrong argument,
   re-introducing the leak/corruption risks of an argument-type mismatch.
2. Implementation-specific handling of the malformed directive can crash on some
   platforms while working on others, an availability and portability hazard.

Where the format string is a compile-time constant the risk is low, because the
mistake is fixed and visible; it becomes more serious only if the invalid
parameter is reached on a runtime-constructed format string.

# Technical details

``printf`` parses each directive as ``%[flags][width][.precision][length]conv``.
Each conversion character accepts only a specific subset of flags and length
modifiers; combinations outside that grammar are undefined. Implementations are
free to do anything, and they diverge:

## glibc / musl

Typically emit the unrecognized directive verbatim (e.g. ``%y`` prints as
``%y``) and do not consume an argument for it, though edge cases vary.

## Windows CRT

Historically more permissive and may interpret some sequences differently, so a
format that "works" on Linux can misbehave on Windows. Length modifiers such as
``%lf`` for ``scanf`` versus ``printf`` are a common cross-platform trap.

# Catching the issue

## Compilers

GCC/Clang ``-Wformat`` rejects unknown conversions and invalid flag/length
combinations on literal format strings; ``-Wformat=2`` adds ``-Wformat-y2k`` and
related checks. Build with ``-Werror=format`` so an invalid specifier stops the
build, and annotate variadic wrappers with
``__attribute__((format(printf, n, m)))``.

## Static analysis

Clang-Tidy, Coverity, PVS-Studio and PC-lint validate format-string grammar.
For runtime-built formats these tools cannot help, so such formats should be
avoided entirely (see the non-constant format string defect).

# How to reproduce

Compile with ``-Wformat``; the compiler flags the unknown conversion, and at
runtime the output is implementation-defined.

```c
#include <stdio.h>

int main(void)
{
    /* %y is not a valid conversion specifier. */
    printf("value: %y\n", 10);

    /* '#' flag is not meaningful for the 's' conversion. */
    printf("%#s\n", "text");

    return 0;
}
```
