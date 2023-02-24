---
title: Allocation of zero size block
author: Maxim Menshikov
layout: defect
permalink: /std/alloc/null
arch:
   - native
vulnerability:
   - None
ddos:
   - None
group_full: std.alloc
group:
   - std
   - alloc
---

Argument of malloc is 0, which is probably a mistake.
