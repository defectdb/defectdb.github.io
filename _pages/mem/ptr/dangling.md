---
title: Dangling pointer
author: Maxim Menshikov
layout: defect
permalink: /mem/ptr/dangling
arch:
   - native
vulnerability:
   - None
ddos:
   - None
group_full: mem.ptr
group:
   - mem
   - ptr
---

The memory by the pointer might be used after freeing.
