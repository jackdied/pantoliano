import curses
import time
import sys
import re

strace_re = re.compile('(\w+)\((\d*).*?(?:= (\d+).*)?$')

'''
Things to colorize:
  greens:
    HTTP status codes
    HTTP GETs
    HTTP read/writes
  reds:
    SQL queries
    SQL responses
    table names (a_b)
  blues:
    gzip streams
    stats
    file read/write

Ways to group:
  listen for a bit, find groups of operations

Look into refresh args, it can do just a part of the screen.
window.refresh([pminrow, pmincol, sminrow, smincol, smaxrow, smaxcol])¶
Update the display immediately (sync actual screen with previous drawing/deleting methods).
The 6 optional arguments can only be specified when the window is a pad created with newpad(). The additional parameters are needed to indicate what part of the pad and screen are involved. pminrow and pmincol specify the upper left-hand corner of the rectangle to be displayed in the pad. sminrow, smincol, smaxrow, and smaxcol specify the edges of the rectangle to be displayed on the screen. The lower right-hand corner of the rectangle to be displayed in the pad is calculated from the screen coordinates, since the rectangles must be the same size. Both rectangles must be entirely contained within their respective structures. Negative values of pminrow, pmincol, sminrow, or smincol are treated as if they were zero.

or window.scroll() with many vertical windows (see subwin)

window.subpad([nlines, ncols], begin_y, begin_x)¶
Return a sub-window, whose upper-left corner is at (begin_y, begin_x), and whose width/height is ncols/nlines.
'''

def redraw(w, buckets, width, height, force=False):
    redrew = 0
    # slide and buckets that need moving
    for x, buff in enumerate(buckets):
        if len(buff) >= curses.LINES:
            buckets[x] = buff[1:]
            redrew += 1
    lines = [''.join(b[y] for b in buckets) for y in range(height-1)]
    for y, line in enumerate(lines):
        try:
            w.addstr(y, 0, line)
        except Exception as e:
            raise ValueError(((0, y), (width, height), len(line)))
    return redrew

def redraw(w, buckets, width, height, force=False):
    redrew = 0
    # slide and buckets that need moving
    do = []
    for x, buff in enumerate(buckets):
        if len(buff) >= height or force:
            buckets[x] = buff[1:]
            redrew += 1
            do.append((x, buff))
    for x, vertical in do:
        for y, c in enumerate(vertical[:height-1]):
            try:
                w.addch(y, x, ord(c))
            except Exception:
                raise ValueError((y, x))
    return redrew

def main(w):
    xx, yy = (curses.COLS - 1), (curses.LINES - 1)
    buckets = [' ' * yy] * xx
    for line in sys.stdin:
        m = strace_re.match(line)
        if not m:
            h = hash(line)
        else:
            h = hash(m.groups())
        h %= len(buckets)
        buckets[h] += line
        redraw(w, buckets, width=xx, height=yy, force=True)
        while redraw(w, buckets, width=xx-1, height=yy-1):
            w.refresh()

def start():
    w = curses.initscr()
    curses.curs_set(0) # hide the cursor
    try:
        main(w)
    finally:
        curses.endwin()

if __name__ == '__main__':
    start()
