---
title: "Constructors and destructors"
author: Maxim Menshikov
layout: defect
permalink: /cpp/ctor_dtor
group:
   - cpp
---

Defects tied to the period when an object is only partially alive — during construction or destruction, when its dynamic type is not yet, or no longer, the most-derived one. Calling a virtual function in these phases dispatches to the constructing or destructing class rather than the override you expect, so polymorphism quietly resolves to the wrong target with no warning.
