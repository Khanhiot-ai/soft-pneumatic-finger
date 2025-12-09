import matplotlib.pyplot as plt
import numpy as np
from setuptools.command.rotate import rotate

# --- EXPERIMENTAL DATA ---

# Pressure levels are the same for both experiments
pressure_levels = [0, 25, 50, 75, 100, 125]

# ==============================================================================
# ====================== DATA FOR 200g OBJECT ==================================
# ==============================================================================
# Clamping forces: 3N, 3.5N, 4N
success_rate_200g_3N = [0, 0, 0, 30, 75, 100]    # <--- REPLACE WITH YOUR DATA
success_rate_200g_3_5N = [0, 0, 20, 50, 90, 100] # <--- REPLACE WITH YOUR DATA
success_rate_200g_4N = [0, 0, 35, 80, 100, 100]    # <--- REPLACE WITH YOUR DATA

# ==============================================================================
# ====================== DATA FOR 500g OBJECT ==================================
# ==============================================================================
# Clamping forces: 8N, 8.5N, 9N
success_rate_500g_8N = [0, 0, 0, 20, 65, 100]     # <--- REPLACE WITH YOUR DATA
success_rate_500g_8_5N = [0, 0, 15, 45, 80, 100]  # <--- REPLACE WITH YOUR DATA
success_rate_500g_9N = [0, 10, 50, 90, 100, 100]     # <--- REPLACE WITH YOUR DATA

# --- PLOTTING ---

# Set up the figure and a grid of subplots (1 row, 2 columns)
# figsize=(16, 7) creates a wider figure to fit both plots comfortably
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 14    ))
plt.style.use('seaborn-v0_8-whitegrid')

# --- PLOT 1: 200g OBJECT (on the left axis, ax1) ---
ax1.plot(pressure_levels, success_rate_200g_3N, marker='o', linestyle='-', label='Grasping force = 3N',linewidth=5, markersize=12)
ax1.plot(pressure_levels, success_rate_200g_3_5N, marker='s', linestyle='-', label='Grasping force = 3.5N',linewidth=5, markersize=12)
ax1.plot(pressure_levels, success_rate_200g_4N, marker='^', linestyle='-', label='Grasping force = 4N',linewidth=5, markersize=12)

# Customize Plot 1
ax1.set_xlabel("Pressure (kPa)", fontsize=30, fontweight='bold', fontdict={'fontname':'Times New Roman'})
ax1.set_ylabel("Rate of success  (%)", fontsize=30, fontweight='bold', fontdict={'fontname':'Times New Roman'})
ax1.set_title("(a) Grasping a 200g object", fontsize=30, fontweight='bold', fontdict={'fontname':'Times New Roman'})
ax1.set_xlim(0, 125)
ax1.set_ylim(0, 105)
ax1.set_xticks(np.arange(0, 126, 25))
ax1.set_yticks(np.arange(0, 101, 20))
ax1.legend(prop={'family': 'Times New Roman', 'size': 17, 'weight': 'bold'},frameon=True,edgecolor='black',loc='upper left',ncol=1)
for label in (ax1.get_xticklabels() + ax1.get_yticklabels()):
    label.set_fontsize(25)  # Đặt cỡ chữ là 14 (bạn có thể thay đổi)
    label.set_fontweight('bold')
    label.set_fontname('Times New Roman')

# --- PLOT 2: 500g OBJECT (on the right axis, ax2) ---
ax2.plot(pressure_levels, success_rate_500g_8N, marker='o', linestyle='-', label='Grasping force = 8N',linewidth=5, markersize=12)
ax2.plot(pressure_levels, success_rate_500g_8_5N, marker='s', linestyle='-', label='Grasping force = 8.5N',linewidth=5, markersize=12)
ax2.plot(pressure_levels, success_rate_500g_9N, marker='^', linestyle='-', label='Grasping force = 9N',linewidth=5, markersize=12)

# Customize Plot 2
ax2.set_xlabel("Pressure (kPa)", fontsize=30, fontweight='bold',fontdict={'fontname':'Times New Roman'})
ax2.set_ylabel("Rate of success (%)", fontsize=30, fontweight='bold',fontdict={'fontname':'Times New Roman'})
ax2.set_title("(b) Grasping a 500g object", fontsize=30, fontweight='bold', fontdict={'fontname':'Times New Roman'})
ax2.set_xlim(0, 125)
ax2.set_ylim(0, 105)
ax2.set_xticks(np.arange(0, 126, 25))
ax2.set_yticks(np.arange(0, 101, 20))
ax2.legend(prop={'family': 'Times New Roman', 'size': 17, 'weight': 'bold'},edgecolor='black',loc='upper left',frameon=True,ncol=1)
for label in (ax2.get_xticklabels() + ax2.get_yticklabels()):
    label.set_fontsize(25)  # Đặt cỡ chữ là 14 (bạn có thể thay đổi)
    label.set_fontweight('bold')
    label.set_fontname('Times New Roman')

# --- OVERALL FIGURE CUSTOMIZATION ---

# Add a main title for the entire figure

# Adjust layout to prevent titles and labels from overlapping
plt.tight_layout(rect=[0, 0, 1, 1]) # rect is used to make space for suptitle

# --- SAVING THE FIGURE ---
output_filename = "comparison_plot_200g_vs_500g.jpg"
plt.savefig(output_filename, dpi=300)

print(f"Combined plot successfully saved to file: {output_filename}")