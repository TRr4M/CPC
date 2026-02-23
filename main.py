from io import StringIO
from contextlib import redirect_stdout
import curses
import threading
import math

default_locs = {i: eval(f"math.{i}") for i in ["pi", "sin", "cos", "tan", "pow", "floor", "ceil", "e"]}

stdscr = curses.initscr()
curses.start_color()
curses.cbreak()

text_buffer = [""]
thread: None | threading.Thread = None

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

keywords = {"import", "in", "for", "if", "while", "else", "elif", "try", "except",
    "pass", "continue", "break", "def", "local", "global", "nonlocal", "return",
    "and", "or", "as", "class"}
ops = set("*()-+=[]{},.<>/:|&")
bools = {"True", "False", "None", "not"}
valid_name_start = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_")
valid_name_chars = valid_name_start.union(set("0123456789"))

def print_highlighted(scr: curses.window, text: str, modifier: int = 0):
    i = 0
    class_names: set[str] = set()

    def string(fstring: bool = False):
        nonlocal i
        start_char = text[i]
        j = i + 1
        while j < len(text) and text[j] != start_char:
            if text[j] == "\\":
                # FIXME highlight special differently
                j += 2
            elif text[j] == "{" and fstring:
                scr.addstr(text[i:j], modifier | C_STR)
                scr.addstr(text[j], modifier | C_SPECIAL)
                i = j + 1
                default("}")
                if i < len(text):
                    scr.addstr(text[i], modifier | C_SPECIAL)
                    i += 1
                    j = i
                else:
                    j = i
            else:
                j += 1
        j += 1
        scr.addstr(text[i:j], modifier | C_STR)
        i = j

    def default(end=None):
        nonlocal i
        while i < len(text) and text[i] != end:
            # Whitespace
            if text[i] in " \n\t":
                scr.addstr(text[i], modifier)
                i += 1
                continue

            # Numbers
            if text[i] in "0123456789":
                j = i
                while j < len(text) and text[j] in "0123456789.":
                    j += 1
                scr.addstr(text[i:j], modifier | C_NUM)
                i = j
                continue

            # Strings
            if text[i] == '"' or text[i] == "'":
                string()
                continue
            if i < len(text) - 1 and (text[i:i+2] == "f'" or text[i:i+2] == 'f"'):
                scr.addstr("f", modifier | C_SPECIAL)
                i += 1
                string(True)
                continue

            # Ops
            cut_text = text[i:]
            found_op = False
            for op in ops:
                if cut_text.startswith(op):
                    scr.addstr(op, modifier | C_OP)
                    i += len(op)
                    found_op = True
                    break
            if found_op:
                continue

            if text[i] in valid_name_start:
                word = ""
                while i < len(text) and text[i] in valid_name_chars:
                    word += text[i]
                    i += 1

                # Keywords
                if word in keywords:
                    scr.addstr(word, modifier | C_KEYWORD)
                    continue

                # Bools
                if word in bools:
                    scr.addstr(word, modifier | C_BOOL)
                    continue

                # Functions
                if i < len(text) and text[i] == "(":
                    scr.addstr(word, modifier | C_FUNC)
                    continue

                # Classes
                if word in class_names:
                    scr.addstr(word, modifier | C_CLASS)
                    continue

                # Variables
                scr.addstr(word, modifier | C_VAR)
                continue

            # Comments
            if text[i] == "#":
                j = i
                while j < len(text) and text[j] != "\n":
                    j += 1
                j += 1
                scr.addstr(text[i:j], modifier | C_COMMENT)
                i = j
                continue

            break

    default()
    # Unable to parse the rest
    scr.addstr(text[i:], modifier)

def print_result(r: str):
    y, x = curses.getsyx()
    # FIXME account for lines that wrap
    stdscr.addstr(max(curses.LINES - r.count("\n") - 1, len(text_buffer) + 1), 0, str(r), curses.A_BOLD | curses.A_REVERSE)
    stdscr.move(y, x)
    curses.setsyx(y, x)

def run():
    def target():
        exec_code = "\n".join(text_buffer[:-1])
        eval_code = text_buffer[-1]
        if eval_code.startswith(" "):
            exec_code += "\n" + eval_code
            eval_code = ""
        locs = default_locs.copy()
        f = StringIO()
        with redirect_stdout(f):
            try:
                exec(exec_code, locals=locs, globals=locs)
                if len(eval_code) > 0:
                    r = eval(eval_code, locals=locs)
                    print(r)
            except Exception as e:
                print(f"({e})")
        print_result(f.getvalue())
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
            elif text_buffer[y][((x-1)//4)*4:x].replace(" ", "") == "":
                text_buffer[y] = text_buffer[y][0:((x-1)//4)*4] + text_buffer[y][x:]
                x = ((x-1)//4)*4
            else:
                text_buffer[y] = text_buffer[y][0:x - 1] + text_buffer[y][x:]
                x -= 1
        elif c == 330: # DELETE
            if x == len(text_buffer[y]):
                if y < len(text_buffer) - 1:
                    text_buffer[y] += text_buffer.pop(y + 1)
            else:
                text_buffer[y] = text_buffer[y][0:x] + text_buffer[y][x + 1:]
        elif c == ord("\t"):
            text_buffer[y] = text_buffer[y][0:x] + "    " + text_buffer[y][x:]
            x += 4
        else:
            text_buffer[y] = text_buffer[y][0:x] + chr(c) + text_buffer[y][x:]
            x += 1

curses.wrapper(main)
