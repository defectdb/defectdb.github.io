---
title: Variable is accessible outside its scope
author: Maxim Menshikov
layout: defect
permalink: /var/scope/outside
arch:
   - native
vulnerability:
   - None
ddos:
   - None
group_full: var/scope
group:
   - var
   - scope
---

Reference to a variable or a pointer to it is invalid after leaving variable's scope.
