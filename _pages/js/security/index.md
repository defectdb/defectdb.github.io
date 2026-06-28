---
title: "Security"
author: Maxim Menshikov
layout: defect
permalink: /js/security
group:
   - js
---

Defects that hand the engine code to execute at runtime, opening the door to injection. Calling `eval()`, or passing a string to `setTimeout` and `setInterval`, compiles and runs whatever text reaches it; once any of that text derives from untrusted input, an attacker can run arbitrary code in the page's context. These entry points also defeat optimization and content-security policies, and almost always have a safe, non-dynamic alternative.
