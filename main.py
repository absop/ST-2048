import time
from random import randint

import sublime
import sublime_plugin

""" 游戏保存记录的方式
每个View有独立对的游戏记录，全局游戏记录只有一个
当某个View关闭时，将它的 游戏记录保存为全局游戏记录，

启动新游戏时，加载全局游戏记录作为View的初始游戏记录
"""

sublime2048_record = "sublime2048.sublime-settings"

class Score():
    def __init__(self):
        self.current = 0
        self.highest = 0

    def increase(self, delta):
        self.current += delta
        self.highest = max(self.current, self.highest)

class Grid():
    def __init__(self, regions, record):
        self.regions = regions
        self.score = Score()
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
    def __init__(self, region, record={}):
        self.grid = Grid(region, record)

    def best(self):
        return self.grid.score.highest

    def score(self):
        return self.grid.score.current

    def add_randnum(self):
        if self.grid.nblank > 0:
            self.grid.add_randnum()

    def move(self, direction):
        return self.moves[direction](self.grid)

    def isalive(self):
        return self.grid.movable()

    def iswon(self):
        return self.grid.maxnum >= 2048


class Sublime2048(sublime_plugin.TextCommand):
    game_captions = ("score", "best", "key", "got")

    game_board_text = """
        ╔═══════╤═══════╤═══════╤═══════╗
        ║ SCORE │  BEST │  Key  │  Got  ║
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
        ╚═══════╧═══════╧═══════╧═══════╝"""
    game_over_tips = """
                 游戏结束
    """
    game_won_tips = """
                  你赢了
    """
    def run(self, edit, command=None, key=None, record=None):
        if command == "move":
            self.move(edit, key)

        elif command == "reset":
            self.game_resart(edit)

        elif command == "setup":
            self.setup(edit, record)

        elif command == "save_record":
            self.save_record()

    def setup(self, edit, record):
        if not record:
            self.create_game_board(self.view)
            record = self.load_record()

        self.regions = self.board_regions()
        self.board = Board(self.regions["cell"], record)
        self.moved = 0
        self.arrow = None
        self.game_overed = not self.board.isalive()
        if self.game_overed:
            self.game_resart(edit)
        self.refresh(edit)

    def create_game_board(self, view):
        view.set_name("2048")
        view.set_scratch(True)
        view.assign_syntax("sublime2048.sublime-syntax")
        view.settings().set("sublime2048", True)
        view.settings().set("draw_white_space", None)
        view.settings().set("color_scheme",
            "Material-Lighter.sublime-color-scheme")
        view.run_command('append', {'characters': self.game_board_text})


    def board_regions(self):
        region = self.view.find(" SCORE ", 0)
        length = self.view.line(region).size() + 1

        start_point = region.begin() + 2 * length
        regions = {
            self.game_captions[i]: sublime.Region(
                start_point + i * 8, start_point + i * 8 + 7)
            for i in range(4)
        }

        grid_regions = regions["grid"] = []
        cell_regions = regions["cell"] = []
        for i in range(4):
            grid_regions.append([])
            cell_regions.append([])
            grid_start_point = region.begin() + (5 + i * 4) * length
            for j in range(4):
                grid_regions[i].append(tuple(
                    sublime.Region(a, a + 7)
                    for a in range(grid_start_point,
                        grid_start_point + 3 * length, length)
                ))
                cell_regions[i].append(grid_regions[i][j][1])
                grid_start_point += 8

        return regions

    def move(self, edit, key):
        self.arrow = key
        if not self.game_overed:
            self.moved = self.board.move(key)
            if self.moved:
                self.board.add_randnum()
                if not self.board.isalive():
                    self.game_over(edit)
                if self.board.iswon():
                    self.game_won(edit)

                record = self.board.grid.record()
                self.view.settings().set("record", record)

                self.refresh(edit)

    def game_won(self, edit):
        endpt = self.view.size()
        self.view.set_read_only(False)
        self.view.insert(edit, endpt, self.game_won_tips)
        self.view.set_read_only(True)

    def game_resart(self, edit):
        self.view.set_read_only(False)
        self.view.erase(edit,
            sublime.Region(len(self.game_board_text), self.view.size()))
        self.view.set_read_only(True)
        self.game_overed = False
        self.board.grid.reset()
        self.refresh(edit)

    def game_over(self, edit):
        endpt = self.view.size()
        self.view.set_read_only(False)
        self.view.insert(edit, endpt, self.game_over_tips)
        self.view.set_read_only(True)
        self.game_overed = True

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

        self.view.replace(edit, self.regions["score"],
                          align("%d" % self.board.score()))
        self.view.replace(edit, self.regions["best"],
                          align("%d" % self.board.best()))
        self.view.replace(edit, self.regions["key"],
                          align(self.arrow or ""))
        self.view.replace(edit, self.regions["got"],
                          formater("%+d", self.moved))

        for row in range(4):
            for col in range(4):
                number = self.board.grid.numbers[row][col]
                region = self.board.grid.regions[row][col]
                key = "%d_%d_sublime2048" % (row, col)
                self.view.replace(edit, region, formater("%d", number))
                self.view.erase_regions(key)
                self.view.add_regions(key,
                    self.regions["grid"][row][col],
                    scope="%d.sublime2048" % number)

        self.view.sel().clear()
        self.view.set_read_only(True)

    def save_record(self):
        settings = sublime.load_settings(sublime2048_record)
        settings.set("record", self.board.grid.record())
        sublime.save_settings(sublime2048_record)
        sublime.status_message("Sublime2048: game record saved")

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

    def on_close(self, view):
        if view.settings().has("sublime2048"):
            view.run_command("sublime2048", {"command": "save_record"})
