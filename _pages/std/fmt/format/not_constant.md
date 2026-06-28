---
title: "Format string is not constant"
author: Maxim Menshikov
layout: defect
permalink: /std/fmt/format/not_constant
arch:
   - native
vulnerability:
   - High
ddos:
   - Medium
group_full: std.fmt.format
group:
   - std
   - fmt
   - format
---
Non-constant format string might be used to corrupt memory. Consider using constant strings.

# Impact

Passing a runtime-determined string as the *format* argument of a ``printf``-
family function — classically ``printf(user_input)`` instead of
``printf("%s", user_input)`` — is the textbook **format string vulnerability**
(CWE-134). If any part of that string is attacker-controlled, the attacker
controls the conversion directives the function executes. Embedding ``%x``/``%p``
walks and dumps the call stack; ``%s`` dereferences stack words as pointers and
prints memory at those addresses; ``%n`` writes the number of bytes emitted so
far *into* memory at an address taken from the argument list. Combined with width
fields and direct parameter access (``%7$n``), an attacker can write chosen
values to chosen addresses, turning a single careless format string into an
information leak and an arbitrary write — frequently a path to remote code
execution.

# Vulnerability potential

This is one of the highest-severity defects in this class; the format string is
effectively a small interpreter driven by the attacker.

1. **Information disclosure.** ``%x``/``%p``/``%s`` leak stack frames, saved
   return addresses, stack canaries, ASLR-defeating pointers and secrets,
   undermining other mitigations.
2. **Arbitrary memory write.** ``%n`` (and ``%hn``/``%hhn``) writes the output
   length to an address pulled from the argument list. With positional
   arguments and width padding, an attacker writes an arbitrary value to an
   arbitrary address.
3. **Control-flow hijack / RCE.** The write primitive can overwrite a return
   address, GOT/PLT entry, function pointer or saved frame pointer, redirecting
   execution to attacker code.
4. **Denial of service.** Even without a crafted write, ``%s`` on bad pointers
   or huge field widths reliably crash or hang the process.

# Technical details

A ``printf``-family function trusts the format string to describe the argument
list. When the format is itself attacker data, the attacker supplies directives
that the function dutifully executes against whatever happens to be on the stack
above the format pointer — there is no validation that those stack slots are
real arguments.

## The %n write primitive

``%n`` is the linchpin: it stores the running output count through a pointer
taken from the next argument slot. By controlling preceding directives (which set
the count via emitted width) and using positional specifiers like ``%37$n``, an
attacker selects both the value and the target. Splitting the write across
``%hn``/``%hhn`` lets them place a full address two bytes or one byte at a time.
Many modern libcs disable ``%n`` for writable format strings (glibc
``_FORTIFY_SOURCE`` rejects ``%n`` in a format located in writable memory), but
leaks via ``%x``/``%s`` generally remain possible.

## Why it slips through

The code often looks harmless and works in testing because benign input contains
no ``%`` characters; the bug only manifests when an attacker includes conversion
specifiers. Logging wrappers, error reporters and ``syslog(level, msg)`` (whose
second parameter is a format) are the usual offenders.

# Catching the issue

## Compilers

GCC and Clang emit ``-Wformat-security`` (and ``-Wformat-nonliteral``) for a
non-literal format with no arguments; enable them via ``-Wformat=2`` and make
them fatal with ``-Werror=format-security``. Annotate every custom logging
wrapper with ``__attribute__((format(printf, n, m)))`` so the checks propagate.

## Hardening and analysis

Build with ``-D_FORTIFY_SOURCE=2`` to block writable-memory ``%n`` at runtime.
Static analyzers (Clang-Tidy, Coverity, PVS-Studio, CodeQL's
``cpp/tainted-format-string``) and taint-tracking flag user data flowing into a
format parameter. The fix is invariably trivial: use a constant format and pass
the data as an argument — ``printf("%s", s)``.

# How to reproduce

Run with an argument containing conversion specifiers, e.g.
``./a.out '%x %x %x %s'``, and observe leaked stack data instead of the literal
text.

```c
#include <stdio.h>

int main(int argc, char **argv)
{
    if (argc < 2)
        return 1;

    /* WRONG: user input is used as the format string. */
    printf(argv[1]);
    printf("\n");

    /* Correct form would be: printf("%s\n", argv[1]); */
    return 0;
}
```
