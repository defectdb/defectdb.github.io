---
title: "Error handling"
author: Maxim Menshikov
layout: defect
permalink: /js/error
group:
   - js
---

Defects in how exceptions are caught and handled. The classic case is an empty `catch` block: the error is intercepted and then discarded, suppressing the diagnostic while leaving the underlying failure unaddressed, so a fault that should have surfaced instead manifests later as corrupt state or silent data loss.
