---
title: "Security"
author: Maxim Menshikov
layout: defect
permalink: /cpp/security
group:
   - cpp
---

Security-relevant defects where a correctness gap becomes an exploitable one. The entry here is the time-of-check / time-of-use race: a program validates a resource — a file's existence, permissions, or type — and then acts on it as a separate step, leaving a window in which an attacker substitutes something else between the check and the use, defeating the validation entirely.
