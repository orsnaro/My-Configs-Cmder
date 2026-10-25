---
name: Something is not working
about: Vitreus will not install, will not start, or something in it is wrong
title: ""
labels: bug
---

**What were you doing, and what went wrong?**
(In your own words. "I clicked the calendar and nothing opened" is a good report.)

**Run this one line in a terminal, then attach the file it makes** (drag it into this box):

```sh
curl -fsSL https://raw.githubusercontent.com/natepayn3/Vitreus/main/bin/vitreus-report | sh
```

It works even if Vitreus did not install or will not start. It writes one plain-text file to your Desktop; open it and look
before you attach it. It blanks out your user name, computer name, network addresses and monitors' names, and it does not
read your notifications, clipboard, calendar or files.
