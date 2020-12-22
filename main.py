import time
import threading
from random import randint
from copy import deepcopy

import sublime
import sublime_plugin

""" 游戏保存记录的方式
每个View有独立对的游戏记录，全局游戏记录只有一个
当某个View关闭时，将它的 游戏记录保存为全局游戏记录，

启动新游戏时，加载全局游戏记录作为View的初始游戏记录
"""

sublime2048_record = "Sublime2048Record.sublime-settings"


class Board():
    def __init__(self, record):
        self.current_score = 0
        self.highest_score = 0
        try:
            self.load(record)
        except:
            self.reset()

    def reset(self):
        self.matrix = [[0 for j in range(4)] for i in range(4)]
        self.current_score = 0
        self.nblank = 16
        self.maxnum = 0
        self.add_randnum()

    def load(self, record):
        try:
            self.matrix = record["matrix"]
            self.highest_score = record["highest_score"]
            self.current_score = record["current_score"]
            self.nblank = len([i for r in self.matrix for i in r if i == 0])
            self.maxnum = max(max(self.matrix))
        except:
            self.reset()
            self.highest_score = 0

    def record(self):
        return {
            "time": time.strftime("%Y%m%d %H:%M:%S"),
            "matrix": self.matrix,
            "highest_score": self.highest_score,
            "current_score": self.current_score
        }

    def accumulate_score(self, score):
        self.current_score += score
        self.highest_score = max(self.current_score, self.highest_score)

    def add_randnum(self):
        # 控制数字2和4的概率,此时2出现概率是80%
        randidx = randint(0, 100) % self.nblank
        randnum = (2, 4)[randint(1, 100) // 80]
        self.maxnum = max(randnum, self.maxnum)

        count = 0
        for i in range(4):
            for j in range(4):
                if self.matrix[i][j] == 0:
                    if count == randidx:
                        self.matrix[i][j] = randnum
                        self.nblank -= 1
                        return (i, j)
                    count += 1

    def movable(self):
        if self.nblank > 0:
            return True
        for i in range(4):
            for j in range(1, 4):
                if (self.matrix[i][j - 1] == self.matrix[i][j] or
                    self.matrix[j - 1][i] == self.matrix[j][i]):
                    return True
        return False


def genmove(array, swap):
    def move(bodrd):
        matrix = bodrd.matrix
        nblank, score, moved = 0, 0, 0
        for i in range(4):
            k = 0
            for j in range(4):
                x1, y1 = swap(i, array[k])
                x2, y2 = swap(i, array[j])
                if j == k or matrix[x2][y2] == 0:
                    continue
                if matrix[x1][y1] == matrix[x2][y2]:
                    matrix[x1][y1] <<= 1
                    bodrd.maxnum = max(matrix[x1][y1], bodrd.maxnum)
                    score += matrix[x1][y1]
                    nblank += 1
                    k += 1
                else:
                    if matrix[x1][y1]:
                        k += 1
                        if k == j:
                            continue
                    x1, y1 = swap(i, array[k])
                    matrix[x1][y1] = matrix[x2][y2]

                matrix[x2][y2] = 0
                moved = 1

        if score > 0:
            bodrd.nblank += nblank
            bodrd.accumulate_score(score)
            return score

        return moved

    return move


class Game():
    moves = {
        "↑": genmove([0, 1, 2, 3], lambda x, y: (y, x)),
        "↓": genmove([3, 2, 1, 0], lambda x, y: (y, x)),
        "←": genmove([0, 1, 2, 3], lambda x, y: (x, y)),
        "→": genmove([3, 2, 1, 0], lambda x, y: (x, y))
    }
    def __init__(self, record={}):
        self.bodrd = Board(record)

    def best(self):
        return self.bodrd.highest_score

    def score(self):
        return self.bodrd.current_score

    def move(self, direction):
        return self.moves[direction](self.bodrd)

    def isalive(self):
        return self.bodrd.movable()

    def iswon(self):
        return self.bodrd.maxnum >= 2048

    def get_best_key(self, total_simulation_times=200):
        simulation_times = int(total_simulation_times / 4)
        possible_directions = ["↑", "↓", "←", "→"]
        cumulate_scores = {}
        simulator = Game()
        for direction in possible_directions:
            cumulate_scores[direction] = 0
            for i in range(simulation_times):
                simulator.bodrd = deepcopy(self.bodrd)
                moved = simulator.move(direction)
                if not moved:
                    break
                cumulate_scores[direction] += moved
                simulator.bodrd.add_randnum()
                while simulator.isalive():
                    d = possible_directions[randint(0, 3)]
                    moved = simulator.move(d)
                    if moved:
                        cumulate_scores[direction] += moved
                        simulator.bodrd.add_randnum()

        best_d, best_s = possible_directions[0], 0
        for direction in possible_directions:
            if cumulate_scores[direction] > best_s:
                best_s = cumulate_scores[direction]
                best_d = direction

        return best_d


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

        elif command == "auto_move":
            if not self.game.isalive():
                self.stop_ai()
                return
            def threaded_auto_run():
                key = self.game.get_best_key()
                self.view.run_command(
                    'sublime2048', {'command': 'move', 'key': key})
                if self.view.settings().get('play2048_ai', False):
                    sublime.set_timeout(
                        lambda: self.view.run_command(
                            'sublime2048', {'command': 'auto_move'}),
                        0)
            thread = threading.Thread(target=threaded_auto_run)
            thread.start()

        elif command == "reset":
            self.game_resart(edit)

        elif command == "setup":
            self.setup(edit, record)

    def setup(self, edit, record):
        if not record:
            self.create_game_board(self.view)
            record = self.load_record()

        score_region = self.view.find(" SCORE ", 0)
        head_line_region = self.view.line(score_region)
        line_length = head_line_region.size() + 1
        pt = head_line_region.end() + 2 * line_length
        self.annotation_region = sublime.Region(pt, pt)

        start_point = score_region.begin() + 2 * line_length
        self.caption_regions = {
            self.game_captions[i]: sublime.Region(
                start_point + i * 8, start_point + i * 8 + 7)
            for i in range(4)
        }

        self.tile_regions = []
        for i in range(4):
            self.tile_regions.append([])
            tile_start_point = score_region.begin() + (5 + i * 4) * line_length
            for j in range(4):
                self.tile_regions[i].append(
                    tuple(
                        sublime.Region(a, a + 7)
                        for a in range(tile_start_point,
                            tile_start_point + 3 * line_length, line_length)
                    )
                )
                tile_start_point += 8

        self.game = Game(record)
        self.moved = 0
        self.arrow = None
        self.game_overed = not self.game.isalive()

        if not self.view.settings().get('play2048_ai', False):
            self.stop_ai()
        if self.game_overed:
            self.game_over(edit)

        self.refresh(edit)

    def create_game_board(self, view):
        view.set_name("2048")
        view.set_scratch(True)
        view.assign_syntax("Sublime2048.sublime-syntax")
        view.settings().set("sublime2048", True)
        view.settings().set("highlight_line", False)
        view.settings().set("scroll_past_end", False)
        view.settings().set("draw_white_space", None)
        view.run_command('append', {'characters': self.game_board_text})

    def run_ai(self):
        self.view.settings().set('play2048_ai', True)
        # self.add_ai_annotation('stop_ai', '停止')
        self.add_ai_annotation('stop_ai', '✘')
        self.view.run_command('sublime2048', {'command': 'auto_move'})

    def stop_ai(self):
        self.view.settings().set('play2048_ai', False)
        # self.add_ai_annotation('run_ai', '自动')
        self.add_ai_annotation('run_ai', '➜')

    def add_ai_annotation(self, href, img):
        content = """
            <span class="label label-success"><a href="%s">%s</a></span>
        """ % (href, img)
        self.view.erase_phantoms('Play2048')
        self.view.add_phantom(
            'Play2048',
            self.annotation_region,
            self.html.format(css=self.css, content=content),
            sublime.LAYOUT_INLINE, self.on_navigate
        )

    def on_navigate(self, href):
        if href == 'run_ai':
            self.run_ai()
        else:
            self.stop_ai()

    def move(self, edit, key):
        self.arrow = key
        if not self.game_overed:
            self.moved = self.game.move(key)
            if self.moved:
                row, col = self.game.bodrd.add_randnum()
                if not self.game.isalive():
                    self.game_over(edit)
                if self.game.iswon():
                    self.game_won(edit)

                record = self.game.bodrd.record()
                self.view.settings().set("record", record)

                self.refresh(edit, row=row, col=col)

    def game_won(self, edit):
        self.status_message(edit, self.game_won_tips)

    def game_resart(self, edit):
        self.status_message(edit, "")
        self.game_overed = False
        self.game.bodrd.reset()
        self.refresh(edit)

    def game_over(self, edit):
        self.status_message(edit, self.game_over_tips)
        self.game_overed = True

    def status_message(self, edit, msg):
        self.view.set_read_only(False)
        self.view.replace(edit,
            sublime.Region(len(self.game_board_text), self.view.size()), msg)
        self.view.set_read_only(True)

    def refresh(self, edit, row=None, col=None):
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

        self.view.replace(edit, self.caption_regions["score"],
                          align("%d" % self.game.score()))
        self.view.replace(edit, self.caption_regions["best"],
                          align("%d" % self.game.best()))
        self.view.replace(edit, self.caption_regions["key"],
                          align(self.arrow or ""))
        self.view.replace(edit, self.caption_regions["got"],
                          formater("%+d", self.moved))

        for x in range(4):
            for y in range(4):
                number = self.game.bodrd.matrix[x][y]
                region = self.tile_regions[x][y][1]
                key = "%d_%d_sublime2048" % (x, y)
                self.view.replace(edit, region, formater("%d", number))
                self.view.erase_regions(key)
                self.view.add_regions(key, self.tile_regions[x][y],
                    scope="%s.sublime2048" % (number or "empty"),
                    flags=sublime.DRAW_NO_OUTLINE|sublime.PERSISTENT)

        self.view.erase_regions("new_sublime2048")
        if row is not None:
            self.view.erase_regions("%d_%d_sublime2048" % (row, col))
            number = self.game.bodrd.matrix[row][col]
            self.view.add_regions("new_sublime2048",
                self.tile_regions[row][col],
                scope="%d.sublime2048 new_number.sublime2048" % number,
                flags=sublime.DRAW_NO_OUTLINE|sublime.PERSISTENT)

        self.view.sel().clear()
        self.view.set_read_only(True)

    def load_record(self):
        settings = sublime.load_settings(sublime2048_record)
        return settings.get("record", {})


class Sublime2048Setup(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.new_file()
        view.run_command("sublime2048", {"command": "setup"})


class Sublime2048Manager(sublime_plugin.ViewEventListener):
    is_activated = False

    @classmethod
    def is_applicable(cls, settings):
        return settings.has("sublime2048")

    def on_query_context(self, key, operator, operand, match_all):
        if self.view.settings().get('play2048_ai', False):
            return False
        return key == "play2048"

    def on_selection_modified(self):
        self.view.sel().clear()

    def on_activated(self):
        if not self.is_activated:
            self.view.run_command("sublime2048", {
                "command": "setup",
                "record": self.view.settings().get("record")
            })
            self.is_activated = True

    def on_close(self):
        if self.view.settings().has("record"):
            self.save_record(self.view.settings().get("record"))
            sublime.status_message("Sublime2048: game record saved")

    def save_record(self, record):
        settings = sublime.load_settings(sublime2048_record)
        settings.set("record", record)
        sublime.save_settings(sublime2048_record)


def plugin_loaded():
    load_resource = sublime.load_resource
    Sublime2048.css = load_resource("Packages/Sublime2048/html/ui.css")
    Sublime2048.html = load_resource("Packages/Sublime2048/html/ui.html")
