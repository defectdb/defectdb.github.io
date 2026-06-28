---
title: "Assignment operator"
author: Maxim Menshikov
layout: defect
permalink: /cpp/op_assign
group:
   - cpp
---

Defects in a user-defined assignment operator that mishandles the boundary cases value semantics demand. The canonical one is the missing self-assignment guard: an operator that releases its own resources before copying from the source breaks when source and target are the same object, freeing the data it is about to read — a hazard the copy-and-swap idiom sidesteps by construction.
