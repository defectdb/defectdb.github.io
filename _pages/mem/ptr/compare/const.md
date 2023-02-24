---
title: Comparing pointer to a constant is strange
author: Maxim Menshikov
layout: defect
permalink: /mem/ptr/compare/const
arch:
   - native
vulnerability:
   - None
ddos:
   - None
group_full: mem.ptr.compare
group:
   - mem
   - ptr
   - compare
---

Comparing pointer to a constant is strange as usually they are not constant.
