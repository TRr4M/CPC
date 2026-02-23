import os
import curses
import threading
import math

stdscr = curses.initscr()
curses.start_color()
curses.cbreak()

os.system("clear")

text_buffer = [""]
thread: None | threading.Thread = None

default_locs = {i: eval(f"math.{i}") for i in ["pi", "sin", "cos", "tan", "pow", "floor", "ceil"]}

curses.init_pair(1, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
C_KEYWORD = curses.color_pair(1)
curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
C_CLASS = curses.color_pair(2)
curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_BLACK)
C_VAR = curses.color_pair(3)
curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLACK)
C_OP = curses.color_pair(4)
curses.init_pair(5, curses.COLOR_YELLOW, curses.COLOR_BLACK)
C_FUNC = curses.color_pair(5)
curses.init_pair(6, curses.COLOR_RED, curses.COLOR_BLACK)
C_STR = curses.color_pair(6)
curses.init_pair(7, curses.COLOR_CYAN, curses.COLOR_BLACK)
C_NUM = curses.color_pair(7)
curses.init_pair(8, curses.COLOR_BLUE, curses.COLOR_BLACK)
C_BOOL = curses.color_pair(8)
curses.init_pair(9, curses.COLOR_BLUE, curses.COLOR_BLACK)
C_SPECIAL = curses.color_pair(9)
curses.init_pair(10, curses.COLOR_GREEN, curses.COLOR_BLACK)
C_COMMENT = curses.color_pair(10) | curses.A_ITALIC

keywords = ["import", "in", "for", "if", "while", "else", "elif", "try", "except",
    "pass", "continue", "break", "def", "local", "global", "nonlocal"]
ops = list("*()-+=[]{},.<>/:|&")
bools = ["True", "False", "None", "not"]

def print_highlighted(scr: curses.window, text: str, modifier: int = 0):
    i = 0

    def string():
        nonlocal i
        start_char = text[i]
        j = i + 1
        while text[j] != start_char:
            if text[j] == "\\":
                # FIXME highlight special differently
                j += 2
            else:
                j += 1
        j += 1
        scr.addstr(text[i:j], modifier | C_STR)
        i = j

    def default():
        nonlocal i
        while i < len(text):
            if text[i] in " \n\t":
                scr.addstr(text[i], modifier)
                i += 1
                continue


    default()

def print_result(r):
    y, x = curses.getsyx()
    stdscr.addstr(min(curses.LINES - 1, len(text_buffer) + 1), 0, str(r), curses.A_BOLD)
    # print_highlighted(stdscr, str(r), min(curses.LINES - 1, len(text_buffer) + 1), curses.A_BOLD)
    stdscr.move(y, x)
    curses.setsyx(y, x)

def run():
    def target():
        try:
            exec_code = "\n".join(text_buffer[:-1])
            eval_code = text_buffer[-1]
            locs = default_locs.copy()
            exec(exec_code, locals=locs)
            r = eval(eval_code, locals=locs)
        except:
            pass # print_result("FAILED")
        else:
            print_result(r)
    thread = threading.Thread(target=target)
    thread.start()

def main(stdscr: curses.window):
    x = 0
    y = 0

    def re_render():
        stdscr.clear()
        # stdscr.addstr(0, 0, "\n".join([i[:curses.COLS] for i in text_buffer]))
        print_highlighted(stdscr, "\n".join([i[:curses.COLS] for i in text_buffer]))
        stdscr.move(y, min(x, curses.COLS - 1))
        curses.setsyx(y, min(x, curses.COLS - 1))
        stdscr.refresh()

    while True:
        if thread is not None:
            thread.join(0)
        re_render()
        run()
        c = stdscr.getch()
        if c == ord("\n"):
            l = text_buffer[y][x:]
            text_buffer[y] = text_buffer[y][:x]
            x = 0
            y += 1
            text_buffer.insert(y, l)
        elif c == curses.KEY_LEFT:
            x -= 1
            if x < 0:
                y -= 1
                if y < 0:
                    y = 0
                    x = 0
                else:
                    x = len(text_buffer[y])
        elif c == curses.KEY_RIGHT:
            x += 1
            if x > len(text_buffer[y]):
                if y < len(text_buffer) - 1:
                    x = 0
                    y += 1
                else:
                    x -= 1
        elif c == curses.KEY_UP:
            y -= 1
            if y < 0:
                y = 0
                x = 0
            else:
                x = min(x, len(text_buffer[y]))
        elif c == curses.KEY_DOWN:
            y += 1
            if y >= len(text_buffer):
                y -= 1
                x = len(text_buffer[y])
            else:
                x = min(x, len(text_buffer[y]))
        elif c == curses.KEY_BACKSPACE:
            if x == 0:
                if y != 0:
                    l = text_buffer.pop(y)
                    y -= 1
                    x = len(text_buffer[y])
                    text_buffer[y] += l
            else:
                text_buffer[y] = text_buffer[y][0:x - 1] + text_buffer[y][x:]
                x -= 1
        elif c == 330: # DELETE
            if x == len(text_buffer[y]):
                if y < len(text_buffer) - 1:
                    text_buffer[y] += text_buffer.pop(y + 1)
            else:
                text_buffer[y] = text_buffer[y][0:x] + text_buffer[y][x + 1:]
        else:
            text_buffer[y] = text_buffer[y][0:x] + chr(c) + text_buffer[y][x:]
            x += 1

try:
    curses.wrapper(main)
except:
    pass
