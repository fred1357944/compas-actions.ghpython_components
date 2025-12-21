
import Rhino.Geometry as rg
import System.Drawing as sd
import math

def create_hex_grid(surface, u_count, v_count):
    if not surface:
        return [], [], []

    u_domain = surface.Domain(0)
    v_domain = surface.Domain(1)
    
    hexagons = []
    curvatures = []
    colors = []
    
    # Simple UV mapping strategy for hexagonal staggering
    # Normalized step sizes
    u_step = (u_domain.Max - u_domain.Min) / u_count
    v_step = (v_domain.Max - v_domain.Min) / v_count
    
    # Max curvature for normalization (dynamic would be better, but fixed for prototype)
    max_k = 0.01 
    min_k = -0.01

    for i in range(u_count):
        for j in range(v_count):
            # Center of the "cell" in UV
            u = u_domain.Min + (i + 0.5) * u_step
            v = v_domain.Min + (j + 0.5) * v_step
            
            # Offset every other row for hex effect
            if j % 2 == 1:
                u += u_step * 0.5
            
            if u > u_domain.Max: continue

            # Evaluate surface properties
            pt = surface.PointAt(u, v)
            curvature = surface.CurvatureAt(u, v)
            
            # Get Gaussian Curvature
            k = curvature.Gaussian
            curvatures.append(k)
            
            # Map curvature to color (Blue=Low, Red=High)
            t = (k - min_k) / (max_k - min_k)
            t = max(0.0, min(1.0, t))
            r = int(255 * t)
            b = int(255 * (1 - t))
            colors.append(sd.Color.FromArgb(r, 0, b))

            # Create a simple hexagon approximation around the center point
            # In a real tool, this would be more complex topological handling
            radius = min(u_step, v_step) * 0.5 # Approximation in parameter space
            
            hex_corners = []
            for angle_deg in range(0, 360, 60):
                angle = math.radians(angle_deg)
                # Offset in UV space (naive mapping)
                du = math.cos(angle) * radius
                dv = math.sin(angle) * radius
                
                # Map back to 3D
                u_local = u + du
                v_local = v + dv
                
                # Clamp to domain to avoid errors
                u_local = max(u_domain.Min, min(u_domain.Max, u_local))
                v_local = max(v_domain.Min, min(v_domain.Max, v_local))

                corner_pt = surface.PointAt(u_local, v_local)
                hex_corners.append(corner_pt)
            
            # Close the loop
            hex_corners.append(hex_corners[0])
            hexagons.append(rg.PolylineCurve(hex_corners))

    return hexagons, curvatures, colors

# Main execution
# Safely get inputs from globals to avoid NameError
_surface = globals().get("Surface")
_u_count = globals().get("U_Count")
_v_count = globals().get("V_Count")

if _surface and _u_count and _v_count:
    # Need to handle the input being a wrapper or direct geometry depending on GH context
    # In SDK mode, inputs are direct objects usually
    
    # Fix: Ensure U_Count and V_Count are integers
    u_cnt = int(_u_count)
    v_cnt = int(_v_count)
    
    # Call logic
    # Note: In the provided componentizer, the code runs inside the component's SolveInstance or similar scope
    # Accessing inputs directly as global variables
    
    Hexagons, Curvature, Colors = create_hex_grid(_surface, u_cnt, v_cnt)

else:
    Hexagons = []
    Curvature = []
    Colors = []
