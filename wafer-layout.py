import math
import numpy as np
import streamlit as st
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle, Circle, Wedge, Polygon

st.set_page_config(
    page_title="Wafer Layout Planner",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Wafer Layout Optimization Tool - Developed by Soud F Choudhury"
    }
)

# =============================================
# Input Parameters
# =============================================
with st.sidebar:
    st.header("Wafer Parameters")
    width = st.number_input("Die Width (mm)", min_value=0.1, value=50.0)
    height = st.number_input("Die Height (mm)", min_value=0.1, value=50.0)
    spacing = st.number_input("Scribe Width (mm)", min_value=0.1, value=0.1)
    edge_exclusion = st.number_input("Edge Exclusion (mm)", min_value=0.1, value=3.0)
    generate_btn = st.button("Generate Layouts")

# =============================================
# Core Algorithm
# =============================================
def generate_positions(dx, dy, width, height, spacing, effective_radius):
    """Generate valid die positions with precise boundary checks"""
    period_x = width + spacing/2
    period_y = height + spacing/2
    positions = []
    
    # Grid boundaries with conservative estimation
    max_x_offset = effective_radius - width/2
    max_y_offset = effective_radius - height/2
    
    i_min = math.ceil((-max_x_offset - dx) / period_x)
    i_max = math.floor((max_x_offset - dx) / period_x)
    j_min = math.ceil((-max_y_offset - dy) / period_y)
    j_max = math.floor((max_y_offset - dy) / period_y)

    # Bottom exclusion boundary
    exclusion_bottom = -150 + 7.5  # -142.5mm

    for i in range(i_min, i_max + 1):
        x = dx + i * period_x
        for j in range(j_min, j_max + 1):
            y = dy + j * period_y
            
            # Check bottom exclusion
            if (y - height/2) < exclusion_bottom:
                continue
                
            # Verify all four corners fit in effective area
            valid = True
            for sx in (-1, 1):
                for sy in (-1, 1):
                    cx = x + sx * width/2
                    cy = y + sy * height/2
                    if cx**2 + cy**2 > effective_radius**2:
                        valid = False
                        break
                if not valid:
                    break
                    
            if valid:
                positions.append((x, y))
                
    return positions

def is_symmetric(positions, tolerance=1e-6):
    """Check if positions are symmetric across both X and Y axes using set lookups."""
    pos_set = {(round(x, 6), round(y, 6)) for x, y in positions}  # Rounded to handle floating-point precision
    
    for x, y in pos_set:
        # Check Y-axis mirror
        if (-x, y) not in pos_set:
            return False
        # Check X-axis mirror
        if (x, -y) not in pos_set:
            return False
    return True

def calculate_balance(positions, effective_radius):
    """Calculate buffer symmetry score"""
    if not positions:
        return 0.0
    
    x_vals = [x for x, _ in positions]
    y_vals = [y for _, y in positions]
    
    max_x = max(x_vals, default=0)
    min_x = min(x_vals, default=0)
    max_y = max(y_vals, default=0)
    min_y = min(y_vals, default=0)
    
    h_diff = abs(max_x + min_x)
    v_diff = abs(max_y + min_y)
    
    return 1 - (h_diff + v_diff) / (2 * effective_radius)

def find_optimal_layouts(width, height, spacing, effective_radius):
    """Optimized layout search with symmetry handling"""
    best_max = {"count": 0, "positions": [], "balance": 0}
    best_sym = {"count": 0, "positions": [], "balance": 0}
    
    # Always check centered layout first
    centered = generate_positions(0, 0, width, height, spacing, effective_radius)
    centered_count = len(centered)
    if centered_count > 0:
        best_max = {
            "count": centered_count,
            "positions": centered,
            "balance": calculate_balance(centered, effective_radius)
        }
        #if is_symmetric(centered):
           # best_sym = best_max.copy()
    

    
    for dx in np.linspace(0, (spacing/2+width)/2, 10):
        #print("check:", dx)
        for dy in np.linspace(0, (spacing/2+height)/2, 10):
            for quadrant in [(dx, dy), (-dx, dy), (dx, -dy), (-dx, -dy)]:
                positions = generate_positions(quadrant[0], quadrant[1], 
                                              width, height, spacing, effective_radius)
                count = len(positions)
                #print("type-",count)
                if count > best_max["count"]:
                    best_max = {
                        "count": count,
                        "positions": positions,
                        "balance": calculate_balance(positions, effective_radius)
                    }
                

                if is_symmetric(positions):
                    #print("sym- ", count)
                    current_balance = calculate_balance(positions, effective_radius)
                    if count > best_sym["count"] or \
                      (count == best_sym["count"] and current_balance > best_sym["balance"]):
                        best_sym = {
                            "count": count,
                            "positions": positions,
                            "balance": current_balance
                        }
                       
    
    return best_max, best_sym, {
        "count": len(centered),
        "positions": centered,
        "balance": calculate_balance(centered, effective_radius)
    }

# =============================================
# Visualization
# =============================================
def create_wafer_plot(layout, title, width, height, effective_radius):
    """Generate a wafer plot with dies"""
    fig = Figure(figsize=(8, 8))
    ax = fig.add_subplot(111)
    
    # Wafer boundaries
    ax.add_patch(Circle((0, 0), 150, edgecolor='black', facecolor='none', linewidth=3))
    ax.add_patch(Circle((0, 0), effective_radius, edgecolor='red', linestyle='-', facecolor='none', linewidth=2, alpha=0.5))
    
    # Fill area between wafer edge and effective radius with Wedge
    if effective_radius < 150:
        wedge = Wedge(
            (0, 0), 150, 0, 360, width=150 - effective_radius,
            facecolor='red', alpha=0.3, edgecolor='none'
        )
        ax.add_patch(wedge)
    
    # Dies
    for x, y in layout["positions"]:
        ax.add_patch(Rectangle(
            (x - width/2, y - height/2), width, height,
            edgecolor='navy', facecolor='skyblue', alpha=0.7
        ))
    
    # Exclusion zones
    exclusion_bottom = -150 + 7.5  # -142.5mm
    
    # Calculate intersection points with wafer edge
    try:
        x_intersect = math.sqrt(150**2 - exclusion_bottom**2)
    except ValueError:
        x_intersect = 0  # Handle case where line is completely outside
    
    x_left = -x_intersect
    x_right = x_intersect
    
    # Plot clipped exclusion line
    ax.plot([x_left, x_right], [exclusion_bottom, exclusion_bottom], 
           color='red', linestyle='-', linewidth=1)
    
    # Fill area between clipped line and wafer edge with green Polygon
    if x_intersect > 0:
        exclusion_polygon = Polygon(
            [(x_left, exclusion_bottom), (x_right, exclusion_bottom), (0, -150)],
            closed=True, facecolor='red', alpha=0.3, edgecolor='none'
        )
        ax.add_patch(exclusion_polygon)
    
    # Formatting
    ax.set_title(f"{title}\n{layout['count']} Dies", fontsize=14, pad=15)
    ax.set_xlim(-160, 160)
    ax.set_ylim(-160, 160)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    return fig

# =============================================
# Main Application
# =============================================
if generate_btn:
    try:
        effective_radius = 150 - edge_exclusion
        if effective_radius <= 0:
            st.error("Edge exclusion exceeds wafer radius")
            st.stop()
            
        if (width/2)**2 + (height/2)**2 > effective_radius**2:
            st.error("Die too large for effective area")
            st.stop()

        # Calculate layouts
        max_layout, sym_layout, centered_layout = find_optimal_layouts(
            width, height, spacing, effective_radius
        )
        
        # Display results
        col1, col2, col3 = st.columns(3)
        with col1:
            st.pyplot(create_wafer_plot(max_layout, "Max Count", width, height, effective_radius))
        with col2:
            st.pyplot(create_wafer_plot(sym_layout, "Symmetric Optimized", width, height, effective_radius))
        with col3:
            st.pyplot(create_wafer_plot(centered_layout, "Centered", width, height, effective_radius))
            
        # Comparison table
        st.subheader("Layout Comparison")
        comparison_data = {
            "Layout": ["Max Count", "Symmetric", "Centered"],
            "Die Count": [max_layout["count"], sym_layout["count"], centered_layout["count"]],
            "Balance Score": [f"{max_layout['balance']:.1%}", 
                             f"{sym_layout['balance']:.1%}", 
                             f"{centered_layout['balance']:.1%}"]
        }
        st.dataframe(comparison_data, use_container_width=True, hide_index=True)
        
    except Exception as e:
        st.error(f"Error: {str(e)}")
