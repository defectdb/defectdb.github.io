---
title: "Architecture"
author: Maxim Menshikov
layout: defect
permalink: /arch
---

Defects where the code compiles and runs correctly yet violates the intended architecture — the rules about which parts of a system are allowed to depend on which others. These are not bugs in any single function but breaches of structural intent: a layer reaching past its boundary, a module importing something it was meant to be insulated from, a dependency that quietly inverts or short-circuits the designed flow of control.

Such violations rarely surface as runtime failures. Instead they accrue as coupling, eroding the separation that makes a system testable, replaceable, and comprehensible, until a change in one corner forces changes everywhere. The entries here concern the linkage between components and the layering policy that is supposed to govern it.
