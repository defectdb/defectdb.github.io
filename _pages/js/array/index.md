---
title: "Arrays"
author: Maxim Menshikov
layout: defect
permalink: /js/array
group:
   - js
---

Defects in how array contents are searched and tested, where the idiom in use predates clearer alternatives. The recurring case is checking membership by comparing a search result against `-1`, an error-prone pattern that breaks down around `NaN` and reads far less plainly than the boolean-returning methods that have since replaced it.
