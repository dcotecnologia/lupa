---
layout: page
title: Documentation
description: How Lupa works, how to configure it, what the install script does, and how to fix common problems on Cinnamon and GNOME.
permalink: /documentation/
---

{% capture documentation %}{% include_relative DOCUMENTATION.md %}{% endcapture %}
{{ documentation | remove_first: '# Documentation' }}
