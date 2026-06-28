---
title: "Members"
author: Maxim Menshikov
layout: defect
permalink: /class/member
group:
   - class
---

Defects in the fields that make up an object's state, where a member is left without a well-defined value before code depends on it. The classic case is a member that no constructor assigns and no default covers, so the first read returns indeterminate or zero-initialized data and the object's invariants silently fail to hold.

