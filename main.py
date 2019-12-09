import os
import time
import json
from random import randint

import sublime
import sublime_plugin

""" 目前
Sublime关闭时，保存每一个View的游戏记录，
关闭一个View时，如果该View有游戏记录，将它的记录保存至全局记录

新启动游戏时，加载全局游戏记录作为View的初始游戏记录
"""

sublime2048_record = "sublime2048.sublime-settings"

class Score():
    def __init__(self):
        self.current = 0
        self.highest = 0

    def increase(self, delta):
        self.current += delta
        self.highest = max(self.current, self.highest)

# 尚未实现动态计算各个数值区域的代码
status_regions = [(136, 143), (144, 151), (152, 159), (160, 167)]

grid_regions = [
    [(304, 311), (312, 319), (320, 327), (328, 335)],
    [(472, 479), (480, 487), (488, 495), (496, 503)],
    [(640, 647), (648, 655), (656, 663), (664, 671)],
    [(808, 815), (816, 823), (824, 831), (832, 839)]
]


class Grid():
    def __init__(self, record):
        self.score = Score()
        self.regions = [
            [sublime.Region(a, b) for a, b in row]
            for row in grid_regions
        ]
        try:
            self.load(record)
        except:
            self.reset()

    def reset(self):
        self.numbers = [[0 for j in range(4)] for i in range(4)]
        self.nblank = 16
        self.maxnum = 0
        self.score.current = 0
        self.add_randnum()

    def load(self, record):
        try:
            self.numbers = record["numbers"]
            self.score.highest = record["score"]["highest"]
            self.score.current = record["score"]["current"]
            self.nblank = len([i for r in self.numbers for i in r if i == 0])
            self.maxnum = max(max(self.numbers))
        except:
            self.reset()
            self.score.highest = 0

    def record(self):
        return {
            "time": time.strftime("%Y%m%d %H:%M:%S"),
            "numbers": self.numbers,
            "score": {
                "highest": self.score.highest,
                "current": self.score.current
            }
        }

    def add_randnum(self):
        # 控制数字2和4的概率,此时2出现概率是80%
        randidx = randint(0, 100) % self.nblank
        randnum = (2, 4)[randint(1, 100) // 80]
        self.maxnum = max(randnum, self.maxnum)

        count = 0
        for i in range(4):
            for j in range(4):
                if self.numbers[i][j] == 0:
                    if count == randidx:
                        self.numbers[i][j] = randnum
                        self.nblank -= 1
                        return (i, j)
                    count += 1

    def movable(self):
        if self.nblank > 0:
            return True
        for i in range(4):
            for j in range(1, 4):
                if (self.numbers[i][j - 1] == self.numbers[i][j] or
                    self.numbers[j - 1][i] == self.numbers[j][i]):
                    return True
        return False


def genmove(inc, begin, end, index):
    def move(grid):
        numbers = grid.numbers
        nblank, score, moved = 0, 0, 0
        for i in range(4):
            k = begin
            for j in range(begin, end, inc(0) - 0):
                x1, y1 = index(i, k)
                x2, y2 = index(i, j)
                if j == k or numbers[x2][y2] == 0:
                    continue
                if numbers[x1][y1] == numbers[x2][y2]:
                    numbers[x1][y1] <<= 1
                    grid.maxnum = max(numbers[x1][y1], grid.maxnum)
                    score += numbers[x1][y1]
                    nblank += 1
                    k = inc(k)
                else:
                    if numbers[x1][y1]:
                        k = inc(k)
                        if k == j:
                            continue
                    x1, y1 = index(i, k)
                    numbers[x1][y1] = numbers[x2][y2]

                numbers[x2][y2] = 0
                moved = 1

        if score > 0:
            grid.nblank += nblank
            grid.score.increase(score)
            return score

        return moved

    return move


class Board():
    moves = {
        "↑": genmove(lambda n: n + 1, 0, +4, lambda x, y: (y, x)),
        "↓": genmove(lambda n: n - 1, 3, -1, lambda x, y: (y, x)),
        "←": genmove(lambda n: n + 1, 0, +4, lambda x, y: (x, y)),
        "→": genmove(lambda n: n - 1, 3, -1, lambda x, y: (x, y))
    }
    def __init__(self, record={}):
        self.grid = Grid(record)

    def best(self):
        return self.grid.score.highest

    def score(self):
        return self.grid.score.current

    def add_randnum(self):
        if self.grid.nblank > 0:
            self.grid.add_randnum()

    def background(self, x, y):
        i = 0
        while (1 << i) < self.grid.numbers[x][y]:
            i += 1
        return self.backgrounds[i]

    def move(self, direction):
        return self.moves[direction](self.grid)

    def isalive(self):
        return self.grid.movable()

    def iswon(self):
        return self.grid.maxnum >= 2048


class Sublime2048(sublime_plugin.TextCommand):
    def run(self, edit, command=None, key=None, record=None):
        if command == "move":
            self.arrow = key
            self.moved = self.board.move(key)
            if self.moved:
                self.board.add_randnum()
                if not self.board.isalive():
                    self.game_over()

                self.refresh(edit)

        elif command == "reset":
            self.board.grid.reset()
            self.refresh(edit)

        elif command == "setup":
            self.setup(edit, record or self.load_record())

        elif command == "save":
            record = self.board.grid.record()
            self.view.settings().set("record", record)

        elif command == "save_record":
            self.save_record()

    def game_over(self):
        pass

    def setup(self, edit, record):
        view = self.view
        view.set_name("2048")
        view.set_scratch(True)
        view.assign_syntax("sublime2048.sublime-syntax")
        view.settings().set("sublime2048", True)
        view.settings().set("color_scheme",
            "Material-Lighter.sublime-color-scheme")
        view.run_command('append', {'characters': """
        ╔═══════╤═══════╤═══════╤═══════╗
        ║ SCORE │  BEST │  Key  │  Get  ║
        ╟───────┼───────┼───────┼───────╢
        ║       │       │       │       ║
        ╠═══════╧═══════╧═══════╧═══════╣
        ╠═══════╤═══════╤═══════╤═══════╣
        ║       │       │       │       ║
        ║   2   │   4   │   8   │   16  ║
        ║       │       │       │       ║
        ╟───────┼───────┼───────┼───────╢
        ║       │       │       │       ║
        ║   32  │  64   │  128  │  256  ║
        ║       │       │       │       ║
        ╟───────┼───────┼───────┼───────╢
        ║       │       │       │       ║
        ║  512  │ 1024  │ 2048  │ 4096  ║
        ║       │       │       │       ║
        ╟───────┼───────┼───────┼───────╢
        ║       │       │       │       ║
        ║  8192 │ 16384 │ 32768 │ 65536 ║
        ║       │       │       │       ║
        ╚═══════╧═══════╧═══════╧═══════╝"""})

        self.board = Board(record)
        self.moved = 0
        self.arrow = None
        self.refresh(edit)

    def refresh(self, edit):
        def align(num):
            ns = 7 - len(num)
            ls = ns >> 1
            rs = ns - ls
            return ' ' * ls + num + ' ' * rs

        def formater(fmt, num):
            if num < 2:
                return "       "
            return align(fmt % num)

        self.view.set_read_only(False)

        self.view.replace(edit, sublime.Region(*status_regions[0]),
                          align("%d" % self.board.score()))
        self.view.replace(edit, sublime.Region(*status_regions[1]),
                          align("%d" % self.board.best()))
        self.view.replace(edit, sublime.Region(*status_regions[2]),
                          align(self.arrow or ""))
        self.view.replace(edit, sublime.Region(*status_regions[3]),
                          formater("%+d", self.moved))

        for row in range(4):
            for col in range(4):
                number = self.board.grid.numbers[row][col]
                region = self.board.grid.regions[row][col]
                self.view.replace(edit, region, formater("%d", number))
        self.view.sel().clear()
        self.view.set_read_only(True)

    def save_record(self):
        sublime.status_message("Sublime2048: save record")
        settings = sublime.load_settings(sublime2048_record)
        settings.set("record", self.board.grid.record())
        sublime.save_settings(sublime2048_record)

    def load_record(self):
        settings = sublime.load_settings(sublime2048_record)
        return settings.get("record", {})


class Sublime2048Setup(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.new_file()
        view.run_command("sublime2048", {"command": "setup"})


class Sublime2048Manager(sublime_plugin.EventListener):
    activated_games = set()

    def on_activated(self, view):
        if view.view_id in self.activated_games:
            return
        settings = view.settings()
        if (settings.has("sublime2048") and settings.has("record")):
            view.run_command("sublime2048",
                {"command": "setup", "record": settings.get("record")})
            self.activated_games.add(view.view_id)

    # 目前没找到在sublime关闭时调用的函数，
    # 只能求助于这个函数，不过不能保存最后记录
    def on_deactivated(self, view):
        if view.settings().has("sublime2048"):
            view.run_command("sublime2048", {"command": "save"})

    def on_close(self, view):
        if view.settings().has("sublime2048"):
            view.run_command("sublime2048", {"command": "save_record"})
