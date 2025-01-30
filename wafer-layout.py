import math
import numpy as np
import streamlit as st
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle, Circle



st.set_page_config(
    page_title="Wafer Layout Planner App",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "App to configure the wafer layout to get an optimized die numbers - Developed by Soud F Choudhury"
    }
)

# Input widgets in sidebar
with st.sidebar:
    st.header("Layout Parameters")
    width = st.number_input("Width (mm):", min_value=0.1, value=5.0)
    height = st.number_input("Height (mm):", min_value=0.1, value=5.0)
    spacing = st.number_input("Scribe Width (mm):", min_value=0.1, value=0.1)
    edge_exclusion = st.number_input("Edge Exclusion (mm):", min_value=0.1, value=3.0)
    generate_btn = st.button("Generate Layout")

def generate_positions(dx, dy, width, height, spacing, effective_radius):
    """Generate positions with buffer analysis"""
    period_x = width + spacing
    period_y = height + spacing
    positions = []
    
    # Calculate grid bounds
    i_min = math.ceil((-effective_radius + width/2 - dx) / period_x)
    i_max = math.floor((effective_radius - width/2 - dx) / period_x)
    j_min = math.ceil((-effective_radius + height/2 - dy) / period_y)
    j_max = math.floor((effective_radius - height/2 - dy) / period_y)

    x_coords, y_coords = [], []
    
    for i in range(i_min, i_max + 1):
        x = dx + i * period_x
        for j in range(j_min, j_max + 1):
            y = dy + j * period_y
            if (abs(x) + width/2)**2 + (abs(y) + height/2)**2 <= effective_radius**2:
                positions.append((x, y))
                x_coords.append(x)
                y_coords.append(y)
    
    # Calculate buffer distances
    buffers = {
        'left': effective_radius - (max(x_coords) + width/2) if x_coords else 0,
        'right': effective_radius - (abs(min(x_coords) - width/2)) if x_coords else 0,
        'top': effective_radius - (max(y_coords) + height/2) if y_coords else 0,
        'bottom': effective_radius - (abs(min(y_coords) - height/2)) if y_coords else 0,
    }
    return positions, buffers

def calculate_optimal_offset(width, height, spacing, effective_radius, step_size=1):
    """Find optimal grid offset ensuring no row has a single die"""
    period_x = width + spacing
    period_y = height + spacing
    best_score = -np.inf
    best_config = {}

    for dx in np.linspace(0, period_x, num=int(period_x/step_size)+1):
        for dy in np.linspace(0, period_y, num=int(period_y/step_size)+1):
            positions, buffers = generate_positions(dx, dy, width, height, spacing, effective_radius)
            if not positions:
                continue

            # Group dies by row (same y-coordinates)
            row_counts = {}
            for x, y in positions:
                row_counts.setdefault(y, []).append(x)

            # Ensure no row has a single die
            if any(len(x_values) == 1 for x_values in row_counts.values()):
                continue  # Skip configurations with 1-die rows

            count = len(positions)
            buffer_values = list(buffers.values())
            balance_score = 1 - (max(buffer_values) - min(buffer_values)) / effective_radius
            total_score = count * (1 + balance_score**2)

            if total_score > best_score:
                best_score = total_score
                best_config = {
                    'dx': dx,
                    'dy': dy,
                    'positions': positions,
                    'buffers': buffers,
                    'count': count
                }

    return best_config



if generate_btn:
    try:
        effective_radius = 150 - edge_exclusion * 1.10
        if effective_radius <= 0:
            st.error("Edge exclusion exceeds wafer radius")
            st.stop()

        if (width/2)**2 + (height/2)**2 > effective_radius**2:
            st.error("Rectangle too large for effective area")
            st.stop()

        # Calculate configurations
        optimized = calculate_optimal_offset(width, height, spacing, effective_radius)
        centered_pos, _ = generate_positions(0, 0, width, height, spacing, effective_radius)

        # Create figure with 3 subplots
        fig = Figure(figsize=(120, 80), dpi=200)
        ax1 = fig.add_subplot(131)
        ax2 = fig.add_subplot(132)

        # Styling parameters
        plot_params = {
            'edgecolor': 'black',
            'facecolor': 'lightblue',
            'linewidth': 5,
            'alpha': 0.9
        }

        wafer_style = {
            'edgecolor': 'Black',
            'facecolor': 'none',
            'linewidth': 10,
            'linestyle': '-'
        }

        edge_exclusion_style = {
            'edgecolor': 'darkgreen',
            'facecolor': 'none',
            'linewidth': 3,
            'linestyle': '--'
        }

        # Common plot settings
        for ax in (ax1, ax2):
            ax.set_aspect('equal')
            ax.add_patch(Circle((0, 0), 150, **wafer_style))
            ax.add_patch(Circle((0, 0), effective_radius, **edge_exclusion_style))
            ax.set_xlim(-160, 160)
            ax.set_ylim(-160, 160)
            ax.grid(True, color='gray', alpha=0.3)
            ax.tick_params(axis='both', labelsize=50)
            ax.set_facecolor('grey')

        # Plot optimized grid (avoiding single-die rows)
        ax1.set_title(f"Optimized Layout: {optimized['count']} Modules\n", fontsize=100)
        for x, y in optimized['positions']:
            ax1.add_patch(Rectangle((x - width/2, y - height/2), width, height, **plot_params))

        # Plot centered grid
        ax2.set_title(f"Centered Layout: {len(centered_pos)} Modules\n", fontsize=100)
        for x, y in centered_pos:
            ax2.add_patch(Rectangle((x - width/2, y - height/2), width, height, **plot_params))

        

        st.pyplot(fig)

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
