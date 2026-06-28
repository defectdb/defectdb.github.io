---
title: "Scopes"
author: Maxim Menshikov
layout: defect
permalink: /var/scope
group:
   - var
---

Defects in where a variable is visible and for how long, where a name reaches code it should not or collides with another in an enclosing scope. These bugs range from the merely suspicious — a variable declared but never used — to the genuinely dangerous, where a name remains accessible beyond its intended region or shadows an outer one, so reads and writes silently target the wrong storage.

