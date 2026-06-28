---
title: "Formatting"
author: Maxim Menshikov
layout: defect
permalink: /std/fmt
group:
   - std
---

Defects in the `printf`/`scanf` family of formatted I/O, where a format string
and its variadic arguments must agree but are checked by neither the type
system nor, in general, the compiler. The format string is effectively a small
program interpreted at run time, and any disagreement between it and the values
supplied reads the argument list incorrectly.

The failures group by which side of that contract is broken: arguments whose
types, count, or presence do not match the directives; format strings that are
malformed or attacker-controlled rather than constant; and individual
conversion parameters that are themselves invalid. Consequences range from
garbage output to out-of-bounds reads and the classic format-string
vulnerability.

