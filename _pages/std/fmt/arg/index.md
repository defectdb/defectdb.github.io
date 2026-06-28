---
title: "Arguments"
author: Maxim Menshikov
layout: defect
permalink: /std/fmt/arg
group:
   - std
   - fmt
---

Defects where the variadic arguments do not correspond to the conversion
directives in the format string. A directive may name a type the matching
argument does not have, an expected argument may be missing entirely, or an
argument may be supplied with no directive to consume it. Because the call
walks the argument list according to the string alone, any such mismatch
misreads the stack — reinterpreting bytes, reading past the end of the list,
or silently ignoring a value.

