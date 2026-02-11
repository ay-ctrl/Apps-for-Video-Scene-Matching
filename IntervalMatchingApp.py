import pygame
from ffpyplayer.player import MediaPlayer
import glob
import csv
import sys
import os

pygame.init()

# -----------------------------------------------------------
# Button Class
# -----------------------------------------------------------
class Button:
    def __init__(self, x, y, w, h, text, font, color=(0, 200, 0)):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.font = font
        self.color = color

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        text_surf = self.font.render(self.text, True, (255, 255, 255))
        screen.blit(text_surf, (self.rect.x + 10, self.rect.y + (self.rect.h - text_surf.get_height()) // 2))

    def is_pressed(self, pos):
        return self.rect.collidepoint(pos)


# -----------------------------------------------------------
# Scrollable List 
# -----------------------------------------------------------
class ScrollList:
    def __init__(self, x, y, w, h, item_height=28):
        self.rect = pygame.Rect(x, y, w, h)
        self.items = []  # each item is a dict: {'start':, 'end':}
        self.scroll_offset = 0
        self.item_height = item_height

    def set_items(self, items):
        """items: list of dicts with start,end"""
        self.items = items

    def scroll(self, delta):
        max_offset = max(0, len(self.items) * self.item_height - self.rect.h)
        self.scroll_offset = min(max(0, self.scroll_offset + delta), max_offset)

    def visible_range(self):
        start_idx = self.scroll_offset // self.item_height
        visible = self.rect.h // self.item_height
        return start_idx, visible

    def draw(self, surface, font, format_time_func):
        pygame.draw.rect(surface, (40, 40, 40), self.rect)
        start_idx, visible = self.visible_range()
        for i in range(start_idx, min(len(self.items), start_idx + visible)):
            item = self.items[i]
            y = self.rect.y + (i - start_idx) * self.item_height + 4
            text = f"{format_time_func(item['start'])}  -  {format_time_func(item['end'])}"
            t_surf = font.render(text, True, (200, 200, 200))
            surface.blit(t_surf, (self.rect.x + 8, y))


# -----------------------------------------------------------
# Control Bar
# -----------------------------------------------------------
class ControlBar:
    def __init__(self, x, y, width, height, margin=30):
        self.rect = pygame.Rect(x, y, width, height)
        self.margin = margin

        self.playing = False
        self.progress = 0.0

        self.btn_w = 30
        self.btn_h = 28

        # --- Progress bar rect ---
        bar_h = 8
        bar_x = x + margin
        bar_w = width - 2 * margin
        bar_y = y + height - bar_h - 8
        self.progress_rect = pygame.Rect(bar_x, bar_y, bar_w, bar_h)

        # --- Buttons ---
        spacing = 12
        total_w = self.btn_w * 3 + spacing * 2

        start_x = bar_x + (bar_w - total_w) // 2
        btn_y = bar_y + bar_h + 6

        self.back_rect = pygame.Rect(start_x, btn_y, self.btn_w, self.btn_h)
        self.play_rect = pygame.Rect(start_x + self.btn_w + spacing, btn_y, self.btn_w, self.btn_h)
        self.next_rect = pygame.Rect(start_x + (self.btn_w + spacing) * 2, btn_y, self.btn_w, self.btn_h)

    def draw(self, surface, video_panel):
        pygame.draw.rect(surface, (50, 50, 50), self.rect)

        # Progress bar
        pygame.draw.rect(surface, (100, 100, 100), self.progress_rect)
        fill_w = int(self.progress_rect.width * self.progress)
        pygame.draw.rect(surface, (200, 0, 0),
                         (self.progress_rect.x, self.progress_rect.y,
                          fill_w, self.progress_rect.height))

        # Buttons
        pygame.draw.rect(surface, (0, 0, 200), self.back_rect)
        pygame.draw.rect(surface,
                         (0, 200, 0) if self.playing else (200, 0, 0),
                         self.play_rect)
        pygame.draw.rect(surface, (0, 0, 200), self.next_rect)

        # --- Time text ---
        font = pygame.font.SysFont(None, 22)

        duration = video_panel.duration if video_panel.duration is not None else 0
        current_sec = duration * self.progress if duration else 0
        total_sec = duration

        left_text = font.render(self.format_time(current_sec), True, (255, 255, 255))
        right_text = font.render(self.format_time(total_sec), True, (255, 255, 255))

        surface.blit(left_text, (self.progress_rect.x, self.progress_rect.y - 22))
        surface.blit(right_text, (self.progress_rect.x + self.progress_rect.width - right_text.get_width(),
                                  self.progress_rect.y - 22))

    def format_time(self, seconds):
        seconds = int(seconds)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        else:
            return f"{m:02d}:{s:02d}"

    def handle_mouse_event(self, pos, button, video_panel):
        if button != 1:
            return

        # Play/Pause
        if self.play_rect.collidepoint(pos):
            video_panel.toggle()
            self.playing = video_panel.playing

        # Backward
        elif self.back_rect.collidepoint(pos):
            video_panel.skip_backward()

        # Forward
        elif self.next_rect.collidepoint(pos):
            video_panel.skip_forward()

        # Progress bar click
        elif self.progress_rect.collidepoint(pos):
            if video_panel.duration:
                ratio = (pos[0] - self.progress_rect.x) / self.progress_rect.width
                video_panel.set_position(ratio)


# -----------------------------------------------------------
# Video Panel Class
# -----------------------------------------------------------
class VideoPanel:
    def __init__(self, x, y, w, h, video_path, audio=True, loop=False):
        # main pannel area
        self.rect = pygame.Rect(x, y, w, h)
        self.video_path = video_path

        self.audio = audio
        self.loop = loop
        self.playing = False
        self.progress = 0.0
        self.frame = None

        # control bar
        self.control_height = 30
        self.margin = 30
        self.control_bar = ControlBar(
            x, 
            y + h - self.control_height - self.margin, 
            w, 
            self.control_height, 
            margin=self.margin
        )

        # player and video metadata
        self.player = None
        self.duration = None

        # frame cache
        self._buf = None
        self._vid_size = None
        self._scaled = None
        self._target = None

        # ffmpeg settings
        self.ff_opts = {
            'paused': 1,
            'an': 1 if not self.audio else 0,
            'sync': 'audio' if self.audio else 'video',
            'fflags': 'nobuffer'
        }

        print("PATH:", self.video_path)
        print("EXISTS:", os.path.exists(self.video_path))

        # player openning
        try:
            self.player = MediaPlayer(
                self.video_path.encode('utf-8'),
                ff_opts=self.ff_opts,
                loglevel="quiet"
            )
        except Exception as e:
            print("Video açılamadı:", self.video_path, e)
            self.player = None

    def toggle(self):
        if not self.player:
            return
        self.playing = not self.playing
        try:
            self.player.set_pause(not self.playing)
        except:
            pass

    def skip_forward(self, sec=30):
        if not self.player or not self.duration:
            return
        try:
            pos = self.player.get_pts() or 0
            self.set_position(min(1.0, (pos + sec) / self.duration))
        except:
            pass

    def skip_backward(self, sec=30):
        if not self.player or not self.duration:
            return
        try:
            pos = self.player.get_pts() or 0
            self.set_position(max(0.0, (pos - sec) / self.duration))
        except:
            pass

    def set_position(self, ratio):
        if not self.player or self.duration is None:
            return
        ratio = max(0.0, min(1.0, ratio))
        try:
            self.player.seek(self.duration * ratio, relative=False, accurate=False)
            self.progress = ratio
        except:
            pass

    def update(self):
        if not self.player:
            return

        frame, val = self.player.get_frame()

        # Is video done (can be frame or val EOF)
        if frame == "eof" or val == "eof":
            if self.loop:
                # Start from beginning
                self.set_position(0.0)
                self.player.set_pause(False)
                self.playing = True
            else:
                self.playing = False
            return

        if frame is None:
            return

        # ffpyplayer sometimes return (img, timestamp)
        if isinstance(frame, tuple):
            img = frame[0]
        else:
            img = frame

        # if img is a frame
        self.frame = img

        # time
        if self.duration is None:
            meta = self.player.get_metadata() or {}
            self.duration = meta.get("duration")

        # playing position
        try:
            pos = self.player.get_pts() or 0
        except:
            pos = 0

        if self.duration:
            self.progress = pos / self.duration

        self.control_bar.progress = self.progress
        self.control_bar.playing = self.playing

    def draw(self, surface):
        if self.frame is None:
            self.control_bar.draw(surface, self)
            return

        img = self.frame

        try:
            w, h = img.get_size()
            data = img.to_bytearray()[0]   # ffpyplayer -> raw RGB
            
            surf = pygame.image.frombuffer(data, (w, h), "RGB")

            # scale as fitting in panel
            tw, th = self.rect.size
            aspect = w / h

            if tw / th > aspect:
                new_h = th
                new_w = int(new_h * aspect)
            else:
                new_w = tw
                new_h = int(new_w / aspect)

            surf = pygame.transform.smoothscale(surf, (new_w, new_h))

            x = self.rect.x + (tw - new_w) // 2
            y = self.rect.y + (th - new_h) // 2

            surface.blit(surf, (x, y))

        except Exception as e:
            print("Draw hata:", e)

        self.control_bar.draw(surface, self)


    def handle_mouse_event(self, pos, button):
        self.control_bar.handle_mouse_event(pos, button, self)

    def get_current_time(self):
        if self.duration:
            return self.duration * self.progress
        try:
            return self.player.get_pts() or 0
        except:
            return 0

    def format_time(self, sec):
        s = int(sec)
        h = s // 3600
        m = (s % 3600) // 60
        s = s % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
    
    def seek_to_second(self, sec):
        if not self.player or not self.duration:
            return

        sec = max(0, min(sec, self.duration))
        ratio = sec / self.duration
        self.set_position(ratio)

# -----------------------------------------------------------
# Main Application
# -----------------------------------------------------------
class VideoApp:
    def __init__(self):
        info = pygame.display.Info()
        self.W = max(800, info.current_w)
        self.H = max(600, info.current_h)

        self.screen = pygame.display.set_mode((self.W, self.H), pygame.RESIZABLE)
        pygame.display.set_caption("Film - Game Scene Matching")

        self.font = pygame.font.SysFont(None, 26)
        self.small_font = pygame.font.SysFont(None, 22)
        self.clock = pygame.time.Clock()
        self.running = True

        # ---------------------------------------------------
        # Layout
        # ---------------------------------------------------
        self.video_area_w = int(self.W * 0.75)
        self.list_area_w = self.W - self.video_area_w

        self.single_video_w = self.video_area_w // 2

        # ---------------------------------------------------
        # Videos
        # ---------------------------------------------------
        video_extensions = ["mp4", "mov", "avi", "mkv"]
        v1, v2 = [], []

        for ext in video_extensions:
            v1.extend(glob.glob(f"control_*.{ext}"))
            v2.extend(glob.glob(f"reference_*.{ext}"))

        video1 = os.path.normpath(v1[0])
        video2 = os.path.normpath(v2[0])

        self.left_panel = VideoPanel(
            0, 0,
            self.single_video_w,
            self.H,
            video1,
            audio=True
        )

        self.right_panel = VideoPanel(
            self.single_video_w, 0,
            self.single_video_w,
            self.H,
            video2,
            audio=False,
            loop=True
        )

        # ---------------------------------------------------
        # CSV
        # ---------------------------------------------------
        self.film_intervals = self.load_csv("film.csv")
        self.game_intervals = self.load_csv("game.csv")

        # add an id to each interval for easier reference and matching
        for i, it in enumerate(self.film_intervals):
            it["id"] = i
            it["matched"] = False

        for i, it in enumerate(self.game_intervals):
            it["id"] = i
            it["matched"] = False

        # ---------------------------------------------------
        # Matrix
        # ---------------------------------------------------
        # film_id -> [game_id, game_id, ...]
        self.match_matrix = {it["id"]: [] for it in self.film_intervals}

        # ---------------------------------------------------
        # Lists
        # ---------------------------------------------------
        right_x = self.video_area_w
        col_w = (self.list_area_w - 30) // 2

        self.film_list = ScrollList(
            right_x + 10, 60,
            col_w, self.H - 70
        )

        self.game_list = ScrollList(
            right_x + 20 + col_w, 60,
            col_w, self.H - 70
        )

        self.film_list.set_items(self.film_intervals)
        self.game_list.set_items(self.game_intervals)

        # selected indexler
        self.selected_film_idx = None
        self.selected_game_idx = None

        # Load existing matchings from CSV to RAM
        self.load_matches_csv()

    def load_matches_csv(self, path="matches.csv"):
        if not os.path.exists(path):
            return

        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert the times in the CSV to seconds
                film_start = self.parse_time(row["film_start"])
                film_end = self.parse_time(row["film_end"])
                game_start = self.parse_time(row["game_start"])
                game_end = self.parse_time(row["game_end"])

                # find film_item and game_item
                film_item = next((it for it in self.film_intervals if it["start"] == film_start and it["end"] == film_end), None)
                game_item = next((it for it in self.game_intervals if it["start"] == game_start and it["end"] == game_end), None)

                if film_item and game_item:
                    film_id = film_item["id"]
                    game_id = game_item["id"]

                    if game_id not in self.match_matrix[film_id]:
                        self.match_matrix[film_id].append(game_id)

                    film_item["matched"] = True
                    game_item["matched"] = True

    # ---------------------------------------------------
    # CSV helpers
    # ---------------------------------------------------
    def load_csv(self, path):
        intervals = []
        if not os.path.exists(path):
            return intervals

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                s = self.parse_time(row["start"])
                e = self.parse_time(row["end"])
                intervals.append({"start": s, "end": e})

        intervals.sort(key=lambda x: x["start"])
        return intervals

    def parse_time(self, val):
        val = val.strip()
        if ":" in val:
            p = list(map(int, val.split(":")))
            if len(p) == 3:
                return p[0] * 3600 + p[1] * 60 + p[2]
            return p[0] * 60 + p[1]
        return float(val)

    # ---------------------------------------------------
    # Loop
    # ---------------------------------------------------
    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(30)
        pygame.quit()

    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.running = False

            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    self.running = False

                elif e.key == pygame.K_x:
                    self.match_selected()
                
                elif e.key == pygame.K_c:
                    self.unmatch_selected_pair()

            elif e.type == pygame.MOUSEBUTTONDOWN:
                self.left_panel.handle_mouse_event(e.pos, e.button)
                self.right_panel.handle_mouse_event(e.pos, e.button)

                self.handle_list_click(e.pos)

                if e.button == 4:
                    self.film_list.scroll(-28)
                    self.game_list.scroll(-28)
                elif e.button == 5:
                    self.film_list.scroll(28)
                    self.game_list.scroll(28)

    # ---------------------------------------------------
    # Selection & Matching
    # ---------------------------------------------------
    def handle_list_click(self, pos):
        film_idx = self.get_clicked_index(self.film_list, pos)
        game_idx = self.get_clicked_index(self.game_list, pos)

        if film_idx is not None:
            self.selected_film_idx = film_idx

            film_item = self.film_intervals[film_idx]
            self.left_panel.seek_to_second(film_item["start"])

        if game_idx is not None:
            self.selected_game_idx = game_idx

            game_item = self.game_intervals[game_idx]
            self.right_panel.seek_to_second(game_item["start"])

    def get_clicked_index(self, scroll_list, pos):
        if not scroll_list.rect.collidepoint(pos):
            return None

        rel_y = pos[1] - scroll_list.rect.y + scroll_list.scroll_offset
        idx = rel_y // scroll_list.item_height
        if 0 <= idx < len(scroll_list.items):
            return idx
        return None

    def match_selected(self):
        if self.selected_film_idx is None or self.selected_game_idx is None:
            return

        film_item = self.film_intervals[self.selected_film_idx]
        game_item = self.game_intervals[self.selected_game_idx]

        film_id = film_item["id"]
        game_id = game_item["id"]

        if game_id not in self.match_matrix[film_id]:
            self.match_matrix[film_id].append(game_id)

        film_item["matched"] = True
        game_item["matched"] = True

        self.append_match_csv(film_item, game_item)

        self.film_list.set_items(self.film_intervals)
        self.game_list.set_items(self.game_intervals)

        self.selected_film_idx = None
        self.selected_game_idx = None

    def update(self):
        self.left_panel.update()
        self.right_panel.update()

    def unmatch_selected_pair(self):
        if self.selected_film_idx is None or self.selected_game_idx is None:
            return

        film_item = self.film_intervals[self.selected_film_idx]
        game_item = self.game_intervals[self.selected_game_idx]

        film_id = film_item["id"]
        game_id = game_item["id"]

        # delete from RAM
        if game_id in self.match_matrix.get(film_id, []):
            self.match_matrix[film_id].remove(game_id)

        film_item["matched"] = False
        game_item["matched"] = False

        # delete from CSV
        self.remove_match_csv(film_item, game_item)

        self.film_list.set_items(self.film_intervals)
        self.game_list.set_items(self.game_intervals)

        self.selected_film_idx = None
        self.selected_game_idx = None


    # ---------------------------------------------------
    # Draw
    # ---------------------------------------------------
    def draw(self):
        self.screen.fill((0, 0, 0))

        self.left_panel.draw(self.screen)
        self.right_panel.draw(self.screen)

        self.draw_titles()
        self.draw_lists()

        pygame.display.flip()

    def draw_titles(self):
        film_t = self.font.render("Film", True, (220, 220, 220))
        game_t = self.font.render("Game", True, (220, 220, 220))
        self.screen.blit(film_t, (self.video_area_w + 10, 20))
        self.screen.blit(game_t, (self.video_area_w + self.list_area_w // 2, 20))

    def draw_lists(self):
        self.draw_scroll_list(self.film_list, self.selected_film_idx)
        self.draw_scroll_list(self.game_list, self.selected_game_idx)

    def draw_scroll_list(self, scroll_list, selected_idx):
        pygame.draw.rect(self.screen, (40, 40, 40), scroll_list.rect)
        start = scroll_list.scroll_offset // scroll_list.item_height
        visible = scroll_list.rect.h // scroll_list.item_height

        for i in range(start, min(len(scroll_list.items), start + visible)):
            item = scroll_list.items[i]
            y = scroll_list.rect.y + (i - start) * scroll_list.item_height + 4

            color = (200, 200, 200)  # default grey

            # Right list: ones that is connected to the selected film is green 
            if scroll_list is self.game_list and self.selected_film_idx is not None:
                film_id = self.film_intervals[self.selected_film_idx]["id"]
                if item["id"] in self.match_matrix.get(film_id, []):
                    color = (0, 180, 0)

            # selected item always appears at the top (yellow)
            if i == selected_idx:
                color = (200, 200, 0)

            txt = f"{self.left_panel.format_time(item['start'])} - {self.left_panel.format_time(item['end'])}"
            surf = self.small_font.render(txt, True, color)
            self.screen.blit(surf, (scroll_list.rect.x + 8, y))
    
    def append_match_csv(self, film_item, game_item, path="matches.csv"):
        file_exists = os.path.exists(path)

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            if not file_exists:
                writer.writerow([
                    "film_start",
                    "film_end",
                    "game_start",
                    "game_end"
                ])

            writer.writerow([
                self.left_panel.format_time(film_item["start"]),
                self.left_panel.format_time(film_item["end"]),
                self.right_panel.format_time(game_item["start"]),
                self.right_panel.format_time(game_item["end"])
            ])

    def remove_match_csv(self, film_item, game_item, path="matches.csv"):
        if not os.path.exists(path):
            return

        # read CSV rows
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = [row for row in reader]

        # use right format
        fs = self.left_panel.format_time(film_item["start"]).strip()
        fe = self.left_panel.format_time(film_item["end"]).strip()
        gs = self.right_panel.format_time(game_item["start"]).strip()
        ge = self.right_panel.format_time(game_item["end"]).strip()

        # Remove the line to be deleted
        rows = [
            row for row in rows
            if not (row["film_start"].strip() == fs and
                    row["film_end"].strip() == fe and
                    row["game_start"].strip() == gs and
                    row["game_end"].strip() == ge)
        ]

        # rewrite CSV
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["film_start","film_end","game_start","game_end"])
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    pygame.init()

    screen = pygame.display.set_mode((1400, 800))
    pygame.display.set_caption("Video Interval Matcher")

    app = VideoApp()
    app.run()


