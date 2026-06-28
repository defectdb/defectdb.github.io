---
title: "Indices"
author: Maxim Menshikov
layout: defect
permalink: /array/index
group:
   - array
---

Faults in the index used to address a single array element, where the computed position falls outside the valid range `0 .. length-1`. The two failure modes are a negative subscript and a value at or beyond the end — both stemming from off-by-one arithmetic, unchecked external input, or a length assumption that no longer holds. The consequence is a memory-safety violation in C and C++ or a thrown exception in checked languages.
