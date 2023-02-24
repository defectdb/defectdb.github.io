---
title: srand() should be called only once
author: Maxim Menshikov
layout: defect
permalink: /std/rng/once
arch:
   - native
vulnerability:
   - None
ddos:
   - None
group_full: std.rng
group:
   - std
   - rng
---

srand() shouldn't be called more than once.
