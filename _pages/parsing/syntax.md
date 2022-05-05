---
title: Syntax error
author: Maxim Menshikov
layout: defect
permalink: /parsing/syntax
arch:
   - native
vulnerability:
   - None
ddos:
   - None
group_full: parsing
group:
   - parsing
---

Syntax errors might appear in the source code due to misuse of syntax constructions and typos.

# Impact
No impact except slowdown in the development.

# Vulnerability potential

None.

# Technical details

When the code is being read, it is processed by lexical analyzer in order to tokenize it (split to separate meaningful words). After tokenization, the syntax analyzer tries to determine the syntax structure of the code. If the syntax structure doesn't comply with the language specification, the code is considered *ill-formed*.
