---
title: "Const qualifier"
author: Maxim Menshikov
layout: defect
permalink: /expr/qualifier/const
group:
   - expr
   - qualifier
---

Defects where the `const` qualifier is dropped, exposing an object that was declared immutable to a path that can write it. Casting away `const`, or passing a constant through an interface that discards the qualifier, defeats the compiler's enforcement and invites writes to read-only storage — undefined behaviour and a guarantee the rest of the code still trusts.

