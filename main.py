"""
Green characters raining down in the terminal.
You might need to restart the terminal window if colors get messed up.
Press any key to exit.
"""
import argparse
import curses
import itertools
import random
import string
import sys
import time


LATIN     = list(string.ascii_letters + string.digits + string.punctuation)
KATAKANA  = range(0x30a0, 0x30ff)
HIRAGANA  = range(0x3041, 0x3097)
KANGXI    = range(0x2f00, 0x2fd5)
NON_LATIN = [chr(c) for c in itertools.chain(KATAKANA, HIRAGANA, KANGXI)]


def random_character(latin_chance=0.6):
    """
    Draw one random token with 2 character width.
    Latin characters, punctuation and digits are weighted to provide a more even distribution.
    """
    if random.random() < latin_chance:
        return random.choice(LATIN) + random.choice(LATIN)
    else:
        return random.choice(NON_LATIN)


class Character:
    """
    Single character in a Column.
    """
    def __init__(self, start_pos, color, symbol=None):
        if symbol is None:
            symbol = random_character()
        self.y, self.x = start_pos
        self.symbol = symbol
        self.color = color


class Column:
    """
    Column of characters falling down with a constant speed.
    """
    def __init__(self, head, colors, min_falling_speed, width):
        self.min_falling_speed = min_falling_speed
        self.characters = []
        self.width = width
        for dy, color in enumerate(colors):
            point = (head[0] - dy, head[1])
            self.characters.append(Character(point, color))

    def step(self, screen):
        """
        Apply the falling speed of this column to y components of all characters and draw them on screen.
        Returns False if the column has crossed the bottom edge of the screen.
        """
        max_y, _ = screen.getmaxyx()
        allowed_y = range(0, max_y)
        def is_on_screen(y):
            return y in allowed_y
        still_visible = False
        y, x = -1, -1
        for char in self.characters:
            y, x = int(char.y), char.x
            char.y += self.min_falling_speed
            if not is_on_screen(y):
                continue
            still_visible = True
            screen.addstr(y, x, char.symbol, char.color)
        # Clear trail of characters after column
        y -= 1
        while is_on_screen(y):
            screen.addstr(y, x, ' '*self.width)
            y -= 1
        return still_visible

    def reset(self, new_min_falling_speed):
        """
        Set new falling speed and generate a new set of characters with the bottom character of
        the column at the top of the screen.
        """
        self.min_falling_speed = new_min_falling_speed
        for dy, char in enumerate(self.characters):
            char.y = -dy
            char.symbol = random_character()


class Rain:
    """
    Column container and terminal instance manipulation.
    """
    def __init__(self, screen, time_step_sec, min_falling_speed):
        self.screen = screen
        self.time_step_sec = time_step_sec
        self.min_falling_speed = min_falling_speed
        self.columns = None
        self.color_pairs = None
        self.column_spacing = 2

    def generate_green_palette(self):
        """
        Generate green palette and overwrite terminal colors.
        """
        # Overwrite terminal colors
        dg = int(1000/min(8, curses.COLORS-1))
        greens = [(0, g, 0) for g in range(1000, dg,  -dg)]
        for i, green in enumerate(greens, start=1):
            curses.init_color(i, *green)
            curses.init_pair(i, i, curses.COLOR_BLACK)

        # Get the overwritten color pairs
        color_pairs = [curses.color_pair(color_id) for color_id in
                       range(1, len(greens)+1)]
        # Stretch the palette so the colors at the ends
        # 'fade in' and 'fade out', but the middle is a longer,
        # continuous sequence of one color
        middle_index = len(color_pairs)//2
        head = color_pairs[:middle_index]
        tail = color_pairs[1 + middle_index:]
        column_height = self.screen.getmaxyx()[0]
        middle = [color_pairs[middle_index] for _ in
                  range(0, column_height)]
        self.color_pairs = head + middle + tail

    def _random_falling_speed(self):
        return random.uniform(self.min_falling_speed, self.min_falling_speed*10)

    def _generate_column(self, x):
        falling_speed = self._random_falling_speed()
        return Column((0, x), self.color_pairs, falling_speed, self.column_spacing)

    def generate_all_columns(self):
        max_x = self.screen.getmaxyx()[1] - self.column_spacing
        self.columns = [self._generate_column(x) for x in
                        range(0, max_x, self.column_spacing)]

    def step(self):
        for column in self.columns:
            if not column.step(self.screen):
                column.reset(self._random_falling_speed())
        self.screen.refresh()
        time.sleep(self.time_step_sec)


def terminal_ok():
    ok = True
    if curses.COLORS < 2 or not curses.has_colors():
        print("ncurses has too few colors in this terminal", file=sys.stderr)
        ok = False
    if not curses.can_change_color():
        print("ncurses cannot change colors in this terminal", file=sys.stderr)
        ok = False
    return ok


def main(screen, time_step_sec, min_falling_speed):
    # Hide cursor
    curses.curs_set(0)
    # Non-blocking getch
    screen.nodelay(1)

    curses.start_color()

    if not terminal_ok():
        sys.exit(1)

    r = Rain(screen, time_step_sec, min_falling_speed)

    r.generate_green_palette()
    r.generate_all_columns()

    # Run animation until any key is pressed
    while screen.getch() == -1:
        r.step()

    screen.clear()
    screen.refresh()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--time-step-sec",
            type=float,
            default=0.01,
            help="Seconds to sleep between rendering steps")
    parser.add_argument("--min-falling-speed",
            type=float,
            default=0.05,
            help="Minimum falling speed for characters.")
    args = parser.parse_args()

    curses.wrapper(main, args.time_step_sec, args.min_falling_speed)
