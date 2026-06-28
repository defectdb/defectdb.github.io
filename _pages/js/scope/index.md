---
title: "Scopes"
author: Maxim Menshikov
layout: defect
permalink: /js/scope
group:
   - js
---

Defects rooted in variable scoping. The `var` declaration is function-scoped and hoisted, so a binding leaks outside the block it appears in and exists — as `undefined` — before its assignment, a mismatch with intuition that produces closure-in-loop surprises and accidental redeclarations that block-scoped `let` and `const` avoid.
