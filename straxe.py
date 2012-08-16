import curses
import time
import sys
import re

strace_re = re.compile('(\w+)\((\d*).*?(?:= (\d+).*)?$')

'''
Things to colorize:
  HTTP status codes
  HTTP GETs
  HTTP read/writes
  gzip streams
  SQL queries
  SQL responses

Ways to group:
  listen for a bit, find groups of operations
'''

def redraw(w, buckets, force=False):
    redrew = 0
    for x, buff in enumerate(buckets):
        for y, c in enumerate(buff[:curses.LINES-1]):
            if not (force or len(buff) > curses.LINES):
                continue
            try:
                w.addch(y, x, ord(c))
            except Exception:
                raise ValueError(((x, y), (curses.COLS, curses.LINES)))
            if len(buff) > curses.LINES:
                buckets[x] = buff[1:]
                redrew += 1
    return redrew

def main(w):
    buckets = [''] * curses.COLS
    for line in sys.stdin:
        m = strace_re.match(line)
        if not m:
            h = hash(line)
        else:
            h = hash(m.groups())
        h %= len(buckets)
        buckets[h] += line
        #w.erase()
        redraw(w, buckets, force=True)
        while redraw(w, buckets):
            w.refresh()

def start():
    try:
        w = curses.initscr()
        main(w)
    finally:
        curses.endwin()

if __name__ == '__main__':
    start()
