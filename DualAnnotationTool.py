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
# Scrollable List (basit yardımcı)
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

        # player opening
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
                # Start again from beginning
                self.set_position(0.0)
                self.player.set_pause(False)
                self.playing = True
            else:
                self.playing = False
            return

        if frame is None:
            return

        # ffpyplayer sometimes returns (img, timestamp)
        if isinstance(frame, tuple):
            img = frame[0]
        else:
            img = frame

        # if img is frame 
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

            # scale as aspect ratio and fit into pannel
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



# -----------------------------------------------------------
# Main Application
# -----------------------------------------------------------
class VideoApp:
    def __init__(self):
        info = pygame.display.Info()
        self.W, self.H = max(800, info.current_w // 1), max(600, info.current_h // 1)
        self.screen = pygame.display.set_mode((self.W, self.H), pygame.RESIZABLE)
        pygame.display.set_caption("Video Panel + Kayıt Listesi")
        self.show_marker = False

        self.font = pygame.font.SysFont(None, 32)
        self.small_font = pygame.font.SysFont(None, 22)
        self.clock = pygame.time.Clock()
        self.running = True

        # Layout
        self.left_w = int(self.W * 0.70)
        self.right_w = self.W - self.left_w
        self.right_video_h = int(self.H * 0.45)
        self.button_h = 60
        self.list_y = self.right_video_h + self.button_h
        self.list_h = self.H - self.list_y

        self.list_x = self.left_w + 10
        self.list_y = self.right_video_h + self.button_h + 10
        self.list_w = self.right_w - 20
        self.list_h = self.H - self.list_y - 10

        video_extensions = ["mp4","mov","avi","mkv"]

        match1 = []
        match2 = []

        for ext in video_extensions:
            match1.extend(glob.glob(os.path.join(f"control_*.{ext}")))
            match2.extend(glob.glob(os.path.join(f"reference_*.{ext}")))

        # prevent double record
        match1 = list(set(match1))
        match2 = list(set(match2))

        print("Bulunan control dosyaları:", match1)
        print("Bulunan reference dosyaları:", match2)

        if not match1 or not match2:
            raise FileNotFoundError("control_ veya reference_ videoları bulunamadı.")

        video1 = os.path.normpath(match1[0]) # 'control_xxxx.mp4'
        video2 = os.path.normpath(match2[0]) # 'reference_xxxx.mp4'

        # video1 ve video2 must be a 'str' type

        self.left_panel = VideoPanel(0, 0, self.left_w, self.H, video1, audio=True)
        self.right_panel = VideoPanel(self.left_w, 0, self.right_w, self.right_video_h, video2, audio=False, loop=True)

        self.scroll_list = ScrollList(self.list_x, self.list_y, self.list_w, self.list_h, item_height=28)

        self.close_button = Button(self.W - 120, 10, 110, 40, "Kapat", self.font, color=(200, 0, 0))

        # intervals: list of dicts {'start': float, 'end': float}
        self.intervals = []
        self.current_start = -1

        # open CSV file for appending
        self.csv_path = 'output.csv'
        new_file = not os.path.exists(self.csv_path)
        self.csvfile = open(self.csv_path, 'a', newline='', encoding='utf-8')
        self.csvwriter = csv.writer(self.csvfile)
        if new_file:
            # Header: start_seconds, end_seconds, start_hms, end_hms
            self.csvwriter.writerow(['start', 'end'])
            self.csvfile.flush()

    def run(self):
        try:
            while self.running:
                self.handle_events()
                self.update()
                self.draw()
                self.clock.tick(30)
        finally:
            # Close file in any case to prevent data loss
            try:
                self.csvfile.close()
            except Exception:
                pass
            pygame.quit()

    def handle_events(self):
        for e in pygame.event.get():
            # Closing window or pressing ESC
            if e.type == pygame.QUIT:
                self.running = False
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                self.running = False

            # Mouse events
            elif e.type == pygame.MOUSEBUTTONDOWN:
                self.left_panel.handle_mouse_event(e.pos, e.button)
                self.right_panel.handle_mouse_event(e.pos, e.button)

                if self.close_button.is_pressed(e.pos):
                    self.running = False

                # Scroll (mouse wheel)
                if e.button == 4:
                    self.scroll_list.scroll(-self.scroll_list.item_height)
                elif e.button == 5:
                    self.scroll_list.scroll(self.scroll_list.item_height)

            # Keyboard events
            if e.type == pygame.KEYDOWN:
                # START: x button
                if e.key == pygame.K_x:
                    t = self.left_panel.get_current_time()
                    self.current_start = t
                    self.show_marker = True   # show circle sign
                    print("START:", self.left_panel.format_time(t))

                # FINISH: c button
                elif e.key == pygame.K_c:
                    if self.current_start != -1:
                        t = self.left_panel.get_current_time()
                        # Protector: if end < start, swap
                        s_val = float(self.current_start)
                        e_val = float(t)
                        if e_val < s_val:
                            s_val, e_val = e_val, s_val
                        item = {'start': s_val, 'end': e_val}
                        self.intervals.append(item)
                        print("FINISH:", self.left_panel.format_time(t))
                        print("Current Intervals:", [
                            (self.left_panel.format_time(i['start']), self.left_panel.format_time(i['end']))
                            for i in self.intervals
                        ])
                        # Write into CSV: numeric second, then readable format
                        try:
                            self.csvwriter.writerow([
                                self.left_panel.format_time(s_val),
                                self.left_panel.format_time(e_val)
                            ])
                            self.csvfile.flush()
                        except Exception as ex:
                            print("CSV yazma hatası:", ex)
                        self.current_start = -1
                        self.show_marker = False   # disable marker
                        # update scroll list items
                        self.scroll_list.set_items(self.intervals)

    def update(self):
        self.left_panel.update()
        self.right_panel.update()
        # update scroll list items 
        self.scroll_list.set_items(self.intervals)

    def draw(self):
        self.screen.fill((0, 0, 0))
        # Videos
        self.left_panel.draw(self.screen)
        self.right_panel.draw(self.screen)

        # If marker is active, draw a red circle
        if self.show_marker:
            pygame.draw.circle(self.screen, (200, 0, 0), (30, 50), 20)

        # Interval list area and content
        self.scroll_list.draw(self.screen, self.small_font, self.left_panel.format_time)

        # Close button
        self.close_button.draw(self.screen)
        pygame.display.flip()


if __name__ == "__main__":
    # python app.py left.mp4 right.mp4
    if len(sys.argv) >= 3:
        left_path = sys.argv[1]
        right_path = sys.argv[2]
    VideoApp().run()
