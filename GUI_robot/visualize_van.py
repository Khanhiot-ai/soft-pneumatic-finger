import matplotlib.pyplot as plt
import numpy as np
import matplotlib.colors as mcolors

# --- Dữ liệu từ bảng của bạn ---
pressures_kpa = [0, 25, 50, 75, 100]

# Tải trọng 100g
forces_100g = [1.0, 1.5, 2.0]
data_100g_raw = [
    ['Fail', 'Fail', 'Slip', 'Slip', 'Slip'],
    ['Fail', 'Fail', 0.915, 0.923, 0.961],
    ['Fail', 0.853, 0.863, 0.901, 0.909]
]

# Tải trọng 200g
forces_200g = [3.0, 3.5, 4.0]
data_200g_raw = [
    ['Fail', 'Fail', 'Slip', 'Slip', 'Slip'],
    ['Fail', 'Fail', 0.736, 0.740, 0.706],
    ['Fail', 0.689, 0.703, 0.710, 0.687]
]


# --- Hàm xử lý dữ liệu cho heatmap ---
def process_data_for_heatmap(data_raw):
    """
    Chuyển đổi dữ liệu thô sang mảng numpy, thay thế 'Fail'/'Slip' bằng NaN
    và lưu vị trí của Fail/Slip để vẽ overlay.
    """
    processed_data = np.full((len(data_raw), len(data_raw[0])), np.nan)
    fail_coords = []
    slip_coords = []

    for r_idx, row in enumerate(data_raw):
        for c_idx, val in enumerate(row):
            if isinstance(val, float):
                processed_data[r_idx, c_idx] = val
            elif val == 'Fail':
                fail_coords.append((c_idx, r_idx))
            elif val == 'Slip':
                slip_coords.append((c_idx, r_idx))
    return processed_data, fail_coords, slip_coords


data_100g_processed, fail_100g_coords, slip_100g_coords = process_data_for_heatmap(data_100g_raw)
data_200g_processed, fail_200g_coords, slip_200g_coords = process_data_for_heatmap(data_200g_raw)

# --- Thiết lập Figure và Subplots ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
plt.style.use('seaborn-v0_8-whitegrid')  # Sử dụng style để có lưới nền

# --- Xác định dải màu toàn cục cho "Tỷ lệ tròn" ---
all_success_ratios = []
for data in [data_100g_processed, data_200g_processed]:
    valid_data = data[~np.isnan(data)]
    if valid_data.size > 0:
        all_success_ratios.extend(valid_data.tolist())

global_min_ratio = min(all_success_ratios) if all_success_ratios else 0.6
global_max_ratio = max(all_success_ratios) if all_success_ratios else 1.0

# --- Tạo Colormap cho heatmap (chỉ cho các giá trị số) ---
# Chọn một colormap tốt cho độ dốc (ví dụ: YlGn, Viridis)
cmap_success = plt.cm.YlGn_r  # hoặc 'viridis'


# --- Hàm vẽ heatmap và overlay ---
def create_heatmap_plot(ax, data_processed, fail_coords, slip_coords, forces, pressures, title, cmap_success, vmin,
                        vmax):
    """Vẽ một heatmap với các overlay cho Fail/Slip."""
    # Vẽ heatmap cho các giá trị Tỷ lệ tròn
    im = ax.imshow(data_processed, cmap=cmap_success, vmin=vmin, vmax=vmax,
                   origin='lower', aspect='auto',
                   extent=[min(pressures) - 12.5, max(pressures) + 12.5, min(forces) - 0.25, max(forces) + 0.25])

    # Vẽ overlay cho Fail (Đỏ)
    for x, y in fail_coords:
        ax.add_patch(plt.Rectangle((pressures[x] - 12.5, forces[y] - 0.25), 25, 0.5,
                                   color='#d62728', edgecolor='white', linewidth=1, zorder=2))
        ax.text(pressures[x], forces[y], 'Fail', ha='center', va='center', color='white', fontsize=10,
                fontweight='bold', zorder=3)

    # Vẽ overlay cho Slip (Cam)
    for x, y in slip_coords:
        ax.add_patch(plt.Rectangle((pressures[x] - 12.5, forces[y] - 0.25), 25, 0.5,
                                   color='#ff7f0e', edgecolor='white', linewidth=1, zorder=2))
        ax.text(pressures[x], forces[y], 'Slip', ha='center', va='center', color='white', fontsize=10,
                fontweight='bold', zorder=3)

    # Thêm giá trị số cho các ô thành công
    for r_idx, row in enumerate(data_processed):
        for c_idx, val in enumerate(row):
            if not np.isnan(val):
                text_color = 'black' if val < (
                            vmin + vmax) / 2 else 'white'  # Tùy chỉnh màu chữ dựa vào độ sáng của màu nền
                ax.text(pressures[c_idx], forces[r_idx], f'{val:.3f}', ha='center', va='center', color=text_color,
                        fontsize=10, fontweight='bold', zorder=3)

    ax.set_title(title, fontsize=25, fontweight='bold',fontdict={'fontname': 'Times New Roman'})
    ax.set_xlabel('Pressure (P) [kPa]', fontsize=25, fontweight='bold',fontdict={'fontname':'Times New Roman'})
    ax.set_ylabel('Normal grasping force (Fₙ) [N]', fontsize=25,fontweight='bold',fontdict={'fontname': 'Times New Roman'})

    # Đặt lại các tick cho trục để căn giữa các ô
    ax.set_xticks(pressures)
    ax.set_yticks(forces)
    ax.set_xlim(min(pressures) - 12.5, max(pressures) + 12.5)
    ax.set_ylim(min(forces) - 0.25, max(forces) + 0.25)
    ax.tick_params(axis='both', which='major', labelsize=10)

    return im


# --- Vẽ từng subplot ---
im1 = create_heatmap_plot(ax1, data_100g_processed, fail_100g_coords, slip_100g_coords,
                          forces_100g, pressures_kpa, '(a) 100g Payload', cmap_success, global_min_ratio,
                          global_max_ratio)

im2 = create_heatmap_plot(ax2, data_200g_processed, fail_200g_coords, slip_200g_coords,
                          forces_200g, pressures_kpa, '(b) 200g Payload', cmap_success, global_min_ratio,
                          global_max_ratio)

# --- Tạo thanh màu chung ---
fig.subplots_adjust(right=0.85, wspace=0.35)
cbar_ax = fig.add_axes([0.88, 0.15, 0.02, 0.7])
cbar = fig.colorbar(im2, cax=cbar_ax)  # Sử dụng im2 để tạo colorbar chung
cbar.set_label('Roundness Ratio (Successful Grasps)', rotation=270, labelpad=20, fontsize=12)
cbar.ax.tick_params(labelsize=10)

# --- Tạo chú giải tùy chỉnh cho Fail/Slip ---
from matplotlib.patches import Patch

legend_elements = [
    Patch(facecolor='#d62728', edgecolor='black', label='Fail'),
    Patch(facecolor='#ff7f0e', edgecolor='black', label='Slip'),
    Patch(facecolor=cmap_success(0.8), edgecolor='black', label='Successful Grasp (High Ratio)'),  # Ví dụ màu xanh đậm
    Patch(facecolor=cmap_success(0.2), edgecolor='black', label='Successful Grasp (Low Ratio)')  # Ví dụ màu xanh nhạt
]
fig.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, 0.98), ncol=2, fontsize=11)

# --- Tiêu đề chung và Lưu file ---
fig.suptitle('Heatmap of Grasping Outcomes in Parameter Space', fontsize=16, fontweight='bold', y=1.05)
plt.savefig("heatmap_parameter_space.png", dpi=300, bbox_inches='tight')
plt.show()