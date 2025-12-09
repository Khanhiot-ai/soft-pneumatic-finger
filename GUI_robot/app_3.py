import matplotlib.pyplot as plt
import numpy as np

# --- BƯỚC 1: CUNG CẤP DỮ LIỆU "INITIAL OPENING" CỦA BẠN VÀO ĐÂY ---

# Mức áp suất (trục X)
pressure_levels = [0, 25, 50, 75, 100]

# ==============================================================================
# ====================== DỮ LIỆU CHO VẬT 200g ===================================
# ==============================================================================
# Lực kẹp: 3N, 3.5N, 4N
# Đơn vị: mm
opening_200g_3N = [65.0, 65.5, 66.0, 66.8, 67.5]  # <--- THAY THẾ DỮ LIỆU CỦA BẠN
opening_200g_3_5N = [64.0, 64.5, 65.0, 65.8, 66.5]  # <--- THAY THẾ DỮ LIỆU CỦA BẠN
opening_200g_4N = [63.0, 63.5, 64.0, 64.8, 65.5]  # <--- THAY THẾ DỮ LIỆU CỦA BẠN

# ==============================================================================
# ====================== DỮ LIỆU CHO VẬT 500g ===================================
# ==============================================================================
# Lực kẹp: 8N, 8.5N, 9N
# Đơn vị: mm
opening_500g_8N = [68.0, 68.5, 69.0, 69.8, 70.5]  # <--- THAY THẾ DỮ LIỆU CỦA BẠN
opening_500g_8_5N = [67.0, 67.5, 68.0, 68.8, 69.5]  # <--- THAY THẾ DỮ LIỆU CỦA BẠN
opening_500g_9N = [66.0, 66.5, 67.0, 67.8, 68.5]  # <--- THAY THẾ DỮ LIỆU CỦA BẠN

# --- BƯỚC 2: CODE VẼ ĐỒ THỊ (Giữ nguyên định dạng) ---

# Thiết lập figure và các subplot (1 hàng, 2 cột)
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7), sharey=True)  # sharey=True để 2 trục Y có cùng thang đo
plt.style.use('seaborn-v0_8-whitegrid')

# --- Đồ thị 1: VẬT 200g (trục bên trái, ax1) ---
ax1.plot(pressure_levels, opening_200g_3N, marker='o', linestyle='-', label='Clamping force = 1N', linewidth=3,
         markersize=10)
ax1.plot(pressure_levels, opening_200g_3_5N, marker='s', linestyle='-', label='Clamping force = 1.5N', linewidth=3,
         markersize=10)
ax1.plot(pressure_levels, opening_200g_4N, marker='^', linestyle='-', label='Clamping force = 2N', linewidth=3,
         markersize=10)

# Tùy chỉnh Đồ thị 1
ax1.set_xlabel("Pressure (P) [kPa]", fontsize=25, fontweight='bold', fontdict={'fontname': 'Times New Roman'})
ax1.set_ylabel("Closing distance (mm)", fontsize=25, fontweight='bold', fontdict={'fontname': 'Times New Roman'})
ax1.set_title("(a) 100g Payload", fontsize=25, fontweight='bold', fontdict={'fontname': 'Times New Roman'})

ax1.legend(prop={'family': 'Times New Roman', 'size': 15, 'weight': 'bold'}, frameon=True, edgecolor='black',
           loc='upper left')
for label in (ax1.get_xticklabels() + ax1.get_yticklabels()):
    label.set_fontsize(25)
    label.set_fontweight('bold')
    label.set_fontname('Times New Roman')

# --- Đồ thị 2: VẬT 500g (trục bên phải, ax2) ---
ax2.plot(pressure_levels, opening_500g_8N, marker='o', linestyle='-', label='Clamping force = 3N', linewidth=3,
         markersize=10)
ax2.plot(pressure_levels, opening_500g_8_5N, marker='s', linestyle='-', label='Clamping force = 3.5N', linewidth=3,
         markersize=10)
ax2.plot(pressure_levels, opening_500g_9N, marker='^', linestyle='-', label='Clamping force = 4N', linewidth=3,
         markersize=10)

# Tùy chỉnh Đồ thị 2
ax2.set_xlabel("Pressure (P) [kPa]", fontsize=25, fontweight='bold', fontdict={'fontname': 'Times New Roman'})
# ax2.set_ylabel("Initial Opening (mm)", fontsize=25, fontweight='bold', fontdict={'fontname':'Times New Roman'}) # Không cần vì đã sharey
ax2.set_title("(b) 200g Payload", fontsize=25, fontweight='bold', fontdict={'fontname': 'Times New Roman'})

ax2.legend(prop={'family': 'Times New Roman', 'size': 15, 'weight': 'bold'}, edgecolor='black', loc='upper left',
           frameon=True)
for label in (ax2.get_xticklabels() + ax2.get_yticklabels()):
    label.set_fontsize(25)
    label.set_fontweight('bold')
    label.set_fontname('Times New Roman')

# --- TÙY CHỈNH CHUNG CHO CẢ 2 ĐỒ THỊ ---
# Bạn có thể điều chỉnh giới hạn và bước nhảy cho phù hợp với dải dữ liệu của mình
for ax in [ax1, ax2]:
    ax.set_xlim(0, 101)
    # ax.set_ylim(62, 72) # Bỏ comment và điều chỉnh nếu cần
    ax.set_xticks(np.arange(0, 101, 25))
    # ax.set_yticks(np.arange(62, 73, 2)) # Bỏ comment và điều chỉnh nếu cần
    ax.grid(True, which='both', linestyle='--', linewidth=0.7)

# --- TIÊU ĐỀ CHUNG VÀ LƯU FILE ---
plt.tight_layout(rect=[0, 0, 1, 0.95])  # rect để tạo không gian cho suptitle

# Lưu file ảnh
output_filename = "initial_opening_plot.png"
plt.savefig(output_filename, dpi=300, bbox_inches='tight')

print(f"Đồ thị đã được lưu vào file: {output_filename}")
plt.show()