---
title: "Loops"
author: Maxim Menshikov
layout: defect
permalink: /loop
---

Defects in the structure and control of iteration, where the loop's own
machinery — its counter, bound, or update — is malformed. The classic case is a
loop whose controlling variable is missing or never advanced toward its
termination condition, so the iteration either fails to progress as intended or
runs without the bound the code assumed.

Such mistakes are easy to overlook because the loop body may look complete and
correct; the fault lies in the scaffolding around it, which determines whether
the loop runs the right number of times, the wrong number, or forever.

