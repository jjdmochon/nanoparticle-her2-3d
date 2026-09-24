#!/usr/bin/env python3
"""
3D Model Generator: 400 nm Polystyrene Nanoparticles Loaded with Cy5 & Conjugated with Anti-HER2 Nanobodies
Binding to a Mammalian Breast Cancer Cell Overexpressing HER2.

Generates:
1. Wavefront OBJ + MTL (nanoparticle_her2_complex.obj / .mtl)
2. Binary glTF 2.0 (nanoparticle_her2_complex.glb)
"""

import os
import sys
import math
import json
import struct
import random

# Output directory
OUTPUT_DIR = r"C:\Users\Juanjo\.gemini\antigravity\scratch\nanoparticle-her2-3d"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Coordinate scale: 1.0 unit = 1.0 nanometre (nm)
# Core nanoparticle diameter: 400 nm -> Radius R = 200 nm
# Centered at (0, 215, 0) nm, so bottom pole is at Y = 15 nm
# Cell membrane outer leaflet at Y = 0 nm
# Binding gap: ~15 nm (spanned by 6 nm PEG linker + 4.5 nm VHH + 11 nm HER2 ECD overlap)

NP_RADIUS = 200.0  # nm
NP_CENTER = (0.0, 215.0, 0.0)
CELL_MEMBRANE_Y = 0.0
MEMBRANE_SIZE = 700.0  # 700 nm x 700 nm patch

random.seed(42)  # Deterministic generation

class MeshBuilder:
    def __init__(self):
        self.vertices = []     # [(x, y, z), ...]
        self.normals = []      # [(nx, ny, nz), ...]
        self.colors = []       # [(r, g, b, a), ...]
        self.groups = {}       # name -> list of triangle tuples: [((v0,n0), (v1,n1), (v2,n2)), ...]
        self.current_group = "default"

    def set_group(self, name):
        self.current_group = name
        if name not in self.groups:
            self.groups[name] = []

    def add_vertex(self, x, y, z, nx=0.0, ny=1.0, nz=0.0, r=0.8, g=0.8, b=0.8, a=1.0):
        idx = len(self.vertices)
        self.vertices.append((x, y, z))
        self.normals.append((nx, ny, nz))
        self.colors.append((r, g, b, a))
        return idx

    def add_triangle(self, v0, v1, v2):
        self.groups[self.current_group].append((v0, v1, v2))

    def add_quad(self, v0, v1, v2, v3):
        self.add_triangle(v0, v1, v2)
        self.add_triangle(v0, v2, v3)

    def add_sphere(self, cx, cy, cz, radius, lat_segs=16, lon_segs=24, color=(0.9, 0.9, 0.9, 1.0),
                   cutaway=False, cut_angle_min=0, cut_angle_max=math.pi/2):
        """Adds a sphere or a sphere with a quadrant cutaway."""
        start_idx = len(self.vertices)
        # Generate grid of vertices
        for i in range(lat_segs + 1):
            theta = i * math.pi / lat_segs  # 0 to pi
            sin_t = math.sin(theta)
            cos_t = math.cos(theta)
            for j in range(lon_segs + 1):
                phi = j * 2.0 * math.pi / lon_segs  # 0 to 2pi
                
                # Check if cutaway
                if cutaway and (cut_angle_min <= phi <= cut_angle_max) and (0 < i < lat_segs):
                    # In cutaway zone, push to center or mark
                    pass
                
                nx = sin_t * math.cos(phi)
                ny = cos_t
                nz = sin_t * math.sin(phi)
                
                x = cx + radius * nx
                y = cy + radius * ny
                z = cz + radius * nz
                self.add_vertex(x, y, z, nx, ny, nz, *color)

        # Generate triangles
        stride = lon_segs + 1
        for i in range(lat_segs):
            for j in range(lon_segs):
                phi = j * 2.0 * math.pi / lon_segs
                if cutaway and (cut_angle_min <= phi < cut_angle_max):
                    continue
                v0 = start_idx + i * stride + j
                v1 = start_idx + (i + 1) * stride + j
                v2 = start_idx + (i + 1) * stride + (j + 1)
                v3 = start_idx + i * stride + (j + 1)
                self.add_quad(v0, v1, v2, v3)

    def add_cylinder(self, p1, p2, radius, segs=12, color=(0.8, 0.8, 0.8, 1.0)):
        """Adds a cylinder between two 3D points."""
        x1, y1, z1 = p1
        x2, y2, z2 = p2
        dx, dy, dz = x2 - x1, y2 - y1, z2 - z1
        length = math.sqrt(dx*dx + dy*dy + dz*dz)
        if length < 1e-6:
            return
        ux, uy, uz = dx / length, dy / length, dz / length

        # Arbitrary perpendicular vector
        if abs(ux) < 0.9:
            px, py, pz = 1.0, 0.0, 0.0
        else:
            px, py, pz = 0.0, 1.0, 0.0
        # Gram-Schmidt
        dot = px*ux + py*uy + pz*uz
        vx, vy, vz = px - dot*ux, py - dot*uy, pz - dot*uz
        vlen = math.sqrt(vx*vx + vy*vy + vz*vz)
        vx, vy, vz = vx/vlen, vy/vlen, vz/vlen
        # Cross product for third axis
        wx = uy*vz - uz*vy
        wy = uz*vx - ux*vz
        wz = ux*vy - uy*vx

        start_idx = len(self.vertices)
        for i in range(segs):
            angle = i * 2.0 * math.pi / segs
            ca, sa = math.cos(angle), math.sin(angle)
            rx = radius * (ca * vx + sa * wx)
            ry = radius * (ca * vy + sa * wy)
            rz = radius * (ca * vz + sa * wz)
            
            # Bottom vertex
            self.add_vertex(x1 + rx, y1 + ry, z1 + rz, ca*vx + sa*wx, ca*vy + sa*wy, ca*vz + sa*wz, *color)
            # Top vertex
            self.add_vertex(x2 + rx, y2 + ry, z2 + rz, ca*vx + sa*wx, ca*vy + sa*wy, ca*vz + sa*wz, *color)

        for i in range(segs):
            ni = (i + 1) % segs
            b0 = start_idx + 2 * i
            t0 = start_idx + 2 * i + 1
            b1 = start_idx + 2 * ni
            t1 = start_idx + 2 * ni + 1
            self.add_quad(b0, t0, t1, b1)

    def add_ellipsoid(self, cx, cy, cz, rx, ry, rz, orient=(0, 1, 0), segs=12, color=(1.0, 0.8, 0.2, 1.0)):
        """Adds an oriented ellipsoid."""
        start_idx = len(self.vertices)
        lat_segs = segs
        lon_segs = segs * 2
        for i in range(lat_segs + 1):
            theta = i * math.pi / lat_segs
            sin_t, cos_t = math.sin(theta), math.cos(theta)
            for j in range(lon_segs + 1):
                phi = j * 2.0 * math.pi / lon_segs
                sin_p, cos_p = math.sin(phi), math.cos(phi)

                lx = rx * sin_t * cos_p
                ly = ry * cos_t
                lz = rz * sin_t * sin_p

                # Normal (normalized ellipsoid gradient)
                enx = lx / (rx*rx)
                eny = ly / (ry*ry)
                enz = lz / (rz*rz)
                enlen = math.sqrt(enx*enx + eny*eny + enz*enz) + 1e-8
                nx, ny, nz = enx/enlen, eny/enlen, enz/enlen

                self.add_vertex(cx + lx, cy + ly, cz + lz, nx, ny, nz, *color)

        stride = lon_segs + 1
        for i in range(lat_segs):
            for j in range(lon_segs):
                v0 = start_idx + i * stride + j
                v1 = start_idx + (i + 1) * stride + j
                v2 = start_idx + (i + 1) * stride + (j + 1)
                v3 = start_idx + i * stride + (j + 1)
                self.add_quad(v0, v1, v2, v3)

def generate_full_scene():
    builder = MeshBuilder()

    # ==========================================
    # 1. POLYSTYRENE CORE WITH CUTAWAY
    # ==========================================
    # We create the 400 nm nanosphere (R = 200 nm) centered at (0, 215, 0)
    # A 90-degree quadrant (x > 0, z > 0) is cut away to expose the Cy5 internal matrix
    builder.set_group("Polystyrene_Core_Cutaway")
    ps_color = (0.85, 0.88, 0.92, 0.85)  # Slightly translucent pearlescent polymer
    builder.add_sphere(NP_CENTER[0], NP_CENTER[1], NP_CENTER[2],
                       NP_RADIUS, lat_segs=32, lon_segs=48, color=ps_color,
                       cutaway=True, cut_angle_min=0.0, cut_angle_max=math.pi / 2.0)

    # Cutaway interior cross-section walls (slice planes at phi = 0 and phi = pi/2)
    builder.set_group("Polystyrene_Cutaway_Walls")
    cut_wall_color = (0.75, 0.80, 0.85, 1.0)
    # Plane 1: phi = 0 (z = 0, x > 0)
    cx, cy, cz = NP_CENTER
    wall1_start = len(builder.vertices)
    segs = 24
    for i in range(segs + 1):
        theta = i * math.pi / segs
        r_edge = NP_RADIUS
        px = cx + r_edge * math.sin(theta)
        py = cy + r_edge * math.cos(theta)
        pz = cz
        builder.add_vertex(cx, cy, cz, 0.0, 0.0, -1.0, *cut_wall_color)
        builder.add_vertex(px, py, pz, 0.0, 0.0, -1.0, *cut_wall_color)
    for i in range(segs):
        v0 = wall1_start + 2 * i
        v1 = wall1_start + 2 * i + 1
        v2 = wall1_start + 2 * (i + 1) + 1
        builder.add_triangle(v0, v1, v2)

    # Plane 2: phi = pi/2 (x = 0, z > 0)
    wall2_start = len(builder.vertices)
    for i in range(segs + 1):
        theta = i * math.pi / segs
        r_edge = NP_RADIUS
        px = cx
        py = cy + r_edge * math.cos(theta)
        pz = cz + r_edge * math.sin(theta)
        builder.add_vertex(cx, cy, cz, 1.0, 0.0, 0.0, *cut_wall_color)
        builder.add_vertex(px, py, pz, 1.0, 0.0, 0.0, *cut_wall_color)
    for i in range(segs):
        v0 = wall2_start + 2 * i
        v1 = wall2_start + 2 * i + 1
        v2 = wall2_start + 2 * (i + 1) + 1
        builder.add_triangle(v0, v2, v1)

    # ==========================================
    # 2. INTERNAL Cy5 FLUOROPHORE MATRIX
    # ==========================================
    # Inside the 400 nm bead (r: 15 to 185 nm from center).
    # Cyanine-5: deep red / far-red emission (670 nm), bright fluorescent glow.
    builder.set_group("Cy5_Fluorophore_Matrix")
    cy5_color = (1.0, 0.05, 0.28, 1.0)     # Vibrant Cy5 crimson
    cy5_glow_color = (1.0, 0.2, 0.45, 0.9) # Fluorophore glow

    num_cy5 = 380
    for _ in range(num_cy5):
        # Sample spherical coordinates inside radius 180 nm
        u = random.random()
        r = 180.0 * (u ** (1.0 / 3.0))
        costheta = 2.0 * random.random() - 1.0
        sintheta = math.sqrt(max(0.0, 1.0 - costheta * costheta))
        phi = 2.0 * math.pi * random.random()

        fx = cx + r * sintheta * math.cos(phi)
        fy = cy + r * costheta
        fz = cz + r * sintheta * math.sin(phi)

        # Planar chromophore representation: small conjugated ring disk/triplet
        mol_rad = 2.4  # nm (small molecule dye scale)
        builder.add_sphere(fx, fy, fz, mol_rad, lat_segs=6, lon_segs=8, color=cy5_color)

    # Internal core fluorescence cloud (concentric glowing shell)
    builder.set_group("Cy5_Internal_Luminescence")
    builder.add_sphere(cx, cy, cz, 120.0, lat_segs=16, lon_segs=24, color=(0.95, 0.0, 0.25, 0.25))

    # ==========================================
    # 3. PEG LINKER CORONA & 4. ANTI-HER2 NANOBODIES (VHH)
    # ==========================================
    # Distributed over sphere surface using spherical Fibonacci lattice
    builder.set_group("PEG_Linkers")
    peg_color = (0.7, 0.85, 0.95, 0.8)  # Hydrophilic polymer stalk
    vhh_color = (0.95, 0.65, 0.12, 1.0)  # Amber-gold immunoglobulin nanobody
    cdr_color = (1.0, 0.35, 0.05, 1.0)  # Hypervariable CDR binding loop (orange-red)

    num_tethers = 140
    golden_ratio = (1.0 + math.sqrt(5.0)) / 2.0

    nanobody_positions = []  # save for HER2 docking

    for i in range(num_tethers):
        # Fibonacci point on unit sphere
        lat = math.asin(-1.0 + 2.0 * float(i) / float(num_tethers))
        lon = 2.0 * math.pi * float(i) / golden_ratio

        nx = math.cos(lat) * math.cos(lon)
        ny = math.sin(lat)
        nz = math.cos(lat) * math.sin(lon)

        # Skip linkers in the cutaway quadrant (x > 0 and z > 0 and ny > -0.2)
        # to keep the cutaway view unobstructed and clean
        if nx > 0.05 and nz > 0.05 and ny > -0.2:
            continue

        # PEG stalk extends from R = 200 nm to R = 208 nm
        p_surf = (cx + NP_RADIUS * nx, cy + NP_RADIUS * ny, cz + NP_RADIUS * nz)
        peg_len = 8.0  # nm
        p_peg_tip = (cx + (NP_RADIUS + peg_len) * nx,
                     cy + (NP_RADIUS + peg_len) * ny,
                     cz + (NP_RADIUS + peg_len) * nz)

        # Coiled / undulating PEG chain (3 segments)
        p_mid1 = (cx + (NP_RADIUS + 2.5) * nx + 1.2 * nz,
                  cy + (NP_RADIUS + 2.5) * ny + 0.8,
                  cz + (NP_RADIUS + 2.5) * nz - 1.2 * nx)
        p_mid2 = (cx + (NP_RADIUS + 5.5) * nx - 1.2 * nz,
                  cy + (NP_RADIUS + 5.5) * ny - 0.8,
                  cz + (NP_RADIUS + 5.5) * nz + 1.2 * nx)

        builder.set_group("PEG_Linkers")
        builder.add_cylinder(p_surf, p_mid1, 0.6, segs=6, color=peg_color)
        builder.add_cylinder(p_mid1, p_mid2, 0.6, segs=6, color=peg_color)
        builder.add_cylinder(p_mid2, p_peg_tip, 0.6, segs=6, color=peg_color)

        # Anti-HER2 Nanobody (VHH) single domain antibody
        # Dimensions ~2.5 nm x 3.0 nm x 4.5 nm
        builder.set_group("Anti_HER2_Nanobodies")
        vhh_center = (cx + (NP_RADIUS + peg_len + 2.2) * nx,
                      cy + (NP_RADIUS + peg_len + 2.2) * ny,
                      cz + (NP_RADIUS + peg_len + 2.2) * nz)

        # If near bottom pole (ny < -0.85), direct orientation downward toward cell membrane
        is_synaptic = (ny < -0.82)
        if is_synaptic:
            nanobody_positions.append(vhh_center)

        # VHH core immunoglobulin beta-barrel
        builder.add_ellipsoid(vhh_center[0], vhh_center[1], vhh_center[2],
                              1.6, 2.3, 1.6, color=vhh_color, segs=8)

        # CDR loop projection (pointing outward along normal or downward towards membrane)
        cdr_tip = (vhh_center[0] + 2.6 * nx,
                   vhh_center[1] + (2.6 * ny if not is_synaptic else -2.6),
                   vhh_center[2] + 2.6 * nz)
        builder.set_group("Anti_HER2_CDR_Loops")
        builder.add_sphere(cdr_tip[0], cdr_tip[1], cdr_tip[2], 1.1, lat_segs=6, lon_segs=8, color=cdr_color)

    # ==========================================
    # 5. CANCER CELL MEMBRANE (LIPID BILAYER PATCH)
    # ==========================================
    builder.set_group("Cancer_Cell_Membrane")
    mem_color_outer = (0.15, 0.55, 0.75, 0.95)  # Cyan-teal phospholipid headgroups
    mem_color_inner = (0.10, 0.40, 0.60, 0.95)
    mem_color_core = (0.25, 0.70, 0.85, 0.6)   # Fluid hydrophobic tail region

    grid_n = 36
    step = MEMBRANE_SIZE / grid_n
    half_size = MEMBRANE_SIZE / 2.0

    # Undulating membrane height function (fluid membrane wave mechanics)
    def mem_height(x, z):
        return 3.5 * math.sin(0.015 * x) * math.cos(0.015 * z) + 1.8 * math.sin(0.03 * x + 0.5)

    mem_start_idx = len(builder.vertices)
    for i in range(grid_n + 1):
        x = -half_size + i * step
        for j in range(grid_n + 1):
            z = -half_size + j * step
            y_base = mem_height(x, z)
            
            # Normal calculation via numerical derivative
            eps = 1.0
            dhdx = (mem_height(x + eps, z) - mem_height(x - eps, z)) / (2.0 * eps)
            dhdz = (mem_height(x, z + eps) - mem_height(x, z - eps)) / (2.0 * eps)
            nx, ny, nz = -dhdx, 1.0, -dhdz
            nlen = math.sqrt(nx*nx + ny*ny + nz*nz)
            nx, ny, nz = nx/nlen, ny/nlen, nz/nlen

            # Outer leaflet headgroup surface (Y = y_base)
            builder.add_vertex(x, y_base, z, nx, ny, nz, *mem_color_outer)

    stride = grid_n + 1
    for i in range(grid_n):
        for j in range(grid_n):
            v0 = mem_start_idx + i * stride + j
            v1 = mem_start_idx + (i + 1) * stride + j
            v2 = mem_start_idx + (i + 1) * stride + (j + 1)
            v3 = mem_start_idx + i * stride + (j + 1)
            builder.add_quad(v0, v1, v2, v3)

    # Lower leaflet / membrane depth layer
    mem_inner_start = len(builder.vertices)
    for i in range(grid_n + 1):
        x = -half_size + i * step
        for j in range(grid_n + 1):
            z = -half_size + j * step
            y_inner = mem_height(x, z) - 4.5  # 4.5 nm bilayer thickness
            builder.add_vertex(x, y_inner, z, 0.0, -1.0, 0.0, *mem_color_inner)

    for i in range(grid_n):
        for j in range(grid_n):
            v0 = mem_inner_start + i * stride + j
            v1 = mem_inner_start + (i + 1) * stride + j
            v2 = mem_inner_start + (i + 1) * stride + (j + 1)
            v3 = mem_inner_start + i * stride + (j + 1)
            builder.add_quad(v0, v3, v2, v1)

    # ==========================================
    # 6. HER2 RECEPTORS (OVEREXPRESSION + ACTIVE SYNAPSE DOCKING)
    # ==========================================
    # High-density distribution on cancer cell membrane
    her2_color_d4 = (0.2, 0.7, 0.4, 1.0)   # Domain IV (juxtamembrane rod)
    her2_color_d3 = (0.1, 0.8, 0.5, 1.0)   # Domain III (globular L2)
    her2_color_d2 = (0.05, 0.9, 0.55, 1.0) # Domain II (dimerization arm)
    her2_color_d1 = (0.25, 0.95, 0.65, 1.0)# Domain I (N-terminal L1)

    # Synaptic docked HER2 receptors (directly underneath nanobodies)
    builder.set_group("HER2_Bound_Complexes")
    synaptic_her2_locs = [
        (-12.0, -10.0),
        (14.0, -8.0),
        (-6.0, 16.0),
        (10.0, 12.0)
    ]

    for hx, hz in synaptic_her2_locs:
        hy = mem_height(hx, hz)
        # Receptor stalks rooted at membrane, extending up 12 nm to engage nanobody CDR loop at Y = 10-12 nm
        p_base = (hx, hy, hz)
        p_d4 = (hx, hy + 3.0, hz)
        p_d3 = (hx + 0.8, hy + 6.0, hz - 0.5)
        p_d2 = (hx - 0.8, hy + 9.0, hz + 0.5)
        p_d1 = (hx, hy + 11.5, hz)

        builder.add_cylinder(p_base, p_d4, 1.1, segs=8, color=her2_color_d4)
        builder.add_ellipsoid(p_d3[0], p_d3[1], p_d3[2], 1.8, 1.8, 1.8, color=her2_color_d3, segs=8)
        builder.add_cylinder(p_d3, p_d2, 1.0, segs=8, color=her2_color_d2)
        builder.add_ellipsoid(p_d1[0], p_d1[1], p_d1[2], 1.9, 2.0, 1.8, color=her2_color_d1, segs=8)

        # Molecular interaction bridge / avidity contact zone (hydrogen bond / salt bridge cluster)
        builder.set_group("Avidity_Binding_Vectors")
        contact_color = (1.0, 0.9, 0.2, 0.9)  # Glowing interaction contact
        builder.add_cylinder(p_d1, (hx, hy + 13.5, hz), 0.5, segs=6, color=contact_color)

    # Non-docked overexpressed HER2 receptors across the surrounding membrane patch
    builder.set_group("HER2_Overexpressed_Receptors")
    num_surrounding_her2 = 42
    for _ in range(num_surrounding_her2):
        # Disperse across membrane
        dist = random.uniform(40.0, 310.0)
        ang = random.uniform(0, 2.0 * math.pi)
        hx = dist * math.cos(ang)
        hz = dist * math.sin(ang)
        hy = mem_height(hx, hz)

        p_base = (hx, hy, hz)
        p_d4 = (hx, hy + 2.8, hz)
        p_d3 = (hx + random.uniform(-0.5, 0.5), hy + 5.6, hz + random.uniform(-0.5, 0.5))
        p_d2 = (p_d3[0] + random.uniform(-0.8, 0.8), hy + 8.5, p_d3[2] + random.uniform(-0.8, 0.8))
        p_d1 = (p_d2[0], hy + 11.0, p_d2[2])

        builder.add_cylinder(p_base, p_d4, 1.0, segs=6, color=her2_color_d4)
        builder.add_ellipsoid(p_d3[0], p_d3[1], p_d3[2], 1.6, 1.6, 1.6, color=her2_color_d3, segs=6)
        builder.add_cylinder(p_d3, p_d2, 0.9, segs=6, color=her2_color_d2)
        builder.add_ellipsoid(p_d1[0], p_d1[1], p_d1[2], 1.7, 1.8, 1.6, color=her2_color_d1, segs=6)

    # ==========================================
    # 7. SCALE BAR & ANNOTATION ANCHORS
    # ==========================================
    builder.set_group("Nanoscale_400nm_Scale_Bar")
    scale_bar_color = (0.9, 0.9, 0.9, 1.0)
    # Horizontal 400 nm reference bar positioned to the left of the nanoparticle
    sb_y = NP_CENTER[1]
    sb_z = -230.0
    sb_x_start = -200.0
    sb_x_end = 200.0  # Exactly 400 nm long
    builder.add_cylinder((sb_x_start, sb_y, sb_z), (sb_x_end, sb_y, sb_z), 2.2, segs=8, color=scale_bar_color)
    # End tick caps
    builder.add_cylinder((sb_x_start, sb_y - 12.0, sb_z), (sb_x_start, sb_y + 12.0, sb_z), 1.8, segs=8, color=scale_bar_color)
    builder.add_cylinder((sb_x_end, sb_y - 12.0, sb_z), (sb_x_end, sb_y + 12.0, sb_z), 1.8, segs=8, color=scale_bar_color)

    return builder

def export_obj(builder, filepath_obj, filepath_mtl):
    """Exports geometry to Wavefront OBJ and MTL files."""
    mtl_filename = os.path.basename(filepath_mtl)
    
    # Material definitions
    materials = {
        "Polystyrene_Core_Cutaway": {"Kd": "0.85 0.88 0.92", "d": "0.85", "Ns": "60", "Ka": "0.2 0.2 0.2"},
        "Polystyrene_Cutaway_Walls": {"Kd": "0.75 0.80 0.85", "d": "1.0", "Ns": "30", "Ka": "0.2 0.2 0.2"},
        "Cy5_Fluorophore_Matrix": {"Kd": "1.00 0.05 0.28", "Ke": "0.85 0.02 0.22", "d": "1.0", "Ns": "90"},
        "Cy5_Internal_Luminescence": {"Kd": "0.95 0.00 0.25", "Ke": "0.60 0.00 0.15", "d": "0.35", "Ns": "10"},
        "PEG_Linkers": {"Kd": "0.70 0.85 0.95", "d": "0.85", "Ns": "40"},
        "Anti_HER2_Nanobodies": {"Kd": "0.95 0.65 0.12", "d": "1.0", "Ns": "75", "Ka": "0.2 0.15 0.05"},
        "Anti_HER2_CDR_Loops": {"Kd": "1.00 0.35 0.05", "d": "1.0", "Ns": "80"},
        "Cancer_Cell_Membrane": {"Kd": "0.15 0.55 0.75", "d": "0.95", "Ns": "35"},
        "HER2_Bound_Complexes": {"Kd": "0.10 0.85 0.45", "Ke": "0.05 0.35 0.15", "d": "1.0", "Ns": "80"},
        "HER2_Overexpressed_Receptors": {"Kd": "0.15 0.75 0.40", "d": "1.0", "Ns": "60"},
        "Avidity_Binding_Vectors": {"Kd": "1.00 0.90 0.20", "Ke": "0.80 0.70 0.10", "d": "0.9", "Ns": "100"},
        "Nanoscale_400nm_Scale_Bar": {"Kd": "0.95 0.95 0.95", "d": "1.0", "Ns": "100"}
    }

    # Write MTL
    with open(filepath_mtl, "w", encoding="utf-8") as f:
        f.write("# Material Library for 400 nm Nanoparticle - HER2 Complex\n")
        f.write("# DestiNA Genomics & Biophysical Modeling Standard\n\n")
        for mat_name, props in materials.items():
            f.write(f"newmtl {mat_name}\n")
            f.write(f"  illum 2\n")
            for k, v in props.items():
                f.write(f"  {k} {v}\n")
            f.write("\n")

    # Write OBJ
    with open(filepath_obj, "w", encoding="utf-8") as f:
        f.write("# 400 nm Polystyrene Nanoparticle Conjugated with Anti-HER2 Nanobody & Loaded with Cy5\n")
        f.write(f"mtllib {mtl_filename}\n\n")

        # Vertices
        for v in builder.vertices:
            f.write(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n")

        # Normals
        for n in builder.normals:
            f.write(f"vn {n[0]:.4f} {n[1]:.4f} {n[2]:.4f}\n")

        # Groups & Faces
        for grp_name, triangles in builder.groups.items():
            if not triangles:
                continue
            f.write(f"\ng {grp_name}\n")
            f.write(f"usemtl {grp_name}\n")
            for t in triangles:
                # 1-indexed in OBJ format
                v0, v1, v2 = t[0] + 1, t[1] + 1, t[2] + 1
                f.write(f"f {v0}//{v0} {v1}//{v1} {v2}//{v2}\n")

    print(f"Exported OBJ: {filepath_obj} ({len(builder.vertices)} vertices, {sum(len(g) for g in builder.groups.values())} triangles)")
    print(f"Exported MTL: {filepath_mtl}")

def export_glb(builder, filepath_glb):
    """Exports geometry to standard binary glTF 2.0 (.glb) with PBR materials."""
    # We pack all vertex positions (FLOAT vec3), normals (FLOAT vec3), and colors (FLOAT vec4)
    # into unified binary buffers, and index buffers (UINT32) for each mesh primitive.

    material_defs = [
        {"name": "Polystyrene_Core_Cutaway", "color": [0.85, 0.88, 0.92, 0.85], "roughness": 0.4, "metallic": 0.05},
        {"name": "Polystyrene_Cutaway_Walls", "color": [0.75, 0.80, 0.85, 1.0], "roughness": 0.6, "metallic": 0.05},
        {"name": "Cy5_Fluorophore_Matrix", "color": [1.0, 0.05, 0.28, 1.0], "roughness": 0.2, "metallic": 0.1, "emissive": [0.95, 0.02, 0.22]},
        {"name": "Cy5_Internal_Luminescence", "color": [0.95, 0.0, 0.25, 0.35], "roughness": 0.9, "metallic": 0.0, "emissive": [0.8, 0.0, 0.2]},
        {"name": "PEG_Linkers", "color": [0.7, 0.85, 0.95, 0.8], "roughness": 0.5, "metallic": 0.1},
        {"name": "Anti_HER2_Nanobodies", "color": [0.95, 0.65, 0.12, 1.0], "roughness": 0.3, "metallic": 0.15},
        {"name": "Anti_HER2_CDR_Loops", "color": [1.0, 0.35, 0.05, 1.0], "roughness": 0.3, "metallic": 0.1},
        {"name": "Cancer_Cell_Membrane", "color": [0.15, 0.55, 0.75, 0.95], "roughness": 0.6, "metallic": 0.05},
        {"name": "HER2_Bound_Complexes", "color": [0.10, 0.85, 0.45, 1.0], "roughness": 0.3, "metallic": 0.15, "emissive": [0.05, 0.4, 0.15]},
        {"name": "HER2_Overexpressed_Receptors", "color": [0.15, 0.75, 0.40, 1.0], "roughness": 0.4, "metallic": 0.1},
        {"name": "Avidity_Binding_Vectors", "color": [1.0, 0.9, 0.2, 0.9], "roughness": 0.2, "metallic": 0.1, "emissive": [0.8, 0.7, 0.1]},
        {"name": "Nanoscale_400nm_Scale_Bar", "color": [0.95, 0.95, 0.95, 1.0], "roughness": 0.2, "metallic": 0.8}
    ]

    mat_map = {m["name"]: idx for idx, m in enumerate(material_defs)}

    # Construct binary buffers
    bin_data = bytearray()
    buffer_views = []
    accessors = []
    meshes = []
    nodes = []

    # 1. Vertex Positions (VEC3 FLOAT)
    pos_bytes = bytearray()
    min_pos = [float('inf')]*3
    max_pos = [float('-inf')]*3
    for v in builder.vertices:
        pos_bytes.extend(struct.pack('<fff', v[0], v[1], v[2]))
        for k in range(3):
            if v[k] < min_pos[k]: min_pos[k] = v[k]
            if v[k] > max_pos[k]: max_pos[k] = v[k]

    pos_bv_idx = len(buffer_views)
    pos_offset = len(bin_data)
    bin_data.extend(pos_bytes)
    # Pad to 4 bytes
    while len(bin_data) % 4 != 0:
        bin_data.append(0)
    buffer_views.append({
        "buffer": 0,
        "byteOffset": pos_offset,
        "byteLength": len(pos_bytes),
        "target": 34962  # ARRAY_BUFFER
    })

    pos_acc_idx = len(accessors)
    accessors.append({
        "bufferView": pos_bv_idx,
        "byteOffset": 0,
        "componentType": 5126,  # FLOAT
        "count": len(builder.vertices),
        "type": "VEC3",
        "min": min_pos,
        "max": max_pos
    })

    # 2. Vertex Normals (VEC3 FLOAT)
    norm_bytes = bytearray()
    for n in builder.normals:
        norm_bytes.extend(struct.pack('<fff', n[0], n[1], n[2]))

    norm_bv_idx = len(buffer_views)
    norm_offset = len(bin_data)
    bin_data.extend(norm_bytes)
    while len(bin_data) % 4 != 0:
        bin_data.append(0)
    buffer_views.append({
        "buffer": 0,
        "byteOffset": norm_offset,
        "byteLength": len(norm_bytes),
        "target": 34962
    })

    norm_acc_idx = len(accessors)
    accessors.append({
        "bufferView": norm_bv_idx,
        "byteOffset": 0,
        "componentType": 5126,
        "count": len(builder.normals),
        "type": "VEC3"
    })

    # 3. For each group, create index buffer and mesh primitive
    mesh_idx = 0
    for grp_name, triangles in builder.groups.items():
        if not triangles:
            continue
        idx_bytes = bytearray()
        for t in triangles:
            idx_bytes.extend(struct.pack('<III', t[0], t[1], t[2]))

        idx_bv_idx = len(buffer_views)
        idx_offset = len(bin_data)
        bin_data.extend(idx_bytes)
        while len(bin_data) % 4 != 0:
            bin_data.append(0)

        buffer_views.append({
            "buffer": 0,
            "byteOffset": idx_offset,
            "byteLength": len(idx_bytes),
            "target": 34963  # ELEMENT_ARRAY_BUFFER
        })

        idx_acc_idx = len(accessors)
        accessors.append({
            "bufferView": idx_bv_idx,
            "byteOffset": 0,
            "componentType": 5125,  # UNSIGNED_INT
            "count": len(triangles) * 3,
            "type": "SCALAR"
        })

        mat_idx = mat_map.get(grp_name, 0)
        meshes.append({
            "name": grp_name,
            "primitives": [{
                "attributes": {
                    "POSITION": pos_acc_idx,
                    "NORMAL": norm_acc_idx
                },
                "indices": idx_acc_idx,
                "material": mat_idx
            }]
        })

        nodes.append({
            "name": grp_name,
            "mesh": mesh_idx
        })
        mesh_idx += 1

    # glTF JSON structure
    gltf_materials = []
    for m in material_defs:
        mat_entry = {
            "name": m["name"],
            "pbrMetallicRoughness": {
                "baseColorFactor": m["color"],
                "metallicFactor": m["metallic"],
                "roughnessFactor": m["roughness"]
            },
            "doubleSided": True
        }
        if "emissive" in m:
            mat_entry["emissiveFactor"] = m["emissive"]
        if m["color"][3] < 1.0:
            mat_entry["alphaMode"] = "BLEND"
        gltf_materials.append(mat_entry)

    gltf_dict = {
        "asset": {
            "version": "2.0",
            "generator": "Antigravity DestiNA 3D Nanoparticle Engine"
        },
        "scene": 0,
        "scenes": [{
            "nodes": list(range(len(nodes)))
        }],
        "nodes": nodes,
        "meshes": meshes,
        "materials": gltf_materials,
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{
            "byteLength": len(bin_data)
        }]
    }

    json_str = json.dumps(gltf_dict, separators=(',', ':'))
    json_bytes = json_str.encode('utf-8')
    # Pad JSON to 4-byte alignment with spaces (0x20)
    json_pad = (4 - (len(json_bytes) % 4)) % 4
    json_bytes += b' ' * json_pad

    # BIN padding to 4-byte alignment with 0x00
    bin_pad = (4 - (len(bin_data) % 4)) % 4
    bin_data += b'\x00' * bin_pad

    total_length = 12 + (8 + len(json_bytes)) + (8 + len(bin_data))

    with open(filepath_glb, "wb") as f:
        # 12-byte Header
        f.write(struct.pack('<4sII', b'glTF', 2, total_length))
        # JSON Chunk header
        f.write(struct.pack('<II', len(json_bytes), 0x4E4F534A))
        f.write(json_bytes)
        # BIN Chunk header
        f.write(struct.pack('<II', len(bin_data), 0x004E4942))
        f.write(bin_data)

    print(f"Exported GLB: {filepath_glb} ({os.path.getsize(filepath_glb):,} bytes)")

def main():
    print("Building 3D Nanoparticle-HER2 Receptor Complex...")
    builder = generate_full_scene()
    
    obj_path = os.path.join(OUTPUT_DIR, "nanoparticle_her2_complex.obj")
    mtl_path = os.path.join(OUTPUT_DIR, "nanoparticle_her2_complex.mtl")
    glb_path = os.path.join(OUTPUT_DIR, "nanoparticle_her2_complex.glb")

    export_obj(builder, obj_path, mtl_path)
    export_glb(builder, glb_path)
    print("3D Model Generation Complete!")

if __name__ == "__main__":
    main()
