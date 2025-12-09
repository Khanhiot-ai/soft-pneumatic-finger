import matplotlib.pyplot as plt
import numpy as np
import matplotlib.patches as mpatches
from matplotlib.colors import Normalize
import matplotlib.cm as cm

# --- Thiết lập font chữ "Times New Roman" ---
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman'] + plt.rcParams['font.serif']
plt.rcParams['mathtext.fontset'] = 'stix'

# --- Dữ liệu gốc ---
pressures_kpa = np.array([0, 25, 50, 75, 100])
forces_100g = np.array([1.0, 1.5, 2.0])
data_100g = [
    ['Fail', 'Fail', 'Slip', 'Slip', 'Slip'],
    ['Fail', 'Fail', 0.915, 0.923, 0.943],
    ['Fail', 0.823, 0.863, 0.901, 0.909]
]
forces_200g = np.array([3.0, 3.5, 4.0])
data_200g = [
    ['Fail', 'Fail', 'Slip', 'Slip', 'Slip'],
    ['Fail', 'Fail', 0.783, 0.774, 0.706],
    ['Fail', 0.674, 0.703, 0.710, 0.687]
]

# --- Định nghĩa màu sắc và Colormap cho dải giá trị ---
COLORS = {
    'Fail': '#d62728',  # Đỏ
    'Slip': '#ff7f0e',  # Cam
}
SUCCESS_CMAP = plt.get_cmap('viridis')
SUCCESS_NORM = Normalize(vmin=0.6, vmax=1.0)


# --- HÀM VẼ BIỂU ĐỒ (Giữ nguyên) ---
def create_discrete_heatmap(ax, data, forces, pressures, title):
    pressure_step = pressures[1] - pressures[0] if len(pressures) > 1 else 1
    force_step = forces[1] - forces[0] if len(forces) > 1 else 1
    for r, row_data in enumerate(data):
        for c, val in enumerate(row_data):
            force = forces[r]
            pressure = pressures[c]
            text_color = 'black'
            font_weight = 'normal'
            if val == 'Fail':
                face_color = COLORS['Fail']
                text_color = 'white'
                font_weight = 'bold'
            elif val == 'Slip':
                face_color = COLORS['Slip']
                text_color = 'white'
                font_weight = 'bold'
            else:
                face_color = SUCCESS_CMAP(SUCCESS_NORM(val))
                if SUCCESS_NORM(val) > 0.5:
                    text_color = 'black'
                else:
                    text_color = 'white'
                val = f'{val:.3f}'
            bottom_left_x = pressure - pressure_step / 2
            bottom_left_y = force - force_step / 2
            rect = mpatches.Rectangle(
                (bottom_left_x, bottom_left_y),
                pressure_step,
                force_step,
                facecolor=face_color,
                edgecolor='black',
                linewidth=1.0
            )
            ax.add_patch(rect)
            ax.text(pressure, force, val,
                    ha='center', va='center',
                    color=text_color, fontsize=10, fontweight=font_weight)
    ax.set_xlim(pressures[0] - pressure_step / 2, pressures[-1] + pressure_step / 2)
    ax.set_ylim(forces[0] - force_step / 2, forces[-1] + force_step / 2)
    ax.set_xticks(pressures)
    ax.set_yticks(forces)

    ax.set_aspect(50)

    ax.set_title(title, fontsize=16, fontweight='bold')
    ax.set_xlabel('Pressure (kPa)', fontsize=15,fontweight='bold')
    ax.set_ylabel(r'Normal grasping force (N)', fontsize=15,fontweight='bold')
    ax.tick_params(axis='both', which='major', labelsize=12)


# --- THAY ĐỔI 1: Điều chỉnh figsize để giảm khoảng trắng ---
fig, axes = plt.subplots(2, 1, figsize=(8, 7), constrained_layout=True)
ax1, ax2 = axes

# --- Vẽ 2 biểu đồ ---
create_discrete_heatmap(ax1, data_100g, forces_100g, pressures_kpa, '(a) 100g Payload')
create_discrete_heatmap(ax2, data_200g, forces_200g, pressures_kpa, '(b) 200g Payload')

# --- THAY ĐỔI 2: Xóa dòng code ẩn nhãn trục x ---
# ax1.set_xlabel('') # Đã xóa dòng này


# --- Sắp xếp Bố cục, Chú giải và Tiêu đề ---
legend_patches = [
    mpatches.Patch(color=COLORS['Fail'], label='Fail'),
    mpatches.Patch(color=COLORS['Slip'], label='Slip'),
]
fig.legend(handles=legend_patches, loc='outside upper center',
           ncol=2, fontsize=12, frameon=False)

sm = cm.ScalarMappable(cmap=SUCCESS_CMAP, norm=SUCCESS_NORM)
sm.set_array([])
cbar = fig.colorbar(sm, ax=axes.ravel().tolist(), orientation='vertical',
                    shrink=0.6, pad=0.1, aspect=25)
cbar.set_label('Roundness Ratio', rotation=270, labelpad=20, fontsize=14,fontweight='bold')
cbar.ax.tick_params(labelsize=12)

# --- Lưu và hiển thị ---
plt.savefig("heatmap_compact.jpg", dpi=300, bbox_inches='tight')
plt.show()