"""A real, synthetic X11 button click (XTest) for UI that CDP cannot see.

Chrome's native extension-permission dialog (and other browser-chrome-
level UI) is not part of any page DOM -- Playwright's page.click() has
nothing to target. XTest.fake_input sends the same class of event a
physical mouse does, through the real X server input pipeline, so this
is a real click, not a simulation shortcut.
"""

import time

from Xlib import X, display
from Xlib.ext import xtest


def click(x: int, y: int, disp: str = None):
    import os
    d = display.Display(disp or os.environ.get("DISPLAY", ":99"))
    try:
        d.sync()
        xtest.fake_input(d, X.MotionNotify, x=x, y=y)
        d.sync()
        time.sleep(0.1)
        xtest.fake_input(d, X.ButtonPress, 1)
        d.sync()
        time.sleep(0.05)
        xtest.fake_input(d, X.ButtonRelease, 1)
        d.sync()
    finally:
        d.close()
