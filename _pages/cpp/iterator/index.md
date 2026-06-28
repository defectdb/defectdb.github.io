---
title: "Iterators"
author: Maxim Menshikov
layout: defect
permalink: /cpp/iterator
group:
   - cpp
---

Defects involving iterator invalidation — using an iterator, pointer, or reference after an operation that the container's specification says may invalidate it. Insertions and erasures can reallocate or splice storage, leaving a previously obtained iterator dangling, so a loop that mutates the very container it is traversing reads or writes freed memory while looking entirely reasonable.
