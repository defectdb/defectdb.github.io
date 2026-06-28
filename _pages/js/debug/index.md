---
title: "Debugging"
author: Maxim Menshikov
layout: defect
permalink: /js/debug
group:
   - js
---

Debugging artifacts left in shipped code. A stray `debugger` statement halts execution whenever developer tools are open, so code meant only for a local session can freeze a user's browser or stall an automated run if it reaches production.
