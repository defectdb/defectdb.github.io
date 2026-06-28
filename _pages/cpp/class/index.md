---
title: "Classes"
author: Maxim Menshikov
layout: defect
permalink: /cpp/class
group:
   - cpp
---

Defects rooted in how a class declares its special member functions and its polymorphic contract. The recurring failure is a base class used through a pointer or reference to it but missing a `virtual` destructor, so deleting a derived object through a base handle runs only the base destructor — leaking the derived part and, formally, invoking undefined behavior.
