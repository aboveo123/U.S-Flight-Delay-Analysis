import pygame
import numpy as np
import pandas as pd
import random
import math
import sys
import os
from pygame.locals import *

# ============================================================
# === BTVN03 - PROFILING ENGINE (bổ sung riêng cho bài tập,
# === KHÔNG thuộc code gốc của project Missing Value Shooter)
# ============================================================
import time
import csv
import functools

PROFILING_ENABLED = False   # bật/tắt profiling bằng cờ toàn cục
call_records = []           # nơi lưu toàn bộ bản ghi sau khi đo
call_stack = []             # stack runtime: mỗi phần tử là 1 dict đang "đang chạy"

def profile_call(func):
    """
    Decorator tự viết để đo function_name, parent_function, depth,
    start_time, end_time, duration, self_time cho mỗi lệnh gọi hàm.
    Chỉ hoạt động khi PROFILING_ENABLED = True, để không ảnh hưởng
    hiệu năng game khi chơi bình thường.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not PROFILING_ENABLED:
            return func(*args, **kwargs)

        depth = len(call_stack)
        parent = call_stack[-1]['name'] if call_stack else None

        frame = {
            'name': func.__qualname__,   # dùng __qualname__ để có "ClassName.method"
            'start': time.perf_counter(),
            'child_time': 0.0
        }
        call_stack.append(frame)
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end = time.perf_counter()
            duration = end - frame['start']
            self_time = duration - frame['child_time']

            call_stack.pop()
            # Cộng duration của hàm này vào "child_time" của hàm cha
            # (đây là cách tránh tính self_time bị trùng với duration của con)
            if call_stack:
                call_stack[-1]['child_time'] += duration

            call_records.append({
                'function_name': frame['name'],
                'parent_function': parent,
                'depth': depth,
                'start_time': frame['start'],
                'end_time': end,
                'duration': duration,
                'self_time': self_time
            })
    return wrapper


def export_profiling_csv(filepath='profiling_data.csv'):
    """Xuất call_records ra file CSV đúng 7 cột theo yêu cầu đề bài."""
    fieldnames = ['function_name', 'parent_function', 'depth',
                  'start_time', 'end_time', 'duration', 'self_time']
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in call_records:
            writer.writerow(row)
    print(f"[Profiling] Đã xuất {len(call_records)} dòng dữ liệu ra {filepath}")
# ============================================================
# === KẾT THÚC PROFILING ENGINE
# ============================================================

# Khởi tạo Pygame
pygame.init()

# Khởi tạo mixer cho âm thanh
pygame.mixer.init()

# Kích thước màn hình
WIDTH, HEIGHT = 1400, 900
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Missing Value Shooter - Bắn số từ bầu trời!")

# Màu sắc
BACKGROUND = (20, 25, 35)
SKY_COLOR = (135, 206, 235)
CLOUD_COLOR = (255, 255, 255)
DATA_TABLE_BG = (40, 45, 60)
CELL_COLOR = (50, 55, 70)
MISSING_CELL_COLOR = (180, 60, 60)
FILLED_CELL_COLOR = (60, 180, 80)
TEXT_COLOR = (240, 240, 240)
UI_BG = (30, 35, 45)
HINT_COLOR = (255, 255, 200)
LASER_COLOR = (255, 50, 50, 180)
BUTTON_COLOR = (70, 130, 180)
BUTTON_HOVER_COLOR = (100, 160, 210)
BUTTON_TEXT_COLOR = (255, 255, 255)

# Màu sắc cho vật phẩm
POWERUP_GOOD_COLOR = (0, 255, 255)  # Màu xanh ngọc sáng
POWERUP_BAD_COLOR = (255, 100, 0)   # Màu cam đỏ
EXPLOSIVE_COLOR = (255, 215, 0)     # Màu vàng cho đạn nổ
TRIPLE_SHOT_COLOR = (100, 255, 100) # Màu xanh lá cho 3 viên liên tiếp
THREE_WAY_COLOR = (100, 200, 255)   # Màu xanh dương cho 3 tia

# Font
try:
    font_xlarge = pygame.font.SysFont('arial', 48, bold=True)
    font_large = pygame.font.SysFont('arial', 36, bold=True)
    font_medium = pygame.font.SysFont('arial', 28)
    font_small = pygame.font.SysFont('arial', 24)
    font_tiny = pygame.font.SysFont('arial', 20)
except:
    font_xlarge = pygame.font.Font(None, 48)
    font_large = pygame.font.Font(None, 36)
    font_medium = pygame.font.Font(None, 28)
    font_small = pygame.font.Font(None, 24)
    font_tiny = pygame.font.Font(None, 20)

# Load hình ảnh
def load_image(filename, size=None):
    try:
        image = pygame.image.load(filename)
        if size:
            image = pygame.transform.scale(image, size)
        return image
    except:
        if size:
            surface = pygame.Surface(size, pygame.SRCALPHA)
        else:
            surface = pygame.Surface((50, 50), pygame.SRCALPHA)
        surface.fill((200, 200, 200, 128))
        return surface

# Thử load ảnh hướng dẫn
try:
    instructions_image = load_image('instructions.png', (WIDTH - 100, HEIGHT - 150))
    has_instructions_image = True
except:
    has_instructions_image = False
    print("Không tìm thấy file instructions.png")

try:
    bubble_images = {
        'correct': load_image('bubble_correct.png', (70, 70)),
        'wrong': load_image('bubble_wrong.png', (70, 70)),
        'highlight': load_image('bubble_highlight.png', (80, 80))
    }
    
    bullet_image = load_image('bullet.png', (30, 30))
    cannon_base_image = load_image('cannon_base.png', (200, 280))
    cannon_barrel_image = load_image('cannon_barrel.png', (200, 200))
    
    target_images = {
        'empty': load_image('target_empty.png', (120, 60)),
        'filled': load_image('target_filled.png', (120, 60))
    }
    
    cloud_image = load_image('cloud.png', (100, 60))
    background_image = load_image('background.png', (WIDTH, HEIGHT))
    
    # Thêm hình ảnh cho vật phẩm
    powerup_good_image = load_image('powerup_good.png', (50, 50))
    powerup_bad_image = load_image('powerup_bad.png', (50, 50))
    
    use_images = True
except:
    print("Không tìm thấy file ảnh, sử dụng đồ họa vẽ")
    use_images = False

# Game states
STATE_MENU = "MENU"
STATE_LEVEL_START = "LEVEL_START"
STATE_PLAYING = "PLAYING"
STATE_LEVEL_COMPLETE = "LEVEL_COMPLETE"
STATE_GAME_OVER = "GAME_OVER"
STATE_GAME_WIN = "GAME_WIN"
STATE_INSTRUCTIONS = "INSTRUCTIONS"

# Quản lý âm thanh
class SoundManager:
    def __init__(self):
        self.sounds = {}
        self.music_playing = False
        
    def load_sound(self, name, filename):
        """Load âm thanh từ file"""
        try:
            self.sounds[name] = pygame.mixer.Sound(filename)
            print(f"Đã load âm thanh: {name}")
        except Exception as e:
            print(f"Không thể tải âm thanh {filename}: {e}")
            
    def play_sound(self, name, volume=0.5):
        """Phát âm thanh"""
        if name in self.sounds:
            self.sounds[name].set_volume(volume)
            self.sounds[name].play()
            
    def play_music(self, filename, volume=0.3, loops=-1):
        """Phát nhạc nền"""
        try:
            pygame.mixer.music.load(filename)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(loops)
            self.music_playing = True
            print(f"Đang phát nhạc nền: {filename}")
        except Exception as e:
            print(f"Không thể tải nhạc nền {filename}: {e}")
            
    def stop_music(self):
        """Dừng nhạc nền"""
        pygame.mixer.music.stop()
        self.music_playing = False
        
    def pause_music(self):
        """Tạm dừng nhạc nền"""
        pygame.mixer.music.pause()
        
    def unpause_music(self):
        """Tiếp tục nhạc nền"""
        pygame.mixer.music.unpause()

# Tạo manager âm thanh
sound_manager = SoundManager()

# Thử load các file âm thanh (bạn cần thêm các file âm thanh tương ứng)
try:
    sound_manager.load_sound('shoot', 'shoot.mp3')
    sound_manager.load_sound('pop', 'pop.wav')
    sound_manager.load_sound('correct', 'correct.wav')
    sound_manager.load_sound('win', 'win.wav')
    sound_manager.load_sound('lose', 'lose.wav')
    sound_manager.load_sound('powerup_good', 'powerup_good.wav')
    sound_manager.load_sound('powerup_bad', 'powerup_bad.wav')
    sound_manager.load_sound('explosion', 'explosion.wav')
    sound_manager.load_sound('triple_shot', 'triple_shot.wav')
    sound_manager.load_sound('three_way', 'three_way.wav')
    sound_manager.load_sound('click', 'click.wav')
except:
    print("Không tìm thấy file âm thanh, game sẽ chạy không có âm thanh")

class Button:
    def __init__(self, x, y, width, height, text, color=BUTTON_COLOR, hover_color=BUTTON_HOVER_COLOR):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.current_color = color
        self.is_hovered = False
        self.clicked = False
        
    def update(self, mouse_pos):
        self.is_hovered = self.rect.collidepoint(mouse_pos)
        self.current_color = self.hover_color if self.is_hovered else self.color
        return self.is_hovered
        
    def draw(self, screen):
        # Vẽ nút với góc bo tròn
        pygame.draw.rect(screen, self.current_color, self.rect, border_radius=15)
        pygame.draw.rect(screen, (255, 255, 255), self.rect, 3, border_radius=15)
        
        # Vẽ vòng sáng khi hover
        if self.is_hovered:
            glow_rect = pygame.Rect(self.rect.x - 5, self.rect.y - 5, 
                                  self.rect.width + 10, self.rect.height + 10)
            pygame.draw.rect(screen, (255, 255, 255, 100), glow_rect, border_radius=20)
        
        # Vẽ text
        text_surface = font_large.render(self.text, True, BUTTON_TEXT_COLOR)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)
        
        # Vẽ icon nếu có
        if "🎮" in self.text:
            icon = font_large.render("🎮", True, BUTTON_TEXT_COLOR)
            icon_rect = icon.get_rect(center=(self.rect.centerx - 80, self.rect.centery))
            screen.blit(icon, icon_rect)
        elif "📖" in self.text:
            icon = font_large.render("📖", True, BUTTON_TEXT_COLOR)
            icon_rect = icon.get_rect(center=(self.rect.centerx - 80, self.rect.centery))
            screen.blit(icon, icon_rect)
        elif "◀" in self.text:
            icon = font_medium.render("◀", True, BUTTON_TEXT_COLOR)
            icon_rect = icon.get_rect(center=(self.rect.centerx - 50, self.rect.centery))
            screen.blit(icon, icon_rect)
    
    def check_click(self, mouse_pos, mouse_click):
        if self.rect.collidepoint(mouse_pos) and mouse_click:
            if 'click' in sound_manager.sounds:
                sound_manager.play_sound('click')
            self.clicked = True
            return True
        return False

class Menu:
    def __init__(self):
        self.buttons = []
        self.create_buttons()
        
    def create_buttons(self):
        button_width = 400
        button_height = 80
        center_x = WIDTH // 2 - button_width // 2
        
        # Các nút cho menu chính
        self.play_button = Button(center_x, 350, button_width, button_height, "🎮 BẮT ĐẦU CHƠI")
        self.instructions_button = Button(center_x, 450, button_width, button_height, "📖 HƯỚNG DẪN")
        self.quit_button = Button(center_x, 550, button_width, button_height, "🚪 THOÁT GAME")
        
        # Các nút cho màn hình hướng dẫn
        self.back_button = Button(50, 50, 200, 60, "◀ QUAY LẠI")
        
        self.buttons = [self.play_button, self.instructions_button, self.quit_button]
    
    def update(self, mouse_pos):
        for button in self.buttons:
            button.update(mouse_pos)
        self.back_button.update(mouse_pos)
    
    def draw_main_menu(self, screen):
        # Vẽ nền
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(200)
        screen.blit(overlay, (0, 0))
        
        # Vẽ tiêu đề
        title = font_xlarge.render("MISSING VALUE SHOOTER", True, (255, 215, 0))
        subtitle = font_large.render("Bắn số từ bầu trời!", True, (200, 200, 255))
        
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 150))
        screen.blit(subtitle, (WIDTH//2 - subtitle.get_width()//2, 220))
        
        # Vẽ các nút
        for button in self.buttons:
            button.draw(screen)
    
    def draw_instructions(self, screen):
        # Vẽ nền
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(200)
        screen.blit(overlay, (0, 0))
        
        # Vẽ nút quay lại
        self.back_button.draw(screen)
        
        if has_instructions_image:
            # Hiển thị ảnh hướng dẫn
            image_rect = instructions_image.get_rect(center=(WIDTH//2, HEIGHT//2))
            screen.blit(instructions_image, image_rect)
            
            # Vẽ khung cho ảnh
            pygame.draw.rect(screen, (255, 215, 0), 
                            (image_rect.x - 5, image_rect.y - 5, 
                             image_rect.width + 10, image_rect.height + 10), 3)
        else:
            # Vẽ hướng dẫn bằng text nếu không có ảnh
            title = font_xlarge.render("HƯỚNG DẪN CHƠI", True, (255, 215, 0))
            screen.blit(title, (WIDTH//2 - title.get_width()//2, 100))
            
            instructions = [
                "🎯 MỤC TIÊU:",
                "   Tìm giá trị đúng để điền vào ô trống trong bảng dữ liệu",
                "",
                "🎮 CÁCH CHƠI:",
                "   1. Bắn phím SPACE để bắn đạn",
                "   2. Khẩu pháo tự động quay 180°",
                "   3. Laser đỏ giúp ngắm bắn",
                "   4. BẮN BỂ các bong bóng SAI để mở đường",
                "   5. Chạm bong bóng XANH LÁ (giá trị đúng) để thắng",
                "",
                "💎 VẬT PHẨM ĐẶC BIỆT:",
                "   • Vật phẩm TỐT (💎): Lần bắn TIẾP THEO có hiệu ứng đặc biệt",
                "   • Vật phẩm XẤU (💀): Gây hiệu ứng xấu ngay lập tức",
                "",
                "📊 CÁC LOẠI DỮ LIỆU:",
                "   • Trung bình (Average): Tính trung bình các giá trị",
                "   • Nội suy (Interpolation): Giá trị giữa 2 số liền kề",
                "   • Forward Fill: Lấy giá trị từ ô phía trước",
                "",
                "⚠️ LƯU Ý:",
                "   • Mỗi level có 10 viên đạn",
                "   • Chạm bong bóng đúng để thắng ngay",
                "   • Hiệu ứng đặc biệt CHỈ có tác dụng với lần bắn NGAY TIẾP THEO"
            ]
            
            for i, line in enumerate(instructions):
                color = (255, 255, 200) if "🎯" in line or "🎮" in line or "💎" in line or "📊" in line or "⚠️" in line else (200, 200, 200)
                text = font_medium.render(line, True, color)
                screen.blit(text, (100, 180 + i * 35))
    
    def handle_click(self, mouse_pos):
        if self.play_button.check_click(mouse_pos, True):
            return "PLAY"
        elif self.instructions_button.check_click(mouse_pos, True):
            return "INSTRUCTIONS"
        elif self.quit_button.check_click(mouse_pos, True):
            return "QUIT"
        elif self.back_button.check_click(mouse_pos, True):
            return "BACK"
        return None

class DatasetGenerator:
    @staticmethod
    def generate_level(level):
        if level == 1:
            data = {
                'ID': list(range(1, 9)),
                'Name': [f'P{i}' for i in range(1, 9)],
                'Age': [25, 32, None, 28, 45, None, 38, 41],
                'Income': [50000, 65000, 72000, 48000, 85000, 92000, 55000, 81000]
            }
            df = pd.DataFrame(data)
            age_values = [x for x in df['Age'] if pd.notna(x)]
            correct_value = int(sum(age_values) / len(age_values)) if age_values else 0
            
            missing_cells = [(2, 'Age')]
            correct_values = [correct_value]
            hint = f"Tìm số {correct_value} (trung bình tuổi)"
            distractors = [correct_value + 5, correct_value - 3, correct_value + 2, 30, 40, 50]
            
        elif level == 2:
            data = {
                'Time': ['9:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00'],
                'Temp': [22.5, None, 24.1, 25.3, 26.8, None, 25.9, 24.7]
            }
            df = pd.DataFrame(data)
            correct_value = round((22.5 + 24.1) / 2, 1)
            
            missing_cells = [(1, 'Temp')]
            correct_values = [correct_value]
            hint = f"Tìm số {correct_value} (trung bình nhiệt độ)"
            distractors = [correct_value + 0.2, correct_value - 0.3, correct_value + 0.5, 23.0, 24.5, 25.0]
            
        elif level == 3:
            data = {
                'Product': ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'],
                'Sales': [150, 200, None, 180, 220, None, 210, 190],
                'Rating': [4.5, 4.2, 4.7, None, 4.8, 4.6, 4.9, None],
                'Category': ['E', 'E', 'B', 'C', None, 'E', 'B', None]
            }
            df = pd.DataFrame(data)
            sales_values = [x for x in df['Sales'] if pd.notna(x)]
            correct_value = int(sum(sales_values) / len(sales_values)) if sales_values else 0
            
            missing_cells = [(2, 'Sales')]
            correct_values = [correct_value]
            hint = f"Tìm số {correct_value} (trung bình sales)"
            distractors = [correct_value + 10, correct_value - 5, correct_value + 15, 170, 210, 230]
            
        else:  # level 4
            data = {
                'Day': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                'Price': [105.2, 106.5, None, None, 108.9, None, 112.5],
                'Volume': [1000, 1200, 1100, None, 1300, 1400, 1500]
            }
            df = pd.DataFrame(data)
            correct_value = 106.5
            
            missing_cells = [(2, 'Price')]
            correct_values = [correct_value]
            hint = f"Tìm số {correct_value} (forward fill)"
            distractors = [correct_value + 0.5, correct_value - 0.2, correct_value + 0.3, 105.0, 107.0, 110.0]
        
        return df, missing_cells, correct_values, hint, distractors

class PowerUp:
    def __init__(self, x, y, power_type):
        self.x = x
        self.y = y
        self.type = power_type  # 'good' hoặc 'bad'
        self.radius = 25
        self.speed_y = random.uniform(1.5, 3.0)  # Tốc độ rơi
        self.speed_x = random.uniform(-0.5, 0.5)  # Di chuyển ngang nhẹ
        self.float_value = random.random() * math.pi * 2
        self.active = True
        self.collected = False
        self.rotation = 0
        self.spawn_time = pygame.time.get_ticks()
        
        # Các loại vật phẩm tốt
        self.good_types = ['triple_shot', 'three_way', 'explosive']
        # Các loại vật phẩm xấu
        self.bad_types = ['lose_ammo', 'slow_cannon']  # Đã bỏ reverse_control
        
        # Chọn loại cụ thể nếu chưa được chỉ định
        if power_type == 'good':
            self.specific_type = random.choice(self.good_types)
            self.color = POWERUP_GOOD_COLOR
            self.glow_color = (0, 200, 255)
        else:  # 'bad'
            self.specific_type = random.choice(self.bad_types)
            self.color = POWERUP_BAD_COLOR
            self.glow_color = (255, 150, 0)
        
        # Biểu tượng cho từng loại
        self.symbols = {
            'triple_shot': '🎯',
            'three_way': '➰',
            'explosive': '💣',
            'lose_ammo': '➖',
            'slow_cannon': '🐌'
        }
        
        # Mô tả cho từng loại
        self.descriptions = {
            'triple_shot': '3 viên liên tiếp',
            'three_way': '3 tia đạn',
            'explosive': 'Đạn nổ',
            'lose_ammo': 'Mất đạn',
            'slow_cannon': 'Làm chậm súng'
        }
        
        self.symbol = self.symbols.get(self.specific_type, '?')
        self.description = self.descriptions.get(self.specific_type, 'Vật phẩm')
    
    @profile_call
    def update(self):
        if not self.collected:
            self.float_value += 0.05
            float_offset = math.sin(self.float_value) * 2
            
            self.rotation += 3
            
            # Di chuyển xuống dưới (rơi)
            self.y += self.speed_y
            self.x += self.speed_x
            
            # Kiểm tra xem có ra khỏi màn hình không
            if self.y > HEIGHT + self.radius:
                self.active = False
                return
            
            # Giới hạn trong màn hình theo chiều ngang
            if self.x < self.radius:
                self.x = self.radius
                self.speed_x *= -0.5
            elif self.x > WIDTH - self.radius:
                self.x = WIDTH - self.radius
                self.speed_x *= -0.5
    
    @profile_call
    def draw(self, screen):
        if self.collected or not self.active:
            return
            
        float_offset = math.sin(self.float_value) * 2
        
        # Vẽ hiệu ứng phát sáng
        for i in range(3):
            glow_radius = self.radius + i * 3
            alpha = 100 - i * 20
            glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surface, (*self.glow_color, alpha), 
                             (glow_radius, glow_radius), glow_radius)
            screen.blit(glow_surface, 
                       (self.x - glow_radius, 
                        self.y - glow_radius + float_offset))
        
        # Vẽ vật phẩm chính
        pygame.draw.circle(screen, self.color, 
                         (int(self.x), int(self.y + float_offset)), 
                         self.radius)
        
        # Vẽ viền
        pygame.draw.circle(screen, (255, 255, 255), 
                         (int(self.x), int(self.y + float_offset)), 
                         self.radius, 2)
        
        # Vẽ biểu tượng
        symbol_surface = font_small.render(self.symbol, True, (30, 30, 30))
        
        # Xoay biểu tượng
        rotated_symbol = pygame.transform.rotate(symbol_surface, self.rotation)
        symbol_rect = rotated_symbol.get_rect(center=(int(self.x), int(self.y + float_offset)))
        screen.blit(rotated_symbol, symbol_rect)
        
        # Vẽ mô tả khi hover
        mouse_x, mouse_y = pygame.mouse.get_pos()
        distance = math.sqrt((mouse_x - self.x)**2 + (mouse_y - (self.y + float_offset))**2)
        
        if distance < self.radius + 10:
            desc_surface = font_tiny.render(self.description, True, (255, 255, 200))
            desc_rect = desc_surface.get_rect(center=(int(self.x), int(self.y + float_offset - 40)))
            
            # Vẽ nền cho mô tả
            pygame.draw.rect(screen, (0, 0, 0, 200), 
                           (desc_rect.x - 5, desc_rect.y - 3, 
                            desc_rect.width + 10, desc_rect.height + 6),
                           border_radius=5)
            pygame.draw.rect(screen, (255, 255, 255), 
                           (desc_rect.x - 5, desc_rect.y - 3, 
                            desc_rect.width + 10, desc_rect.height + 6),
                           1, border_radius=5)
            
            screen.blit(desc_surface, desc_rect)
    
    def check_collision(self, bullet_x, bullet_y, bullet_radius):
        if self.collected or not self.active:
            return False
        distance = math.sqrt((bullet_x - self.x)**2 + (bullet_y - self.y)**2)
        return distance < (bullet_radius + self.radius)

class NumberBubble:
    def __init__(self, value, x, y, correct_value=None, is_moving=True, speed_factor=1.0, move_direction="horizontal", level=1):
        self.value = value
        self.x = x
        self.y = y
        self.radius = 35
        self.is_moving = is_moving
        self.speed_factor = speed_factor
        self.move_direction = move_direction  # "horizontal", "vertical", "random"
        self.original_y = y  # Lưu vị trí y ban đầu để di chuyển theo sóng
        self.level = level  # Sửa: Nhận level làm tham số
        
        # Sử dụng level để quyết định cách di chuyển
        if self.level >= 2:
            # Từ level 2: Chỉ di chuyển theo đường thẳng ngang
            self.speed_x = random.choice([-1, 1]) * random.uniform(1.5, 3.0) * speed_factor
            self.speed_y = 0
        else:
            # Level 1: Di chuyển tự do (giữ nguyên)
            self.speed_x = random.uniform(-0.5, 0.5) * speed_factor
            self.speed_y = random.uniform(-0.3, 0.3) * speed_factor
        
        self.is_correct = False
        if correct_value is not None:
            if isinstance(correct_value, float):
                self.is_correct = abs(float(value) - correct_value) < 0.01
            else:
                self.is_correct = str(value) == str(correct_value)
        
        if self.is_correct:
            self.color = (100, 255, 100)
        else:
            self.color = (
                random.randint(200, 255),
                random.randint(200, 255),
                random.randint(180, 220)
            )
        
        self.collected = False
        self.float_value = random.random() * math.pi * 2
    
    @profile_call
    def update(self):
        if not self.collected and self.is_moving:
            self.float_value += 0.03 * self.speed_factor
            float_offset = math.sin(self.float_value) * 2
            
            # Từ level 2: Chỉ di chuyển ngang
            if self.level >= 2:
                self.x += self.speed_x
                # Thêm hiệu ứng nổi nhẹ
                self.y = self.original_y + float_offset * 2
            else:
                # Level 1: Di chuyển tự do (giữ nguyên)
                self.x += self.speed_x
                self.y += self.speed_y + float_offset * 0.1
            
            # Giới hạn theo chiều ngang
            if self.x < self.radius:
                self.x = self.radius
                self.speed_x = abs(self.speed_x)
            elif self.x > WIDTH - self.radius:
                self.x = WIDTH - self.radius
                self.speed_x = -abs(self.speed_x)
                
            # Giới hạn theo chiều dọc (chỉ level 1)
            if self.level == 1:
                if self.y < 100:
                    self.y = 100
                    self.speed_y *= -1
                elif self.y > HEIGHT * 0.6:
                    self.y = HEIGHT * 0.6
                    self.speed_y *= -1
        elif not self.collected:
            # Vẫn có hiệu ứng float ngay cả khi không di chuyển
            self.float_value += 0.03
    
    @profile_call
    def draw(self, screen):
        if self.collected:
            return
            
        if use_images:
            if self.is_correct:
                image = bubble_images['correct']
            else:
                image = bubble_images['wrong']
            
            float_offset = math.sin(self.float_value) * 3
            screen.blit(image, (int(self.x - image.get_width() // 2), 
                              int(self.y - image.get_height() // 2 + float_offset)))
        else:
            float_offset = math.sin(self.float_value) * 3
            color = self.color
            if self.is_correct:
                pulse = (math.sin(pygame.time.get_ticks() * 0.005) + 1) * 50
                color = (100 + int(pulse), 255, 100)
            
            pygame.draw.circle(screen, color, 
                             (int(self.x), int(self.y + float_offset)), self.radius)
            
            if self.is_correct:
                pygame.draw.circle(screen, (255, 255, 255), 
                                 (int(self.x), int(self.y + float_offset)), self.radius, 4)
            else:
                pygame.draw.circle(screen, (255, 255, 255), 
                                 (int(self.x), int(self.y + float_offset)), self.radius, 3)
        
        if isinstance(self.value, float):
            value_text = f"{self.value:.1f}"
        else:
            value_text = str(self.value)
            
        text_color = (30, 30, 30)
        text_surface = font_medium.render(value_text, True, text_color)
        text_rect = text_surface.get_rect(center=(int(self.x), int(self.y)))
        screen.blit(text_surface, text_rect)
        
        if self.is_correct:
            correct_text = font_tiny.render("ĐÚNG", True, (0, 100, 0))
            correct_rect = correct_text.get_rect(center=(int(self.x), int(self.y) + 40))
            screen.blit(correct_text, correct_rect)
        
    @profile_call
    def check_collision(self, bullet_x, bullet_y, bullet_radius):
        if self.collected:
            return False
        distance = math.sqrt((bullet_x - self.x)**2 + (bullet_y - self.y)**2)
        return distance < (bullet_radius + self.radius)

class Explosion:
    def __init__(self, x, y, radius=80):
        self.x = x
        self.y = y
        self.radius = radius
        self.max_radius = radius
        self.current_radius = 10
        self.growth_rate = 8
        self.active = True
        self.particles = []
        self.create_particles()
        
    def create_particles(self):
        # Tạo các hạt nhỏ cho vụ nổ
        for _ in range(20):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 6)
            size = random.uniform(2, 6)
            lifetime = random.randint(20, 40)
            self.particles.append({
                'x': self.x,
                'y': self.y,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'size': size,
                'lifetime': lifetime,
                'color': (random.randint(200, 255), random.randint(100, 200), random.randint(0, 100))
            })
    
    @profile_call
    def update(self):
        # Cập nhật bán kính vụ nổ
        if self.current_radius < self.max_radius:
            self.current_radius += self.growth_rate
        else:
            self.current_radius = self.max_radius
        
        # Cập nhật các hạt
        for particle in self.particles[:]:
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['vy'] += 0.1  # Trọng lực
            particle['lifetime'] -= 1
            if particle['lifetime'] <= 0:
                self.particles.remove(particle)
        
        # Kiểm tra kết thúc vụ nổ
        if self.current_radius >= self.max_radius and len(self.particles) == 0:
            self.active = False
    
    @profile_call
    def draw(self, screen):
        # Vẽ vòng nổ chính
        for i in range(3):
            radius = int(self.current_radius * (0.7 + i * 0.15))
            alpha = 150 - i * 50
            color = (255, 200, 0, alpha)
            
            # Tạo surface với alpha
            explosion_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(explosion_surface, color, (radius, radius), radius)
            screen.blit(explosion_surface, (self.x - radius, self.y - radius))
        
        # Vẽ các tia lửa
        for i in range(12):
            angle = i * math.pi / 6
            length = self.current_radius * 0.8
            end_x = self.x + math.cos(angle) * length
            end_y = self.y + math.sin(angle) * length
            
            # Vẽ tia lửa với gradient
            for j in range(3):
                sub_length = length * (0.6 + j * 0.2)
                sub_end_x = self.x + math.cos(angle) * sub_length
                sub_end_y = self.y + math.sin(angle) * sub_length
                color = (255, 150 - j * 30, 0)
                pygame.draw.line(screen, color, 
                               (int(self.x), int(self.y)), 
                               (int(sub_end_x), int(sub_end_y)), 
                               max(1, 5 - j * 2))
        
        # Vẽ các hạt nhỏ
        for particle in self.particles:
            pygame.draw.circle(screen, particle['color'], 
                             (int(particle['x']), int(particle['y'])), 
                             int(particle['size']))
    
    def check_collision(self, x, y, radius=0):
        """Kiểm tra va chạm với vụ nổ"""
        distance = math.sqrt((x - self.x)**2 + (y - self.y)**2)
        return distance < (self.current_radius + radius)

class Bullet:
    def __init__(self, x, y, angle, bullet_type='normal'):
        self.x = x
        self.y = y
        self.radius = 15
        self.speed = 15
        self.angle = angle
        self.vx = math.cos(angle) * self.speed
        self.vy = -math.sin(angle) * self.speed
        self.active = True
        self.collected_value = None
        self.bullet_type = bullet_type  # 'normal', 'explosive', 'triple', 'three_way'
        
        # Màu sắc theo loại đạn
        if bullet_type == 'explosive':
            self.color = EXPLOSIVE_COLOR
            self.explosion_radius = 80
        elif bullet_type == 'triple':
            self.color = TRIPLE_SHOT_COLOR
        elif bullet_type == 'three_way':
            self.color = THREE_WAY_COLOR
        else:
            self.color = (255, 100, 100)
    
    @profile_call
    def update(self):
        if not self.active:
            return False
            
        self.x += self.vx
        self.y += self.vy
        
        # Kiểm tra nếu ra khỏi màn hình
        if (self.x < -100 or self.x > WIDTH + 100 or 
            self.y < -100 or self.y > HEIGHT + 100):
            self.active = False
            return True
        return False
    
    @profile_call
    def draw(self, screen):
        if not self.active:
            return
            
        if use_images and bullet_image:
            rotated_bullet = pygame.transform.rotate(bullet_image, math.degrees(self.angle))
            screen.blit(rotated_bullet, 
                       (int(self.x - rotated_bullet.get_width() // 2),
                        int(self.y - rotated_bullet.get_height() // 2)))
        else:
            # Vẽ đạn với màu theo loại
            bullet_color = self.color
            pygame.draw.circle(screen, bullet_color, (int(self.x), int(self.y)), self.radius)
            pygame.draw.circle(screen, (255, 255, 255), (int(self.x), int(self.y)), self.radius, 2)
            
            # Vẽ ký hiệu đặc biệt trên đạn
            if self.bullet_type == 'explosive':
                # Vẽ dấu hiệu nổ
                pygame.draw.circle(screen, (255, 50, 0), (int(self.x), int(self.y)), 8)
                for i in range(4):
                    angle = i * math.pi / 2
                    length = 10
                    end_x = self.x + math.cos(angle) * length
                    end_y = self.y + math.sin(angle) * length
                    pygame.draw.line(screen, (255, 50, 0), 
                                   (int(self.x), int(self.y)), 
                                   (int(end_x), int(end_y)), 3)
            elif self.bullet_type == 'triple':
                # Vẽ số 3
                text = font_tiny.render("3", True, (0, 0, 0))
                text_rect = text.get_rect(center=(int(self.x), int(self.y)))
                screen.blit(text, text_rect)
            elif self.bullet_type == 'three_way':
                # Vẽ 3 đường
                for i in range(3):
                    angle_offset = (i - 1) * 0.3
                    length = 15
                    end_x = self.x + math.cos(self.angle + angle_offset) * length
                    end_y = self.y + math.sin(self.angle + angle_offset) * length
                    pygame.draw.line(screen, (255, 255, 255), 
                                   (int(self.x), int(self.y)), 
                                   (int(end_x), int(end_y)), 3)
        
        if self.collected_value is not None:
            value_text = str(self.collected_value)
            if isinstance(self.collected_value, float):
                value_text = f"{self.collected_value:.1f}"
                
            text_surface = font_tiny.render(value_text, True, (0, 0, 0))
            text_rect = text_surface.get_rect(center=(int(self.x), int(self.y) + 25))
            
            pygame.draw.rect(screen, (255, 255, 200), 
                           (text_rect.x - 5, text_rect.y - 3, 
                            text_rect.width + 10, text_rect.height + 6),
                           border_radius=5)
            pygame.draw.rect(screen, (100, 100, 100), 
                           (text_rect.x - 5, text_rect.y - 3, 
                            text_rect.width + 10, text_rect.height + 6),
                           2, border_radius=5)
            
            screen.blit(text_surface, text_rect)

class Cannon:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.angle = math.pi / 2
        self.base_rotation_speed = 0.02
        self.rotation_speed = self.base_rotation_speed
        self.rotating_right = True
        self.barrel_length = 100
        
        self.min_angle = 0
        self.max_angle = math.pi
        
        self.show_laser = True
        self.laser_length = 150
        
        # Hiệu ứng đặc biệt
        self.slow_timer = 0
    
    @profile_call
    def update(self):
        # Cập nhật hiệu ứng làm chậm
        if self.slow_timer > 0:
            self.slow_timer -= 1
            self.rotation_speed = self.base_rotation_speed * 0.3
        else:
            self.rotation_speed = self.base_rotation_speed
        
        # Cập nhật góc quay
        if self.rotating_right:
            self.angle += self.rotation_speed
            if self.angle > self.max_angle:
                self.angle = self.max_angle
                self.rotating_right = False
        else:
            self.angle -= self.rotation_speed
            if self.angle < self.min_angle:
                self.angle = self.min_angle
                self.rotating_right = True

    def draw_laser(self, screen):
        if not self.show_laser:
            return
            
        laser_end_x = self.x + math.cos(self.angle) * self.laser_length
        laser_end_y = self.y - math.sin(self.angle) * self.laser_length
        
        # Vẽ đường laser đơn giản không chia vạch
        pygame.draw.line(screen, (255, 50, 50), 
                        (int(self.x), int(self.y)), 
                        (int(laser_end_x), int(laser_end_y)), 4)
        
        # Vẽ mũi tên nhọn ở cuối laser
        arrow_length = 15  # Giảm kích thước mũi tên
        arrow_angle = math.pi / 6  # 30 độ
        
        # Tính góc pháp tuyến
        angle1 = self.angle + arrow_angle
        angle2 = self.angle - arrow_angle
        
        # Tính điểm cho mũi tên
        arrow_x1 = laser_end_x - arrow_length * math.cos(angle1)
        arrow_y1 = laser_end_y + arrow_length * math.sin(angle1)
        
        arrow_x2 = laser_end_x - arrow_length * math.cos(angle2)
        arrow_y2 = laser_end_y + arrow_length * math.sin(angle2)
        
        # Vẽ tam giác mũi tên
        pygame.draw.polygon(screen, (255, 50, 50), [
            (int(laser_end_x), int(laser_end_y)),
            (int(arrow_x1), int(arrow_y1)),
            (int(arrow_x2), int(arrow_y2))
        ])
    
    @profile_call
    def draw(self, screen):
        self.draw_laser(screen)
        
        if use_images and cannon_base_image:
            screen.blit(cannon_base_image, 
                       (self.x - cannon_base_image.get_width() // 2,
                        self.y - cannon_base_image.get_height() // 2))
        else:
            pygame.draw.circle(screen, (100, 100, 100), (self.x, self.y), 40)
            pygame.draw.circle(screen, (80, 80, 80), (self.x, self.y), 40, 3)
        
        barrel_end_x = self.x + math.cos(self.angle) * self.barrel_length
        barrel_end_y = self.y - math.sin(self.angle) * self.barrel_length
        
        if use_images and cannon_barrel_image:
            rotated_barrel = pygame.transform.rotate(cannon_barrel_image, -math.degrees(self.angle))
            screen.blit(rotated_barrel,
                       (self.x - rotated_barrel.get_width() // 2,
                        self.y - rotated_barrel.get_height() // 2))
        else:
            pygame.draw.line(screen, (120, 120, 120), 
                           (self.x, self.y), 
                           (int(barrel_end_x), int(barrel_end_y)), 25)
            pygame.draw.line(screen, (80, 80, 80), 
                           (self.x, self.y), 
                           (int(barrel_end_x), int(barrel_end_y)), 5)
        
        # Vẽ hiệu ứng đặc biệt trên súng
        if self.slow_timer > 0:
            # Hiệu ứng làm chậm (màu xanh dương)
            pygame.draw.circle(screen, (0, 100, 255), (int(self.x), int(self.y)), 45, 3)
            slow_text = font_tiny.render("CHẬM", True, (0, 100, 255))
            screen.blit(slow_text, (self.x - 25, self.y - 60))
        
        pygame.draw.circle(screen, (255, 200, 0), (int(self.x), int(self.y)), 8)
        
    
    def shoot(self, bullet_type='normal'):
        sound_manager.play_sound('shoot')
        barrel_end_x = self.x + math.cos(self.angle) * (self.barrel_length + 10)
        barrel_end_y = self.y - math.sin(self.angle) * (self.barrel_length + 10)
        return Bullet(barrel_end_x, barrel_end_y, self.angle, bullet_type)
    
    def apply_slow_effect(self, duration=300):  # 5 giây
        self.slow_timer = duration

class TargetCell:
    def __init__(self, x, y, row_idx, col_name, correct_value=None):
        self.x = x
        self.y = y
        self.width = 150
        self.height = 60
        self.row_idx = row_idx
        self.col_name = col_name
        self.correct_value = correct_value
        self.filled = False
        self.filled_value = None
        self.blink_timer = 0
        self.show_hint = False
        self.hint_timer = 0
        self.hovered = False
        
    def update(self, mouse_pos):
        mouse_x, mouse_y = mouse_pos
        self.hovered = (
            abs(mouse_x - self.x) < self.width and
            abs(mouse_y - self.y) < self.height
        )
        return self.hovered
        
    def draw(self, screen):
        if self.hovered and not self.filled:
            color = (255, 150, 100)
            border_color = (255, 255, 100)
        elif self.blink_timer > 0:
            if self.blink_timer % 10 < 5:
                color = (255, 255, 100)
                border_color = (255, 255, 200)
            else:
                color = (255, 100, 100) if not self.filled else (100, 255, 100)
                border_color = (255, 200, 200) if not self.filled else (200, 255, 200)
        else:
            color = (255, 100, 100) if not self.filled else (100, 255, 100)
            border_color = (255, 200, 200) if not self.filled else (200, 255, 200)
        
        pygame.draw.rect(screen, color, 
                        (self.x - self.width//2, self.y - self.height//2, 
                         self.width, self.height), 
                        border_radius=12)
        pygame.draw.rect(screen, border_color, 
                        (self.x - self.width//2, self.y - self.height//2, 
                         self.width, self.height), 
                        4, border_radius=12)
        
        if not self.filled:
            target_icon = "🎯"
            color_text = (255, 255, 200)
            icon_size = font_large
        else:
            target_icon = "✅"
            color_text = (200, 255, 200)
            icon_size = font_large
            
        icon_surface = icon_size.render(target_icon, True, color_text)
        icon_rect = icon_surface.get_rect(center=(self.x, self.y - 10))
        screen.blit(icon_surface, icon_rect)
        
        label_text = f"{self.col_name}[{self.row_idx+1}]"
        label_surface = font_small.render(label_text, True, (255, 255, 200))
        label_rect = label_surface.get_rect(center=(self.x, self.y + 25))
        screen.blit(label_surface, label_rect)
        
        if self.filled and self.filled_value is not None:
            value_text = str(self.filled_value)
            if isinstance(self.filled_value, float):
                value_text = f"{self.filled_value:.1f}"
            value_surface = font_medium.render(value_text, True, (200, 255, 200))
            value_rect = value_surface.get_rect(center=(self.x, self.y + 50))
            screen.blit(value_surface, value_rect)
        
        if self.show_hint and self.hint_timer > 0 and self.correct_value is not None:
            hint_text = f"💡 Giá trị đúng: {self.correct_value}"
            hint_surface = font_small.render(hint_text, True, (100, 255, 100))
            hint_rect = hint_surface.get_rect(center=(self.x, self.y + 70))
            screen.blit(hint_surface, hint_rect)
        
        if self.hovered and not self.filled:
            glow_surface = pygame.Surface((self.width + 20, self.height + 20), pygame.SRCALPHA)
            pygame.draw.rect(glow_surface, (255, 255, 200, 50), 
                           (0, 0, self.width + 20, self.height + 20), 
                           border_radius=15)
            screen.blit(glow_surface, 
                       (self.x - (self.width + 20)//2, 
                        self.y - (self.height + 20)//2))
        
        if self.blink_timer > 0:
            self.blink_timer -= 1
                
        if self.show_hint and self.hint_timer > 0:
            self.hint_timer -= 1
            if self.hint_timer == 0:
                self.show_hint = False
    
    def check_collision(self, bullet_x, bullet_y, bullet_radius):
        if self.filled:
            return False
            
        rect_left = self.x - self.width // 2
        rect_top = self.y - self.height // 2
        rect_right = self.x + self.width // 2
        rect_bottom = self.y + self.height // 2
        
        closest_x = max(rect_left, min(bullet_x, rect_right))
        closest_y = max(rect_top, min(bullet_y, rect_bottom))
        
        distance_x = bullet_x - closest_x
        distance_y = bullet_y - closest_y
        
        return (distance_x**2 + distance_y**2) <= (bullet_radius**2)

class DataTable:
    def __init__(self, df, missing_cells, correct_values):
        self.df = df.copy()
        self.missing_cells = missing_cells
        self.correct_values = correct_values
        self.cell_width = 120
        self.cell_height = 50
        self.header_height = 40
        self.row_height = 50
        self.table_x = 50
        self.table_y = HEIGHT - 320
        self.targets = []
        
        cols = list(df.columns)
        for idx, (row_idx, col_name) in enumerate(missing_cells):
            col_idx = cols.index(col_name)
            x = self.table_x + col_idx * self.cell_width + self.cell_width//2
            y = self.table_y + self.header_height + (row_idx + 0.5) * self.row_height
            
            correct_val = correct_values[idx] if idx < len(correct_values) else None
            target = TargetCell(x, y, row_idx, col_name, correct_val)
            self.targets.append(target)
            break
    
    @profile_call
    def update(self, mouse_pos):
        if self.targets:
            return self.targets[0].update(mouse_pos)
        return False
    
    @profile_call
    def draw(self, screen):
        table_width = len(self.df.columns) * self.cell_width
        table_height = self.header_height + len(self.df) * self.row_height
        
        pygame.draw.rect(screen, DATA_TABLE_BG, 
                        (self.table_x, self.table_y, table_width, table_height),
                        border_radius=10)
        pygame.draw.rect(screen, (200, 200, 200), 
                        (self.table_x, self.table_y, table_width, table_height),
                        2, border_radius=10)
        
        cols = list(self.df.columns)
        for i, col in enumerate(cols):
            x = self.table_x + i * self.cell_width
            pygame.draw.rect(screen, (60, 65, 80), 
                           (x, self.table_y, self.cell_width, self.header_height))
            
            col_text = col if len(col) <= 8 else col[:8] + "..."
            text_surface = font_small.render(col_text, True, (255, 255, 200))
            text_rect = text_surface.get_rect(center=(x + self.cell_width//2, 
                                                    self.table_y + self.header_height//2))
            screen.blit(text_surface, text_rect)
        
        for i in range(len(self.df)):
            row_y = self.table_y + self.header_height + i * self.row_height
            
            for j, col in enumerate(cols):
                cell_x = self.table_x + j * self.cell_width
                is_missing = (i, col) in self.missing_cells
                
                if is_missing:
                    cell_color = (150, 50, 50)
                else:
                    cell_color = (70, 75, 90)
                    
                pygame.draw.rect(screen, cell_color, 
                               (cell_x, row_y, self.cell_width, self.row_height))
                
                value = self.df.iloc[i][col]
                if pd.isna(value) or value is None:
                    if is_missing:
                        continue
                    else:
                        continue
                else:
                    if isinstance(value, float):
                        value_text = f"{value:.1f}"
                    else:
                        value_text = str(value)
                    color = (240, 240, 240) if not is_missing else (255, 200, 200)
                
                text_surface = font_tiny.render(value_text, True, color)
                text_rect = text_surface.get_rect(center=(cell_x + self.cell_width//2, 
                                                        row_y + self.row_height//2))
                screen.blit(text_surface, text_rect)
        
        if self.targets:
            self.targets[0].draw(screen)

# === BTVN03: hàm bổ sung riêng cho bài tập, không thuộc code gốc ===
@profile_call
def calculate_combo_bonus(streak, level, depth_limit=5):
    """
    Tính điểm combo theo cấp số nhân bằng đệ quy.
    Hàm này KHÔNG thuộc logic gốc của game, được thêm vào
    chỉ để phục vụ minh họa đệ quy cho bài tập profiling.
    Mỗi lần gọi đệ quy là 1 entry riêng trong call_records,
    với parent_function là chính tên hàm này và depth tăng dần.
    """
    if streak <= 0 or depth_limit <= 0:
        return 0
    base_bonus = 10 * level
    return base_bonus + calculate_combo_bonus(streak - 1, level, depth_limit - 1)

class Game:
    def __init__(self):
        self.cannon = Cannon(WIDTH // 2, HEIGHT - 150)
        self.bullets = []
        self.max_bullets = 10
        self.bullets_fired = 0
        
        # Thêm vật phẩm
        self.powerups = []
        
        # Thêm vụ nổ
        self.explosions = []
        
        # Hiệu ứng đặc biệt - CHỈ cho lần bắn TIẾP THEO
        self.next_shot_effect = None  # None, 'triple', 'three_way', 'explosive'
        
        # Quản lý spawn vật phẩm
        self.last_powerup_spawn = 0
        self.powerup_spawn_delay = 2000  # 2 giây
        
        # Tạo nút cho menu in-game
        self.menu_button = Button(WIDTH - 120, 20, 100, 40, "Menu")
        self.help_button = Button(WIDTH - 230, 20, 100, 40, "?")
        
        self.reset()
        
    def reset(self):
        self.level = 1
        self.bullets_fired = 0
        self.max_levels = 4
        self.game_state = STATE_MENU
        self.hint = ""
        self.selected_target = None
        self.distractors = []
        self.previous_state = None
        
        # Reset hiệu ứng
        self.next_shot_effect = None
        
        self.generate_level()
        
    @profile_call
    def generate_level(self):
        self.df, self.missing_cells, self.correct_values, self.hint, self.distractors = DatasetGenerator.generate_level(self.level)
        
        self.data_table = DataTable(self.df, self.missing_cells, self.correct_values)
        self.create_number_bubbles()
        
        self.bullets = []
        self.explosions = []
        self.powerups = []
        self.bullets_fired = 0
        self.selected_target = None
        self.show_tutorial = True
        self.tutorial_timer = 180
        
        # RESET HIỆU ỨNG KHI CHUYỂN LEVEL
        self.next_shot_effect = None
        
        # CẤU HÌNH ĐỘ KHÓ DỰA TRÊN LEVEL
        if self.level >= 2:
            # Tăng tốc độ quay của pháo từ level 2
            self.cannon.base_rotation_speed = 0.03 + (self.level - 2) * 0.005  # Level 2: 0.03, Level 3: 0.035, Level 4: 0.04
            self.cannon.rotation_speed = self.cannon.base_rotation_speed
            
            # Rút ngắn laser để tăng độ khó
            self.cannon.laser_length = max(100, 150 - (self.level - 1) * 15)  # Level 2: 135px, Level 3: 120px, Level 4: 105px
        else:
            # Level 1: giữ nguyên
            self.cannon.base_rotation_speed = 0.02
            self.cannon.rotation_speed = self.cannon.base_rotation_speed
            self.cannon.laser_length = 150
        
        # Reset hiệu ứng súng
        self.cannon.slow_timer = 0
        
        # Reset spawn timer
        self.last_powerup_spawn = pygame.time.get_ticks()
    
    @profile_call
    def create_number_bubbles(self):
        self.number_bubbles = []
        correct_value = self.correct_values[0]
        
        # CẬP NHẬT: TỪ LEVEL 2 - BONG BÓNG CHỈ DI CHUYỂN THEO ĐƯỜNG THẲNG NGANG
        if self.level == 1:
            # LEVEL 1: Các bong bóng đứng yên, bong bóng sai che bong bóng đúng
            correct_x, correct_y = WIDTH // 2, 250
            correct_bubble = NumberBubble(correct_value, correct_x, correct_y, correct_value, is_moving=False, level=self.level)
            self.number_bubbles.append(correct_bubble)
            
            # Tạo 16 bong bóng sai che xung quanh
            wrong_positions = [
                (correct_x - 120, correct_y - 80), (correct_x + 120, correct_y - 80),
                (correct_x + 220, correct_y - 80), (correct_x - 220, correct_y - 80),
                (correct_x - 120, correct_y + 80), (correct_x + 120, correct_y + 80),
                (correct_x , correct_y - 80), (correct_x + 90 , correct_y),
                (correct_x - 90 , correct_y), (correct_x + 180 , correct_y),
                (correct_x - 180 , correct_y), (correct_x, correct_y + 80),
                (correct_x, correct_y + 150), (correct_x + 90, correct_y + 150),
                (correct_x - 90, correct_y + 150), (correct_x , correct_y + 220)
            ]
            
            for i, (x, y) in enumerate(wrong_positions):
                if i < len(self.distractors):
                    value = self.distractors[i]
                else:
                    value = random.randint(10, 100)
                
                # ĐẢM BẢO giá trị không trùng với correct_value
                while str(value) == str(correct_value):
                    value = random.randint(10, 100)
                
                # QUAN TRỌNG: Truyền correct_value=None để không đánh dấu là bong bóng đúng
                bubble = NumberBubble(value, x, y, correct_value=None, is_moving=False, level=self.level)
                self.number_bubbles.append(bubble)
                
        else:
            # TỪ LEVEL 2 TRỞ ĐI: bong bóng di chuyển theo đường thẳng ngang
            # Tính hệ số độ khó
            difficulty_factor = 1.0 + (self.level - 2) * 0.5  # Level 2: 1.0, Level 3: 1.5, Level 4: 2.0
            
            # Tạo bong bóng đúng - Ở TRÊN CÙNG
            x = random.randint(200, WIDTH - 200)
            y = 150  # Vị trí trên cùng
            bubble = NumberBubble(correct_value, x, y, correct_value, is_moving=True, 
                                  speed_factor=difficulty_factor, level=self.level)
            self.number_bubbles.append(bubble)
            
            # TĂNG SỐ LƯỢNG BONG BÓNG SAI THEO LEVEL
            n_distractors = min(12 + (self.level - 2) * 4, 25)  # Level 2: 12, Level 3: 16, Level 4: 20
            
            # Tạo nhiều giá trị nhiễu hơn nếu cần
            extended_distractors = self.distractors.copy()
            while len(extended_distractors) < n_distractors:
                if random.random() < 0.5:
                    # Thêm số nguyên
                    new_value = random.randint(10, 100)
                    # Đảm bảo không trùng với các giá trị đã có
                    while any(str(new_value) == str(d) for d in extended_distractors) or str(new_value) == str(correct_value):
                        new_value = random.randint(10, 100)
                    extended_distractors.append(new_value)
                else:
                    # Thêm số thập phân
                    new_value = round(random.uniform(10, 100), 1)
                    # Đảm bảo không trùng với các giá trị đã có
                    while any(abs(new_value - float(d)) < 0.1 for d in extended_distractors if isinstance(d, (int, float))) or abs(new_value - float(correct_value)) < 0.1:
                        new_value = round(random.uniform(10, 100), 1)
                    extended_distractors.append(new_value)
            
            # Tạo các hàng cho bong bóng sai - bong bóng sai ở các hàng bên dưới
            rows = 4  # 4 hàng
            row_height = (HEIGHT - 400) // rows
            
            for i in range(n_distractors):
                if i < len(extended_distractors):
                    value = extended_distractors[i]
                else:
                    if random.random() < 0.3:
                        value = random.choice(['X', 'Y', 'Z'])
                    else:
                        value = random.randint(10, 100)
                
                # Đảm bảo không trùng với giá trị đúng
                while str(value) == str(correct_value):
                    value = random.randint(10, 100)
                
                # Phân bố bong bóng theo hàng (từ hàng 1 đến 4)
                row = (i % rows) + 1  # Bắt đầu từ hàng 1, không phải 0
                x = random.randint(100, WIDTH - 100)
                y = 150 + row * row_height  # Các hàng dưới bong bóng đúng
                
                # Tốc độ ngẫu nhiên khác nhau để tạo độ phức tạp
                speed_multiplier = random.uniform(0.8, 1.5)
                
                # QUAN TRỌNG: Truyền correct_value=None để không đánh dấu là bong bóng đúng
                bubble = NumberBubble(value, x, y, correct_value=None, is_moving=True, 
                                      speed_factor=difficulty_factor * speed_multiplier, level=self.level)
                
                # 50% bong bóng di chuyển ngược chiều
                if random.random() < 0.5:
                    bubble.speed_x *= -1
                
                self.number_bubbles.append(bubble)
    
    @profile_call
    def spawn_powerup(self):
        """Tạo vật phẩm mới rơi từ trên xuống"""
        current_time = pygame.time.get_ticks()
        
        # TĂNG TẦN SUẤT VẬT PHẨM TỪ LEVEL 2
        if self.level == 1:
            spawn_delay = 5000  # Level 1: 5 giây
        else:
            spawn_delay = max(1000, 3000 - (self.level - 2) * 500)  # Level 2: 3s, Level 3: 2.5s, Level 4: 2s
        
        if current_time - self.last_powerup_spawn > spawn_delay:
            self.last_powerup_spawn = current_time
            
            # TỪ LEVEL 2: Tăng tỉ lệ vật phẩm xấu
            if self.level == 1:
                power_type = 'good'  # Level 1 chỉ có vật phẩm tốt
            else:
                # Level 2+: 50% tốt, 50% xấu
                power_type = 'good' if random.random() < 0.5 else 'bad'
            
            # Vị trí xuất hiện ngẫu nhiên từ trên cùng
            x = random.randint(50, WIDTH - 50)
            y = -50
            
            powerup = PowerUp(x, y, power_type)
            self.powerups.append(powerup)
    
    @profile_call
    def update(self):
        if self.game_state == STATE_PLAYING:
            if self.tutorial_timer > 0:
                self.tutorial_timer -= 1
            
            # Spawn vật phẩm mới (chỉ từ level 2 trở đi)
            if self.level >= 2:
                self.spawn_powerup()
            
            mouse_pos = pygame.mouse.get_pos()
            
            # Cập nhật các nút in-game
            self.menu_button.update(mouse_pos)
            self.help_button.update(mouse_pos)
            
            if self.data_table:
                self.data_table.update(mouse_pos)
            
            self.cannon.update()
            
            for bubble in self.number_bubbles:
                bubble.update()
            
            # Cập nhật vật phẩm (chỉ từ level 2 trở đi)
            if self.level >= 2:
                for powerup in self.powerups[:]:
                    powerup.update()
                    if not powerup.active:
                        self.powerups.remove(powerup)
            
            # Cập nhật vụ nổ
            for explosion in self.explosions[:]:
                explosion.update()
                if not explosion.active:
                    self.explosions.remove(explosion)
            
            bullets_to_remove = []
            
            for i, bullet in enumerate(self.bullets):
                if bullet.active:
                    stopped = bullet.update()
                    
                    if stopped:
                        bullets_to_remove.append(i)
                        continue
                    
                    # Nếu là đạn nổ, kiểm tra va chạm đặc biệt
                    if bullet.bullet_type == 'explosive':
                        # Kiểm tra xem đạn nổ có chạm bong bóng không
                        for bubble in self.number_bubbles:
                            if not bubble.collected and bubble.check_collision(bullet.x, bullet.y, bullet.radius):
                                # Tạo vụ nổ
                                explosion = Explosion(bullet.x, bullet.y)
                                self.explosions.append(explosion)
                                sound_manager.play_sound('explosion')
                                bullet.active = False
                                break
                        
                        # Kiểm tra xem đạn nổ có chạm vật phẩm không
                        for powerup in self.powerups:
                            if not powerup.collected and powerup.check_collision(bullet.x, bullet.y, bullet.radius):
                                # Tạo vụ nổ
                                explosion = Explosion(bullet.x, bullet.y)
                                self.explosions.append(explosion)
                                sound_manager.play_sound('explosion')
                                bullet.active = False
                                break
                    
                    # KIỂM TRA VA CHẠM VỚI BONG BÓNG
                    # Kiểm tra tất cả bong bóng để tìm bong bóng gần nhất mà đạn chạm
                    closest_bubble = None
                    min_distance = float('inf')
                    
                    for bubble in self.number_bubbles:
                        if not bubble.collected and bubble.check_collision(bullet.x, bullet.y, bullet.radius):
                            distance = math.sqrt((bullet.x - bubble.x)**2 + (bullet.y - bubble.y)**2)
                            if distance < min_distance:
                                min_distance = distance
                                closest_bubble = bubble
                    
                    if closest_bubble:
                        bullet.active = False
                        closest_bubble.collected = True
                        
                        # Phát âm thanh khi chạm bong bóng
                        if closest_bubble.is_correct:
                            sound_manager.play_sound('correct')
                            
                            # THẮNG NGAY LẬP TỨC KHI CHẠM BONG BÓNG ĐÚNG
                            if self.data_table.targets:
                                target = self.data_table.targets[0]
                                if not target.filled:
                                    target.filled = True
                                    target.filled_value = closest_bubble.value
                                    target.blink_timer = 30
                            
                            # Phát âm thanh chiến thắng
                            sound_manager.play_sound('win')
                            
                            if self.level < self.max_levels:
                                self.game_state = STATE_LEVEL_COMPLETE
                            else:
                                self.game_state = STATE_GAME_WIN
                            
                            return
                        else:
                            # Bắn trúng bong bóng sai
                            sound_manager.play_sound('pop')
                        
                        continue
                    
                    # KIỂM TRA VA CHẠM VỚI VẬT PHẨM (chỉ từ level 2)
                    if self.level >= 2:
                        powerup_collided = None
                        for powerup in self.powerups:
                            if not powerup.collected and powerup.check_collision(bullet.x, bullet.y, bullet.radius):
                                powerup_collided = powerup
                                break
                        
                        if powerup_collided:
                            bullet.active = False
                            powerup_collided.collected = True
                            
                            # Xử lý hiệu ứng vật phẩm
                            self.apply_powerup_effect(powerup_collided)
                            
                            continue
                    
                    # KIỂM TRA VA CHẠM VỚI MỤC TIÊU
                    if self.data_table.targets:
                        target = self.data_table.targets[0]
                        if not target.filled and target.check_collision(bullet.x, bullet.y, bullet.radius):
                            bullet.active = False
                            # Không làm gì khi chạm mục tiêu mà không có giá trị
                            continue
            
            # Kiểm tra va chạm với vụ nổ
            for explosion in self.explosions:
                # Kiểm tra bong bóng với vụ nổ
                for bubble in self.number_bubbles:
                    if not bubble.collected and explosion.check_collision(bubble.x, bubble.y, bubble.radius):
                        bubble.collected = True
                        
                        # Phát âm thanh khi chạm bong bóng
                        if bubble.is_correct:
                            sound_manager.play_sound('correct')
                            
                            # THẮNG NGAY LẬP TỨC KHI CHẠM BONG BÓNG ĐÚNG
                            if self.data_table.targets:
                                target = self.data_table.targets[0]
                                if not target.filled:
                                    target.filled = True
                                    target.filled_value = bubble.value
                                    target.blink_timer = 30
                            
                            # Phát âm thanh chiến thắng
                            sound_manager.play_sound('win')
                            
                            if self.level < self.max_levels:
                                self.game_state = STATE_LEVEL_COMPLETE
                            else:
                                self.game_state = STATE_GAME_WIN
                            
                            return
                        else:
                            sound_manager.play_sound('pop')
                
                # Kiểm tra vật phẩm với vụ nổ
                for powerup in self.powerups:
                    if not powerup.collected and explosion.check_collision(powerup.x, powerup.y, powerup.radius):
                        powerup.collected = True
                        # Xử lý hiệu ứng vật phẩm
                        self.apply_powerup_effect(powerup)
            
            for i in sorted(bullets_to_remove, reverse=True):
                if i < len(self.bullets):
                    del self.bullets[i]
            
            if self.game_state == STATE_PLAYING:
                active_bullets = sum(1 for b in self.bullets if b.active)
                
                if self.bullets_fired >= self.max_bullets and active_bullets == 0:
                    if not self.selected_target or not self.selected_target.filled:
                        # Phát âm thanh thua
                        sound_manager.play_sound('lose')
                        self.game_state = STATE_GAME_OVER
    
    @profile_call
    def apply_powerup_effect(self, powerup):
        """Áp dụng hiệu ứng của vật phẩm - CHỈ cho lần bắn TIẾP THEO"""
        if powerup.type == 'good':
            sound_manager.play_sound('powerup_good')
            
            if powerup.specific_type == 'triple_shot':
                self.next_shot_effect = 'triple'  # CHỈ lần bắn TIẾP THEO
                # Thông báo
                self.show_powerup_message("LẦN BẮN TIẾP: 3 viên liên tiếp!")
                
            elif powerup.specific_type == 'three_way':
                self.next_shot_effect = 'three_way'  # CHỈ lần bắn TIẾP THEO
                # Thông báo
                self.show_powerup_message("LẦN BẮN TIẾP: 3 tia đạn!")
                
            elif powerup.specific_type == 'explosive':
                self.next_shot_effect = 'explosive'  # CHỈ lần bắn TIẾP THEO
                # Thông báo
                self.show_powerup_message("LẦN BẮN TIẾP: Đạn nổ!")
                
        else:  # Vật phẩm xấu
            sound_manager.play_sound('powerup_bad')
            
            if powerup.specific_type == 'lose_ammo':
                # Mất 2 viên đạn NGAY LẬP TỨC
                self.bullets_fired = min(self.max_bullets, self.bullets_fired + 2)
                # Thông báo
                self.show_powerup_message("MẤT ĐẠN! -2 viên đạn", is_bad=True)
                
            elif powerup.specific_type == 'slow_cannon':
                # Làm chậm súng trong 5 giây NGAY LẬP TỨC
                self.cannon.apply_slow_effect(300)
                # Thông báo
                self.show_powerup_message("SÚNG CHẬM! Tốc độ quay giảm", is_bad=True)
    
    #Hàm này quá nhỏ nên ko đo
    def show_powerup_message(self, message, is_bad=False):
        """Hiển thị thông báo khi nhận vật phẩm"""
        self.powerup_message = message
        self.powerup_message_timer = 120  # 2 giây
        self.powerup_message_is_bad = is_bad
    
    @profile_call
    def shoot_bullet(self):
        if self.game_state == STATE_PLAYING and self.bullets_fired < self.max_bullets:
            bullet_type = 'normal'
            
            # Xác định loại đạn cho lần bắn này (CHỈ lần TIẾP THEO)
            if self.next_shot_effect:
                bullet_type = self.next_shot_effect
                # SAU KHI BẮN, RESET HIỆU ỨNG (CHỈ CÓ TÁC DỤNG 1 LẦN)
                self.next_shot_effect = None
            
            # Tạo đạn
            if bullet_type == 'triple':
                sound_manager.play_sound('triple_shot')
                # Tạo 3 viên đạn với góc lệch nhỏ
                bullets = []
                for i in range(3):
                    angle_offset = (i - 1) * 0.1  # -0.1, 0, 0.1
                    bullet = Bullet(
                        self.cannon.x + math.cos(self.cannon.angle + angle_offset) * (self.cannon.barrel_length + 10),
                        self.cannon.y - math.sin(self.cannon.angle + angle_offset) * (self.cannon.barrel_length + 10),
                        self.cannon.angle + angle_offset,
                        'triple'
                    )
                    bullets.append(bullet)
                
                self.bullets.extend(bullets)
                self.bullets_fired += 1  # Chỉ tính 1 lần bắn
                return True
                
            elif bullet_type == 'three_way':
                sound_manager.play_sound('three_way')
                # Tạo 3 viên đạn với góc lệch lớn hơn
                bullets = []
                for i in range(3):
                    angle_offset = (i - 1) * 0.3  # -0.3, 0, 0.3
                    bullet = Bullet(
                        self.cannon.x + math.cos(self.cannon.angle + angle_offset) * (self.cannon.barrel_length + 10),
                        self.cannon.y - math.sin(self.cannon.angle + angle_offset) * (self.cannon.barrel_length + 10),
                        self.cannon.angle + angle_offset,
                        'three_way'
                    )
                    bullets.append(bullet)
                
                self.bullets.extend(bullets)
                self.bullets_fired += 1  # Chỉ tính 1 lần bắn
                return True
                
            else:
                # Đạn thường hoặc đạn nổ
                bullet = self.cannon.shoot(bullet_type)
                self.bullets.append(bullet)
                self.bullets_fired += 1
                return True
        return False
    
    @profile_call
    def draw_ui(self, screen):
        ui_top = pygame.Surface((WIDTH, 80))
        ui_top.fill(UI_BG)
        pygame.draw.rect(ui_top, (0, 0, 0, 100), (0, 78, WIDTH, 2))
        
        level_text = font_medium.render(f"Cấp độ: {self.level}/{self.max_levels}", True, TEXT_COLOR)
        
        bullets_text = font_medium.render(f"Đạn: {self.bullets_fired}/{self.max_bullets}", True, 
                                         (255, 150, 150) if self.bullets_fired >= self.max_bullets else TEXT_COLOR)
        
        ui_top.blit(level_text, (20, 20))
        ui_top.blit(bullets_text, (WIDTH // 2 - 60, 20))
        
        # HIỂN THỊ ĐỘ KHÓ
        if self.level >= 2:
            difficulty_text = font_small.render(f"🎯 ĐỘ KHÓ: {'★' * self.level}", True, (255, 100, 100))
            ui_top.blit(difficulty_text, (WIDTH - 200, 20))
        
        hint_text = font_small.render(f"💡 {self.hint}", True, HINT_COLOR)
        ui_top.blit(hint_text, (20, 55))
        
        shoot_text = font_small.render("BẮN: Phím SPACE", True, (255, 200, 100))
        ui_top.blit(shoot_text, (WIDTH // 2 + 100, 55))
        
        # Hiển thị hiệu ứng đạn đặc biệt CHO LẦN BẮN TIẾP THEO
        if self.next_shot_effect:
            effect_name = {
                'triple': '3 liên tiếp',
                'three_way': '3 tia',
                'explosive': 'Đạn nổ'
            }.get(self.next_shot_effect, 'Đặc biệt')
            
            effect_text = font_tiny.render(f"LẦN TIẾP: {effect_name}", True, (255, 255, 100))
            ui_top.blit(effect_text, (WIDTH - 200, 40))
        
        screen.blit(ui_top, (0, 0))
        
        ui_bottom = pygame.Surface((WIDTH, 100))
        ui_bottom.fill(UI_BG)
        pygame.draw.rect(ui_bottom, (0, 0, 0, 100), (0, 0, WIDTH, 2))
        screen.blit(ui_bottom, (0, HEIGHT - 100))
        
        self.cannon.draw(screen)
        
        # Vẽ nút menu và help khi đang chơi
        if self.game_state == STATE_PLAYING:
            self.menu_button.draw(screen)
            self.help_button.draw(screen)
        
        if self.show_tutorial and self.tutorial_timer > 0:
            self.draw_tutorial(screen)
        
        # Hiển thị thông báo vật phẩm nếu có
        if hasattr(self, 'powerup_message_timer') and self.powerup_message_timer > 0:
            self.draw_powerup_message(screen)
        
        # Đếm số bong bóng còn lại (chỉ để tham khảo)
        remaining_correct = len([b for b in self.number_bubbles if not b.collected and b.is_correct])
        if remaining_correct > 0 and self.game_state == STATE_PLAYING:
            correct_text = font_tiny.render(f"Bong bóng đúng còn lại: {remaining_correct}", True, (100, 255, 100))
            screen.blit(correct_text, (WIDTH - 250, 60))
    
    def draw_tutorial(self, screen):
        tutorial_box = pygame.Surface((500, 200), pygame.SRCALPHA)
        tutorial_box.fill((0, 0, 0, 200))
        pygame.draw.rect(tutorial_box, (255, 215, 0), 
                        (0, 0, 500, 200), 3, border_radius=10)
        
        screen.blit(tutorial_box, (WIDTH//2 - 250, 100))
        
        correct_value = self.correct_values[0] if self.correct_values else "?"
        
        if self.level == 1:
            tutorial_text = [
                f"LEVEL {self.level} - HỌC CÁCH CHƠI",
                f"TÌM SỐ: {correct_value}",
                f"1. Bong bóng ĐÚNG (XANH LÁ) bị bong bóng SAI che",
                f"2. BẮN bong bóng SAI để mở đường",
                f"3. Bắn trúng bong bóng ĐÚNG để thắng ngay",
            ]
        else:
            tutorial_text = [
                f"🎯 LEVEL {self.level} - ĐỘ KHÓ CAO!",
                f"TÌM SỐ: {correct_value}"
            ]
        
        for i, text in enumerate(tutorial_text):
            color = (255, 215, 0) if i == 0 else (200, 255, 200)
            if i == 1:
                color = (100, 255, 100)
            if i == 2 or i == 3 or i == 4:
                color = (255, 255, 100)
            if i == 5 or i == 6:
                color = (100, 255, 255)
            text_surf = font_small.render(text, True, color)
            screen.blit(text_surf, (WIDTH//2 - text_surf.get_width()//2, 120 + i * 25))
    
    def draw_powerup_message(self, screen):
        message_box = pygame.Surface((400, 60), pygame.SRCALPHA)
        
        if self.powerup_message_is_bad:
            message_box.fill((255, 50, 50, 200))
            border_color = (255, 150, 150)
            text_color = (255, 255, 200)
        else:
            message_box.fill((50, 200, 255, 200))
            border_color = (150, 255, 255)
            text_color = (255, 255, 200)
        
        pygame.draw.rect(message_box, border_color, 
                        (0, 0, 400, 60), 3, border_radius=10)
        
        screen.blit(message_box, (WIDTH//2 - 200, HEIGHT - 400))
        
        message_surf = font_medium.render(self.powerup_message, True, text_color)
        screen.blit(message_surf, (WIDTH//2 - message_surf.get_width()//2, HEIGHT - 380))
        
        self.powerup_message_timer -= 1
    
    @profile_call
    def draw_sky_numbers(self, screen):
        # Vẽ bong bóng theo thứ tự: sai trước (gần), đúng sau (xa)
        # Sắp xếp theo y để bong bóng gần (y lớn) vẽ trước, xa (y nhỏ) vẽ sau
        for bubble in sorted(self.number_bubbles, key=lambda b: b.y, reverse=True):
            bubble.draw(screen)
        
        for powerup in self.powerups:
            powerup.draw(screen)
        
        for explosion in self.explosions:
            explosion.draw(screen)
    
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
            
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                if self.game_state == STATE_LEVEL_START:
                    self.game_state = STATE_PLAYING
                elif self.game_state == STATE_LEVEL_COMPLETE:
                    self.level += 1
                    self.generate_level()
                    self.game_state = STATE_PLAYING
                elif self.game_state in [STATE_GAME_OVER, STATE_GAME_WIN]:
                    self.reset()
                    self.game_state = STATE_MENU
                elif self.game_state == STATE_PLAYING:
                    self.shoot_bullet()
                    
            elif event.key == pygame.K_r:
                self.reset()
                
            elif event.key == pygame.K_ESCAPE:
                if self.game_state == STATE_PLAYING:
                    self.game_state = STATE_MENU
                else:
                    pygame.quit()
                    sys.exit()
            
            elif event.key == pygame.K_l and self.game_state == STATE_PLAYING:
                self.cannon.show_laser = not self.cannon.show_laser
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if self.game_state == STATE_PLAYING:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    
                    # Kiểm tra nút menu
                    if self.menu_button.rect.collidepoint(mouse_x, mouse_y):
                        self.game_state = STATE_MENU
                        return
                    
                    # Kiểm tra nút help
                    if self.help_button.rect.collidepoint(mouse_x, mouse_y):
                        self.previous_state = self.game_state
                        self.game_state = STATE_INSTRUCTIONS
                        return
                    
                    if self.data_table.targets:
                        target = self.data_table.targets[0]
                        if not target.filled:
                            if (abs(mouse_x - target.x) < target.width and
                                abs(mouse_y - target.y) < target.height):
                                
                                if self.selected_target:
                                    self.selected_target.blink_timer = 0
                                self.selected_target = target
                                target.blink_timer = 60

    def draw_level_start(self, screen):
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(200)
        screen.blit(overlay, (0, 0))
        
        title = font_xlarge.render(f"LEVEL {self.level}", True, (255, 255, 200))
        subtitle = font_large.render("BẮN SỐ TỪ BẦU TRỜI", True, (200, 200, 255))
        
        correct_value = self.correct_values[0] if self.correct_values else "?"
        
        if self.level == 1:
            instructions = [
                "🎮 LEVEL 1 - HỌC CÁCH CHƠI:",
                f"TÌM SỐ: {correct_value}",
                "",
                "⚠️ QUAN TRỌNG:",
                "  • Chạm bong bóng ĐÚNG để thắng ngay",
                "Nhấn SPACE để bắt đầu",
                "ESC để về menu"
            ]
        else:
            difficulty_info = ""
            if self.level == 2:
                difficulty_info = "Bong bóng chỉ di chuyển NGANG"
            elif self.level == 3:
                difficulty_info = "Tốc độ bong bóng: +100% | Laser: 120px"
            elif self.level == 4:
                difficulty_info = "Tốc độ bong bóng: +150% | Laser: 105px"
                
            instructions = [
                f"🎯 LEVEL {self.level} - ĐỘ KHÓ RẤT CAO!",
                f"TÌM SỐ: {correct_value}",
                "Nhấn SPACE để bắt đầu",
                "ESC để về menu"
            ]
        
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 100))
        screen.blit(subtitle, (WIDTH//2 - subtitle.get_width()//2, 170))
        
        for i, line in enumerate(instructions):
            color = (255, 255, 200) if i == 0 else (200, 200, 200)
            if i == 1:
                color = (100, 255, 100)
            if i == 2 or i == 3 or i == 4 or i == 5 or i == 6:
                color = (255, 255, 100)
            if "⚠️" in line:
                color = (255, 150, 100)
            if "💎" in line:
                color = (0, 255, 255)
            
            text = font_medium.render(line, True, color)
            screen.blit(text, (WIDTH//2 - text.get_width()//2, 240 + i * 30))
            
    def draw_level_complete(self, screen):
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(200)
        screen.blit(overlay, (0, 0))
        
        title = font_xlarge.render("CHIẾN THẮNG! 🎉", True, (100, 255, 100))
        shots_text = font_medium.render(f"Số đạn đã dùng: {self.bullets_fired}/{self.max_bullets}", True, TEXT_COLOR)
        
        if self.level < self.max_levels:
            next_text = font_medium.render("Nhấn SPACE để tiếp tục Level " + str(self.level + 1), True, (200, 200, 255))
        else:
            next_text = font_medium.render("Nhấn SPACE để xem kết quả cuối cùng", True, (200, 200, 255))
        
        screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 80))
        screen.blit(shots_text, (WIDTH//2 - shots_text.get_width()//2, HEIGHT//2 - 20))
        screen.blit(next_text, (WIDTH//2 - next_text.get_width()//2, HEIGHT//2 + 40))
        
    def draw_game_over(self, screen):
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(200)
        screen.blit(overlay, (0, 0))
        
        title = font_xlarge.render("HẾT ĐẠN! 💀", True, (255, 100, 100))
        shots_text = font_medium.render(f"Đã dùng: {self.bullets_fired} viên đạn", True, TEXT_COLOR)
        
        if self.data_table.targets and not self.data_table.targets[0].filled:
            target = self.data_table.targets[0]
            correct_info = font_medium.render(f"Giá trị đúng: {target.correct_value}", True, (200, 255, 200))
            screen.blit(correct_info, (WIDTH//2 - correct_info.get_width()//2, HEIGHT//2 + 60))
        
        restart_text = font_medium.render("Nhấn SPACE để về menu chính", True, (200, 200, 255))
        
        screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 80))
        screen.blit(shots_text, (WIDTH//2 - shots_text.get_width()//2, HEIGHT//2 - 20))
        screen.blit(restart_text, (WIDTH//2 - restart_text.get_width()//2, HEIGHT//2 + 100))
        
    def draw_game_win(self, screen):
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(200)
        screen.blit(overlay, (0, 0))
        
        title = font_xlarge.render("CHIẾN THẮNG CUỐI CÙNG! 🏆", True, (100, 255, 100))
        shots_text = font_medium.render(f"Hoàn thành tất cả {self.max_levels} level!", True, TEXT_COLOR)
        
        rating_text = font_medium.render("Bạn đã chiến thắng!", True, (255, 215, 0))
        restart_text = font_medium.render("Nhấn SPACE để về menu chính", True, (200, 200, 255))
        
        screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 120))
        screen.blit(shots_text, (WIDTH//2 - shots_text.get_width()//2, HEIGHT//2 - 50))
        screen.blit(rating_text, (WIDTH//2 - rating_text.get_width()//2, HEIGHT//2 + 0))
        screen.blit(restart_text, (WIDTH//2 - restart_text.get_width()//2, HEIGHT//2 + 100))

def main():
    clock = pygame.time.Clock()
    game = Game()
    menu = Menu()
    
    # Thử phát nhạc nền
    try:
        sound_manager.play_music('background_music.mp3', volume=0.3)
    except:
        print("Không tìm thấy nhạc nền, game sẽ chạy không có nhạc nền")
    
    clouds = []
    for _ in range(10):
        x = random.randint(0, WIDTH)
        y = random.randint(50, int(HEIGHT * 0.7))
        width = random.randint(60, 180)
        height = random.randint(40, 80)
        clouds.append([x, y, width, height])
    
    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # Xử lý sự kiện cho menu
            if game.game_state == STATE_MENU:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    action = menu.handle_click(mouse_pos)
                    if action == "PLAY":
                        game.game_state = STATE_LEVEL_START
                    elif action == "INSTRUCTIONS":
                        game.game_state = STATE_INSTRUCTIONS
                    elif action == "QUIT":
                        running = False
            # Xử lý sự kiện cho màn hình hướng dẫn
            elif game.game_state == STATE_INSTRUCTIONS:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    action = menu.handle_click(mouse_pos)
                    if action == "BACK":
                        if game.previous_state:
                            game.game_state = game.previous_state
                            game.previous_state = None
                        else:
                            game.game_state = STATE_MENU
            # Xử lý sự kiện cho game
            else:
                game.handle_event(event)
        
        # Cập nhật game
        if game.game_state == STATE_PLAYING:
            game.update()
        elif game.game_state in [STATE_MENU, STATE_INSTRUCTIONS]:
            menu.update(mouse_pos)
        
        # Vẽ nền
        if use_images and background_image:
            screen.blit(background_image, (0, 0))
        else:
            screen.fill(SKY_COLOR)
            
            for cloud in clouds:
                cloud[0] += 0.15
                if cloud[0] > WIDTH + 200:
                    cloud[0] = -200
                    cloud[1] = random.randint(50, int(HEIGHT * 0.7))
                
                if use_images and cloud_image:
                    screen.blit(cloud_image, (cloud[0], cloud[1]))
                else:
                    pygame.draw.ellipse(screen, CLOUD_COLOR, 
                                      (cloud[0], cloud[1], cloud[2], cloud[3]))
        
        # Vẽ các thành phần game
        if game.game_state not in [STATE_MENU, STATE_INSTRUCTIONS]:
            game.draw_sky_numbers(screen)
            
            for bullet in game.bullets:
                bullet.draw(screen)
                
            game.data_table.draw(screen)
            game.draw_ui(screen)
            
            if game.game_state == STATE_LEVEL_START:
                game.draw_level_start(screen)
            elif game.game_state == STATE_LEVEL_COMPLETE:
                game.draw_level_complete(screen)
            elif game.game_state == STATE_GAME_OVER:
                game.draw_game_over(screen)
            elif game.game_state == STATE_GAME_WIN:
                game.draw_game_win(screen)
        
        # Vẽ menu
        if game.game_state == STATE_MENU:
            menu.draw_main_menu(screen)
        elif game.game_state == STATE_INSTRUCTIONS:
            menu.draw_instructions(screen)
        
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()
    sys.exit()

def run_profiling_session(n_frames=60):
    """
    === BTVN03: hàm bổ sung riêng cho bài tập ===
    Chạy game ở chế độ headless trong n_frames frame để sinh dữ liệu
    profiling có kiểm soát, không cần người chơi tương tác bằng tay.
    Mô phỏng: khởi tạo Game -> chuyển sang PLAYING -> bắn vài viên đạn
    -> chạy update() lặp lại n_frames lần -> xuất CSV.
    """
    global PROFILING_ENABLED
    PROFILING_ENABLED = True

    game = Game()
    game.game_state = STATE_PLAYING

    # Bắn vài viên đạn để tạo ra các nhánh check_collision, explosion...
    for _ in range(5):
        game.shoot_bullet()

    # Gọi thử hàm đệ quy minh họa
    calculate_combo_bonus(5, game.level)

    # Chạy n_frames update() liên tiếp (không cần mở cửa sổ hiển thị thật)
    clock = pygame.time.Clock()
    for _ in range(n_frames):
        game.update()
        clock.tick(60)

    export_profiling_csv('profiling_data.csv')
    print(f"[Profiling] Tổng số lệnh gọi hàm đã ghi nhận: {len(call_records)}")
    depths = set(r['depth'] for r in call_records)
    print(f"[Profiling] Các mức depth xuất hiện: {sorted(depths)}")


if __name__ == "__main__":
    if "--profile" in sys.argv:
        run_profiling_session(n_frames=60)
    else:
        main()