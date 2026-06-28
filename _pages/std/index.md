---
title: "Standard Library"
author: Maxim Menshikov
layout: defect
permalink: /std
---

Defects that arise not from a language's core semantics but from misuse of the
standard library and platform runtime — the allocator, the `printf` family,
mutexes, hash maps, the threading layer, and the pseudo-random generator. These
are well-documented interfaces with precise contracts, yet their preconditions
are easy to violate in ways the compiler cannot catch.

The recurring theme is a mismatch between what the caller assumes and what the
API actually guarantees: a format string that disagrees with its arguments, a
lock released twice or never taken, a generator reseeded on every call, a
zero-size allocation whose return value is implementation-defined. Each entry
isolates one such contract and the undefined behavior, crash, or silent
corruption that follows when it is broken.

