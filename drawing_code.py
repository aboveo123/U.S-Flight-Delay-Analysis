import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib
from collections import Counter

# Cấu hình matplotlib
matplotlib.rcParams['font.family'] = 'DejaVu Sans'
matplotlib.rcParams['font.size'] = 9

# ============================================================
# BƯỚC 1: Đọc dữ liệu profiling đầy đủ
# ============================================================
df_full = pd.read_csv('profiling_data.csv')

# ============================================================
# BƯỚC 2: Chọn 1 frame "Game.update" đại diện để vẽ
# ============================================================
game_updates = df_full[df_full['function_name'] == 'Game.update'].sort_values('start_time')

best_idx = None
best_count = -1
for idx, row in game_updates.iterrows():
    mask = (df_full['start_time'] >= row['start_time']) & \
           (df_full['end_time'] <= row['end_time']) & \
           (df_full.index != idx)
    count = mask.sum()
    if count > best_count:
        best_count = count
        best_idx = idx

root_row = df_full.loc[best_idx]
t_start = root_row['start_time']
t_end = root_row['end_time']
print(f"Đã chọn frame đại diện: start_time={t_start}, số lệnh gọi con={best_count}")

# Lấy toàn bộ các dòng (con) nằm trong khoảng thời gian của frame này
mask = (df_full['start_time'] >= t_start) & \
       (df_full['end_time'] <= t_end) & \
       (df_full.index != best_idx)
df_children = df_full[mask].copy()

# ============================================================
# BƯỚC 3: Chuẩn hóa thời gian về mốc 0, đổi sang milliseconds
# ============================================================
df_children['start_ms'] = (df_children['start_time'] - t_start) * 1000
df_children['end_ms'] = (df_children['end_time'] - t_start) * 1000
df_children['self_time_ms'] = df_children['self_time'] * 1000

# Loại bỏ outlier
duration_threshold = df_children['duration'].quantile(0.98)
df_children = df_children[df_children['duration'] <= duration_threshold].copy()

# Thêm root (Game.update) vào để vẽ depth = 0
root_record = {
    'function_name': 'Game.update',
    'depth': 0,
    'start_ms': 0.0,
    'end_ms': (t_end - t_start) * 1000,
    'self_time_ms': root_row['self_time'] * 1000
}
df_plot = pd.concat([
    pd.DataFrame([root_record]),
    df_children[['function_name', 'depth', 'start_ms', 'end_ms', 'self_time_ms']]
], ignore_index=True)

# ============================================================
# BƯỚC 4: Cấu hình màu theo từng hàm cụ thể (tên đầy đủ)
# ============================================================
function_colors = {
    'Game.update': '#7f1d1d',
    'NumberBubble.check_collision': '#fbbf24',
    'NumberBubble.update': '#60a5fa',
    'Bullet.update': '#34d399',
    'DataTable.update': '#a78bfa',
    'Cannon.update': '#f472b6',
}
default_color = '#999999'

# Tính min/max self_time riêng theo từng hàm
group_minmax = {}
for name in df_plot['function_name'].unique():
    vals = df_plot[df_plot['function_name'] == name]['self_time_ms']
    group_minmax[name] = (vals.min(), vals.max())

def get_alpha(row):
    mn, mx = group_minmax[row['function_name']]
    if mx == mn:
        return 1.0
    return 0.4 + 0.6 * (row['self_time_ms'] - mn) / (mx - mn)

# Độ rộng tối thiểu để vẽ
x_total = df_plot['end_ms'].max() - df_plot['start_ms'].min()
min_draw_width = x_total * 0.0015
label_threshold = x_total * 0.015  # block phải đủ rộng mới hiện chữ

# ============================================================
# BƯỚC 5: Hàm vẽ chung cho Flame Chart và Icicle Chart
# ============================================================
def plot_chart(df, mode, filename, title):
    fig, ax = plt.subplots(figsize=(20, 7))
    max_depth = int(df['depth'].max())
    hidden_labels = []
    
    for _, row in df.iterrows():
        depth = int(row['depth'])
        # Icicle: gốc TRÊN, con XUỐNG dưới | Flame: gốc DƯỚI, con LÊN trên
        y = depth if mode == 'icicle' else (max_depth - depth)
        
        x = row['start_ms']
        real_width = row['end_ms'] - row['start_ms']
        draw_width = max(real_width, min_draw_width)
        
        color = function_colors.get(row['function_name'], default_color)
        alpha = get_alpha(row)
        
        rect = patches.Rectangle((x, y), draw_width, 0.9,
                                  facecolor=color, alpha=alpha,
                                  edgecolor='black', linewidth=0.3)
        ax.add_patch(rect)
        
        # Chỉ hiện label ngắn nếu block đủ rộng
        label = row['function_name'].split('.')[-1]
        if real_width >= label_threshold:
            ax.text(x + draw_width / 2, y + 0.45, label,
                     ha='center', va='center', fontsize=7, clip_on=True)
        else:
            hidden_labels.append(row['function_name'])
    
    ax.set_xlim(df['start_ms'].min(), df['end_ms'].max())
    ax.set_ylim(-0.5, max_depth + 1.5)
    ax.set_xlabel("Thời gian (ms) — mốc 0 = lúc Game.update() bắt đầu", fontsize=10)
    ax.set_ylabel("Call depth", fontsize=10)
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.set_yticks(range(0, max_depth + 1))
    ax.set_yticklabels(
        range(0, max_depth + 1) if mode == 'icicle'
        else [max_depth - d for d in range(0, max_depth + 1)]
    )
    
    # Legend với TÊN ĐẦY ĐỦ của từng hàm
    legend_handles = [
        patches.Patch(facecolor=c, edgecolor='black', label=n, alpha=0.8)
        for n, c in function_colors.items() if n in df['function_name'].unique()
    ]
    ax.legend(handles=legend_handles, loc='upper right', fontsize=9,
              title='Hàm (Function Name)', title_fontsize=10,
              framealpha=0.95)
    
    plt.tight_layout()
    # LƯU ẢNH VÀO FILE
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"✓ Đã lưu: {filename}")
    plt.close()
    
    return hidden_labels

# ============================================================
# BƯỚC 6: Vẽ và lưu 2 file ảnh
# ============================================================
print("\n=== Đang vẽ biểu đồ ===")
hidden_flame = plot_chart(
    df_plot, mode='flame', filename='flame_chart.png',
    title='Flame Chart — Game.update() và các hàm con (1 frame đại diện)'
)

hidden_icicle = plot_chart(
    df_plot, mode='icicle', filename='icicle_chart.png',
    title='Icicle Chart — Game.update() và các hàm con (1 frame đại diện)'
)

# ============================================================
# BƯỚC 7: In thống kê
# ============================================================
print("\n=== Thống kê các hàm bị ẩn label ===")
print(Counter(hidden_flame))

print("\n=== Hoàn thành! ===")
print("Đã tạo 2 file: flame_chart.png và icicle_chart.png")