---
title: "Qualifiers"
author: Maxim Menshikov
layout: defect
permalink: /expr/qualifier
group:
   - expr
---

Defects involving type qualifiers — the annotations such as `const` that constrain how a value may be used. A qualifier encodes a promise to the compiler and the reader; the defects here are the points where that promise is quietly broken, allowing access the qualifier was meant to forbid.

