import contextlib
import curses
import itertools as it
import time
import sys
import re
import random

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
'''

def log(*args):
    open('log', 'a+').write(repr(args) + '\n')

def colorize_line(line, colorizers=[]):
    """ yield (color, text) pairs if the line matches the map.
        the regular expressions should use the color name as the match name.
        '(?P<GREEN>hello)'
    """
    answer = dict((i, 'PLAIN_') for i in range(len(line)))
    for regexp in colorizers:
        m = re.search(regexp, line)
        also = '_'
        if m:
            assert len(m.groups()) == 1, "Multiple Groups Not Supported"
            for color, text in m.groupdict().items():
                if color[-1] in 'XB':
                    also = ''
                for i, c in enumerate(m.group(1), m.start()):
                    answer[i] = color + also
    for i, c in enumerate(line):
        yield (c, answer[i])
    return

def get_lines(howlong=0.1):
    """ get as many lines as possible from stdin without blocking """
    import fcntl, os
    fl = fcntl.fcntl(sys.stdin.fileno(), fcntl.F_GETFL)
    fcntl.fcntl(sys.stdin.fileno(), fcntl.F_SETFL, fl | os.O_NONBLOCK)
    curr = ''
    while True:
        lines = []
        start = time.time()
        endtime = time.time() + howlong
        while not lines:
            try:
                for c in sys.stdin.read(10):
                    curr += c
                    if c == '\n':
                        lines.append(curr)
                        curr = ''
                        break
            except IOError:
                pass
        log(len(lines), time.time() - endtime, time.time() < endtime, '%25.3f %25.3f %25.3f' % (start, time.time(), endtime))
        yield lines


strace_re = re.compile('(\w+)\((\d*).*?(?:= (\d+).*)?$')

def main(w):
    xx, yy = (curses.COLS - 1), (curses.LINES - 1)
    xx = 127
    w = curses.newpad(yy, xx)
    buckets = [list(colorize_line(' ' * yy)) for _ in range(xx)]
    coloring = ['(?P<GREEN>SELECT)', '(?P<BLUE>(?:lstat|stat))', '^(?P<RED>writev)',
                '"(?P<RED>HTTP/[^"]+)', '/data/code/(?P<CYAN>[^.]+\.\w*)',
                '(?P<WHITEB>GET[^"]+)"', '(?P<YELLOWB>portal_\w+_\w+_\w+)',
               ]
    for lines in get_lines():
        for line in lines:
            m = strace_re.match(line)
            if not m:
                h = hash(line)
            else:
                h = hash(m.groups())
            h %= len(buckets)
            if len(buckets[h]) < 1024 * 5: # skip backlogs
                buckets[h] += list(colorize_line(line, coloring))
        redraw(w, buckets, width=xx, height=yy-1)


def redraw(w, buckets, width, height):
    # slide and buckets that need moving
    do = []
    for x, buff in enumerate(buckets):
        if len(buff) >= height:
            buckets[x] = buff[1:]
            do.append((x, buff))
    if False and len(do) > 0.3 * len(buckets):
        redraw_fullscreen(w, buckets, width, height)
    else:
        redraw_incremental(w, do, width, height)

def print_this(w, cname, func, args):
    also = cname[-1]
    cname = cname[:-1]
    color = color_map[cname]
    w.attrset(curses.color_pair(color))
    if also == 'B':
        w.attrset(curses.A_BLINK)
    elif also == 'X':
        w.attrset(curses.A_BOLD)
    else:
        w.attroff(curses.A_BLINK | curses.A_BOLD)
    func(*args)

def redraw_fullscreen(w, buckets, width, height):
    for y in range(height-3):
        row = [bucket[y] for bucket in buckets]
        x = 0
        for color, pairs in it.groupby(row, lambda x:x[1]):
            text = ''.join(char for char, color in pairs)
            try:
                log(color, x, y, text, len(text), len(row))
                print_this(w, color, w.addstr, (y, x, text))
            except Exception:
                raise ValueError((color, (x, y, text), len(row)))
            x += len(text)
    w.refresh(0, 0, 0, 0, height, width)

def redraw_incremental(w, do, width, height):
    for x, vertical in do:
        for y, cpair in enumerate(vertical[:height]):
            char, cname = cpair
            print_this(w, cname, w.addch, (y, x, ord(char)))
        w.refresh(0, x, 0, x, height, x)
    return

color_map = {}

def start():
    global color_map
    w = curses.initscr()
    curses.curs_set(0) # hide the cursor
    curses.start_color() # announce it isn't 1985
    try:
        color_map = {'PLAIN': 0, 'GREEN' : 1, 'RED': 2, 'BLUE':3, 'CYAN':4, 'WHITE':5, 'YELLOW':6}
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_WHITE)
        curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_RED)
        curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(6, curses.COLOR_YELLOW, curses.COLOR_WHITE)
        main(w)
    finally:
        curses.endwin()

if __name__ == '__main__':
    start()
