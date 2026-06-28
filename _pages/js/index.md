---
title: "JavaScript"
author: Maxim Menshikov
layout: defect
permalink: /js
---

Defects that stem from JavaScript's permissive, dynamically typed nature — the language runs almost anything, so mistakes surface as wrong results at runtime rather than errors at parse time. This section collects the constructs and habits that quietly turn working-looking code into a bug: coercion in comparisons, swallowed asynchronous failures, leftover debugging artifacts, and legacy forms the language has since outgrown.

The common thread is that the engine forgives what it should reject. Implicit type conversion, function-scoped `var`, ignored promise rejections, and dynamic evaluation all execute happily while hiding correctness, security, or maintainability problems. The sub-areas group these by where they bite — array and comparison semantics, error and async handling, scoping rules, and the `eval`-family entry points that open the door to injection.
