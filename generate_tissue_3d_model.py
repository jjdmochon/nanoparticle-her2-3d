#!/usr/bin/env python3
"""
3D Model Generator: In Vivo Breast Cancer Tissue Targeted by 400 nm Polystyrene Nanoparticles
(Anti-HER2 Nanobody Conjugated, Cy5 Loaded)

Generates:
1. breast_tissue_targeting.obj / .mtl (Wavefront format)
2. breast_tissue_targeting.glb (glTF 2.0 binary format)

Scale: 1.0 unit = 1.0 micrometre (µm) for the tissue view.
400 nm nanoparticles are represented at 0.4 µm diameter (or scaled for visual legibility at 0.8–1.2 µm).
"""

import os
import sys
import math
import json
import struct
import random

OUTPUT_DIR = r"C:\Users\Juanjo\.gemini\antigravity\scratch\nanoparticle-her2-3d"
os.makedirs(OUTPUT_DIR, exist_ok=True)

random.seed(1337)

class TissueMeshBuilder:
    def __init__(self):
        self.vertices = []
        self.normals = []
        self.colors = []
        self.groups = {}
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

    def add_sphere(self, cx, cy, cz, radius, lat_segs=10, lon_segs=16, color=(0.9, 0.9, 0.9, 1.0), roughness=0.0):
        start_idx = len(self.vertices)
        for i in range(lat_segs + 1):
            theta = i * math.pi / lat_segs
            sin_t = math.sin(theta)
            cos_t = math.cos(theta)
            for j in range(lon_segs + 1):
                phi = j * 2.0 * math.pi / lon_segs
                nx = sin_t * math.cos(phi)
                ny = cos_t
                nz = sin_t * math.sin(phi)
                
                # Optional surface perturbation (cellular pleomorphism)
                r_eff = radius
                if roughness > 0:
                    r_eff += roughness * math.sin(4 * theta) * math.cos(4 * phi)

                x = cx + r_eff * nx
                y = cy + r_eff * ny
                z = cz + r_eff * nz
                self.add_vertex(x, y, z, nx, ny, nz, *color)

        stride = lon_segs + 1
        for i in range(lat_segs):
            for j in range(lon_segs):
                v0 = start_idx + i * stride + j
                v1 = start_idx + (i + 1) * stride + j
                v2 = start_idx + (i + 1) * stride + (j + 1)
                v3 = start_idx + i * stride + (j + 1)
                self.add_quad(v0, v1, v2, v3)

    def add_cylinder(self, p1, p2, radius, segs=10, color=(0.8, 0.8, 0.8, 1.0)):
        x1, y1, z1 = p1
        x2, y2, z2 = p2
        dx, dy, dz = x2 - x1, y2 - y1, z2 - z1
        length = math.sqrt(dx*dx + dy*dy + dz*dz)
        if length < 1e-6:
            return
        ux, uy, uz = dx / length, dy / length, dz / length

        if abs(ux) < 0.9: px, py, pz = 1.0, 0.0, 0.0
        else: px, py, pz = 0.0, 1.0, 0.0

        dot = px*ux + py*uy + pz*uz
        vx, vy, vz = px - dot*ux, py - dot*uy, pz - dot*uz
        vlen = math.sqrt(vx*vx + vy*vy + vz*vz)
        vx, vy, vz = vx/vlen, vy/vlen, vz/vlen

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
            self.add_vertex(x1 + rx, y1 + ry, z1 + rz, ca*vx + sa*wx, ca*vy + sa*wy, ca*vz + sa*wz, *color)
            self.add_vertex(x2 + rx, y2 + ry, z2 + rz, ca*vx + sa*wx, ca*vy + sa*wy, ca*vz + sa*wz, *color)

        for i in range(segs):
            ni = (i + 1) % segs
            b0 = start_idx + 2 * i
            t0 = start_idx + 2 * i + 1
            b1 = start_idx + 2 * ni
            t1 = start_idx + 2 * ni + 1
            self.add_quad(b0, t0, t1, b1)

    def add_tube_curve(self, points, radius, segs=8, color=(0.8, 0.8, 0.8, 1.0)):
        for i in range(len(points) - 1):
            self.add_cylinder(points[i], points[i+1], radius, segs=segs, color=color)

def generate_tissue_scene():
    builder = TissueMeshBuilder()

    # ==========================================
    # 1. HER2-OVEREXPRESSING BREAST CARCINOMA CELL NEST
    # ==========================================
    # Center of tumor nest: (15, 0, 0) µm
    # 16 packed pleomorphic breast cancer cells with irregular ruffled membrane
    builder.set_group("Breast_Carcinoma_Cells")
    cancer_color = (0.35, 0.18, 0.28, 1.0)  # Dense malignant cell violet/purple
    cancer_membrane_color = (0.50, 0.22, 0.38, 1.0)

    cancer_cell_centers = [
        (15.0, 0.0, 0.0, 11.0),
        (26.0, 4.0, -6.0, 10.0),
        (8.0, -5.0, 8.0, 9.5),
        (22.0, -8.0, 10.0, 10.5),
        (4.0, 6.0, -8.0, 9.0),
        (18.0, 12.0, 4.0, 10.0),
        (30.0, -2.0, 6.0, 9.5),
        (12.0, -12.0, -4.0, 9.0),
        (2.0, -2.0, -14.0, 8.5),
        (24.0, 8.0, -16.0, 9.0),
        (35.0, 5.0, -2.0, 8.5),
        (10.0, 14.0, -10.0, 8.5),
        (28.0, -14.0, -2.0, 8.0),
        (16.0, -6.0, 20.0, 8.5),
        (6.0, 8.0, 14.0, 8.0)
    ]

    for cx, cy, cz, rad in cancer_cell_centers:
        builder.add_sphere(cx, cy, cz, rad, lat_segs=12, lon_segs=18, color=cancer_color, roughness=0.8)

    # Overexpressed HER2 Receptor Surface Mantle (Glowing emerald puncta on cancer cells)
    builder.set_group("HER2_Receptor_Mantle")
    her2_puncta_color = (0.1, 0.9, 0.5, 0.8)
    for cx, cy, cz, rad in cancer_cell_centers:
        for _ in range(25):
            u = random.random()
            costheta = 2.0 * random.random() - 1.0
            sintheta = math.sqrt(max(0.0, 1.0 - costheta * costheta))
            phi = 2.0 * math.pi * random.random()
            px = cx + (rad + 0.3) * sintheta * math.cos(phi)
            py = cy + (rad + 0.3) * costheta
            pz = cz + (rad + 0.3) * sintheta * math.sin(phi)
            builder.add_sphere(px, py, pz, 0.4, lat_segs=4, lon_segs=6, color=her2_puncta_color)

    # ==========================================
    # 2. TUMOR MICROVASCULATURE (LEAKY FENESTRATED CAPILLARY)
    # ==========================================
    # Vessel runs along X = -38 µm, from Z = -50 to Z = +50 µm
    builder.set_group("Tumor_Capillary_Vessel")
    vessel_color = (0.75, 0.25, 0.25, 0.85)  # Endothelial lumen red
    vessel_outer_color = (0.65, 0.20, 0.22, 0.75)

    vessel_points = []
    for zi in range(-55, 60, 10):
        # Slight tortuosity typical of tumor angiogenesis
        vx = -38.0 + 3.0 * math.sin(0.06 * zi)
        vy = 4.0 * math.cos(0.05 * zi)
        vessel_points.append((vx, vy, float(zi)))

    # Longitudinal segmented vessel with fenestrations
    vessel_radius = 9.5  # µm (capillary/venule caliber)
    for i in range(len(vessel_points) - 1):
        p1 = vessel_points[i]
        p2 = vessel_points[i+1]
        builder.add_cylinder(p1, p2, vessel_radius, segs=14, color=vessel_color)

    # Red Blood Cells (Biconcave discocytes) inside the vessel lumen
    builder.set_group("Red_Blood_Cells")
    rbc_color = (0.85, 0.08, 0.08, 1.0)
    for _ in range(28):
        t = random.uniform(0.05, 0.95)
        # Interpolate along vessel
        idx = int(t * (len(vessel_points) - 1))
        p_base = vessel_points[idx]
        rx = p_base[0] + random.uniform(-4.5, 4.5)
        ry = p_base[1] + random.uniform(-4.5, 4.5)
        rz = p_base[2] + random.uniform(-4.0, 4.0)
        # Biconcave flat disc (flattened sphere)
        builder.add_sphere(rx, ry, rz, 2.2, lat_segs=6, lon_segs=10, color=rbc_color)

    # Endothelial Fenestrations / Leaky Gaps (EPR Portal)
    builder.set_group("Vessel_Fenestrations_EPR")
    fen_color = (1.0, 0.45, 0.2, 0.9)
    fenestration_sites = [
        (-30.0, 2.0, -20.0),
        (-29.0, -1.0, -5.0),
        (-31.0, 4.0, 15.0),
        (-28.0, -3.0, 32.0)
    ]
    for fx, fy, fz in fenestration_sites:
        builder.add_sphere(fx, fy, fz, 1.8, lat_segs=6, lon_segs=8, color=fen_color)

    # ==========================================
    # 3. EXTRACELLULAR MATRIX (COLLAGEN FIBRILS / STROMA)
    # ==========================================
    builder.set_group("Extracellular_Matrix_Fibrils")
    ecm_color = (0.75, 0.72, 0.65, 0.65)  # Collagen fiber off-white/beige

    for _ in range(45):
        # Collagen fibers bridging vessel and tumor nest
        start_x = random.uniform(-32.0, -20.0)
        start_y = random.uniform(-18.0, 18.0)
        start_z = random.uniform(-45.0, 45.0)

        end_x = random.uniform(-5.0, 38.0)
        end_y = random.uniform(-18.0, 18.0)
        end_z = random.uniform(-45.0, 45.0)

        mid_x = (start_x + end_x) * 0.5 + random.uniform(-3, 3)
        mid_y = (start_y + end_y) * 0.5 + random.uniform(-4, 4)
        mid_z = (start_z + end_z) * 0.5 + random.uniform(-3, 3)

        builder.add_tube_curve([(start_x, start_y, start_z), (mid_x, mid_y, mid_z), (end_x, end_y, end_z)],
                               0.35, segs=4, color=ecm_color)

    # ==========================================
    # 4. NORMAL BREAST TISSUE & STROMA (ADIPOCYTES / HEALTHY DUCT)
    # ==========================================
    # Adipose tissue at positive X/Z boundary (X: 38 to 60 µm)
    builder.set_group("Normal_Breast_Adipocytes")
    fat_color = (0.92, 0.90, 0.78, 0.85)  # Rounded pale lipid-filled cells

    adipocyte_centers = [
        (46.0, -12.0, -25.0, 12.0),
        (52.0, 2.0, -18.0, 14.0),
        (48.0, 16.0, -10.0, 13.0),
        (54.0, -8.0, 8.0, 14.5),
        (48.0, 10.0, 22.0, 13.5),
        (56.0, -4.0, 32.0, 12.5),
        (42.0, 24.0, 4.0, 11.5)
    ]
    for ax, ay, az, arad in adipocyte_centers:
        builder.add_sphere(ax, ay, az, arad, lat_segs=10, lon_segs=14, color=fat_color)

    # ==========================================
    # 5. TARGETED NANOPARTICLES (CY5 CORE + VHH CORONA)
    # ==========================================
    # Scale: Visual representation of 400 nm nanoparticles (~0.7 µm radius for visual clarity)
    builder.set_group("Targeted_Nanoparticles_Tumor")
    np_cy5_core_color = (1.0, 0.02, 0.25, 1.0) # Intense glowing Cy5 red
    np_vhh_corona_color = (0.95, 0.65, 0.10, 0.9) # Amber nanobody corona

    # A. Extravasating nanoparticles (traveling from leaky capillary through ECM)
    builder.set_group("Extravasating_Nanoparticles")
    for _ in range(24):
        # Distributed in the interstitial corridor (X from -28 to -2 µm)
        nx = random.uniform(-28.0, -2.0)
        ny = random.uniform(-14.0, 14.0)
        nz = random.uniform(-35.0, 35.0)
        # Core
        builder.add_sphere(nx, ny, nz, 0.75, lat_segs=6, lon_segs=8, color=np_cy5_core_color)
        # Corona
        builder.add_sphere(nx, ny, nz, 0.95, lat_segs=6, lon_segs=8, color=np_vhh_corona_color)

    # B. Bound nanoparticles densely decorating the HER2-overexpressing cancer cells
    builder.set_group("Targeted_Nanoparticles_Bound")
    for cx, cy, cz, rad in cancer_cell_centers:
        # 6 to 9 nanoparticles per cell membrane
        num_np_bound = random.randint(6, 10)
        for _ in range(num_np_bound):
            costheta = 2.0 * random.random() - 1.0
            sintheta = math.sqrt(max(0.0, 1.0 - costheta * costheta))
            phi = 2.0 * math.pi * random.random()

            # Surface docking position
            bx = cx + (rad + 0.8) * sintheta * math.cos(phi)
            by = cy + (rad + 0.8) * costheta
            bz = cz + (rad + 0.8) * sintheta * math.sin(phi)

            builder.add_sphere(bx, by, bz, 0.85, lat_segs=6, lon_segs=8, color=np_cy5_core_color)
            builder.add_sphere(bx, by, bz, 1.10, lat_segs=6, lon_segs=8, color=np_vhh_corona_color)

    # ==========================================
    # 6. HISTOLOGICAL SCALE BAR (50 µm)
    # ==========================================
    builder.set_group("Tissue_Scale_Bar_50um")
    sb_color = (0.95, 0.95, 0.95, 1.0)
    builder.add_cylinder((-25.0, -22.0, -40.0), (25.0, -22.0, -40.0), 0.6, segs=8, color=sb_color)
    builder.add_cylinder((-25.0, -24.0, -40.0), (-25.0, -20.0, -40.0), 0.5, segs=6, color=sb_color)
    builder.add_cylinder((25.0, -24.0, -40.0), (25.0, -20.0, -40.0), 0.5, segs=6, color=sb_color)

    return builder

def export_tissue_obj(builder, filepath_obj, filepath_mtl):
    mtl_filename = os.path.basename(filepath_mtl)
    materials = {
        "Breast_Carcinoma_Cells": {"Kd": "0.38 0.18 0.32", "d": "1.0", "Ns": "40"},
        "HER2_Receptor_Mantle": {"Kd": "0.10 0.90 0.50", "Ke": "0.10 0.70 0.35", "d": "0.9", "Ns": "80"},
        "Tumor_Capillary_Vessel": {"Kd": "0.75 0.22 0.22", "d": "0.85", "Ns": "60"},
        "Red_Blood_Cells": {"Kd": "0.85 0.08 0.08", "d": "1.0", "Ns": "50"},
        "Vessel_Fenestrations_EPR": {"Kd": "1.00 0.45 0.20", "Ke": "0.80 0.35 0.10", "d": "0.95", "Ns": "90"},
        "Extracellular_Matrix_Fibrils": {"Kd": "0.75 0.72 0.65", "d": "0.65", "Ns": "25"},
        "Normal_Breast_Adipocytes": {"Kd": "0.92 0.90 0.78", "d": "0.88", "Ns": "30"},
        "Extravasating_Nanoparticles": {"Kd": "1.00 0.02 0.25", "Ke": "0.90 0.01 0.20", "d": "1.0", "Ns": "100"},
        "Targeted_Nanoparticles_Bound": {"Kd": "1.00 0.02 0.25", "Ke": "0.95 0.02 0.25", "d": "1.0", "Ns": "100"},
        "Tissue_Scale_Bar_50um": {"Kd": "0.95 0.95 0.95", "d": "1.0", "Ns": "100"}
    }

    with open(filepath_mtl, "w", encoding="utf-8") as f:
        f.write("# Material Library for In Vivo Breast Tissue Targeting\n\n")
        for mat_name, props in materials.items():
            f.write(f"newmtl {mat_name}\n  illum 2\n")
            for k, v in props.items():
                f.write(f"  {k} {v}\n")
            f.write("\n")

    with open(filepath_obj, "w", encoding="utf-8") as f:
        f.write(f"# In Vivo Breast Cancer Tissue Targeted by 400 nm Polystyrene Nanoparticles\n")
        f.write(f"mtllib {mtl_filename}\n\n")
        for v in builder.vertices:
            f.write(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n")
        for n in builder.normals:
            f.write(f"vn {n[0]:.4f} {n[1]:.4f} {n[2]:.4f}\n")
        for grp_name, triangles in builder.groups.items():
            if not triangles: continue
            f.write(f"\ng {grp_name}\nusemtl {grp_name}\n")
            for t in triangles:
                v0, v1, v2 = t[0] + 1, t[1] + 1, t[2] + 1
                f.write(f"f {v0}//{v0} {v1}//{v1} {v2}//{v2}\n")

    print(f"Exported Tissue OBJ: {filepath_obj} ({len(builder.vertices):,} vertices)")

def export_tissue_glb(builder, filepath_glb):
    material_defs = [
        {"name": "Breast_Carcinoma_Cells", "color": [0.38, 0.18, 0.32, 1.0], "roughness": 0.5, "metallic": 0.05},
        {"name": "HER2_Receptor_Mantle", "color": [0.10, 0.90, 0.50, 0.85], "roughness": 0.2, "metallic": 0.1, "emissive": [0.1, 0.7, 0.35]},
        {"name": "Tumor_Capillary_Vessel", "color": [0.75, 0.22, 0.22, 0.85], "roughness": 0.4, "metallic": 0.05},
        {"name": "Red_Blood_Cells", "color": [0.85, 0.08, 0.08, 1.0], "roughness": 0.3, "metallic": 0.05},
        {"name": "Vessel_Fenestrations_EPR", "color": [1.00, 0.45, 0.20, 0.95], "roughness": 0.2, "metallic": 0.1, "emissive": [0.8, 0.35, 0.1]},
        {"name": "Extracellular_Matrix_Fibrils", "color": [0.75, 0.72, 0.65, 0.65], "roughness": 0.6, "metallic": 0.02},
        {"name": "Normal_Breast_Adipocytes", "color": [0.92, 0.90, 0.78, 0.88], "roughness": 0.6, "metallic": 0.05},
        {"name": "Extravasating_Nanoparticles", "color": [1.00, 0.02, 0.25, 1.0], "roughness": 0.2, "metallic": 0.1, "emissive": [0.9, 0.01, 0.2]},
        {"name": "Targeted_Nanoparticles_Bound", "color": [1.00, 0.02, 0.25, 1.0], "roughness": 0.2, "metallic": 0.1, "emissive": [0.95, 0.02, 0.25]},
        {"name": "Tissue_Scale_Bar_50um", "color": [0.95, 0.95, 0.95, 1.0], "roughness": 0.2, "metallic": 0.8}
    ]

    mat_map = {m["name"]: idx for idx, m in enumerate(material_defs)}

    bin_data = bytearray()
    buffer_views = []
    accessors = []
    meshes = []
    nodes = []

    # Positions
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
    while len(bin_data) % 4 != 0: bin_data.append(0)
    buffer_views.append({"buffer": 0, "byteOffset": pos_offset, "byteLength": len(pos_bytes), "target": 34962})
    pos_acc_idx = len(accessors)
    accessors.append({"bufferView": pos_bv_idx, "byteOffset": 0, "componentType": 5126, "count": len(builder.vertices), "type": "VEC3", "min": min_pos, "max": max_pos})

    # Normals
    norm_bytes = bytearray()
    for n in builder.normals:
        norm_bytes.extend(struct.pack('<fff', n[0], n[1], n[2]))
    norm_bv_idx = len(buffer_views)
    norm_offset = len(bin_data)
    bin_data.extend(norm_bytes)
    while len(bin_data) % 4 != 0: bin_data.append(0)
    buffer_views.append({"buffer": 0, "byteOffset": norm_offset, "byteLength": len(norm_bytes), "target": 34962})
    norm_acc_idx = len(accessors)
    accessors.append({"bufferView": norm_bv_idx, "byteOffset": 0, "componentType": 5126, "count": len(builder.normals), "type": "VEC3"})

    mesh_idx = 0
    for grp_name, triangles in builder.groups.items():
        if not triangles: continue
        idx_bytes = bytearray()
        for t in triangles:
            idx_bytes.extend(struct.pack('<III', t[0], t[1], t[2]))
        idx_bv_idx = len(buffer_views)
        idx_offset = len(bin_data)
        bin_data.extend(idx_bytes)
        while len(bin_data) % 4 != 0: bin_data.append(0)
        buffer_views.append({"buffer": 0, "byteOffset": idx_offset, "byteLength": len(idx_bytes), "target": 34963})
        idx_acc_idx = len(accessors)
        accessors.append({"bufferView": idx_bv_idx, "byteOffset": 0, "componentType": 5125, "count": len(triangles) * 3, "type": "SCALAR"})

        mat_idx = mat_map.get(grp_name, 0)
        meshes.append({"name": grp_name, "primitives": [{"attributes": {"POSITION": pos_acc_idx, "NORMAL": norm_acc_idx}, "indices": idx_acc_idx, "material": mat_idx}]})
        nodes.append({"name": grp_name, "mesh": mesh_idx})
        mesh_idx += 1

    gltf_materials = []
    for m in material_defs:
        mat_entry = {
            "name": m["name"],
            "pbrMetallicRoughness": {"baseColorFactor": m["color"], "metallicFactor": m["metallic"], "roughnessFactor": m["roughness"]},
            "doubleSided": True
        }
        if "emissive" in m: mat_entry["emissiveFactor"] = m["emissive"]
        if m["color"][3] < 1.0: mat_entry["alphaMode"] = "BLEND"
        gltf_materials.append(mat_entry)

    gltf_dict = {
        "asset": {"version": "2.0", "generator": "Antigravity Breast Tissue In Vivo 3D Engine"},
        "scene": 0,
        "scenes": [{"nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": meshes,
        "materials": gltf_materials,
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(bin_data)}]
    }

    json_str = json.dumps(gltf_dict, separators=(',', ':'))
    json_bytes = json_str.encode('utf-8')
    json_pad = (4 - (len(json_bytes) % 4)) % 4
    json_bytes += b' ' * json_pad
    bin_pad = (4 - (len(bin_data) % 4)) % 4
    bin_data += b'\x00' * bin_pad
    total_length = 12 + (8 + len(json_bytes)) + (8 + len(bin_data))

    with open(filepath_glb, "wb") as f:
        f.write(struct.pack('<4sII', b'glTF', 2, total_length))
        f.write(struct.pack('<II', len(json_bytes), 0x4E4F534A))
        f.write(json_bytes)
        f.write(struct.pack('<II', len(bin_data), 0x004E4942))
        f.write(bin_data)

    print(f"Exported Tissue GLB: {filepath_glb} ({os.path.getsize(filepath_glb):,} bytes)")

def main():
    print("Building In Vivo Breast Tissue Targeting 3D Model...")
    builder = generate_tissue_scene()
    obj_path = os.path.join(OUTPUT_DIR, "breast_tissue_targeting.obj")
    mtl_path = os.path.join(OUTPUT_DIR, "breast_tissue_targeting.mtl")
    glb_path = os.path.join(OUTPUT_DIR, "breast_tissue_targeting.glb")
    export_tissue_obj(builder, obj_path, mtl_path)
    export_tissue_glb(builder, glb_path)
    print("Tissue 3D Model Generation Complete!")

if __name__ == "__main__":
    main()
