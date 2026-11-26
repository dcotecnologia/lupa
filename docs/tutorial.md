---
layout: page
title: Tutorial
description: "A five-minute tour of Lupa: open it with Super+Space, launch apps, do quick math, find files and search the web."
permalink: /tutorial/
---

{% capture tutorial %}{% include_relative TUTORIAL.md %}{% endcapture %}
{{ tutorial | remove_first: '# Tutorial' }}
