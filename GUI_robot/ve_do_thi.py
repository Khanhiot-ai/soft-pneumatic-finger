import matplotlib.pyplot as plt
import numpy as np
from pyqtgraph.examples.PColorMeshItem import edgecolors

# --- Dữ liệu giả lập cho các vật phẩm ---
# Vaseline Jar (Grasping Force = 1 N)
vaseline_pressures = np.array([0, 25, 50, 75, 100,125])
vaseline_success_rates = np.array([20, 80, 100, 100, 100, 100])

# Tomato (Grasping Force = 0.5 N)
tomato_pressures = np.array([0, 25, 50, 75, 100,125])
tomato_success_rates = np.array([0, 20, 90, 100, 100,100])

# Egg (Grasping Force = 1 N)
egg_pressures = np.array([0, 25, 50, 75, 100, 125])
egg_success_rates = np.array([0, 10, 40, 60, 85, 100])

# Water Bottle (Grasping Force = 2 N) - Vật dễ gắp hơn
water_bottle_pressures = np.array([0, 25, 50, 75, 100,125]) # Có thêm điểm ở 20, 40, 60, 80 kPa
water_bottle_success_rates = np.array([0, 0, 0, 30, 90,100]) # Tỷ lệ thành công cao hơn và đạt 100% sớm

# --- Chuẩn bị dữ liệu cho việc vẽ biểu đồ ---
all_pressures = np.unique(np.concatenate([
    vaseline_pressures,
    tomato_pressures,
    egg_pressures,
    water_bottle_pressures
]))
all_pressures = np.sort(all_pressures)

# --- BẮT ĐẦU VẼ BIỂU ĐỒ ---
fig, ax = plt.subplots(figsize=(11, 7)) # Tăng nhẹ kích thước biểu đồ cho cân đối

plt.style.use('seaborn-v0_8-whitegrid')
ax.grid(True, linestyle=':', alpha=0.7, color='lightgray')

# --- Vẽ từng đường cong ---
# Sử dụng marker và linestyle khác nhau cho từng đường để dễ phân biệt
ax.plot(vaseline_pressures, vaseline_success_rates, marker='o', linestyle='-', linewidth=5, markersize=12, label='Vaseline jar (1 N)', color='#1f77b4') # Blue
ax.plot(tomato_pressures, tomato_success_rates, marker='x', linestyle='-', linewidth=5, markersize=12, label='Tomato (0.5 N)', color='#ff7f0e') # Orange
ax.plot(egg_pressures, egg_success_rates, marker='s', linestyle='-', linewidth=5, markersize=12, label='Egg (1 N)', color='#2ca02c') # Green
ax.plot(water_bottle_pressures, water_bottle_success_rates, marker='^', linestyle='-', linewidth=5, markersize=12, label='Water bottle (1 N)', color='#d62728') # Red, new marker for distinctness


# --- Tinh chỉnh trục và nhãn ---
ax.set_xlabel('Pressure (kPa)', fontsize=25, fontweight='bold',fontdict={'fontname':'Times New Roman'})
ax.set_ylabel('Rate of Success (%)', fontsize=25, fontweight='bold',fontdict={'fontname':'Times New Roman'})

# Đặt giới hạn trục X ĐẾN 100 kPa
ax.set_xlim(0, 126)
ax.set_xticks(np.arange(0, 126, 25)) # Bước nhảy 10 kPa

# Đặt giới hạn trục Y
ax.set_ylim(-5, 105)
ax.set_yticks(np.arange(0, 101, 10))

ax.tick_params(axis='both', which='major', labelsize=10)
for label in (ax.get_xticklabels() + ax.get_yticklabels()):
    label.set_fontsize(25)  # Đặt cỡ chữ là 14 (bạn có thể thay đổi)
    label.set_fontweight('bold')
    label.set_fontname('Times New Roman')
# Thêm chú giải
# Điều chỉnh vị trí chú giải để nó không che khuất các đường và trông đẹp hơn
ax.legend(prop={'size': 15,'family': 'Times New Roman', 'weight': 'bold'},frameon=True, loc='lower right',edgecolor= 'black')
plt.tight_layout(rect=[0, 0, 1, 0.96])

# Cải thiện bố cục tổng thể
plt.tight_layout() # Tự động điều chỉnh các tham số subplot để phù hợp chặt chẽ vào hình

# Lưu biểu đồ
plt.savefig("grasping_success_rate_plot_with_water_bottle_1.jpg", dpi=300, bbox_inches='tight')
plt.show()

print("The grasping success rate plot with Water Bottle and improved layout has been saved as grasping_success_rate_plot_with_water_bottle.png")