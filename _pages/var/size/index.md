---
title: "Size"
author: Maxim Menshikov
layout: defect
permalink: /var/size
group:
   - var
---

Defects where a variable or container is sized out of proportion to what it actually holds. Over-allocating capacity wastes memory and can pessimize cache behavior and growth assumptions; the value still works, but its footprint reflects a guess rather than the data it was meant to store.

