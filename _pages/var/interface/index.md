---
title: "Interfaces"
author: Maxim Menshikov
layout: defect
permalink: /var/interface
group:
   - var
---

Defects in variables of an interface type, where the variable carries no concrete implementation behind it. Calling through such a value — a nil interface, or one whose dynamic type is itself absent — fails at the dispatch point rather than at assignment, making the empty interface easy to pass around unnoticed until it is finally invoked.

