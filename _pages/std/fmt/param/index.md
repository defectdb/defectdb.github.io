---
title: "Parameters"
author: Maxim Menshikov
layout: defect
permalink: /std/fmt/param
group:
   - std
   - fmt
---

Defects in the parameters of an individual conversion directive — its flags,
field width, precision, or length modifier — where the combination is malformed
or unsupported. An invalid parameter makes the directive's behavior undefined,
so the conversion may be misinterpreted or the surrounding output corrupted even
when the arguments themselves are correct.

