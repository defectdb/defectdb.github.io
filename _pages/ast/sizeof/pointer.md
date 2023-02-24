---
title: sizeof() is likely to be misused
author: Maxim Menshikov
layout: defect
permalink: /ast/sizeof/pointer
arch:
   - native
vulnerability:
   - None
ddos:
   - None
group_full: ast.sizeof
group:
   - ast
   - sizeof
---

sizeof() is used on pointer rather than array
