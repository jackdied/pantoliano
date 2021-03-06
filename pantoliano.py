import collections
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
        while time.time() < endtime and len(lines) < 20:
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

def jaccard(past, curr):
    old = set()
    for line in past:
        old |= line
    curr = set(curr)
    try:
        return float(len(old & curr)) /float(len(old | curr))
    except ZeroDivisionError:
        return 0

def bucket_finder(past, curr):
    # jaccard similarity
    best = -1
    which = None
    scores = [jaccard(lines, curr) for lines in past]
    #log(list('%4.2f' % v for v in scores))
    for i, score in enumerate(scores):
        if score > best:
            best = score
            which = i
    return which + random.randrange(-3, 3)

def main(w):
    xx, yy = (curses.COLS - 1), (curses.LINES - 1)
    w = curses.newpad(yy, xx)
    buckets = [list(colorize_line(' ' * yy)) for _ in range(xx-1)]
    the_past = [collections.deque([], 5) for _ in range(xx-1)]
    coloring = ['(?P<GREEN>SELECT)', '(?P<BLUE>(?:lstat|stat))', '^(?P<RED>writev)',
                '"(?P<RED>HTTP/[^"]+)', '(?P<CYAN>/data/code/[^.]+\.\w*)',
                '(?P<WHITEB>GET[^"]+)"', '(?P<YELLOWB>portal_\w+_\w+_\w+)',
                '(?P<YELLOWB>(?:masterapp|activitystream|analytics|api|comments|dashbaord|front_end|limit|socialmedia|tagging|userauth|entity)_\w+)',
               ]
    count = 0
    for lines in get_lines():
        log(len(lines))
        for line in lines:
            line = line.replace('\n', ' ')
            if count % 50 == 0:
                h = random.randrange(0, len(buckets))
            elif count < len(buckets) * 5:
                m = strace_re.match(line)
                if m:
                    h = hash(m.groups())
                else:
                    h = random.randrange(10, len(buckets))
                h = h % len(buckets)
            else:
                h = max(0, min(len(buckets)-1, bucket_finder(the_past, line)))
            #log('hash', h)
            if len(buckets[h]) < 1024: # avoid overflows
                the_past[h].append(tokenize(line))
                buckets[h] += list(colorize_line(line, coloring))
            count += 1
        redraw(w, buckets, width=xx, height=yy-1, bold=(count < buckets * 50))

def tokenize(line):
    parts = line.split()
    out = set()
    for part in parts:
        if re.match('^[a-zA-Z0-9]+$', part):
            out.add(part)
    return out

def redraw(w, buckets, width, height, bold=False):
    # slide and buckets that need moving
    do = []
    for x, buff in enumerate(buckets):
        if len(buff) >= height:
            step = max(1, len(buff)/200)
            buckets[x] = buff[step:]
            do.append((x, buff))
    redraw_fullscreen(w, buckets, width, height)

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
                #log(color, x, y, text, len(text), len(row))
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
