import contextlib
import curses
import time
import sys
import re
import random

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

def log(*args):
    open('log', 'a+').write(repr(args) + '\n')

def colorize_line(line, colorizers=[]):
    """ yield (color, text) pairs if the line matches the map.
        the regular expressions should use the color name as the match name.
        '(?P<GREEN>hello)'
    """
    answer = dict((i, 'PLAIN') for i in range(len(line)))
    for regexp in colorizers:
        m = re.search(regexp, line)
        if m:
            assert len(m.groups()) == 1, "Multiple Groups Not Supported"
            for color, text in m.groupdict().items():
                for i, c in enumerate(m.group(1), m.start()):
                    answer[i] = color
    for i, c in enumerate(line):
        yield (c, answer[i])
    return

def get_lines(maxlines=5):
    """ get as many lines as possible from stdin without blocking """
    import fcntl, os
    fl = fcntl.fcntl(sys.stdin.fileno(), fcntl.F_GETFL)
    fcntl.fcntl(sys.stdin.fileno(), fcntl.F_SETFL, fl | os.O_NONBLOCK)
    curr = ''
    while True:
        lines = []
        try:
            for c in sys.stdin.read(10):
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
    ww = w
    w = curses.newpad(yy, xx)
    buckets = [list(colorize_line(' ' * yy)) for _ in range(xx)]
    coloring = ['(?P<GREEN>SELECT)']
    for lines in get_lines():
        for line in lines:
            m = strace_re.match(line)
            if not m:
                h = hash(line)
            else:
                h = hash(m.groups())
            h %= len(buckets)
            buckets[h] += list(colorize_line(line, coloring))
        redraw(w, buckets, width=xx, height=yy-1, ww=ww)


def redraw(w, buckets, width, height, ww):
    # slide and buckets that need moving
    do = []
    for x, buff in enumerate(buckets):
        if len(buff) >= height:
            buckets[x] = buff[1:]
            do.append((x, buff))
    for x, vertical in do:
        for y, cpair in enumerate(vertical[:height]):
            char, color = cpair
            color = color_map[color]
            w.attrset(curses.color_pair(color))
            w.addch(y, x, ord(char))
        w.refresh(0, x, 0, x, height, x)
    return

color_map = {}

def start():
    global color_map
    w = curses.initscr()
    curses.curs_set(0) # hide the cursor
    curses.start_color() # announce it isn't 1985
    try:
        color_map = {'PLAIN': 0, 'GREEN' : 1}
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_BLACK)
        main(w)
    finally:
        curses.endwin()

if __name__ == '__main__':
    start()
