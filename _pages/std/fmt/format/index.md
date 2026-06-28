---
title: "Format"
author: Maxim Menshikov
layout: defect
permalink: /std/fmt/format
group:
   - std
   - fmt
---

Defects in the format string itself, principally the use of a non-constant
string where a literal is expected. When the format is a variable — worse, one
derived from external input — the caller loses the compiler's ability to check
directives against arguments and opens the door to the format-string
vulnerability, in which directives like `%n` let an attacker read or write
memory through the formatting call.

