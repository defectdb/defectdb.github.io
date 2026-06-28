---
title: "Result"
author: Maxim Menshikov
layout: defect
permalink: /fn/result
group:
   - fn
---

Defects in how a function's return value is consumed, chiefly the failure to
consume it at all. When a result that reports an error, a status, or a computed
output is discarded, the program proceeds as though the call succeeded and
produced nothing of consequence — masking failures and acting on state that was
never actually established.

