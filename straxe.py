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

he following table lists the predefined colors:

Constant	Color
COLOR_BLACK	Black
COLOR_BLUE	Blue
COLOR_CYAN	Cyan (light greenish blue)
COLOR_GREEN	Green
COLOR_MAGENTA	Magenta (purplish red)
COLOR_RED	Red
COLOR_WHITE	White
COLOR_YELLOW	Yellow

Ways to group:
  listen for a bit, find groups of operations

Look into refresh args, it can do just a part of the screen.
window.refresh([pminrow, pmincol, sminrow, smincol, smaxrow, smaxcol])
Update the display immediately (sync actual screen with previous drawing/deleting methods).
The 6 optional arguments can only be specified when the window is a pad created with newpad(). The additional parameters are needed to indicate what part of the pad and screen are involved. pminrow and pmincol specify the upper left-hand corner of the rectangle to be displayed in the pad. sminrow, smincol, smaxrow, and smaxcol specify the edges of the rectangle to be displayed on the screen. The lower right-hand corner of the rectangle to be displayed in the pad is calculated from the screen coordinates, since the rectangles must be the same size. Both rectangles must be entirely contained within their respective structures. Negative values of pminrow, pmincol, sminrow, or smincol are treated as if they were zero.

or window.scroll() with many vertical windows (see subwin)

window.subpad([nlines, ncols], begin_y, begin_x)
Return a sub-window, whose upper-left corner is at (begin_y, begin_x), and whose width/height is ncols/nlines.
'''

def get_lines(maxlines=5):
    """ get as many lines as possible from stdin without blocking """
    import fcntl, os
    fl = fcntl.fcntl(sys.stdin.fileno(), fcntl.F_GETFL)
    fcntl.fcntl(sys.stdin.fileno(), fcntl.F_SETFL, fl | os.O_NONBLOCK)
    curr = ''
    while True:
        lines = []
        try:
            for c in sys.stdin.read(1):
                curr += c
                if c == '\n':
                    lines.append(curr)
                    curr = ''
                if len(lines) >= maxlines:
                    break
        except IOError:
            pass
        yield lines

def main(w):
    xx, yy = (curses.COLS - 1), (curses.LINES - 1)
    w = curses.newpad(yy, xx)
    buckets = [' ' * yy] * xx
    for lines in get_lines():
        for line in lines:
            m = strace_re.match(line)
            if not m:
                h = hash(line)
            else:
                h = hash(m.groups())
            h %= len(buckets)
            buckets[h] += line
        redraw(w, buckets, width=xx-1, height=yy-1)


def redraw(w, buckets, width, height, force=False):
    # slide and buckets that need moving
    do = []
    for x, buff in enumerate(buckets):
        if len(buff) >= height or force:
            buckets[x] = buff[1:]
            do.append((x, buff))
    for x, vertical in do:
        if 5 > x > 40:
            continue
        for y, c in enumerate(vertical[:height-2]):
            try:
                w.addch(y, x, ord(c))
            except Exception:
                raise ValueError((y, x))
        w.refresh(0, x, 0, x, height, x)
    return

def start():
    w = curses.initscr()
    curses.curs_set(0) # hide the cursor
    try:
        main(w)
    finally:
        curses.endwin()

if __name__ == '__main__':
    start()
