---
title: "Confusion"
author: Maxim Menshikov
layout: defect
permalink: /var/confusion
group:
   - var
---

Defects where a null, empty, or otherwise sentinel value is treated as if it were a meaningful one. The confusion typically comes from conflating "absent" with "present but blank" — an empty string, a zero, or a null reference passed through code that expected real data — so a missing value flows onward instead of being caught at the point it should have been checked.

