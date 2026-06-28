---
title: "Abstract Syntax Tree"
author: Maxim Menshikov
layout: defect
permalink: /ast
---

Defects that surface in the shape of the program itself — the abstract syntax tree — rather than in its runtime values or types. These are problems a tool can see by inspecting how an expression is built: which operator joins which operands, and what the operands actually denote.

Because the evidence is structural, the entries here tend to be high-confidence, language-agnostic smells. A binary operator applied to two textually identical operands, or a `sizeof` whose operand is not the thing the author meant to measure, are both wrong on their face regardless of the values that flow through them at run time.

