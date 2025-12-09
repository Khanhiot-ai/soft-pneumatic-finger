import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import griddata
from matplotlib.colors import Normalize, LinearSegmentedColormap
import matplotlib.patches as mpatches
from matplotlib.cm import ScalarMappable

pressures_kpa_raw = np.array([0, 25, 50, 75, 100])
forces_100g_raw = np.array([1.0, 1.5, 2.0])
data_100g_raw = [
    ['Fail', 'Fail', 'Slip', 'Slip', 'Fail'],
    ['Fail', 'Fail', 0.915, 0.923, 0.943],
    ['Fail', 0.853, 0.863, 0.901, 0.909]
]
forces_200g_raw = np.array([3.0, 3.5, 4.0])
data_200g_raw = [
    ['Fail', 'Fail', 'Slip', 'Slip', 'Fail'],
    ['Fail', 'Fail', 0.736, 0.740, 0.706],
    ['Fail', 0.689, 0.703, 0.710, 0.687]
]

def prepare_data_for_seamless_plot(forces_raw, pressures_raw, data_raw):
    points, values = [], []
    for r_idx, force in enumerate(forces_raw):
        for c_idx, pressure in enumerate(pressures_raw):
            result = data_raw[r_idx][c_idx]
            points.append((pressure, force))
            if result == 'Fail':
                values.append(-1.0)
            elif result == 'Slip':
                values.append(0.0)
            else:
                values.append(float(result))
    return np.array(points), np.array(values)


points_100g, values_100g = prepare_data_for_seamless_plot(forces_100g_raw, pressures_kpa_raw, data_100g_raw)
points_200g, values_200g = prepare_data_for_seamless_plot(forces_200g_raw, pressures_kpa_raw, data_200g_raw)

grid_p, grid_f_100g = np.mgrid[0:100:200j, 1.0:2.0:200j]
grid_p, grid_f_200g = np.mgrid[0:100:200j, 3.0:4.0:200j]
interp_values_100g = griddata(points_100g, values_100g, (grid_p, grid_f_100g), method='cubic')
interp_values_200g = griddata(points_200g, values_200g, (grid_p, grid_f_200g), method='cubic')

norm_for_plotting = Normalize(vmin=-1.0, vmax=1.0)
cmap_list = [
    (norm_for_plotting(-1.0), "gray"),
    (norm_for_plotting(0.0), "gray"),
    (norm_for_plotting(0.0), "dodgerblue"),
    (norm_for_plotting(0.59), "dodgerblue"),
    (norm_for_plotting(0.6), "yellow"),
    (norm_for_plotting(1.0), "red")
]
custom_cmap_for_plotting = LinearSegmentedColormap.from_list("custom_cmap", cmap_list)


# --- Hàm vẽ biểu đồ với chuyển tiếp mượt mà ---
def create_seamless_contour_plot(ax, grid_p, grid_f, interp_values, title, cmap, norm, forces_raw):
    # Vẽ nền màu
    ax.contourf(grid_p, grid_f, interp_values, levels=100, cmap=cmap, norm=norm, extend='both')
    # Chỉ vẽ đường viền đen cho vùng Success (0.6 -> 1.0)
    ax.contour(grid_p, grid_f, interp_values, levels=np.linspace(0.6, 1.0, 12), colors='black', linewidths=0.7)

    # Đặt tiêu đề và các nhãn trục
    ax.set_title(title, fontsize=35, fontweight='bold', fontdict={'fontname': 'Times New Roman'}, pad=20)
    ax.set_xlabel('Pressure (kPa)', fontsize=35, fontweight='bold', fontdict={'fontname': 'Times New Roman'})
    ax.set_ylabel('Normal grasping force (N)', fontsize=35, fontweight='bold', fontdict={'fontname': 'Times New Roman'})
    ax.set_xticks(pressures_kpa_raw)
    ax.set_yticks(forces_raw)
    ax.set_xlim(min(pressures_kpa_raw), max(pressures_kpa_raw))
    for label in (ax.get_xticklabels() + ax.get_yticklabels()):
        label.set_fontsize(25)
        label.set_fontweight('bold')
        label.set_fontname('Times New Roman')


fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 9), constrained_layout=True)


ax1.set_ylim(min(forces_100g_raw), max(forces_100g_raw))
create_seamless_contour_plot(ax1, grid_p, grid_f_100g, interp_values_100g, '(a) 100g Payload', custom_cmap_for_plotting,
                             norm_for_plotting, forces_100g_raw)

ax2.set_ylim(min(forces_200g_raw), max(forces_200g_raw))
create_seamless_contour_plot(ax2, grid_p, grid_f_200g, interp_values_200g, '(b) 200g Payload', custom_cmap_for_plotting,
                             norm_for_plotting, forces_200g_raw)

fail_patch = mpatches.Patch(color='gray', label='Fail')
slip_patch = mpatches.Patch(color='dodgerblue', label='Slip')
ax1.legend(handles=[fail_patch, slip_patch], loc='upper left',
           prop={'family': 'Times New Roman', 'size': 25, 'weight': 'bold'})

success_cmap = LinearSegmentedColormap.from_list("success_cmap", ["yellow", "red"])
success_norm = Normalize(vmin=0.6, vmax=1.0)
mappable = ScalarMappable(norm=success_norm, cmap=success_cmap)

cbar = fig.colorbar(mappable, ax=[ax1, ax2], pad=0.02, ticks=[0.6, 0.8, 1.0])
cbar.ax.set_yticklabels(['0.6', '0.8', '1.0'], fontweight='bold', fontdict={'fontname': 'Times New Roman'})
cbar.set_label('Roundness ratio', rotation=270, labelpad=25, fontsize=35, fontweight='bold',
               fontfamily='Times New Roman')
cbar.ax.tick_params(labelsize=25)
plt.savefig("final_plot.pdf", dpi=300, bbox_inches='tight')
plt.show()