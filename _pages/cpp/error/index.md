---
title: "Error handling"
author: Maxim Menshikov
layout: defect
permalink: /cpp/error
group:
   - cpp
---

Defects in how failure is detected and propagated — most often a `catch` clause that intercepts an exception and then does nothing with it. Swallowing the error discards the diagnostic information the throw site provided and lets the program continue past a condition it never actually handled, converting a loud, locatable failure into silent, corrupted state downstream.
