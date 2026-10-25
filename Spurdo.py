import pymem
import pymem.process
import tkinter as tk
from tkinter import colorchooser
import time
import threading
import struct
import ctypes
import sys
import math
import json
import os

# WinAPI helpers
user32 = ctypes.windll.user32
winmm = ctypes.WinDLL('winmm')

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000
GWLP_WNDPROC = -4
WM_NCHITTEST = 0x0084
HTTRANSPARENT = -1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020

VK_MAP = {
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
    "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
    "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    "insert": 0x2D, "delete": 0x2E, "home": 0x24, "end": 0x23,
    "mouse4": 0x05, "mouse5": 0x06, "alt": 0x12,
}

def hotkey_to_vk(key):
    key = key.strip().lower()
    if key in VK_MAP:
        return VK_MAP[key]
    if len(key) == 1:
        return ord(key.upper())
    try:
        return int(key, 0)
    except Exception:
        return 0x70

hotkey = "f1"

# Fatality-style colors
BG_DARK = "#1a1208"
BG_PANEL = "#241808"
BG_TAB = "#2a2008"
ACCENT = "#ffcc00"  # spurdo yellow       # розовый
ACCENT_DIM = "#cc9900"
TEXT_COL = "#e0e0e0"
TEXT_DIM = "#888888"

try:
    winmm.timeBeginPeriod(1)
    print("[+] Таймер 1ms.")
except Exception as e:
    print(f"[!] Таймер: {e}")

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    print("[-] run as admin or spurdo cry :(")
    input("Enter...")
    sys.exit(1)


print(r"""
  ____  ____  _   _ ____  ____   ___
 / ___||  _ \| | | |  _ \|  _ \ / _ \
 \___ \| |_) | | | | |_) | | | | | | |
  ___) |  __/| |_| |  _ <| |_| | |_| |
 |____/|_|    \___/|_| \_\____/ \___/
        SPURDO EXTERNAL xDDDD
        offsets 2026-10-23 :D
""")

print("[+] admin ok xDDD spurdo has rights")

# ------------------------------------------------------------
# ПАТТЕРН-СКАН
# ------------------------------------------------------------
def pattern_scan_manual(start_addr, size, pattern, mask):
    try:
        data = pm.read_bytes(start_addr, size)
        plen = len(pattern)
        for i in range(size - plen + 1):
            ok = True
            for j in range(plen):
                if mask[j] == 'x' and data[i + j] != pattern[j]:
                    ok = False
                    break
            if ok:
                return start_addr + i
    except Exception as e:
        print(f"[!] Скан: {e}")
    return 0

def find_global_ptr(pattern, mask, offset=3, instr_len=7):
    addr = pattern_scan_manual(client.lpBaseOfDll, client.SizeOfImage, pattern, mask)
    if not addr:
        return 0
    try:
        rel = pm.read_int(addr + offset)
        target = addr + instr_len + rel
        return pm.read_longlong(target)
    except:
        return 0

def find_game_entity_system():
    return find_global_ptr(
        b"\x48\x8B\x1D\x00\x00\x00\x00\x48\x89\x1D\x00\x00\x00\x00",
        "xxx????xxx????"
    )

def find_local_player_controller():
    return find_global_ptr(
        b"\x48\x8B\x05\x00\x00\x00\x00\x41\x89\xBE",
        "xxx????xxx"
    )

def find_view_matrix():
    pattern = b"\x48\x8D\x0D\x00\x00\x00\x00\x48\xC1\xE0\x06"
    mask = "xxx????xxxx"
    addr = pattern_scan_manual(client.lpBaseOfDll, client.SizeOfImage, pattern, mask)
    if addr:
        rel = pm.read_int(addr + 3)
        return addr + 7 + rel
    return 0

# ------------------------------------------------------------
# ПОДКЛЮЧЕНИЕ
# ------------------------------------------------------------
print("[*] Подключение к cs2.exe...")
try:
    pm = pymem.Pymem("cs2.exe")
    client = pymem.process.module_from_name(pm.process_handle, "client.dll")
    base = client.lpBaseOfDll
    print(f"[+] client.dll = {hex(base)}")
except Exception as e:
    print(f"[-] Ошибка: {e}")
    input("Enter...")
    sys.exit(1)

# Offsets from cs2-dumper 2026-10-23 — всегда приоритет дампу
FALLBACK_OFFSETS = {
    # cs2-dumper 2026-10-23 — Spurdo External style
    "dwGameEntitySystem":      0x271C8B8,
    "dwLocalPlayerController": 0x253EEF8,
    "dwViewMatrix":            0x256CFE0,
    "dwForceJump":             0x22363E0,
    "dwLocalPlayerPawn":       0x25676D8,
    "dwCSGOInput":             0x257D780,
    "dwViewAngles":            0x257DE08,
    "dwAttack":                0x2235ED0,
    "dwZoom":                  0x257D610,
    "dwHighestEntityIndex":    0x2120,
    "dwPlantedC4":             0x24CD930,
    "dwGlobalVars":            0x2232088,
}

# путь к cfg рядом со скриптом
CFG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spurdo_config.json")

print("[*] reading offsets from dumper xD...")
entity_system = pm.read_longlong(base + FALLBACK_OFFSETS["dwGameEntitySystem"])
local_controller = pm.read_longlong(base + FALLBACK_OFFSETS["dwLocalPlayerController"])
view_matrix_addr = base + FALLBACK_OFFSETS["dwViewMatrix"]
jump_addr = base + FALLBACK_OFFSETS["dwForceJump"]
local_pawn_ptr = base + FALLBACK_OFFSETS["dwLocalPlayerPawn"]
csgo_input_ptr = base + FALLBACK_OFFSETS["dwCSGOInput"]
view_angles_addr = base + FALLBACK_OFFSETS["dwViewAngles"]
attack_addr = base + FALLBACK_OFFSETS["dwAttack"]
zoom_addr = base + FALLBACK_OFFSETS["dwZoom"]
planted_c4_addr = base + FALLBACK_OFFSETS["dwPlantedC4"]
global_vars_addr = base + FALLBACK_OFFSETS["dwGlobalVars"]

print(f"[+] GameEntitySystem: {hex(entity_system)}")
print(f"[+] LocalPlayerController: {hex(local_controller)}")
print(f"[+] ViewMatrix: {hex(view_matrix_addr)}")
print(f"[+] ViewAngles: {hex(view_angles_addr)}")
print(f"[+] Attack: {hex(attack_addr)}")
print(f"[+] Jump: {hex(jump_addr)}")
print(f"[+] Zoom: {hex(zoom_addr)}")

def is_valid_ptr(ptr):
    return ptr is not None and ptr > 0x10000 and ptr < 0x7FFFFFFFFFFF and ptr != 0xFFFFFFFFFFFFFFFF

if not is_valid_ptr(entity_system):
    print("[-] GameEntitySystem невалиден!")
    input("Enter...")
    sys.exit(1)

# ------------------------------------------------------------
# ОФФСЕТЫ ПОЛЕЙ
# ------------------------------------------------------------
CTRL_OFFSETS = {
    'm_hPlayerPawn':   0x92C,
    'm_iszPlayerName': 0x6FC,
}

PAWN_OFFSETS = {
    'm_iHealth':            0x34C,
    'm_iTeamNum':           0x3E7,
    'm_lifeState':          0x354,
    'm_vOldOrigin':         0x14A4,
    'm_pGameSceneNode':     0x330,
    'm_fFlags':             0x3F4,
    'm_pObserverServices':  0x1308,
    'm_pWeaponServices':    0x12F0,
    'm_entitySpottedState': 0x1E88,
    'm_vecAbsVelocity':     0x3F8,
    'm_bIsScoped':          0x1EA0,
    'm_bIsDefusing':        0x1EA2,
    'm_ArmorValue':         0x1ED0,
    'm_flFlashDuration':    0x1510,
    'm_aimPunchAngle':      0x16CC,
}

# AWP, SSG08, SCAR-20, G3SG1
SNIPER_DEF_IDS = {9, 40, 38, 11}

OBS_OFFSETS = {
    'm_iObserverMode':   0x48,
    'm_hObserverTarget': 0x4C,
}

WPN_SVC_OFFSETS = {
    'm_hActiveWeapon': 0x60,
}

# weapon + AttributeManager(0x1290) + Item(0x50) + m_iItemDefinitionIndex(0x1BA)
WPN_ITEM_DEF_INDEX = 0x1290 + 0x50 + 0x1BA  # 0x149A

SPOTTED_B_OFFSET = 0x8  # EntitySpottedState_t::m_bSpotted

# Entity identity / projectiles (cs2-dumper 2026-10-23)
ENT_P_ENTITY = 0x10          # C_BaseEntity::m_pEntity -> CEntityIdentity*
ENT_DESIGNER_NAME = 0x20     # CEntityIdentity::m_designerName
ENT_VEC_VELOCITY = 0x430     # C_BaseEntity::m_vecVelocity
PROJ_INIT_POS = 0x12B0       # C_BaseCSGrenadeProjectile::m_vInitialPosition
PROJ_INIT_VEL = 0x12BC       # C_BaseCSGrenadeProjectile::m_vInitialVelocity
SMOKE_DETONATION = 0x1378    # C_SmokeGrenadeProjectile::m_vSmokeDetonationPos
SMOKE_DID_EFFECT = 0x1364    # m_bDidSmokeEffect
MOLOTOV_IS_INC = 0x1348      # C_MolotovProjectile::m_bIsIncGrenade

# grenade radii (units)
RADIUS_SMOKE = 144.0
RADIUS_MOLOTOV = 120.0
RADIUS_HE = 350.0

GRENADE_NAMES = {
    "C_SmokeGrenadeProjectile": "smoke",
    "C_MolotovProjectile": "molotov",
    "C_Inferno": "inferno",
    "C_HEGrenadeProjectile": "he",
    "C_FlashbangProjectile": "flash",
    "C_DecoyProjectile": "decoy",
    "C_BaseCSGrenadeProjectile": "nade",
}

# shared grenade list for draw: dicts with type, pos, vel, active_smoke_pos
grenades_data = []


WEAPON_NAMES = {
    1: "DEAGLE", 2: "DUALIES", 3: "FIVE-SEVEN", 4: "GLOCK",
    7: "AK-47", 8: "AUG", 9: "AWP", 10: "FAMAS", 11: "G3SG1",
    13: "GALIL", 14: "M249", 16: "M4A4", 17: "MAC-10", 19: "P90",
    23: "MP5", 24: "UMP-45", 25: "XM1014", 26: "BIZON", 27: "MAG-7",
    28: "NEGEV", 29: "SAWED-OFF", 30: "TEC-9", 31: "ZEUS", 32: "P2000",
    33: "MP7", 34: "MP9", 35: "NOVA", 36: "P250", 38: "SCAR-20",
    39: "SG553", 40: "SSG08", 41: "KNIFE", 42: "KNIFE", 43: "FLASH",
    44: "HE", 45: "SMOKE", 46: "MOLOTOV", 47: "DECOY", 48: "INCENDIARY",
    49: "C4", 59: "KNIFE", 60: "M4A1-S", 61: "USP-S", 63: "CZ75",
    64: "R8",
}

# dwViewAngles — прямой адрес float[3], не смещение от CCSGOInput
VIEW_ANGLES_OFFSET = 0

BONE_INDICES = {
    'pelvis': 1, 'spine0': 2, 'spine1': 3, 'spine2': 4,
    'neck': 6, 'head': 7,
    'clavicle_L': 8, 'shoulder_L': 9, 'elbow_L': 10, 'hand_L': 11,
    'clavicle_R': 12, 'shoulder_R': 13, 'elbow_R': 14, 'hand_R': 15,
    'hip_L': 17, 'knee_L': 18, 'foot_L': 19,
    'hip_R': 20, 'knee_R': 21, 'foot_R': 22,
}

CONNECTIONS = [
    ('head', 'neck'), ('neck', 'spine2'), ('spine2', 'spine1'),
    ('spine1', 'spine0'), ('spine0', 'pelvis'),
    ('neck', 'shoulder_L'), ('shoulder_L', 'elbow_L'), ('elbow_L', 'hand_L'),
    ('neck', 'shoulder_R'), ('shoulder_R', 'elbow_R'), ('elbow_R', 'hand_R'),
    ('pelvis', 'hip_L'), ('hip_L', 'knee_L'), ('knee_L', 'foot_L'),
    ('pelvis', 'hip_R'), ('hip_R', 'knee_R'), ('knee_R', 'foot_R'),
]

# ------------------------------------------------------------
# ЧТЕНИЕ ПАМЯТИ
# ------------------------------------------------------------
def safe_read_int(addr, default=0):
    try: return pm.read_int(addr)
    except: return default

def safe_read_longlong(addr, default=0):
    try: return pm.read_longlong(addr)
    except: return default

def safe_read_uchar(addr, default=0):
    try: return pm.read_uchar(addr)
    except: return default

def safe_read_float(addr, default=0.0):
    try: return pm.read_float(addr)
    except: return default

def get_entity_by_index(entity_system, index):
    if index < 0:
        return 0
    try:
        list_entry_ptr = entity_system + 0x10 + 8 * (index >> 9)
        list_entry = safe_read_longlong(list_entry_ptr)
        if not is_valid_ptr(list_entry):
            return 0
        entity_ptr = list_entry + 0x70 * (index & 0x1FF)
        return safe_read_longlong(entity_ptr)
    except:
        return 0

def read_matrix():
    try:
        data = pm.read_bytes(view_matrix_addr, 16 * 4)
        return struct.unpack('f' * 16, data)
    except:
        return [0.0] * 16

def world_to_screen(pos, matrix, sw, sh):
    x, y, z = pos
    w = matrix[12] * x + matrix[13] * y + matrix[14] * z + matrix[15]
    if w < 0.01:
        return None
    inv = 1.0 / w
    sx = (sw / 2) + (matrix[0] * x + matrix[1] * y + matrix[2] * z + matrix[3]) * inv * (sw / 2)
    sy = (sh / 2) - (matrix[4] * x + matrix[5] * y + matrix[6] * z + matrix[7]) * inv * (sh / 2)
    return (int(sx), int(sy))

def get_weapon_def_index(pawn):
    """Item definition index активного оружия."""
    try:
        svc = safe_read_longlong(pawn + PAWN_OFFSETS['m_pWeaponServices'])
        if not is_valid_ptr(svc):
            return 0
        handle = safe_read_int(svc + WPN_SVC_OFFSETS['m_hActiveWeapon'], 0)
        if not handle or handle == -1:
            return 0
        wpn = get_entity_by_index(entity_system, handle & 0x7FFF)
        if not is_valid_ptr(wpn):
            return 0
        return safe_read_int(wpn + WPN_ITEM_DEF_INDEX, 0) & 0xFFFF
    except Exception:
        return 0

def get_weapon_name(pawn):
    """Активное оружие через WeaponServices → handle → item def index."""
    try:
        def_idx = get_weapon_def_index(pawn)
        return WEAPON_NAMES.get(def_idx, f"WPN{def_idx}" if def_idx else "")
    except Exception:
        return ""

def is_player_spotted(pawn):
    """m_bSpotted из EntitySpottedState_t (радар/LOS от движка)."""
    try:
        state = pawn + PAWN_OFFSETS['m_entitySpottedState']
        return bool(safe_read_uchar(state + SPOTTED_B_OFFSET, 0))
    except Exception:
        return False

def get_bone_positions(pawn, matrix, sw, sh):
    bones = {}
    scene_node = safe_read_longlong(pawn + PAWN_OFFSETS['m_pGameSceneNode'])
    if not is_valid_ptr(scene_node):
        return bones
    bone_array = safe_read_longlong(scene_node + 0x1C0)
    if not is_valid_ptr(bone_array):
        return bones
    try:
        bone_count = struct.unpack('<H', pm.read_bytes(scene_node + 0x1D4, 2))[0]
    except Exception:
        bone_count = 0
    if bone_count <= 0 or bone_count > 128:
        return bones
    for name, idx in BONE_INDICES.items():
        if idx >= bone_count:
            continue
        try:
            bone_addr = bone_array + idx * 0x20
            x = safe_read_float(bone_addr + 0x00, float("nan"))
            y = safe_read_float(bone_addr + 0x04, float("nan"))
            z = safe_read_float(bone_addr + 0x08, float("nan"))
            if not all(math.isfinite(v) for v in (x, y, z)):
                continue
            if max(abs(x), abs(y), abs(z)) > 100000:
                continue
            screen = world_to_screen((x, y, z), matrix, sw, sh)
            if not screen:
                continue
            sx, sy = screen
            if sx < -200 or sx > sw + 200 or sy < -200 or sy > sh + 200:
                continue
            bones[name] = (sx, sy)
        except Exception:
            continue
    return bones

def get_bone_world(pawn, bone_name):
    scene_node = safe_read_longlong(pawn + PAWN_OFFSETS['m_pGameSceneNode'])
    if not is_valid_ptr(scene_node):
        return None
    bone_array = safe_read_longlong(scene_node + 0x1C0)
    if not is_valid_ptr(bone_array):
        return None
    idx = BONE_INDICES.get(bone_name)
    if idx is None:
        return None
    try:
        bone_addr = bone_array + idx * 0x20
        x = safe_read_float(bone_addr + 0x00, float("nan"))
        y = safe_read_float(bone_addr + 0x04, float("nan"))
        z = safe_read_float(bone_addr + 0x08, float("nan"))
        if not all(math.isfinite(v) for v in (x, y, z)):
            return None
        return (x, y, z)
    except:
        return None

def get_view_angles():
    """pitch, yaw из dwViewAngles (x=pitch, y=yaw)."""
    try:
        pitch = pm.read_float(view_angles_addr)
        yaw = pm.read_float(view_angles_addr + 4)
        return yaw, pitch
    except:
        return 0.0, 0.0

def set_view_angles(yaw, pitch):
    try:
        pm.write_float(view_angles_addr, pitch)
        pm.write_float(view_angles_addr + 4, yaw)
    except:
        pass

# ------------------------------------------------------------
# CS2 FOREGROUND CHECK
# ------------------------------------------------------------
def is_cs2_foreground():
    """True если активное окно принадлежит процессу cs2.exe."""
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return pid.value == pm.process_id
    except Exception:
        return False

# ------------------------------------------------------------
# ГЛОБАЛЬНОЕ СОСТОЯНИЕ
# ------------------------------------------------------------
players_data = []       # враги: (name, health, team, pawn, pos, weapon, spotted)
grenades_data = []      # list of grenade dicts
all_alive_data = []     # все живые: (name, health, team, pawn, pos, weapon, spotted)
spectators_data = []
local_team = 0
local_origin = (0.0, 0.0, 0.0)
local_yaw = 0.0
running = True
esp_enabled = True
bhop_enabled = False
autostrafe_enabled = False
autostrafe_speed = 5.0
local_pawn_addr = 0
local_flags = 0
local_pawn_handle = 0

trigger_enabled = False
trigger_delay_ms = 50
trigger_fov = 5.0
trigger_hold = True
trigger_key_vk = 0x06
trigger_active = False
_last_shot_time = 0.0
# hitboxes: несколько галочек одновременно
trigger_hitboxes = {
    "head": True, "neck": False, "chest": True,
    "stomach": False, "arms": False, "legs": False,
}

# Aimbot
aim_enabled = False
rcs_enabled = False
rcs_pitch = 2.0
rcs_yaw = 2.0
rcs_standalone = True
bomb_data = None

aim_fov = 5.0
aim_smooth = 4.0          # 1 = мгновенно, больше = плавнее
aim_hold = True
aim_key_vk = 0x05         # mouse4 по умолчанию
aim_active = False
aim_visible_only = False  # только spotted
aim_autofire = False
aim_autofire_delay_ms = 50
aim_autozoom = False      # автоскоп на снайперках
aim_hitboxes = {
    "head": True, "neck": True, "chest": False,
    "stomach": False, "arms": False, "legs": False,
}
_aim_last_shot = 0.0
_autozoom_was_scoped = False

# кости для каждого хитбокса (+ fallback Z если кости нет)
HITBOX_BONES = {
    # z-offset только fallback если кости нет; head чуть ниже макушки
    "head":    [("head", 70.0)],
    "neck":    [("neck", 62.0)],
    "chest":   [("spine2", 50.0), ("spine1", 44.0)],
    "stomach": [("spine0", 36.0), ("pelvis", 30.0)],
    "arms":    [
        ("shoulder_L", 54.0), ("elbow_L", 46.0), ("hand_L", 40.0),
        ("shoulder_R", 54.0), ("elbow_R", 46.0), ("hand_R", 40.0),
    ],
    "legs":    [
        ("hip_L", 26.0), ("knee_L", 14.0), ("foot_L", 3.0),
        ("hip_R", 26.0), ("knee_R", 14.0), ("foot_R", 3.0),
    ],
}
# подправить точку прицела по кости (голова — чуть вниз от bone)
HITBOX_AIM_ADJUST = {
    "head": (0.0, 0.0, -2.0),
}

radar_enabled = True

def _bones_from_hitboxes(pawn, pos, hitboxes):
    """Список world-позиций костей по выбранным хитбоксам."""
    result = []
    for hb, enabled in hitboxes.items():
        if not enabled:
            continue
        adj = HITBOX_AIM_ADJUST.get(hb, (0.0, 0.0, 0.0))
        for bone_name, zoff in HITBOX_BONES.get(hb, []):
            b = get_bone_world(pawn, bone_name)
            if not b:
                b = (pos[0], pos[1], pos[2] + zoff)
            b = (b[0] + adj[0], b[1] + adj[1], b[2] + adj[2])
            result.append(b)
    if not result:
        b = get_bone_world(pawn, "head")
        if not b:
            b = (pos[0], pos[1], pos[2] + 70.0)
        result.append((b[0], b[1], b[2] - 2.0))
    return result

def get_designer_name(entity):
    """CEntityIdentity designer name string."""
    try:
        ident = safe_read_longlong(entity + ENT_P_ENTITY)
        if not is_valid_ptr(ident):
            return ""
        name_ptr = safe_read_longlong(ident + ENT_DESIGNER_NAME)
        if not is_valid_ptr(name_ptr):
            return ""
        return pm.read_string(name_ptr, 64) or ""
    except Exception:
        return ""

def read_vec3(addr):
    try:
        return (
            safe_read_float(addr, 0.0),
            safe_read_float(addr + 4, 0.0),
            safe_read_float(addr + 8, 0.0),
        )
    except Exception:
        return (0.0, 0.0, 0.0)

def simulate_grenade_path(origin, velocity, steps=64, dt=0.05, gravity=800.0):
    """Simple external nade prediction (no bounce). Returns list of world points."""
    pts = [origin]
    ox, oy, oz = origin
    vx, vy, vz = velocity
    x, y, z = ox, oy, oz
    for _ in range(steps):
        vz -= gravity * dt
        x += vx * dt
        y += vy * dt
        z += vz * dt
        pts.append((x, y, z))
        if z < origin[2] - 2000:  # fell too far
            break
        # stop roughly at ground relative to start (approx)
        if z < origin[2] - 5 and vz < 0 and abs(vz) > 50:
            # crude ground hit
            break
    return pts


def get_armor(pawn):
    try:
        return max(0, min(100, safe_read_int(pawn + PAWN_OFFSETS['m_ArmorValue'], 0)))
    except Exception:
        return 0

def is_scoped(pawn):
    try:
        return bool(safe_read_uchar(pawn + PAWN_OFFSETS['m_bIsScoped'], 0))
    except Exception:
        return False

def is_defusing(pawn):
    try:
        return bool(safe_read_uchar(pawn + PAWN_OFFSETS['m_bIsDefusing'], 0))
    except Exception:
        return False

def is_flashed(pawn):
    try:
        return safe_read_float(pawn + PAWN_OFFSETS['m_flFlashDuration'], 0.0) > 0.15
    except Exception:
        return False

def get_curtime():
    try:
        gv = safe_read_longlong(global_vars_addr)
        if not is_valid_ptr(gv):
            return 0.0
        return safe_read_float(gv + 0x30, 0.0)
    except Exception:
        return 0.0

def update_bomb_info():
    global bomb_data
    try:
        c4 = safe_read_longlong(planted_c4_addr)
        if not is_valid_ptr(c4):
            bomb_data = None
            return
        ticking = safe_read_uchar(c4 + 0x1288, 0)
        if not ticking:
            bomb_data = None
            return
        blow = safe_read_float(c4 + 0x12B8, 0.0)
        site = safe_read_int(c4 + 0x128C, 0)
        pos = (
            safe_read_float(c4 + PAWN_OFFSETS['m_vOldOrigin'], 0.0),
            safe_read_float(c4 + PAWN_OFFSETS['m_vOldOrigin'] + 4, 0.0),
            safe_read_float(c4 + PAWN_OFFSETS['m_vOldOrigin'] + 8, 0.0),
        )
        bomb_data = {"blow": blow, "site": site, "pos": pos}
    except Exception:
        bomb_data = None


def memory_updater():
    global players_data, all_alive_data, spectators_data, grenades_data, bomb_data
    global local_team, local_pawn_addr, local_flags, local_pawn_handle
    global local_origin, local_yaw
    global entity_system, local_controller

    while running:
        try:
            # глобалы могут обновляться между картами
            entity_system = safe_read_longlong(base + FALLBACK_OFFSETS["dwGameEntitySystem"], entity_system)
            local_controller = safe_read_longlong(base + FALLBACK_OFFSETS["dwLocalPlayerController"], local_controller)

            if not is_valid_ptr(entity_system) or not is_valid_ptr(local_controller):
                players_data = []
                all_alive_data = []
                spectators_data = []
                local_pawn_addr = 0
                time.sleep(0.1)
                continue

            lp_handle = safe_read_int(local_controller + CTRL_OFFSETS['m_hPlayerPawn'], -1)
            local_pawn_handle = lp_handle
            if lp_handle == -1 or lp_handle == 0:
                local_pawn_addr = 0
                local_flags = 0
                players_data = []
                all_alive_data = []
                spectators_data = []
                time.sleep(0.05)
                continue

            pawn_index = lp_handle & 0x7FFF
            local_pawn = get_entity_by_index(entity_system, pawn_index)
            local_pawn_addr = local_pawn if is_valid_ptr(local_pawn) else 0

            if is_valid_ptr(local_pawn):
                local_team = safe_read_uchar(local_pawn + PAWN_OFFSETS['m_iTeamNum'], 0)
                local_flags = safe_read_int(local_pawn + PAWN_OFFSETS['m_fFlags'], 0)
                lx = safe_read_float(local_pawn + PAWN_OFFSETS['m_vOldOrigin'], 0.0)
                ly = safe_read_float(local_pawn + PAWN_OFFSETS['m_vOldOrigin'] + 4, 0.0)
                lz = safe_read_float(local_pawn + PAWN_OFFSETS['m_vOldOrigin'] + 8, 0.0)
                local_origin = (lx, ly, lz)
                yaw, _ = get_view_angles()
                local_yaw = yaw
            else:
                local_team = 0
                local_flags = 0
                local_origin = (0.0, 0.0, 0.0)

            observed_handle = lp_handle
            if is_valid_ptr(local_pawn):
                obs_svc = safe_read_longlong(local_pawn + PAWN_OFFSETS['m_pObserverServices'])
                if is_valid_ptr(obs_svc):
                    tgt = safe_read_int(obs_svc + OBS_OFFSETS['m_hObserverTarget'], 0)
                    if tgt and tgt != -1 and tgt != 0:
                        observed_handle = tgt

            max_entities = safe_read_int(entity_system + FALLBACK_OFFSETS["dwHighestEntityIndex"], 0)
            new_enemies = []
            new_all = []
            new_specs = []

            for i in range(1, min(max_entities + 1, 1024)):
                entity = get_entity_by_index(entity_system, i)
                if not is_valid_ptr(entity):
                    continue

                p_handle = safe_read_int(entity + CTRL_OFFSETS['m_hPlayerPawn'], -1)
                if p_handle == -1 or p_handle == 0:
                    continue
                p_idx = p_handle & 0x7FFF
                pawn = get_entity_by_index(entity_system, p_idx)
                if not is_valid_ptr(pawn):
                    continue

                # spectators
                obs = safe_read_longlong(pawn + PAWN_OFFSETS['m_pObserverServices'])
                if is_valid_ptr(obs):
                    mode = safe_read_uchar(obs + OBS_OFFSETS['m_iObserverMode'], 0)
                    if mode > 0:
                        tgt_h = safe_read_int(obs + OBS_OFFSETS['m_hObserverTarget'], 0)
                        if tgt_h and (tgt_h & 0x7FFF) == (observed_handle & 0x7FFF):
                            t = safe_read_uchar(pawn + PAWN_OFFSETS['m_iTeamNum'], 0)
                            n = pm.read_string(entity + CTRL_OFFSETS['m_iszPlayerName'], 64) or "Unknown"
                            new_specs.append((n, t))

                life_state = safe_read_uchar(pawn + PAWN_OFFSETS['m_lifeState'], 1)
                if life_state != 0:
                    continue
                health = safe_read_int(pawn + PAWN_OFFSETS['m_iHealth'], 0)
                if health <= 0 or health > 100:
                    continue
                team = safe_read_uchar(pawn + PAWN_OFFSETS['m_iTeamNum'], 0)
                if team == 0:
                    continue
                # skip self
                if (p_handle & 0x7FFF) == (lp_handle & 0x7FFF):
                    continue

                x = safe_read_float(pawn + PAWN_OFFSETS['m_vOldOrigin'], 0.0)
                y = safe_read_float(pawn + PAWN_OFFSETS['m_vOldOrigin'] + 4, 0.0)
                z = safe_read_float(pawn + PAWN_OFFSETS['m_vOldOrigin'] + 8, 0.0)
                if x == 0.0 and y == 0.0 and z == 0.0:
                    continue
                name = pm.read_string(entity + CTRL_OFFSETS['m_iszPlayerName'], 64) or "Unknown"
                wpn = get_weapon_name(pawn)
                spotted = is_player_spotted(pawn)
                armor = get_armor(pawn)
                scoped = is_scoped(pawn)
                defusing = is_defusing(pawn)
                flashed = is_flashed(pawn)
                # name, hp, team, pawn, pos, weapon, spotted, armor, scoped, defusing, flashed
                entry = (name, health, team, pawn, (x, y, z), wpn, spotted, armor, scoped, defusing, flashed)
                new_all.append(entry)
                if team != local_team:
                    new_enemies.append(entry)

            players_data = new_enemies
            # --- grenades / projectiles ---
            new_nades = []
            try:
                max_e = safe_read_int(entity_system + FALLBACK_OFFSETS["dwHighestEntityIndex"], 0)
                max_e = min(max(max_e, 0), 2048)
                for i in range(64, max_e + 1):  # skip low player slots mostly
                    ent = get_entity_by_index(entity_system, i)
                    if not is_valid_ptr(ent):
                        continue
                    dname = get_designer_name(ent)
                    if not dname:
                        continue
                    gtype = None
                    for key, val in GRENADE_NAMES.items():
                        if key in dname or dname.endswith(key.replace('C_', '')):
                            gtype = val
                            break
                    # also match partial
                    if gtype is None:
                        dl = dname.lower()
                        if 'smokegrenadeprojectile' in dl:
                            gtype = 'smoke'
                        elif 'molotovprojectile' in dl or 'incendiarygrenadeprojectile' in dl:
                            gtype = 'molotov'
                        elif 'hegrenadeprojectile' in dl:
                            gtype = 'he'
                        elif 'flashbangprojectile' in dl:
                            gtype = 'flash'
                        elif 'decoyprojectile' in dl:
                            gtype = 'decoy'
                        elif 'inferno' in dl:
                            gtype = 'inferno'
                    if not gtype:
                        continue
                    pos = read_vec3(ent + PAWN_OFFSETS['m_vOldOrigin'])
                    if pos == (0.0, 0.0, 0.0):
                        pos = read_vec3(ent + PROJ_INIT_POS)
                    vel = read_vec3(ent + ENT_VEC_VELOCITY)
                    if vel == (0.0, 0.0, 0.0):
                        vel = read_vec3(ent + PROJ_INIT_VEL)
                    smoke_pos = None
                    if gtype == 'smoke':
                        did = safe_read_uchar(ent + SMOKE_DID_EFFECT, 0)
                        if did:
                            smoke_pos = read_vec3(ent + SMOKE_DETONATION)
                            if smoke_pos == (0.0, 0.0, 0.0):
                                smoke_pos = pos
                    new_nades.append({
                        'type': gtype,
                        'pos': pos,
                        'vel': vel,
                        'smoke_pos': smoke_pos,
                        'entity': ent,
                    })
            except Exception:
                pass
            grenades_data = new_nades
            update_bomb_info()
            all_alive_data = new_all
            spectators_data = new_specs
        except Exception:
            pass
        time.sleep(0.05)

# ------------------------------------------------------------
# BHOP / STRAFE / TRIGGER
# ------------------------------------------------------------
VK_SPACE = 0x20
VK_A = 0x41
VK_D = 0x44
VK_INSERT = 0x2D

FL_ONGROUND = 1 << 0
# Source2 button states
BTN_RELEASE = 256
BTN_PRESS   = 65537

def _get_local_pawn_flags():
    """Актуальный pawn + flags. Сначала из memory_updater, иначе из dwLocalPlayerPawn."""
    pawn = local_pawn_addr
    if is_valid_ptr(pawn):
        try:
            flags = pm.read_int(pawn + PAWN_OFFSETS['m_fFlags'])
            return pawn, flags
        except Exception:
            pass
    try:
        pawn = pm.read_longlong(local_pawn_ptr)
        if is_valid_ptr(pawn):
            flags = pm.read_int(pawn + PAWN_OFFSETS['m_fFlags'])
            return pawn, flags
    except Exception:
        pass
    return 0, 0

def _eye_origin(feet_origin):
    """Позиция глаз: origin пешки + view offset (~64)."""
    return (feet_origin[0], feet_origin[1], feet_origin[2] + 64.0)

def _angle_fov(local_pos, target_pos, yaw, pitch):
    """Угловая дистанция (градусы) от прицела до точки."""
    dx = target_pos[0] - local_pos[0]
    dy = target_pos[1] - local_pos[1]
    dz = target_pos[2] - local_pos[2]
    hyp = math.hypot(dx, dy)
    if hyp < 0.001:
        return 999.0
    target_yaw = math.degrees(math.atan2(dy, dx))
    target_pitch = -math.degrees(math.atan2(dz, hyp))
    dyaw = (target_yaw - yaw + 180.0) % 360.0 - 180.0
    dpitch = target_pitch - pitch
    return math.hypot(dyaw, dpitch)

def _fire_attack():
    """Один выстрел: press → короткая пауза → release."""
    try:
        pm.write_int(attack_addr, BTN_PRESS)
        time.sleep(0.012)
        pm.write_int(attack_addr, BTN_RELEASE)
    except Exception:
        pass

def bhop_thread():
    """Perfect bhop: на земле — jump press, в воздухе — release. Только пока зажат Space."""
    global bhop_enabled
    while running:
        if not bhop_enabled:
            time.sleep(0.01)
            continue
        try:
            if not is_cs2_foreground():
                time.sleep(0.005)
                continue
            space = bool(user32.GetAsyncKeyState(VK_SPACE) & 0x8000)
            if not space:
                try:
                    pm.write_int(jump_addr, BTN_RELEASE)
                except Exception:
                    pass
                time.sleep(0.002)
                continue

            pawn, flags = _get_local_pawn_flags()
            if not is_valid_ptr(pawn):
                time.sleep(0.001)
                continue

            on_ground = bool(flags & FL_ONGROUND)
            if on_ground:
                # кадр на земле → прыжок
                pm.write_int(jump_addr, BTN_PRESS)
            else:
                # в воздухе → отпустить, чтобы следующий прыжок снова сработал
                pm.write_int(jump_addr, BTN_RELEASE)
        except Exception:
            pass
        time.sleep(0.0005)  # ~2k Hz poll

def autostrafe_thread():
    """
    Velocity-sync strafe:
    в воздухе синхронизирует yaw с направлением скорости ±90°,
    чтобы A/D давали нормальный круг / sync, а не рандомный крутёж.
    """
    global autostrafe_enabled, autostrafe_speed
    while running:
        if not autostrafe_enabled:
            time.sleep(0.01)
            continue
        try:
            if not is_cs2_foreground():
                time.sleep(0.005)
                continue
            if not (user32.GetAsyncKeyState(VK_SPACE) & 0x8000):
                time.sleep(0.001)
                continue
            pawn, flags = _get_local_pawn_flags()
            if not is_valid_ptr(pawn):
                time.sleep(0.001)
                continue
            if flags & FL_ONGROUND:
                time.sleep(0.001)
                continue

            vx = safe_read_float(pawn + PAWN_OFFSETS['m_vecAbsVelocity'], 0.0)
            vy = safe_read_float(pawn + PAWN_OFFSETS['m_vecAbsVelocity'] + 4, 0.0)
            speed = math.hypot(vx, vy)
            if speed < 20.0:
                time.sleep(0.001)
                continue

            vel_yaw = math.degrees(math.atan2(vy, vx))
            yaw, pitch = get_view_angles()
            a_down = bool(user32.GetAsyncKeyState(VK_A) & 0x8000)
            d_down = bool(user32.GetAsyncKeyState(VK_D) & 0x8000)

            # оптимальный yaw: скорость ± 90° в сторону нажатия
            if a_down and not d_down:
                ideal = vel_yaw + 90.0
            elif d_down and not a_down:
                ideal = vel_yaw - 90.0
            else:
                # без A/D — лёгкий circle в сторону текущей мыши
                delta = _normalize_angle(yaw - vel_yaw)
                if abs(delta) < 5.0:
                    time.sleep(0.001)
                    continue
                ideal = vel_yaw + (90.0 if delta > 0 else -90.0)

            ideal = _normalize_angle(ideal)
            dyaw = _normalize_angle(ideal - yaw)
            # speed scale: не дёргать резко
            step = max(1.0, float(autostrafe_speed))
            if abs(dyaw) > step:
                dyaw = step if dyaw > 0 else -step
            set_view_angles(_normalize_angle(yaw + dyaw), pitch)
        except Exception:
            pass
        time.sleep(0.001)

def triggerbot_thread():
    """
    Triggerbot:
    - hold / toggle по кнопке
    - FOV в градусах (угол от прицела до кости)
    - head only / body
    - delay между выстрелами
    - только враги из players_data
    """
    global trigger_enabled, trigger_active, _last_shot_time
    prev_key = False
    while running:
        if not trigger_enabled:
            time.sleep(0.01)
            continue
        try:
            key_down = bool(user32.GetAsyncKeyState(trigger_key_vk) & 0x8000)
            if trigger_hold:
                active = key_down
            else:
                if key_down and not prev_key:
                    trigger_active = not trigger_active
                prev_key = key_down
                active = trigger_active
            if not active:
                time.sleep(0.001)
                continue
            if not is_cs2_foreground():
                time.sleep(0.01)
                continue

            now = time.time()
            if (now - _last_shot_time) * 1000.0 < trigger_delay_ms:
                time.sleep(0.001)
                continue

            yaw, pitch = get_view_angles()
            feet = local_origin
            if feet[0] == 0.0 and feet[1] == 0.0:
                time.sleep(0.001)
                continue
            origin = _eye_origin(feet)

            best_fov = float(trigger_fov)
            target_found = False
            hb_snap = dict(trigger_hitboxes)

            enemies = list(players_data)
            for entry in enemies:
                name, health, team, pawn, pos = entry[0], entry[1], entry[2], entry[3], entry[4]
                spotted = entry[6] if len(entry) > 6 else True
                if health <= 0:
                    continue
                candidates = _bones_from_hitboxes(pawn, pos, hb_snap)
                bone = min(candidates, key=lambda b: _angle_fov(origin, b, yaw, pitch))
                fov = _angle_fov(origin, bone, yaw, pitch)
                if fov < best_fov:
                    best_fov = fov
                    target_found = True

            if target_found:
                _fire_attack()
                _last_shot_time = time.time()
        except Exception:
            pass
        time.sleep(0.001)

def _calc_angle(src, dst):
    """pitch, yaw от src к dst (градусы)."""
    dx = dst[0] - src[0]
    dy = dst[1] - src[1]
    dz = dst[2] - src[2]
    hyp = math.hypot(dx, dy)
    if hyp < 0.001:
        return 0.0, 0.0
    yaw = math.degrees(math.atan2(dy, dx))
    pitch = -math.degrees(math.atan2(dz, hyp))
    return pitch, yaw

def _normalize_angle(a):
    while a > 180.0:
        a -= 360.0
    while a < -180.0:
        a += 360.0
    return a

def _force_zoom(press=True):
    """Нажать/отпустить кнопку zoom."""
    try:
        pm.write_int(zoom_addr, BTN_PRESS if press else BTN_RELEASE)
    except Exception:
        pass

def aimbot_thread():
    """
    Aimbot:
    - hold / toggle, FOV, smooth, hitboxes
    - visible only (m_bSpotted)
    - autofire + delay когда прицел на цели
    - autozoom на снайперках (AWP/SSG/SCAR/G3SG1)
    """
    global aim_enabled, aim_active, _aim_last_shot, _autozoom_was_scoped
    prev_key = False
    while running:
        if not aim_enabled:
            if _autozoom_was_scoped:
                _force_zoom(False)
                _autozoom_was_scoped = False
            time.sleep(0.01)
            continue
        try:
            key_down = bool(user32.GetAsyncKeyState(aim_key_vk) & 0x8000)
            if aim_hold:
                active = key_down
            else:
                if key_down and not prev_key:
                    aim_active = not aim_active
                prev_key = key_down
                active = aim_active
            if not active:
                if _autozoom_was_scoped:
                    _force_zoom(False)
                    _autozoom_was_scoped = False
                time.sleep(0.001)
                continue
            if not is_cs2_foreground():
                time.sleep(0.01)
                continue

            feet = local_origin
            if feet[0] == 0.0 and feet[1] == 0.0:
                time.sleep(0.001)
                continue
            origin = _eye_origin(feet)

            # autozoom: если снайперка и не в скоупе — жмём zoom
            if aim_autozoom and is_valid_ptr(local_pawn_addr):
                def_idx = get_weapon_def_index(local_pawn_addr)
                if def_idx in SNIPER_DEF_IDS:
                    scoped = bool(safe_read_uchar(local_pawn_addr + PAWN_OFFSETS['m_bIsScoped'], 0))
                    if not scoped:
                        _force_zoom(True)
                        _autozoom_was_scoped = True
                    else:
                        _force_zoom(False)
                else:
                    if _autozoom_was_scoped:
                        _force_zoom(False)
                        _autozoom_was_scoped = False

            cur_yaw, cur_pitch = get_view_angles()
            best_fov = float(aim_fov)
            best_bone = None
            hb_snap = dict(aim_hitboxes)
            vis_only = aim_visible_only

            enemies = list(players_data)
            for entry in enemies:
                name, health, team, pawn, pos = entry[0], entry[1], entry[2], entry[3], entry[4]
                spotted = entry[6] if len(entry) > 6 else True
                if health <= 0:
                    continue
                if vis_only and not spotted:
                    continue
                candidates = _bones_from_hitboxes(pawn, pos, hb_snap)
                for bone in candidates:
                    fov = _angle_fov(origin, bone, cur_yaw, cur_pitch)
                    if fov < best_fov:
                        best_fov = fov
                        best_bone = bone

            if best_bone is None:
                time.sleep(0.001)
                continue

            tgt_pitch, tgt_yaw = _calc_angle(origin, best_bone)
            dyaw = _normalize_angle(tgt_yaw - cur_yaw)
            dpitch = _normalize_angle(tgt_pitch - cur_pitch)

            smooth = max(1.0, float(aim_smooth))
            new_yaw = cur_yaw + dyaw / smooth
            new_pitch = cur_pitch + dpitch / smooth
            new_pitch = max(-89.0, min(89.0, new_pitch))
            new_yaw = _normalize_angle(new_yaw)
            set_view_angles(new_yaw, new_pitch)

            # autofire: если почти на кости
            if aim_autofire and best_fov < 1.5:
                now = time.time()
                if (now - _aim_last_shot) * 1000.0 >= aim_autofire_delay_ms:
                    _fire_attack()
                    _aim_last_shot = now
        except Exception:
            pass
        time.sleep(0.001)

# ------------------------------------------------------------
# ОВЕРЛЕЙ + FATALITY GUI
# ------------------------------------------------------------

def rcs_thread():
    """Standalone RCS — compensate aim punch on view angles."""
    global rcs_enabled, rcs_pitch, rcs_yaw
    old_punch = (0.0, 0.0)
    while running:
        if not rcs_enabled:
            old_punch = (0.0, 0.0)
            time.sleep(0.01)
            continue
        try:
            if not is_cs2_foreground():
                time.sleep(0.01)
                continue
            pawn = local_pawn_addr
            if not is_valid_ptr(pawn):
                time.sleep(0.005)
                continue
            # aim punch
            px = safe_read_float(pawn + PAWN_OFFSETS['m_aimPunchAngle'], 0.0)
            py = safe_read_float(pawn + PAWN_OFFSETS['m_aimPunchAngle'] + 4, 0.0)
            # shots fired heuristic: punch changed
            if abs(px) < 0.01 and abs(py) < 0.01:
                old_punch = (0.0, 0.0)
                time.sleep(0.001)
                continue
            yaw, pitch = get_view_angles()
            dx = (px - old_punch[0]) * rcs_pitch
            dy = (py - old_punch[1]) * rcs_yaw
            # CS2 punch is typically applied *2 on screen
            new_pitch = pitch - dx * 2.0
            new_yaw = yaw - dy * 2.0
            try:
                pm.write_float(view_angles_addr, float(new_yaw))
                pm.write_float(view_angles_addr + 4, float(new_pitch))
            except Exception:
                pass
            old_punch = (px, py)
            time.sleep(0.001)
        except Exception:
            time.sleep(0.01)


class Overlay(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SPURDO CHEAT xDDD")
        self.sw = self.winfo_screenwidth()
        self.sh = self.winfo_screenheight()
        self.geometry(f"{self.sw}x{self.sh}+0+0")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.wm_attributes("-alpha", 0.95)
        self.wm_attributes("-transparentcolor", "black")
        self.configure(bg="black")
        self.config(cursor="none")

        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0,
                                width=self.sw, height=self.sh, cursor="none")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # ---- ESP visuals ----
        self.esp_on = tk.BooleanVar(value=True)
        self.draw_mode = tk.StringVar(value="box")  # box / skeleton
        self.show_box = tk.BooleanVar(value=True)
        self.show_name = tk.BooleanVar(value=True)
        self.show_hp_bar = tk.BooleanVar(value=True)
        self.show_hp_text = tk.BooleanVar(value=True)
        self.show_hp_gradient = tk.BooleanVar(value=True)
        self.show_weapon = tk.BooleanVar(value=True)
        self.show_weapon_icon = tk.BooleanVar(value=True)
        self.hp_bar_side = tk.StringVar(value="left")   # left / right / bottom / top
        self.name_pos = tk.StringVar(value="above")     # above / below
        self.weapon_pos = tk.StringVar(value="below")   # above / below
        self.name_color = tk.StringVar(value="#FFEebb")
        self.box_color = tk.StringVar(value="#FFCC00")
        self.hp_full_color = tk.StringVar(value="#00FF66")
        self.hp_low_color = tk.StringVar(value="#FF2244")
        self.font_size = tk.IntVar(value=11)
        self.box_thickness = tk.IntVar(value=1)

        # off-screen arrows
        self.arrows_on = tk.BooleanVar(value=True)
        self.arrow_size = tk.IntVar(value=14)
        self.arrow_radius = tk.IntVar(value=180)  # distance from center
        self.arrow_color = tk.StringVar(value="#FFCC00")
        self.arrow_show_hp = tk.BooleanVar(value=True)

        # Spurdo-style extras
        self.box_style = tk.StringVar(value="corner")  # corner / full
        self.show_armor = tk.BooleanVar(value=True)
        self.show_scoped = tk.BooleanVar(value=True)
        self.show_defusing = tk.BooleanVar(value=True)
        self.show_flashed = tk.BooleanVar(value=True)
        self.esp_visible_only = tk.BooleanVar(value=False)
        self.watermark_on = tk.BooleanVar(value=True)
        self.bomb_timer_on = tk.BooleanVar(value=True)
        self.sniper_crosshair = tk.BooleanVar(value=True)
        self.rcs_on = tk.BooleanVar(value=False)
        self.rcs_pitch_var = tk.DoubleVar(value=2.0)
        self.rcs_yaw_var = tk.DoubleVar(value=2.0)

        # grenades
        self.nade_traj_on = tk.BooleanVar(value=True)
        self.nade_radius_on = tk.BooleanVar(value=True)
        self.nade_traj_color = tk.StringVar(value="#FFCC00")
        self.smoke_color = tk.StringVar(value="#88AACC")
        self.molly_color = tk.StringVar(value="#FF6622")
        self.he_color = tk.StringVar(value="#FF4444")

        # radar / misc (kept)
        self.radar_on = tk.BooleanVar(value=False)
        self.radar_x = tk.IntVar(value=40)
        self.radar_y = tk.IntVar(value=40)
        self.radar_size = tk.IntVar(value=160)
        self.radar_range = tk.IntVar(value=2500)
        self.radar_shape = tk.StringVar(value="square")

        # aim / trigger vars (compat)
        self.trig_enabled_var = tk.BooleanVar(value=False)
        self.trig_delay_var = tk.IntVar(value=50)
        self.trig_fov_var = tk.DoubleVar(value=5.0)
        self.trig_mode_var = tk.StringVar(value="hold")
        self.trig_hb = {
            "head": tk.BooleanVar(value=True), "neck": tk.BooleanVar(value=True),
            "chest": tk.BooleanVar(value=True), "stomach": tk.BooleanVar(value=False),
            "arms": tk.BooleanVar(value=False), "legs": tk.BooleanVar(value=False),
        }
        self.aim_enabled_var = tk.BooleanVar(value=False)
        self.aim_fov_var = tk.DoubleVar(value=5.0)
        self.aim_smooth_var = tk.DoubleVar(value=4.0)
        self.aim_mode_var = tk.StringVar(value="hold")
        self.aim_vis_var = tk.BooleanVar(value=False)
        self.aim_autofire_var = tk.BooleanVar(value=False)
        self.aim_autofire_delay_var = tk.IntVar(value=50)
        self.aim_autozoom_var = tk.BooleanVar(value=False)
        self.aim_hb = {
            "head": tk.BooleanVar(value=True), "neck": tk.BooleanVar(value=True),
            "chest": tk.BooleanVar(value=True), "stomach": tk.BooleanVar(value=False),
            "arms": tk.BooleanVar(value=False), "legs": tk.BooleanVar(value=False),
        }
        self.bhop_var = tk.BooleanVar(value=False)
        self.strafe_var = tk.BooleanVar(value=False)

        self.menu_open = False
        self.menu_win = None
        self._drag_data = {"x": 0, "y": 0}

        self.after(10, self.update_loop)
        self.bind_all("<Insert>", self.toggle_menu)
        self.bind_all("<Home>", self.toggle_menu)

        # click-through
        self.after(100, self._make_clickthrough)

    def _make_clickthrough(self):
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            if not hwnd:
                hwnd = self.winfo_id()
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x80000
            WS_EX_TRANSPARENT = 0x20
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT)
        except Exception:
            pass

    # ---------- menu UI helpers ----------
    def _section(self, parent, title, row):
        tk.Label(parent, text=title, fg=ACCENT, bg="#0a0a0a",
                 font=("Segoe UI", 10, "bold")).grid(row=row, column=0, columnspan=3,
                                                     sticky="w", pady=(8, 2))
        return row + 1

    def _chk(self, parent, text, var, row, cmd=None, col=0, colspan=2):
        tk.Checkbutton(parent, text=text, variable=var, command=cmd,
                       fg=TEXT_COL, bg="#0a0a0a", selectcolor="#1e1e1e",
                       activebackground="#0a0a0a", font=("Segoe UI", 9),
                       anchor="w").grid(row=row, column=col, columnspan=colspan, sticky="w")

    def _lbl(self, parent, text, row):
        tk.Label(parent, text=text, fg=TEXT_DIM, bg="#0a0a0a",
                 font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w")

    def _scale(self, parent, var, row, frm, to, res, cmd=None):
        tk.Scale(parent, variable=var, from_=frm, to=to, resolution=res,
                 orient="horizontal", length=160, bg="#0a0a0a", fg=TEXT_COL,
                 troughcolor="#222", highlightthickness=0, command=cmd).grid(
            row=row, column=1, columnspan=2, sticky="w")

    def _color_btn(self, parent, var, row, label="Цвет"):
        self._lbl(parent, label, row)
        def pick():
            c = colorchooser.askcolor(color=var.get())
            if c and c[1]:
                var.set(c[1])
        tk.Button(parent, textvariable=var, command=pick, bg=var.get(),
                  fg="#000", font=("Segoe UI", 8), width=10).grid(row=row, column=1, sticky="w")

    def toggle_menu(self, event=None):
        if self.menu_open and self.menu_win and self.menu_win.winfo_exists():
            self.menu_win.destroy()
            self.menu_open = False
            return
        self.menu_open = True
        w = tk.Toplevel(self)
        self.menu_win = w
        w.title("SPURDO xDDD")
        w.geometry("420x640+80+80")
        w.configure(bg=BG_DARK)
        w.attributes("-topmost", True)
        w.protocol("WM_DELETE_WINDOW", self.toggle_menu)

        nb_frame = tk.Frame(w, bg=BG_DARK)
        nb_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        tabs = ["AIMBOT", "VISUALS", "NADES", "MISC", "OTHER"]
        self._tab_frames = {}
        btn_row = tk.Frame(nb_frame, bg=BG_DARK)
        btn_row.pack(fill=tk.X)
        content = tk.Frame(nb_frame, bg="#0a0a0a")
        content.pack(fill=tk.BOTH, expand=True, pady=4)

        def show_tab(name):
            for f in self._tab_frames.values():
                f.pack_forget()
            self._tab_frames[name].pack(fill=tk.BOTH, expand=True)

        for t in tabs:
            tk.Button(btn_row, text=t, command=lambda n=t: show_tab(n),
                      bg=BG_PANEL, fg=TEXT_COL, activebackground=ACCENT,
                      font=("Segoe UI", 9, "bold"), relief="flat",
                      padx=8, pady=4).pack(side=tk.LEFT, padx=2)
            fr = tk.Frame(content, bg="#0a0a0a")
            self._tab_frames[t] = fr

        self._fill_aim_tab()
        self._fill_esp_tab()
        self._fill_nades_tab()
        self._fill_misc_tab()
        self._fill_other_tab()
        show_tab("AIMBOT")

    def _fill_esp_tab(self):
        f = self._tab_frames["VISUALS"]
        r = 0
        r = self._section(f, "Основное", r)
        self._chk(f, "ESP вкл", self.esp_on, r); r += 1
        self._chk(f, "Бокс", self.show_box, r); r += 1
        self._chk(f, "Скелет", tk.BooleanVar(value=False), r)  # mode via radio
        self._lbl(f, "Режим", r)
        tk.Radiobutton(f, text="Box", variable=self.draw_mode, value="box",
                       fg=TEXT_COL, bg="#0a0a0a", selectcolor="#1e1e1e").grid(row=r, column=1, sticky="w")
        tk.Radiobutton(f, text="Skeleton", variable=self.draw_mode, value="skeleton",
                       fg=TEXT_COL, bg="#0a0a0a", selectcolor="#1e1e1e").grid(row=r, column=2, sticky="w"); r += 1

        r = self._section(f, "Инфо", r)
        self._chk(f, "Ник", self.show_name, r); r += 1
        self._chk(f, "HP бар", self.show_hp_bar, r); r += 1
        self._chk(f, "HP число", self.show_hp_text, r); r += 1
        self._chk(f, "HP градиент", self.show_hp_gradient, r); r += 1
        self._chk(f, "Оружие (текст)", self.show_weapon, r); r += 1
        self._chk(f, "Иконка оружия", self.show_weapon_icon, r); r += 1
        self._chk(f, "Armor bar", self.show_armor, r); r += 1
        self._chk(f, "Scoped flag", self.show_scoped, r); r += 1
        self._chk(f, "Defusing", self.show_defusing, r); r += 1
        self._chk(f, "Flashed", self.show_flashed, r); r += 1
        self._chk(f, "Visible only", self.esp_visible_only, r); r += 1
        self._lbl(f, "Box style", r)
        tk.Radiobutton(f, text="Corner", variable=self.box_style, value="corner",
                       fg=TEXT_COL, bg="#0a0a0a", selectcolor="#1e1e1e").grid(row=r, column=1, sticky="w")
        tk.Radiobutton(f, text="Full", variable=self.box_style, value="full",
                       fg=TEXT_COL, bg="#0a0a0a", selectcolor="#1e1e1e").grid(row=r, column=2, sticky="w"); r += 1

        r = self._section(f, "Позиции", r)
        self._lbl(f, "HP бар", r)
        for i, v in enumerate(("left", "right", "bottom", "top")):
            tk.Radiobutton(f, text=v, variable=self.hp_bar_side, value=v,
                           fg=TEXT_COL, bg="#0a0a0a", selectcolor="#1e1e1e",
                           font=("Segoe UI", 8)).grid(row=r, column=1+i, sticky="w")
        r += 1
        self._lbl(f, "Ник", r)
        tk.Radiobutton(f, text="above", variable=self.name_pos, value="above",
                       fg=TEXT_COL, bg="#0a0a0a", selectcolor="#1e1e1e").grid(row=r, column=1, sticky="w")
        tk.Radiobutton(f, text="below", variable=self.name_pos, value="below",
                       fg=TEXT_COL, bg="#0a0a0a", selectcolor="#1e1e1e").grid(row=r, column=2, sticky="w"); r += 1
        self._lbl(f, "Оружие", r)
        tk.Radiobutton(f, text="above", variable=self.weapon_pos, value="above",
                       fg=TEXT_COL, bg="#0a0a0a", selectcolor="#1e1e1e").grid(row=r, column=1, sticky="w")
        tk.Radiobutton(f, text="below", variable=self.weapon_pos, value="below",
                       fg=TEXT_COL, bg="#0a0a0a", selectcolor="#1e1e1e").grid(row=r, column=2, sticky="w"); r += 1

        self._lbl(f, "Размер шрифта", r)
        self._scale(f, self.font_size, r, 8, 18, 1); r += 1
        self._lbl(f, "Толщина бокса", r)
        self._scale(f, self.box_thickness, r, 1, 3, 1); r += 1
        self._color_btn(f, self.box_color, r, "Бокс"); r += 1
        self._color_btn(f, self.name_color, r, "Ник"); r += 1

    def _fill_arrows_tab(self):
        f = self._tab_frames["VISUALS"]
        r = 0
        r = self._section(f, "Off-screen стрелки", r)
        self._chk(f, "Включить", self.arrows_on, r); r += 1
        self._chk(f, "Показывать HP", self.arrow_show_hp, r); r += 1
        self._lbl(f, "Размер", r)
        self._scale(f, self.arrow_size, r, 8, 30, 1); r += 1
        self._lbl(f, "Радиус от центра", r)
        self._scale(f, self.arrow_radius, r, 80, 400, 5); r += 1
        self._color_btn(f, self.arrow_color, r, "Цвет"); r += 1

    def _fill_nades_tab(self):
        f = self._tab_frames["NADES"]
        r = 0
        r = self._section(f, "Гранаты", r)
        self._chk(f, "Траектория полёта", self.nade_traj_on, r); r += 1
        self._chk(f, "Радиусы smoke/molly/HE", self.nade_radius_on, r); r += 1
        self._color_btn(f, self.nade_traj_color, r, "Линия"); r += 1
        self._color_btn(f, self.smoke_color, r, "Smoke"); r += 1
        self._color_btn(f, self.molly_color, r, "Molly"); r += 1
        self._color_btn(f, self.he_color, r, "HE"); r += 1
        tk.Label(f, text="Предикт без отскоков (approx).\nРадиус smoke≈144, molly≈120 units.",
                 fg=TEXT_DIM, bg="#0a0a0a", font=("Segoe UI", 8), justify="left").grid(
            row=r, column=0, columnspan=3, sticky="w", pady=8)

    def _fill_aim_tab(self):
        f = self._tab_frames["AIMBOT"]
        r = 0
        r = self._section(f, "Aimbot", r)
        self._chk(f, "Включить Aimbot", self.aim_enabled_var, r, self.apply_aim); r += 1
        self._chk(f, "Только видимые", self.aim_vis_var, r, self.apply_aim); r += 1
        self._chk(f, "Autofire", self.aim_autofire_var, r, self.apply_aim); r += 1
        self._chk(f, "Autozoom", self.aim_autozoom_var, r, self.apply_aim); r += 1
        self._lbl(f, "FOV", r)
        self._scale(f, self.aim_fov_var, r, 0.5, 20, 0.5, lambda v: self.apply_aim()); r += 1
        self._lbl(f, "Smooth", r)
        self._scale(f, self.aim_smooth_var, r, 1, 20, 0.5, lambda v: self.apply_aim()); r += 1
        
        
        r = self._section(f, "RCS xD", r)
        self._chk(f, "RCS enable", self.rcs_on, r, self.apply_rcs); r += 1
        self._lbl(f, "RCS pitch", r)
        self._scale(f, self.rcs_pitch_var, r, 0, 5, 0.1, lambda v: self.apply_rcs()); r += 1
        self._lbl(f, "RCS yaw", r)
        self._scale(f, self.rcs_yaw_var, r, 0, 5, 0.1, lambda v: self.apply_rcs()); r += 1
        r = self._section(f, "Triggerbot", r)
        self._chk(f, "Включить Trigger", self.trig_enabled_var, r, self.apply_trig); r += 1
        self._lbl(f, "Delay ms", r)
        self._scale(f, self.trig_delay_var, r, 0, 200, 5, lambda v: self.apply_trig()); r += 1
        self._lbl(f, "FOV", r)
        self._scale(f, self.trig_fov_var, r, 0.5, 15, 0.5, lambda v: self.apply_trig()); r += 1

    def _fill_misc_tab(self):
        f = self._tab_frames["MISC"]
        r = 0
        r = self._section(f, "Движение", r)
        self._chk(f, "Bhop", self.bhop_var, r, self.apply_misc); r += 1
        self._chk(f, "Autostrafe", self.strafe_var, r, self.apply_misc); r += 1
        r = self._section(f, "Радар", r)
        self._chk(f, "Радар", self.radar_on, r); r += 1
        self._lbl(f, "Размер", r)
        self._scale(f, self.radar_size, r, 80, 300, 5); r += 1
        self._lbl(f, "Дальность", r)
        self._scale(f, self.radar_range, r, 500, 5000, 100); r += 1
        tk.Label(f, text="Insert / Home — меню\nЗапуск от админа, CS2 оконный полный экран",
                 fg=TEXT_DIM, bg="#0a0a0a", font=("Segoe UI", 8)).grid(
            row=r, column=0, columnspan=3, sticky="w", pady=12)

    
    def _fill_other_tab(self):
        f = self._tab_frames.get("OTHER")
        if f is None:
            return
        r = 0
        r = self._section(f, "HUD xD", r)
        self._chk(f, "Watermark", self.watermark_on, r); r += 1
        self._chk(f, "Bomb timer", self.bomb_timer_on, r); r += 1
        self._chk(f, "Sniper crosshair", self.sniper_crosshair, r); r += 1
        r = self._section(f, "Arrows", r)
        self._chk(f, "Offscreen arrows", self.arrows_on, r); r += 1
        self._chk(f, "Arrow HP", self.arrow_show_hp, r); r += 1
        self._lbl(f, "Arrow size", r)
        self._scale(f, self.arrow_size, r, 8, 30, 1); r += 1
        self._lbl(f, "Arrow radius", r)
        self._scale(f, self.arrow_radius, r, 80, 400, 5); r += 1
        tk.Label(f, text="SPURDO EXTERNAL xDDD\nInsert/Home = menu\nAdmin + borderless window",
                 fg=TEXT_DIM, bg="#0a0a0a", font=("Segoe UI", 8),
                 justify="left").grid(row=r, column=0, columnspan=3, sticky="w", pady=12)

    def apply_rcs(self, *_):
        global rcs_enabled, rcs_pitch, rcs_yaw
        rcs_enabled = self.rcs_on.get()
        rcs_pitch = float(self.rcs_pitch_var.get())
        rcs_yaw = float(self.rcs_yaw_var.get())

    def apply_aim(self, *_):
        global aim_enabled, aim_fov, aim_smooth, aim_hold, aim_visible_only
        global aim_autofire, aim_autofire_delay, aim_autozoom, aim_hitboxes
        aim_enabled = self.aim_enabled_var.get()
        aim_fov = float(self.aim_fov_var.get())
        aim_smooth = float(self.aim_smooth_var.get())
        aim_hold = self.aim_mode_var.get() == "hold"
        aim_visible_only = self.aim_vis_var.get()
        aim_autofire = self.aim_autofire_var.get()
        aim_autofire_delay = int(self.aim_autofire_delay_var.get())
        aim_autozoom = self.aim_autozoom_var.get()
        for k, v in self.aim_hb.items():
            aim_hitboxes[k] = v.get()

    def apply_trig(self, *_):
        global trigger_enabled, trigger_delay, trigger_fov, trigger_hold, trigger_hitboxes
        trigger_enabled = self.trig_enabled_var.get()
        trigger_delay = int(self.trig_delay_var.get())
        trigger_fov = float(self.trig_fov_var.get())
        trigger_hold = self.trig_mode_var.get() == "hold"
        for k, v in self.trig_hb.items():
            trigger_hitboxes[k] = v.get()

    def apply_misc(self, *_):
        global bhop_enabled, autostrafe_enabled
        bhop_enabled = self.bhop_var.get()
        autostrafe_enabled = self.strafe_var.get()

    # ---------- drawing ----------
    def _hp_color(self, health):
        h = max(0, min(100, int(health))) / 100.0
        if not self.show_hp_gradient.get():
            return self.hp_full_color.get() if h > 0.3 else self.hp_low_color.get()
        # lerp green -> red
        r1, g1, b1 = 0x00, 0xFF, 0x66
        r2, g2, b2 = 0xFF, 0x22, 0x44
        r = int(r1 * h + r2 * (1 - h))
        g = int(g1 * h + g2 * (1 - h))
        b = int(b1 * h + b2 * (1 - h))
        return f"#{r:02X}{g:02X}{b:02X}"

    def _weapon_icon(self, weapon: str) -> str:
        """Простая текстовая «иконка» по имени."""
        if not weapon:
            return ""
        w = weapon.lower()
        icons = {
            "ak": "AK", "m4": "M4", "awp": "AWP", "ssg": "SCOUT", "deagle": "DEAG",
            "usp": "USP", "glock": "GLOCK", "knife": "KNIFE", "zeus": "ZEUS",
            "he": "HE", "flash": "FLASH", "smoke": "SMOKE", "molotov": "MOLLY",
            "inc": "INC", "decoy": "DECOY", "mp": "SMG", "p90": "P90",
            "nova": "NOVA", "xm": "XM", "mag7": "MAG7", "negev": "NEGEV",
            "m249": "M249", "cz": "CZ", "tec": "TEC9", "five": "FIVE",
            "revolver": "R8", "dual": "DUALS", "p250": "P250", "famas": "FAMAS",
            "galil": "GALIL", "sg": "SG", "aug": "AUG", "mac": "MAC10",
            "ump": "UMP", "bizon": "BIZON", "mp9": "MP9", "mp7": "MP7",
            "mp5": "MP5", "scar": "SCAR", "g3sg1": "G3",
        }
        for k, v in icons.items():
            if k in w:
                return f":D[{v}]"
        return f"[{weapon[:6]}]"

    def draw_player_esp(self, head, feet, name, health, weapon="", armor=0, scoped=False, defusing=False, flashed=False):
        hx, hy = head
        fx, fy = feet
        h = max(8, fy - hy)
        w = h * 0.45
        left, right = hx - w / 2, hx + w / 2
        top, bot = hy, fy
        col = self.box_color.get()
        th = max(1, int(self.box_thickness.get()))
        fs = max(8, int(self.font_size.get()))
        hp_col = self._hp_color(health)

        if self.show_box.get() and self.draw_mode.get() == "box":
            if getattr(self, "box_style", None) and self.box_style.get() == "full":
                self.canvas.create_rectangle(left, top, right, bot, outline=col, width=th, tags="esp")
            else:
                cw = max(4, w * 0.25)
                ch = max(4, h * 0.2)
                for (x1, y1, x2, y2) in (
                    (left, top, left + cw, top), (left, top, left, top + ch),
                    (right - cw, top, right, top), (right, top, right, top + ch),
                    (left, bot, left + cw, bot), (left, bot - ch, left, bot),
                    (right - cw, bot, right, bot), (right, bot - ch, right, bot),
                ):
                    self.canvas.create_line(x1, y1, x2, y2, fill=col, width=th, tags="esp")

        # HP bar
        if self.show_hp_bar.get():
            side = self.hp_bar_side.get()
            frac = max(0.0, min(1.0, health / 100.0))
            if side == "left":
                bx = left - 6
                self.canvas.create_rectangle(bx, top, bx + 3, bot, outline="#222", fill="#222", tags="esp")
                self.canvas.create_rectangle(bx, bot - h * frac, bx + 3, bot, outline="", fill=hp_col, tags="esp")
            elif side == "right":
                bx = right + 3
                self.canvas.create_rectangle(bx, top, bx + 3, bot, outline="#222", fill="#222", tags="esp")
                self.canvas.create_rectangle(bx, bot - h * frac, bx + 3, bot, outline="", fill=hp_col, tags="esp")
            elif side == "top":
                by = top - 6
                self.canvas.create_rectangle(left, by, right, by + 3, outline="#222", fill="#222", tags="esp")
                self.canvas.create_rectangle(left, by, left + w * frac, by + 3, outline="", fill=hp_col, tags="esp")
            else:  # bottom
                by = bot + 3
                self.canvas.create_rectangle(left, by, right, by + 3, outline="#222", fill="#222", tags="esp")
                self.canvas.create_rectangle(left, by, left + w * frac, by + 3, outline="", fill=hp_col, tags="esp")

        # name
        name_y_above = top - 4
        name_y_below = bot + (12 if self.hp_bar_side.get() == "bottom" else 4)
        if self.show_name.get() and name:
            ny = name_y_above if self.name_pos.get() == "above" else name_y_below
            anchor = "s" if self.name_pos.get() == "above" else "n"
            self.canvas.create_text(hx, ny, text=name, fill=self.name_color.get(),
                                    font=("Segoe UI", fs, "bold"), anchor=anchor, tags="esp")

        # hp text
        if self.show_hp_text.get():
            self.canvas.create_text(hx, (top + bot) / 2, text=str(int(health)),
                                    fill=hp_col, font=("Segoe UI", max(8, fs - 1), "bold"),
                                    tags="esp")

        # armor bar (opposite of hp if left/right)
        if self.show_armor.get() and armor > 0:
            afrac = max(0.0, min(1.0, armor / 100.0))
            acol = "#55AAFF"
            side = self.hp_bar_side.get()
            if side == "left":
                bx = right + 3
                self.canvas.create_rectangle(bx, top, bx + 3, bot, outline="#222", fill="#222", tags="esp")
                self.canvas.create_rectangle(bx, bot - h * afrac, bx + 3, bot, outline="", fill=acol, tags="esp")
            elif side == "right":
                bx = left - 6
                self.canvas.create_rectangle(bx, top, bx + 3, bot, outline="#222", fill="#222", tags="esp")
                self.canvas.create_rectangle(bx, bot - h * afrac, bx + 3, bot, outline="", fill=acol, tags="esp")

        # status flags
        flags = []
        if self.show_scoped.get() and scoped:
            flags.append("SCOPE")
        if self.show_defusing.get() and defusing:
            flags.append("DEFUSE")
        if self.show_flashed.get() and flashed:
            flags.append("FLASH")
        if flags:
            self.canvas.create_text(hx, top - (int(self.font_size.get()) + 6 if self.show_name.get() else 2),
                                    text=" ".join(flags), fill="#FFEE55",
                                    font=("Segoe UI", max(8, int(self.font_size.get()) - 1), "bold"),
                                    anchor="s", tags="esp")

        # weapon
        if self.show_weapon.get() or self.show_weapon_icon.get():
            parts = []
            if self.show_weapon_icon.get():
                parts.append(self._weapon_icon(weapon))
            if self.show_weapon.get() and weapon:
                parts.append(weapon)
            txt = " ".join(p for p in parts if p)
            if txt:
                if self.weapon_pos.get() == "above":
                    wy = name_y_above - (fs + 2 if self.show_name.get() and self.name_pos.get() == "above" else 0)
                    anchor = "s"
                else:
                    wy = name_y_below + (fs + 2 if self.show_name.get() and self.name_pos.get() == "below" else 0)
                    if self.hp_bar_side.get() == "bottom":
                        wy += 6
                    anchor = "n"
                self.canvas.create_text(hx, wy, text=txt, fill="#CCCCCC",
                                        font=("Segoe UI", max(8, fs - 1)), anchor=anchor, tags="esp")

    def draw_skeleton(self, pawn, matrix, sw, sh, pos=None, name="", health=0, weapon=""):
        bones = get_bone_positions(pawn, matrix, sw, sh)
        color = self.box_color.get()
        head_s = feet_s = None
        if pos:
            feet_s = world_to_screen(pos, matrix, sw, sh)
            head_ap = world_to_screen((pos[0], pos[1], pos[2] + 72), matrix, sw, sh)
            if feet_s and head_ap:
                head_s = head_ap
        max_seg = 80
        if head_s and feet_s:
            max_seg = max(40, abs(feet_s[1] - head_s[1]) * 0.55)
        for b1, b2 in CONNECTIONS:
            if b1 not in bones or b2 not in bones:
                continue
            p1, p2 = bones[b1], bones[b2]
            d = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if d < 1 or d > max_seg:
                continue
            self.canvas.create_line(p1[0], p1[1], p2[0], p2[1],
                                    fill=color, width=1.5, tags="esp")
        if 'head' in bones:
            hx, hy = bones['head']
            r = 4
            self.canvas.create_oval(hx - r, hy - r, hx + r, hy + r,
                                    outline=color, width=1.5, tags="esp")
        if head_s and feet_s:
            self.draw_player_esp(head_s, feet_s, name, health, weapon)

    def draw_offscreen_arrow(self, pos, matrix, sw, sh, health=100):
        if not self.arrows_on.get():
            return
        # if on screen — skip
        scr = world_to_screen(pos, matrix, sw, sh)
        if scr and 0 <= scr[0] < sw and 0 <= scr[1] < sh:
            return
        # direction from view matrix forward-ish using world delta to local
        lx, ly, lz = local_origin
        dx, dy = pos[0] - lx, pos[1] - ly
        # approximate yaw from view angles
        try:
            yaw, pitch = get_view_angles()
        except Exception:
            yaw = 0.0
        # angle of enemy relative to view
        ang = math.degrees(math.atan2(dy, dx))
        rel = math.radians(ang - yaw)
        # screen center + radius
        cx, cy = sw / 2, sh / 2
        rad = float(self.arrow_radius.get())
        ax = cx + math.cos(rel) * rad
        ay = cy - math.sin(rel) * rad
        size = float(self.arrow_size.get())
        # triangle pointing outward
        ux, uy = math.cos(rel), -math.sin(rel)
        px, py = -uy, ux
        p1 = (ax + ux * size, ay + uy * size)
        p2 = (ax - ux * size * 0.5 + px * size * 0.6, ay - uy * size * 0.5 + py * size * 0.6)
        p3 = (ax - ux * size * 0.5 - px * size * 0.6, ay - uy * size * 0.5 - py * size * 0.6)
        col = self.arrow_color.get()
        self.canvas.create_polygon(p1[0], p1[1], p2[0], p2[1], p3[0], p3[1],
                                   fill=col, outline="", tags="esp")
        if self.arrow_show_hp.get():
            self.canvas.create_text(ax, ay + size + 8, text=str(int(health)),
                                    fill=col, font=("Segoe UI", 9, "bold"), tags="esp")

    def _draw_world_circle(self, center, radius, matrix, sw, sh, color, segments=48):
        pts = []
        for i in range(segments + 1):
            a = (i / segments) * 2 * math.pi
            wx = center[0] + math.cos(a) * radius
            wy = center[1] + math.sin(a) * radius
            wz = center[2]
            s = world_to_screen((wx, wy, wz), matrix, sw, sh)
            if s:
                pts.append(s)
        for i in range(len(pts) - 1):
            self.canvas.create_line(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1],
                                    fill=color, width=1, tags="esp")

    def draw_grenades(self, matrix, sw, sh):
        if not grenades_data:
            return
        traj_col = self.nade_traj_color.get()
        for g in list(grenades_data):
            gtype = g.get("type", "")
            pos = g.get("pos", (0, 0, 0))
            vel = g.get("vel", (0, 0, 0))
            smoke_pos = g.get("smoke_pos")

            # trajectory for flying nades
            if self.nade_traj_on.get() and gtype in ("smoke", "molotov", "he", "flash", "decoy"):
                speed = math.sqrt(vel[0]**2 + vel[1]**2 + vel[2]**2)
                if speed > 5:
                    path = simulate_grenade_path(pos, vel)
                    screen_pts = []
                    for p in path:
                        s = world_to_screen(p, matrix, sw, sh)
                        if s:
                            screen_pts.append(s)
                    for i in range(len(screen_pts) - 1):
                        self.canvas.create_line(screen_pts[i][0], screen_pts[i][1],
                                                screen_pts[i+1][0], screen_pts[i+1][1],
                                                fill=traj_col, width=2, tags="esp")
                    if screen_pts:
                        self.canvas.create_text(screen_pts[-1][0], screen_pts[-1][1],
                                                text=gtype.upper(), fill=traj_col,
                                                font=("Segoe UI", 8, "bold"), tags="esp")

            # radii
            if self.nade_radius_on.get():
                if gtype == "smoke":
                    c = smoke_pos if smoke_pos else pos
                    self._draw_world_circle(c, RADIUS_SMOKE, matrix, sw, sh, self.smoke_color.get())
                elif gtype in ("molotov", "inferno"):
                    self._draw_world_circle(pos, RADIUS_MOLOTOV, matrix, sw, sh, self.molly_color.get())
                elif gtype == "he":
                    # only show radius near end of path / low velocity
                    speed = math.sqrt(vel[0]**2 + vel[1]**2 + vel[2]**2)
                    if speed < 40:
                        self._draw_world_circle(pos, RADIUS_HE * 0.35, matrix, sw, sh, self.he_color.get())

    def draw_radar(self):
        if not self.radar_on.get():
            return
        size = self.radar_size.get()
        rx, ry = self.radar_x.get(), self.radar_y.get()
        rng = max(100, self.radar_range.get())
        cx, cy = rx + size / 2, ry + size / 2
        scale = (size / 2 - 8) / rng
        self.canvas.create_rectangle(rx, ry, rx + size, ry + size,
                                     fill="#0a0a0a", outline=ACCENT, tags="esp")
        self.canvas.create_oval(cx - 2, cy - 2, cx + 2, cy + 2, fill=ACCENT, tags="esp")
        try:
            yaw, _ = get_view_angles()
        except Exception:
            yaw = 0.0
        yaw_r = math.radians(yaw)
        lx, ly, _ = local_origin
        for entry in players_data:
            pos = entry[4]
            dx, dy = pos[0] - lx, pos[1] - ly
            # rotate by -yaw
            rx_ = dx * math.cos(-yaw_r) - dy * math.sin(-yaw_r)
            ry_ = dx * math.sin(-yaw_r) + dy * math.cos(-yaw_r)
            px = cx + rx_ * scale
            py = cy - ry_ * scale
            if rx <= px <= rx + size and ry <= py <= ry + size:
                self.canvas.create_oval(px - 3, py - 3, px + 3, py + 3,
                                        fill="#FF4DA6", outline="", tags="esp")

    def draw_spectator_list(self, sw, sh):
        specs = spectators_data
        if not specs:
            return
        x = sw - 180
        y = sh // 2 - (len(specs) * 18) // 2
        self.canvas.create_text(x, y - 18, text="SPEC xD", fill=ACCENT,
                                font=("Segoe UI", 11, "bold"), anchor="nw", tags="esp")
        for i, (name, team) in enumerate(specs):
            sq = "#e8a838" if team == 2 else ("#5b9bd5" if team == 3 else "#aaaaaa")
            yy = y + i * 18
            self.canvas.create_rectangle(x, yy + 2, x + 12, yy + 14, fill=sq, outline="", tags="esp")
            self.canvas.create_text(x + 18, yy, text=name, fill="#ffffff",
                                    font=("Segoe UI", 10), anchor="nw", tags="esp")

    def draw_all(self):
        self.canvas.delete("esp")
        self.canvas.delete("status")
        sw, sh = self.sw, self.sh
        if not self.esp_on.get():
            return
        view = read_matrix()
        if view[0] == 0.0:
            return

        mode = self.draw_mode.get()
        cnt = 0
        for entry in list(players_data):
            name, health, team, pawn, pos = entry[0], entry[1], entry[2], entry[3], entry[4]
            weapon = entry[5] if len(entry) > 5 else ""
            spotted = entry[6] if len(entry) > 6 else True
            armor = entry[7] if len(entry) > 7 else 0
            scoped = entry[8] if len(entry) > 8 else False
            defusing = entry[9] if len(entry) > 9 else False
            flashed = entry[10] if len(entry) > 10 else False
            if self.esp_visible_only.get() and not spotted:
                continue
            head = world_to_screen((pos[0], pos[1], pos[2] + 65), view, sw, sh)
            feet = world_to_screen(pos, view, sw, sh)
            on_screen = bool(head and feet)
            if on_screen:
                if mode == "skeleton":
                    self.draw_skeleton(pawn, view, sw, sh, pos, name, health, weapon)
                else:
                    self.draw_player_esp(head, feet, name, health, weapon, armor, scoped, defusing, flashed)
                cnt += 1
            else:
                self.draw_offscreen_arrow(pos, view, sw, sh, health)

        self.draw_grenades(view, sw, sh)
        self.draw_radar()
        self.draw_spectator_list(sw, sh)

        
        # watermark
        if self.watermark_on.get():
            self.canvas.create_text(sw - 12, 12, text="SPURDO EXTERNAL xD",
                                    fill=ACCENT, font=("Segoe UI", 12, "bold"),
                                    anchor="ne", tags="status")
        # bomb timer
        if self.bomb_timer_on.get() and bomb_data:
            cur = get_curtime()
            left_t = bomb_data["blow"] - cur
            if left_t > 0:
                site = "A" if bomb_data["site"] == 0 else ("B" if bomb_data["site"] == 1 else "?")
                col = "#FF3333" if left_t < 5 else ("#FFAA00" if left_t < 15 else "#FFEE55")
                self.canvas.create_text(sw / 2, 48, text=f"BOMB {site} {left_t:.1f}s",
                                        fill=col, font=("Segoe UI", 16, "bold"), tags="status")
                bp = bomb_data.get("pos")
                if bp:
                    bs = world_to_screen(bp, view, sw, sh)
                    if bs:
                        self.canvas.create_text(bs[0], bs[1], text=f"C4 {left_t:.1f}",
                                                fill=col, font=("Segoe UI", 11, "bold"), tags="esp")
        # sniper crosshair
        if self.sniper_crosshair.get() and is_valid_ptr(local_pawn_addr):
            try:
                if is_scoped(local_pawn_addr) or get_weapon_def_index(local_pawn_addr) in SNIPER_DEF_IDS:
                    cx, cy = sw / 2, sh / 2
                    g = 6
                    self.canvas.create_line(cx - 12, cy, cx - g, cy, fill="#00FF88", width=1, tags="esp")
                    self.canvas.create_line(cx + g, cy, cx + 12, cy, fill="#00FF88", width=1, tags="esp")
                    self.canvas.create_line(cx, cy - 12, cx, cy - g, fill="#00FF88", width=1, tags="esp")
                    self.canvas.create_line(cx, cy + g, cx, cy + 12, fill="#00FF88", width=1, tags="esp")
            except Exception:
                pass

        st = f"SPURDO esp:{cnt} nades:{len(grenades_data)} xD"
        if bhop_enabled:
            st += " | bhop:D"
        if aim_enabled:
            st += " | aim:DD"
        if trigger_enabled:
            st += " | trig:D"
        self.canvas.create_text(100, 30, text=st, fill=ACCENT,
                                font=("Segoe UI", 11, "bold"), tags="status")

    def update_loop(self):
        try:
            self.draw_all()
        except Exception:
            pass
        self.after(8, self.update_loop)


# ------------------------------------------------------------
# ЗАПУСК
# ------------------------------------------------------------
if __name__ == "__main__":
    try:
        print("[*] starting spurdo threads xD...")
        threading.Thread(target=memory_updater, daemon=True).start()
        threading.Thread(target=bhop_thread, daemon=True).start()
        threading.Thread(target=autostrafe_thread, daemon=True).start()
        threading.Thread(target=triggerbot_thread, daemon=True).start()
        threading.Thread(target=aimbot_thread, daemon=True).start()
        threading.Thread(target=rcs_thread, daemon=True).start()
        print("[+] spurdo ready :DDD")
        print("[!] cs2 windowed fullscreen or spurdo no see")
        print("[!] Insert/Home = spurdo menu xDDD")
        app = Overlay()
        while running:
            try:
                if not app.winfo_exists():
                    break
                app.update()
                time.sleep(0.005)
            except tk.TclError:
                break
            except Exception as e:
                print(f"[!] {e}")
                time.sleep(0.1)
        print("[*] spurdo go sleep määää")
    except Exception as e:
        print(f"[-] {e}")
        import traceback
        traceback.print_exc()
    finally:
        running = False
        try:
            winmm.timeEndPeriod(1)
        except Exception:
            pass
        input("Enter...")
