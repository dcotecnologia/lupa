---
layout: default
---

<!-- markdownlint-disable MD041 -->
<div class="more">
 <h2>See it at work</h2>
 <figure>
  <img src="{{ '/screenshots/apps.png' | relative_url }}" alt="Searching for an application with Spotlight for Linux" loading="lazy" width="640" height="173">
  <figcaption>Type a few letters of an application and press Enter.</figcaption>
 </figure>
 <figure>
  <img src="{{ '/screenshots/calculator.png' | relative_url }}" alt="Using the built-in calculator of Spotlight for Linux" loading="lazy" width="640" height="173">
  <figcaption>Type a calculation; Enter copies the result.</figcaption>
 </figure>
</div>
<div class="more">
 <h2>Questions</h2>
 <h3>Which desktops does it work on?</h3>
 <p>It is a GTK 3 app written in Python, so it runs on Linux Mint Cinnamon, GNOME, Xfce, MATE and other GTK desktops. The installer binds Super+Space for you on Cinnamon; on the others you bind a key to the command yourself.</p>
 <h3>How do I install and update it?</h3>
 <p>One command, <a href="{{ '/install/' | relative_url }}">on the install page</a>. Run it again to update; it checks the sha256 of the download against the one GitHub publishes.</p>
 <h3>Does it send my searches anywhere?</h3>
 <p>No. It has no telemetry, history or network of its own. The web search row only opens your browser with the text you typed.</p>
 <h3>Is it a replacement for macOS Spotlight?</h3>
 <p>It covers the daily part: opening apps, finding files and doing quick math from the keyboard. It is not affiliated with Apple. <a href="{{ '/documentation/' | relative_url }}">The documentation</a> lists what it does and its limits.</p>
</div>
