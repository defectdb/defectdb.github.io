---
title: "States"
author: Maxim Menshikov
layout: defect
permalink: /var/state
group:
   - var
---

Defects where a variable is read before it has been given a defined value. An uninitialized read returns whatever happened to occupy the storage, producing nondeterministic behavior that may pass tests by accident and fail unpredictably in the field — one of the most common and hardest-to-reproduce sources of corruption.

