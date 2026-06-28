---
title: "Linkage"
author: Maxim Menshikov
layout: defect
permalink: /arch/linkage
group:
   - arch
---

Defects where one component calls into another that the layering policy forbids it to reach. The dependency is real and the call succeeds at runtime; what fails is the architectural contract that says this module may not know about that one.

The cases differ in how the boundary is crossed: a call that escapes the set of dependencies a component is permitted to use at all, and a call to a target that is explicitly disallowed even though it might otherwise look reachable. Both tighten coupling and undermine the isolation the structure was meant to guarantee.
