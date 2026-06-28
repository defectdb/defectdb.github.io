---
title: "Strings"
author: Maxim Menshikov
layout: defect
permalink: /csharp/string
group:
   - csharp
---

Defects in string comparison and construction, where the value semantics programmers expect of `string` diverge from how the type actually behaves. Strings are immutable reference types, so equality and concatenation each carry a subtlety that ordinary-looking code steps into.

Comparing with `==` against a value typed as `object` silently falls back to reference equality rather than content equality, and building a string by repeated `+` inside a loop allocates a fresh copy on every iteration — quadratic work that a `StringBuilder` collapses to linear.

