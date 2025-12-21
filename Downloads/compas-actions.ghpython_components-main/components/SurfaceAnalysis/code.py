import Rhino.Geometry as rg
import System.Drawing as sd
import math

def create_hex_grid(surface, u_count, v_count):
    print("Function called with U={}, V={}".format(u_count, v_count))
    if not surface:
        print("Surface object is invalid or None inside function")
        return [], [], []

    u_domain = surface.Domain(0)
    v_domain = surface.Domain(1)
    
    hexagons = []
    curvatures = []
    colors = []
    
    # Simple UV mapping strategy
    u_step = (u_domain.Max - u_domain.Min) / u_count
    v_step = (v_domain.Max - v_domain.Min) / v_count
    
    max_k = 0.01 
    min_k = -0.01

    for i in range(u_count):
        for j in range(v_count):
            # Center of the "cell" in UV
            u = u_domain.Min + (i + 0.5) * u_step
            v = v_domain.Min + (j + 0.5) * v_step
            
            # Offset every other row
            if j % 2 == 1:
                u += u_step * 0.5
            
            # Boundary check
            if u > u_domain.Max: 
                continue

            # Evaluate
            try:
                pt = surface.PointAt(u, v)
                curvature = surface.CurvatureAt(u, v)
                
                # Gaussian Curvature
                if curvature:
                    k = curvature.Gaussian
                else:
                    k = 0.0
                curvatures.append(k)
                
                # Color mapping
                t = (k - min_k) / (max_k - min_k)
                t = max(0.0, min(1.0, t))
                r = int(255 * t)
                b = int(255 * (1 - t))
                colors.append(sd.Color.FromArgb(r, 0, b))

                # Hexagon geometry
                radius = min(u_step, v_step) * 0.5
                hex_corners = []
                for angle_deg in range(0, 360, 60):
                    angle = math.radians(angle_deg)
                    du = math.cos(angle) * radius
                    dv = math.sin(angle) * radius
                    
                    u_local = u + du
                    v_local = v + dv
                    
                    u_local = max(u_domain.Min, min(u_domain.Max, u_local))
                    v_local = max(v_domain.Min, min(v_domain.Max, v_local))

                    corner_pt = surface.PointAt(u_local, v_local)
                    hex_corners.append(corner_pt)
                
                hex_corners.append(hex_corners[0])
                hexagons.append(rg.PolylineCurve(hex_corners))
            except Exception as e:
                print("Error at grid {},{}: {}".format(i, j, e))
                continue

    print("Generated {} hexagons".format(len(hexagons)))
    return hexagons, curvatures, colors

# --- Main Execution ---
print("--- Script Start ---")

# 1. Fetch Inputs
_surface = globals().get("Surface")
_u = globals().get("U_Count")
_v = globals().get("V_Count")

print("Input Type Surface: {}".format(type(_surface)))
print("Input Value U: {}".format(_u))
print("Input Value V: {}".format(_v))

# 2. Validate and Execute
if _surface and _u is not None and _v is not None:
    try:
        u_cnt = int(_u)
        v_cnt = int(_v)
        
        # Check if surface is actually a Rhino Geometry or needs conversion
        # (Sometimes TypeHint wraps it)
        if hasattr(_surface, "Value"):
            _surface = _surface.Value
            
        Hexagons, Curvature, Colors = create_hex_grid(_surface, u_cnt, v_cnt)
    except Exception as e:
        print("Execution Error: {}".format(e))
        Hexagons = []
        Curvature = []
        Colors = []
else:
    print("Missing Inputs. Please connect Surface, U, and V.")
    Hexagons = []
    Curvature = []
    Colors = []