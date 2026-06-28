---
title: "Static"
author: Maxim Menshikov
layout: defect
permalink: /var/static
group:
   - var
---

Defects in variables with static storage duration, whose single shared instance persists for the life of the program. Because such a variable is initialized once and seen everywhere, leaving it without a proper initial value — or relying on an unclear initialization order — exposes the omission across every use at once.

