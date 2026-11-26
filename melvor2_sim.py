# -*- coding: utf-8 -*-
"""
Melvor Idle 2 combat simulator.

Reads the game's own data (MelvorBase.json embedded in Melvor2.exe) and the
newest local save, rebuilds the player's current gear/levels, then Monte-Carlo
simulates repeated fights against every enemy / dungeon and reports XP per hour,
food consumed per hour, kill speed and safety.

Usage (from a PowerShell prompt):
    python melvor2_sim.py                 # build app.html from the newest save, serve it on http://127.0.0.1:8765 and open it
    python melvor2_sim.py --no-serve      # just write app.html (file://); the in-app save-refresh button is then unavailable
    python melvor2_sim.py --cli --hours 2 # Python-side simulation, writes report.html / results.json
    python melvor2_sim.py --cli --stance LongRange --food Trout
    python melvor2_sim.py --cli --filter Golbin --verbose

app.html embeds the game data + your save snapshot; change gear / stance / food /
auto-eat in the browser and re-run there. While this script's server is running,
the "↺ 세이브 갱신" button in the app re-reads the newest save (POST /api/refresh
rebuilds app.html, then the page reloads); GET /api/status reports whether the
save on disk is newer than the snapshot.

Formulas follow the Melvor Idle 2 community wiki (wikily.gg / melvorcalc.com /
melvor2.com) plus the game's own data file. See the assumptions block in the
HTML report.
"""
import argparse, ctypes, glob, json, math, os, random, re, shutil, struct, sys, time
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

FROZEN = bool(getattr(sys, "frozen", False))          # running as a PyInstaller exe (mods/melvor2Simulator/Melvor2Simulator.exe)
# HERE: where app.html / cache / results are written and served from (next to the script or the exe).
HERE = os.path.dirname(os.path.abspath(sys.executable if FROZEN else __file__))
# RES_DIR: bundled app_template.html / profit.js / profit.css inside the exe; a copy next to the exe wins (see res()).
RES_DIR = getattr(sys, "_MEIPASS", HERE)

def _writable(d):
    try:
        os.makedirs(d, exist_ok=True)
        t = os.path.join(d, ".write_test"); open(t, "w").close(); os.remove(t)
        return True
    except OSError:
        return False

# OUT_DIR: where app.html / cache / results are written and served from. Next to the script/exe when that folder is
# writable; a Steam folder under Program Files usually is not for a normal user, then %LOCALAPPDATA%\Melvor2Simulator is used.
OUT_DIR = HERE if _writable(HERE) else os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "Melvor2Simulator")
if OUT_DIR != HERE:
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"알림: {HERE} 에 쓰기 권한이 없어 출력 폴더로 {OUT_DIR} 를 사용합니다.")

def _find_game_dir():
    """Walk up from HERE until a folder containing Melvor2.exe is found (Melvor2Sim/ or mods/<name>/ inside the game folder)."""
    d = HERE
    for _ in range(5):
        if os.path.exists(os.path.join(d, "Melvor2.exe")):
            return d
        parent = os.path.dirname(d)
        if parent == d: break
        d = parent
    for cand in (os.environ.get("MELVOR2_DIR", ""), r"C:\Program Files (x86)\Steam\steamapps\common\Melvor Idle 2"):
        if cand and os.path.exists(os.path.join(cand, "Melvor2.exe")):
            return cand
    return os.path.dirname(HERE)

def res(name):
    """Path of a resource file: a copy next to the script/exe takes precedence over the one bundled in the exe."""
    local = os.path.join(HERE, name)
    return local if os.path.exists(local) else os.path.join(RES_DIR, name)

GAME_DIR = _find_game_dir()
EXE = os.path.join(GAME_DIR, "Melvor2.exe")
DATA_DIR = os.path.join(GAME_DIR, "data_GamesByMalcs.Melvor2_windows_x86_64")
NATIVE_DLL = os.path.join(DATA_DIR, "System.IO.Compression.Native.dll")
CACHE_DIR = os.path.join(OUT_DIR, "cache")
SAVE_ROOT = os.path.join(os.environ.get("APPDATA", ""), "Games By Malcs", "Melvor Idle 2")

NS = "MelvorBase:"
def short(s):
    return s.split(":", 1)[1] if isinstance(s, str) and ":" in s else s

# Level -> cumulative XP (levels 1..120), from the game's XP table.
XP_TABLE = [0, 83, 174, 276, 388, 512, 650, 801, 969, 1154, 1358, 1583, 1832, 2107, 2410, 2745, 3115, 3523, 3973, 4470,
            5018, 5623, 6291, 7028, 7841, 8739, 9730, 10823, 12030, 13362, 14832, 16455, 18246, 20223, 22405, 24813, 27472, 30407, 33646, 37222,
            41170, 45527, 50338, 55648, 61510, 67982, 75126, 83013, 91719, 101331, 111943, 123658, 136592, 150871, 166634, 184038, 203252, 224464, 247884, 273740,
            302286, 333802, 368597, 407013, 449426, 496252, 547951, 605030, 668048, 737625, 814442, 899254, 992892, 1096275, 1210418, 1336440, 1475578, 1629197, 1798805, 1986065,
            2192815, 2421084, 2673111, 2951370, 3258591, 3597789, 3972291, 4385773, 4842292, 5346329, 5902828, 6517250, 7195626, 7944611, 8771555, 9684574, 10692626, 11805603, 13034427, 14391157,
            15889106, 17542973, 19368988, 21385070, 23611002, 26068628, 28782065, 31777939, 35085651, 38737657, 42769797, 47221638, 52136865, 57563714, 63555439, 70170836, 77474824, 85539078, 94442733, 104273162]

def level_from_xp(xp):
    lvl = 1
    for i, need in enumerate(XP_TABLE):
        if xp >= need:
            lvl = i + 1
    return lvl

# ----------------------------------------------------------------------------
# 1. Game data: extract Data/Packages/MelvorBase.json from the embedded Godot PCK
# ----------------------------------------------------------------------------
def extract_game_data():
    os.makedirs(CACHE_DIR, exist_ok=True)
    cached = os.path.join(CACHE_DIR, "MelvorBase.json")
    if os.path.exists(cached) and os.path.getmtime(cached) >= os.path.getmtime(EXE):
        return json.load(open(cached, encoding="utf-8"))
    print("게임 데이터 추출 중 (Melvor2.exe -> MelvorBase.json)...")
    with open(EXE, "rb") as f:
        f.seek(0x3C); pe = struct.unpack("<I", f.read(4))[0]
        f.seek(pe); assert f.read(4) == b"PE\0\0", "PE header not found"
        _, nsec, _, _, _, optsz, _ = struct.unpack("<HHIIIHH", f.read(20))
        f.seek(pe + 24 + optsz)
        pck_base = None
        for _ in range(nsec):
            name = f.read(8).rstrip(b"\0"); vs, va, rs, rp = struct.unpack("<IIII", f.read(16)); f.read(16)
            if name == b"pck":
                pck_base = rp
        assert pck_base is not None, "pck section not found"
        f.seek(pck_base); assert f.read(4) == b"GDPC"
        ver = struct.unpack("<I", f.read(4))[0]; f.read(12)
        flags = struct.unpack("<I", f.read(4))[0]
        file_base = struct.unpack("<q", f.read(8))[0]
        if ver >= 3:
            dir_off = struct.unpack("<q", f.read(8))[0]
            f.seek(pck_base + dir_off)
        else:
            f.seek(16 * 4, 1)
        count = struct.unpack("<I", f.read(4))[0]
        target = None
        for _ in range(count):
            n = struct.unpack("<I", f.read(4))[0]; p = f.read(n).rstrip(b"\0").decode("utf-8", "replace")
            off, size = struct.unpack("<qq", f.read(16)); f.read(16); fl = struct.unpack("<I", f.read(4))[0]
            if p.endswith("Data/Packages/MelvorBase.json"):
                target = (off, size, fl)
        assert target, "MelvorBase.json not in pck"
        off, size, fl = target
        assert not (fl & 1), "data file is encrypted"
        abs_off = pck_base + off + (file_base if (flags & 2) else 0)
        f.seek(abs_off); raw = f.read(size)
    open(cached, "wb").write(raw)
    return json.loads(raw.decode("utf-8"))

# ----------------------------------------------------------------------------
# 2. Save file: Brotli stream (unterminated) -> .NET BinaryWriter payload
# ----------------------------------------------------------------------------
def brotli_decode(data):
    try:
        dll = ctypes.CDLL(NATIVE_DLL)
        create = dll.BrotliDecoderCreateInstance; create.restype = ctypes.c_void_p
        create.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        stream = dll.BrotliDecoderDecompressStream; stream.restype = ctypes.c_int
        stream.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_char_p),
                           ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_char_p), ctypes.POINTER(ctypes.c_size_t)]
        destroy = dll.BrotliDecoderDestroyInstance; destroy.argtypes = [ctypes.c_void_p]
        st = create(None, None, None)
        inbuf = ctypes.create_string_buffer(data, len(data))
        avail_in = ctypes.c_size_t(len(data)); next_in = ctypes.c_char_p(ctypes.addressof(inbuf))
        out = bytearray(); total = ctypes.c_size_t(0)
        res = 3
        while True:
            chunk = ctypes.create_string_buffer(1 << 20)
            avail_out = ctypes.c_size_t(len(chunk)); next_out = ctypes.c_char_p(ctypes.addressof(chunk))
            res = stream(st, ctypes.byref(avail_in), ctypes.byref(next_in), ctypes.byref(avail_out), ctypes.byref(next_out), ctypes.byref(total))
            got = len(chunk) - avail_out.value; out += chunk.raw[:got]
            # 3 = needs more output; 2 = needs more input (the stream is unterminated, so this is also returned
            # when the output buffer fills exactly as the input runs out); 1 = done; 0 = error
            if res in (0, 1) or (res != 3 and got == 0):
                break
        destroy(st)
        if out:
            return bytes(out)
    except Exception as e:  # pragma: no cover
        print("ctypes brotli failed:", e)
    # fallback: node.js
    import subprocess, tempfile
    tmp_in = tempfile.mktemp(suffix=".sav"); tmp_out = tempfile.mktemp(suffix=".bin")
    open(tmp_in, "wb").write(data)
    js = ("const z=require('zlib'),fs=require('fs');const d=fs.readFileSync(process.argv[1]);"
          "fs.writeFileSync(process.argv[2], z.brotliDecompressSync(d,{finishFlush:z.constants.BROTLI_OPERATION_FLUSH}));")
    subprocess.check_call(["node", "-e", js, tmp_in, tmp_out])
    return open(tmp_out, "rb").read()

class Reader:
    def __init__(self, b, p=0): self.b = b; self.p = p
    def i32(self): v = struct.unpack_from("<i", self.b, self.p)[0]; self.p += 4; return v
    def i64(self): v = struct.unpack_from("<q", self.b, self.p)[0]; self.p += 8; return v
    def f64(self): v = struct.unpack_from("<d", self.b, self.p)[0]; self.p += 8; return v
    def u8(self): v = self.b[self.p]; self.p += 1; return v
    def str(self):
        n = 0; sh = 0
        while True:
            c = self.b[self.p]; self.p += 1; n |= (c & 0x7F) << sh; sh += 7
            if c < 0x80: break
        s = self.b[self.p:self.p + n].decode("utf-8", "replace"); self.p += n; return s

def find_newest_save():
    files = glob.glob(os.path.join(SAVE_ROOT, "**", "saves", "*.sav"), recursive=True)
    if not files:
        raise SystemExit("세이브 파일을 찾을 수 없습니다: " + SAVE_ROOT)
    return max(files, key=os.path.getmtime)

def parse_save(raw, gd=None):
    r = Reader(raw)
    info = {"version": r.i32()}
    r.p += 16
    info["name"] = r.str(); info["label"] = r.str(); r.i64()
    info["active_skill"] = r.str(); r.str(); info["active_action"] = r.str(); r.str()
    # skill experience
    xp = {}
    for m in re.finditer(rb"(.)(MelvorBase:[A-Za-z]+)(....)(....)\nExperience\x08\x00\x00\x00(.{8})", raw, re.S):
        if m.group(1)[0] != len(m.group(2)): continue  # length prefix must match the entity id
        xp[short(m.group(2).decode())] = struct.unpack("<d", m.group(5))[0]
    info["xp"] = xp
    # equipment
    i = raw.find(b"\tEquipment"); rr = Reader(raw, i + len(b"\tEquipment")); rr.i32(); n = rr.i32()
    equip = {}
    for _ in range(n):
        slot = short(rr.str()); ln = rr.i32(); end = rr.p + ln
        qty = rr.i32(); occupied = rr.u8(); has = rr.u8()
        item = short(rr.str()) if has else None
        rr.p = end
        if item and qty >= 0:
            equip[slot] = (item, qty)
        elif item and occupied:
            equip[slot] = (item, -1)  # occupied by a 2H item in another slot
    info["equipment"] = equip
    # food slot
    j = raw.find(b"\x04Food"); food = None
    if j >= 0:
        rr = Reader(raw, j + 5); ln = rr.i32(); has = rr.u8()
        if has:
            name = short(rr.str()); q = rr.i64()
            food = (name, q)
    info["food"] = food
    # bank
    bank = {}
    k = raw.find(b"MelvorBase:Bank")
    if k >= 0:
        rr = Reader(raw, k + len(b"MelvorBase:Bank")); seclen = rr.i32(); end = rr.p + seclen
        rr.p = raw.find(b"MelvorBase:", rr.p, end) - 1
        while 0 < rr.p < end:
            n = raw[rr.p]
            if n == 0 or n > 64 or raw[rr.p + 1:rr.p + 12] != b"MelvorBase:":
                break
            sid = short(rr.str()); q = rr.i32(); rr.p += 2
            if q < 0 or q > 10 ** 9: break
            bank[sid] = q
    info["bank"] = bank
    # weapon type -> stance preference map in Combat.Player block
    stance_map = {}
    m = re.search(rb"\x07\x00\x00\x00\x10MelvorBase:Melee\x0fMelvorBase:Stab", raw)
    if m:
        rr = Reader(raw, m.start()); cnt = rr.i32()
        for _ in range(cnt):
            wt = short(rr.str()); st = short(rr.str()); stance_map[wt] = st
    info["stance_map"] = stance_map
    pm = re.search(rb"\x06Player(....)\x04\x00\x00\x00(....)", raw, re.S)
    info["current_hp"] = struct.unpack("<i", pm.group(2))[0] if pm else None
    info.update(parse_skilling(raw))
    info["astro"] = parse_astrology(raw, gd) if gd is not None else {}
    return info

# ----------------------------------------------------------------------------
# 3. Model building
# ----------------------------------------------------------------------------
class GameData:
    def __init__(self, d):
        self.raw = d
        O = d["Objects"]
        for i in O["Item"]:  # capability keys are namespaced ("MelvorBase:Food") -> use short keys
            i["Capabilities"] = {short(k): v for k, v in i["Capabilities"].items()}
        self.items = {i["Id"]: i for i in O["Item"]}
        self.enemies = {e["Id"]: e for e in O["Enemy"]}
        self.attacks = {a["Id"]: a for a in O["Attack"]}
        self.stances = {s["Id"]: s for s in O["AttackStance"]}
        self.styles = {s["Id"]: s for s in O["CombatStyle"]}
        self.weapon_types = {w["Id"]: w for w in O["WeaponType"]}
        self.areas = O["CombatArea"]; self.dungeons = O["Dungeon"]
        self.passives = {p["Id"]: p for p in O["CombatPassive"]}
        self.dots = {e["Id"]: e for e in O["DamageOverTimeEffect"]}
        self.stuns = {e["Id"]: e for e in O["StunEffect"]}
        self.eot_heal = {e["Id"]: e for e in O["EndOfTurnHealingEffect"]}
        self.triangle = O["CombatTriangleBonus"]; self.elemental = O["ElementalBonus"]

    def triangle_mods(self, p_style, e_style):
        maxhit, resist = 1.0, 1.0
        for t in self.triangle:
            if short(t["PlayerStyle"]) == p_style and short(t["EnemyStyle"]) == e_style:
                for b in t["Bonuses"]["Component"]:
                    if b["Stat"]["Name"] == "MaxHitCombatTriangle": maxhit += b["Value"]
                    if b["Stat"]["Name"] == "ResistanceCombatTriangle": resist += b["Value"]
        return maxhit, resist

    def element_mod(self, p_elements, e_element):
        mod = 1.0
        for t in self.elemental:
            if short(t["PlayerElement"]) in p_elements and short(t["EnemyElement"]) == e_element:
                for b in t["Bonuses"]["Component"]:
                    if b["Stat"]["Name"] == "PercentMaxHit": mod += b["Value"]
        return mod

def style_of_stance(gd, stance): return short(gd.stances[stance]["CombatStyle"])

def accuracy_level(gd, style, levels):
    return sum(levels.get(short(l["Level"]), 1) * l["Ratio"] for l in gd.styles[style]["AccuracyRatingLevels"])

def evasion_level(gd, attacker_style, levels):
    return sum(levels.get(short(l["Level"]), 1) * l["Ratio"] for l in gd.styles[attacker_style]["EvasionLevels"])

def rating(level, bonus): return math.floor((level + 9) * (bonus + 64))

def hit_chance(acc, eva):
    if acc <= 0: return 0.0
    if eva <= 0: return 1.0
    return 1 - eva / (2 * acc) if acc >= eva else acc / (2 * eva)

def max_hit(gd, style, levels, stats):
    f = gd.styles[style]["MaxHitFormula"]
    L = sum(levels.get(short(l["Level"]), 1) * l["Ratio"] for l in f["Data"]["Levels"])
    if short(f["Type"]) == "StrengthBonus":
        sb = stats.get(short(f["Data"]["StrengthBonusStat"]), 0)
        return max(1, math.floor(22 + L + (L + 17) * sb / 64))
    M = stats.get(short(f["Data"]["MaxHitStat"]), 0); D = stats.get(short(f["Data"]["DamageBonusStat"]), 0)
    return max(1, math.floor(M * (1 + D) * (1 + (L + 1) / 200)))

class Player:
    def __init__(self, gd, save, args):
        self.gd = gd
        self.levels = {k: level_from_xp(v) for k, v in save["xp"].items()}
        for k in ("Attack", "Strength", "Defence", "Ranged", "Magic", "Prayer"): self.levels.setdefault(k, 1)
        self.levels.setdefault("Hitpoints", 10)
        self.equipment = save["equipment"]
        self.stats = defaultdict(float); self.power = 0; self.protection = 0; self.elements = {"Neutral"}
        self.weapon_type = None; self.unmodeled = []
        for slot, (item, qty) in self.equipment.items():
            if qty == -1: continue
            it = gd.items.get(item); eq = it["Capabilities"].get("Equipment") if it else None
            if not eq: continue
            for s in eq["Stats"]["Stats"]: self.stats[short(s["Stat"])] += s["Value"]
            for p in eq["Stats"]["PowerRatings"]: self.power += p["Value"]
            for p in eq["Stats"]["ProtectionRatings"]: self.protection += p["Value"]
            if eq.get("Bonuses"): self.unmodeled.append(f"{item} 장비 보너스")
            w = it["Capabilities"].get("Weapon")
            if slot == "Weapon" and w:
                self.weapon_type = short(w["Type"]); self.elements = {short(e) for e in w.get("Elements", [])} or {"Neutral"}
        if self.weapon_type is None: self.weapon_type = "Melee"
        wt = gd.weapon_types.get(self.weapon_type, {"Stances": [NS + "Stab"]})
        allowed = [short(s) for s in wt["Stances"]]
        self.stance = args.stance or save["stance_map"].get(self.weapon_type) or allowed[0]
        if self.stance not in allowed:
            print(f"경고: 스탠스 {self.stance} 는 무기 종류 {self.weapon_type} 에서 불가 ({allowed}); {allowed[0]} 사용")
            self.stance = allowed[0]
        st = gd.stances[self.stance]
        self.style = style_of_stance(gd, self.stance)
        self.xp_rates = {short(g["Component"]["Entity"]): g["ExperiencePerDamage"] for g in st["ExperienceGain"]}
        self.def_bonus_levels = sum(b["Value"] for b in st["Bonuses"]["Component"] if b["Stat"]["Name"] == "FlatCombatLevel")
        lv = dict(self.levels); lv["Defence"] = lv.get("Defence", 1) + self.def_bonus_levels
        self.eff_levels = lv
        self.interval = max(250, int(self.stats.get("AttackInterval", 4000) or 4000))
        self.max_hp = self.levels["Hitpoints"] * 10
        self.max_hit_base = max_hit(gd, self.style, self.levels, self.stats)
        self.accuracy = rating(accuracy_level(gd, self.style, self.levels), self.stats.get(short(st["AccuracyStat"]), 0))
        # food
        food_name = args.food or (save["food"][0] if save["food"] else None)
        if not food_name or "Food" not in gd.items.get(food_name, {}).get("Capabilities", {}):
            food_name = "Trout"
        self.food = food_name; self.food_heal = gd.items[food_name]["Capabilities"]["Food"]["BaseHealing"]
        self.food_qty = save["food"][1] if save["food"] and save["food"][0] == food_name else save["bank"].get(food_name, 0)
        self.ae_threshold = args.autoeat_threshold; self.ae_eff = args.autoeat_efficiency
        self.light = args.light
        self.combat_level = math.floor(sum(self.levels.get(short(r["Level"]), 1) * r["Ratio"] for r in gd.styles[self.style]["CombatLevelRatios"]))

    def evasion_vs(self, enemy_stance, enemy_style):
        est = self.gd.stances[enemy_stance]
        lvl = evasion_level(self.gd, enemy_style, self.eff_levels)
        return rating(lvl, self.stats.get(short(est["EvasionStat"]), 0))

class Enemy:
    def __init__(self, gd, e):
        self.gd = gd; self.id = e["Id"]; self.name = e["DisplayName"]
        self.levels = {short(l["Key"]): l["Value"] for l in e["Levels"]}
        self.stats = {short(s["Stat"]): s["Value"] for s in e["Stats"]["Stats"]}
        self.power = sum(p["Value"] for p in e["Stats"]["PowerRatings"])
        self.protection = sum(p["Value"] for p in e["Stats"]["ProtectionRatings"])
        self.stance = short(e["Stances"][0]["Stance"]); self.style = style_of_stance(gd, self.stance)
        self.element = short(e.get("Element") or "Neutral")
        self.max_hp = self.levels.get("Hitpoints", 1) * 10
        self.interval = int(self.stats.get("AttackInterval", 4000))
        self.armour = self.stats.get("Armour", 0); self.max_ward = int(self.stats.get("MaximumWard", 0))
        self.lifesteal = self.stats.get("Lifesteal", 0)
        self.max_hit = max_hit(gd, self.style, self.levels, self.stats)
        st = gd.stances[self.stance]
        self.accuracy = rating(accuracy_level(gd, self.style, self.levels), self.stats.get(short(st["AccuracyStat"]), 0))
        # Attack selection mirrors CharacterComponent.NormalizeAttackChances: one roll over cumulative
        # chances; the normal attack gets 1 - sum(special chances) when that sum is below 1.
        specials = [(a["Chance"], gd.attacks[short(a["Attack"])]) for a in e["Attacks"]]
        total = sum(c for c, _ in specials)
        if total >= 1 and total > 0:
            specials = [(c / total, atk) for c, atk in specials]
        self.specials = specials
        self.special_total = min(1.0, total)
        # per-kill bonus XP (CombatExperienceStats.KilledExperienceStats): rate * (4*Armour + 50*Ward)
        self.kill_xp_factor = 4.0 * self.stats.get("Armour", 0) + 50.0 * self.stats.get("MaximumWard", 0)
        self.combat_level = math.floor(sum(self.levels.get(short(r["Level"]), 1) * r["Ratio"] for r in gd.styles[self.style]["CombatLevelRatios"]))
        self.eot_heal_pct = 0.0; self.onhit_dots = []; self.unmodeled = []
        for pid in e["Passives"]:
            p = gd.passives.get(short(pid))
            if not p: continue
            for ce in p["Modifiers"]["CombatEffect"]:
                eff = ce["Modifier"]["Effect"]; et = short(eff["Type"]); trig = short(ce["Modifier"]["Trigger"]["Type"])
                if et == "EndOfTurnHealing" and trig == "AtStartOfFight":
                    h = gd.eot_heal[short(eff["Data"]["Effect"])]["HealingPerTurn"]
                    self.eot_heal_pct += h["Formula"]["Data"]["Percent"] * ce["Chance"]
                elif et == "DamageOverTime" and trig == "OnAttack" and ce["Modifier"]["AppliesTo"] == "Target":
                    self.onhit_dots.append((ce["Chance"], gd.dots[short(eff["Data"]["Effect"])]))
                else:
                    self.unmodeled.append(f"{p['DisplayName']}({et})")
            for b in p["Modifiers"]["Component"]:
                self.unmodeled.append(f"{p['DisplayName']}({b['Stat']['Name']})")
        for ch, atk in self.specials:
            for eff in atk["OnHitEffects"] + atk["PreHitEffects"]:
                et = short(eff["Effect"]["Type"])
                if et not in ("DamageOverTime", "Stun"):
                    self.unmodeled.append(f"{atk['DisplayName']}({et})")
        self.unmodeled = sorted(set(self.unmodeled))

    def evasion_vs(self, player_stance, player_style):
        pst = self.gd.stances[player_stance]
        return rating(evasion_level(self.gd, player_style, self.levels), self.stats.get(short(pst["EvasionStat"]), 0))

    def max_burst(self):
        """largest damage one attack action can deal before resistance (for the safety check)."""
        worst = self.max_hit
        for ch, atk in self.specials:
            tot = 0
            for h in atk["Hits"]:
                for dm in h["Damage"]:
                    f = dm["Formula"]; t = short(f["Type"]); pct = f["Data"].get("Percent", 1)
                    if t in ("NormalDamage", "MaxHit"): tot += h["Count"] * self.max_hit * pct
            worst = max(worst, tot)
        return worst

# ----------------------------------------------------------------------------
# 4. Simulation
# ----------------------------------------------------------------------------
RESPAWN_MS = 3000

class Sim:
    def __init__(self, gd, player, enemies, hours, seed, darkness=0, name=""):
        self.gd = gd; self.p = player; self.sequence = enemies; self.T = int(hours * 3600 * 1000)
        self.rng = random.Random(seed); self.darkness = darkness; self.name = name

    def run(self):
        gd, p, rng = self.gd, self.p, self.rng
        dark_factor = max(0.0, 1 - 0.05 * max(0, self.darkness - p.light))
        res = dict(kills=0, deaths=0, food=0, healed=0, dmg_taken=0, dmg_dealt=0, xp=defaultdict(float),
                   player_attacks=0, player_hits=0, enemy_attacks=0, enemy_hits=0, loops=0, fight_ms=0)
        self.hp = p.max_hp; t = 0; idx = 0
        thresh_hp = round(p.max_hp * p.ae_threshold)  # FoodComponent.AutoEat uses Math.Round
        heal_amount = max(1, int(p.food_heal * p.ae_eff))

        def spawn(i, start):
            e = self.sequence[i % len(self.sequence)]
            tri_mh, tri_res = gd.triangle_mods(p.style, e.style)
            el = gd.element_mod(p.elements, e.element)
            p_maxhit = max(1, math.floor(p.max_hit_base * tri_mh * el))
            e_res = min(0.70, e.protection / (p.power + e.protection) if (p.power + e.protection) > 0 else 0)
            p_res = min(0.70, (p.protection / (e.power + p.protection) if (e.power + p.protection) > 0 else 0) * tri_res)
            p_hit = hit_chance(p.accuracy * dark_factor, e.evasion_vs(p.stance, p.style))
            e_hit = hit_chance(e.accuracy, p.evasion_vs(e.stance, e.style) * dark_factor)
            return dict(e=e, hp=e.max_hp, ward=e.max_ward, armour_broken=False, p_maxhit=p_maxhit, e_res=e_res, p_res=p_res,
                        p_hit=p_hit, e_hit=e_hit, start=start)

        f = spawn(0, 0); p_next = p.interval; e_next = f["e"].interval
        dots = []  # [next_t, procs_left, dmg, interval]
        stunned = 0
        fb = spawn(len(self.sequence) - 1, 0)  # boss / last enemy of a dungeon for the displayed figures
        info = dict(p_hit=fb["p_hit"], e_hit=fb["e_hit"], p_maxhit=fb["p_maxhit"], e_res=fb["e_res"], p_res=fb["p_res"])

        def take_damage(amount):
            amount = max(1, int(amount)); self.hp -= amount; res["dmg_taken"] += amount
            if self.hp <= 0:
                res["deaths"] += 1; self.hp = p.max_hp; return True
            if self.hp <= thresh_hp:
                n = max(1, (p.max_hp - self.hp) // heal_amount)
                healed = min(p.max_hp - self.hp, n * heal_amount)
                self.hp += healed; res["food"] += n; res["healed"] += healed
            return False

        guard = 0
        while True:
            guard += 1
            if guard > 5_000_000: break
            dot_next = min((d[0] for d in dots), default=float("inf"))
            t = min(p_next, e_next, dot_next)
            if t >= self.T: t = self.T; break
            e = f["e"]
            if dot_next <= p_next and dot_next <= e_next:
                died = False
                for d in dots:
                    if d[0] <= t:
                        d[0] += d[3]; d[1] -= 1
                        if take_damage(max(1, math.floor(d[2] * (1 - f["p_res"])))): died = True; break
                dots = [] if died else [d for d in dots if d[1] > 0]
                if died:
                    stunned = 0; t_spawn = t + RESPAWN_MS; idx = 0; f = spawn(0, t_spawn)
                    p_next = t_spawn + p.interval; e_next = t_spawn + f["e"].interval
                continue
            if p_next <= e_next:
                # ---- player attack ----
                p_next += p.interval
                if stunned > 0:
                    stunned -= 1; continue
                res["player_attacks"] += 1
                if rng.random() < f["p_hit"]:
                    res["player_hits"] += 1
                    dmg = rng.randint(1, f["p_maxhit"])
                    dmg = math.floor(dmg * (1 - f["e_res"]))
                    if f["ward"] > 0:
                        dmg = math.floor(dmg * (1 - f["ward"] / e.max_ward)); f["ward"] -= 1
                    if e.armour and not f["armour_broken"]:
                        dmg -= e.armour
                        if dmg >= e.armour: f["armour_broken"] = True
                    dmg = max(1, dmg)
                    dealt = min(dmg, f["hp"]); f["hp"] -= dmg; res["dmg_dealt"] += dealt
                    for skill, rate in p.xp_rates.items(): res["xp"][skill] += dealt * rate
                    if f["hp"] <= 0:
                        res["kills"] += 1; res["fight_ms"] += t - f["start"]
                        if e.kill_xp_factor:
                            for skill, rate in p.xp_rates.items(): res["xp"][skill] += rate * e.kill_xp_factor
                        idx += 1
                        if idx % len(self.sequence) == 0: res["loops"] += 1
                        t_spawn = t + RESPAWN_MS
                        f = spawn(idx, t_spawn)
                        p_next = t_spawn + p.interval; e_next = t_spawn + f["e"].interval
                        dots = []
                continue
            # ---- enemy attack ----
            e_next += e.interval
            res["enemy_attacks"] += 1
            special = None
            roll = rng.random()
            if roll < e.special_total:
                acc = 0.0
                for ch, atk in e.specials:
                    acc += ch
                    if roll < acc: special = atk; break
                if special is None: special = e.specials[-1][1]
            died = False
            if special is None:
                if rng.random() < f["e_hit"]:
                    res["enemy_hits"] += 1
                    dmg = max(1, math.floor(rng.randint(1, e.max_hit) * (1 - f["p_res"])))
                    died = take_damage(dmg)
                    if e.lifesteal: f["hp"] = min(e.max_hp, f["hp"] + math.floor(dmg * e.lifesteal))
                    for ch, dot in e.onhit_dots:
                        if not died and rng.random() < ch:
                            dots.append([t + dot["ProcInterval"], dot["ProcCount"], max(1, math.floor(e.max_hit * dot["DamagePerProc"]["Formula"]["Data"]["Percent"])), dot["ProcInterval"]])
            else:
                landed = False
                for h in special["Hits"]:
                    for _ in range(h["Count"]):
                        if special["IsAvoidable"] and rng.random() >= f["e_hit"]: continue
                        landed = True; res["enemy_hits"] += 1
                        dmg = 0
                        for dm in h["Damage"]:
                            fo = dm["Formula"]; ty = short(fo["Type"]); pct = fo["Data"].get("Percent", 1)
                            if ty == "NormalDamage": dmg += rng.randint(1, e.max_hit) * pct
                            elif ty == "MaxHit": dmg += e.max_hit * pct
                            elif ty == "CurrentHitpoints": dmg += self.hp * pct
                            elif ty == "MaxHitpoints": dmg += p.max_hp * pct
                            else: dmg += e.max_hit * pct
                        dmg = max(1, math.floor(dmg * (1 - f["p_res"])))
                        if take_damage(dmg): died = True; break
                        if e.lifesteal: f["hp"] = min(e.max_hp, f["hp"] + math.floor(dmg * e.lifesteal))
                    if died: break
                if landed and not died:
                    for eff in special["OnHitEffects"]:
                        if eff.get("AppliesTo") != "Target" or rng.random() >= eff["Chance"]: continue
                        et = short(eff["Effect"]["Type"])
                        if et == "DamageOverTime":
                            dot = gd.dots[short(eff["Effect"]["Data"]["Effect"])]
                            dots.append([t + dot["ProcInterval"], dot["ProcCount"], max(1, math.floor(e.max_hit * dot["DamagePerProc"]["Formula"]["Data"]["Percent"])), dot["ProcInterval"]])
                        elif et == "Stun":
                            st = gd.stuns.get(short(eff["Effect"]["Data"]["Effect"]))
                            stunned += (st or {}).get("DefaultTurns", 1) or 1
            if e.eot_heal_pct and not died:
                f["hp"] = min(e.max_hp, f["hp"] + math.floor(f["hp"] * e.eot_heal_pct))
            if died:
                dots = []; stunned = 0
                t_spawn = t + RESPAWN_MS; idx = 0; f = spawn(0, t_spawn)
                p_next = t_spawn + p.interval; e_next = t_spawn + f["e"].interval
            if res["deaths"] >= 30 and res["kills"] == 0:
                break
        hours = max(t, 1) / 3600000.0
        return dict(name=self.name, hours=hours, kills_h=res["kills"] / hours, deaths_h=res["deaths"] / hours,
                    food_h=res["food"] / hours, healed_h=res["healed"] / hours, dmg_taken_h=res["dmg_taken"] / hours,
                    loops_h=res["loops"] / hours, attacks_h=res["player_attacks"] / hours,
                    xp_h={k: v / hours for k, v in res["xp"].items()},
                    p_hit=info["p_hit"], e_hit=info["e_hit"], p_maxhit=info["p_maxhit"], e_res=info["e_res"], p_res=info["p_res"],
                    avg_fight_s=(res["fight_ms"] / res["kills"] / 1000) if res["kills"] else None,
                    kills=res["kills"], deaths=res["deaths"])

# ----------------------------------------------------------------------------
# 5. Reporting
# ----------------------------------------------------------------------------
def fmt(v, d=1):
    return "-" if v is None else f"{v:,.{d}f}"

def build_targets(gd, args):
    targets = []
    seen = set()
    for a in gd.areas:
        if not a["Enemies"]: continue
        for eid in a["Enemies"]:
            e = short(eid)
            if e in seen or e not in gd.enemies: continue
            seen.add(e)
            targets.append(dict(kind="적", id=e, name=gd.enemies[e]["DisplayName"], area=a["DisplayName"], category=short(a["Category"]),
                                difficulty=short(a["Difficulty"]), darkness=a["Darkness"], seq=[Enemy(gd, gd.enemies[e])],
                                unlock=len(a["UnlockRequirements"])))
    for d in gd.dungeons:
        seq = []
        for g in d["Enemies"]:
            for _ in range(g["Count"]):
                seq.append(Enemy(gd, gd.enemies[short(g["Enemies"][0]["Enemy"])]))
        targets.append(dict(kind="던전", id=d["Id"], name=d["DisplayName"], area=d["DisplayName"], category="StandardDungeons",
                            difficulty=short(d["Difficulty"]), darkness=d["Darkness"], seq=seq, unlock=len(d["UnlockRequirements"])))
    if args.filter:
        pat = args.filter.lower()
        targets = [t for t in targets if pat in t["id"].lower() or pat in t["name"].lower() or pat in t["area"].lower()]
    return targets

COMBAT_SKILLS = ["Attack", "Strength", "Defence", "Ranged", "Magic"]

def player_res_vs(gd, player, en):
    base = player.protection / (en.power + player.protection) if en.power + player.protection > 0 else 0
    return min(0.7, base * gd.triangle_mods(player.style, en.style)[1])

# ----------------------------------------------------------------------------
# 6. Interactive app export (app.html = app_template.html + embedded data bundle)
# ----------------------------------------------------------------------------
DAMAGE_TYPES = ("NormalDamage", "MaxHit", "CurrentHitpoints", "MaxHitpoints")

def _name(x):
    return x["Singular"] if isinstance(x, dict) else x

def _req_levels(reqs):
    out = {}
    for r in reqs or []:
        if short(r["Type"]) == "Level":
            out[short(r["Data"]["Component"]["Entity"])] = r["Data"]["Level"]
    return out

def _bonus_texts(bon):
    out = []
    if not bon: return out
    for b in bon.get("Global", []) or []:
        out.append(f"{b.get('StatGroup')} {b.get('Value')}")
    for b in bon.get("Component", []) or []:
        st = b["Stat"]["Name"]; lc = b.get("LocalContext") or {}
        ctx = short(lc.get("CombatStat")) if lc.get("CombatStat") else ""
        out.append(f"{st}{'('+ctx+')' if ctx else ''} {b.get('Value')}")
    for b in bon.get("CombatEffect", []) or []:
        eff = b["Modifier"]["Effect"]; d = eff.get("Data") or {}
        trig = (b["Modifier"].get("Trigger") or {}).get("Type")
        out.append((short(d["Effect"]) if d.get("Effect") else short(eff["Type"])) + (" (" + short(trig) + ")" if trig else ""))
    return list(dict.fromkeys(out))

def export_attack(gd, atk):
    hits = []
    for h in atk["Hits"]:
        hits.append(dict(count=h["Count"], dmg=[dict(t=short(dm["Formula"]["Type"]) if short(dm["Formula"]["Type"]) in DAMAGE_TYPES else "MaxHit",
                                                    pct=dm["Formula"]["Data"].get("Percent", 1)) for dm in h["Damage"]]))
    onhit = []; unmodeled = [f"{atk['DisplayName']}({short(eff['Effect']['Type'])})" for eff in atk["PreHitEffects"]]
    for eff in atk["OnHitEffects"]:
        et = short(eff["Effect"]["Type"])
        if et == "DamageOverTime" and eff.get("AppliesTo") == "Target":
            dot = gd.dots[short(eff["Effect"]["Data"]["Effect"])]
            onhit.append(dict(kind="dot", ch=eff["Chance"], interval=dot["ProcInterval"], count=dot["ProcCount"],
                              pct=dot["DamagePerProc"]["Formula"]["Data"]["Percent"], name=dot["DisplayName"]))
        elif et == "Stun" and eff.get("AppliesTo") == "Target":
            st = gd.stuns.get(short(eff["Effect"]["Data"]["Effect"])) or {}
            onhit.append(dict(kind="stun", ch=eff["Chance"], turns=st.get("DefaultTurns", 1) or 1))
        else:
            unmodeled.append(f"{atk['DisplayName']}({et})")
    return dict(name=atk["DisplayName"], avoidable=atk["IsAvoidable"], hits=hits, onhit=onhit, unmodeled=sorted(set(unmodeled)))

def _drops(d):
    """Enemy Drops / Dungeon Rewards -> compact {fixed:[[item,min,max]], tables:[{ch,t:[[item,min,max,w]]}], gp:[min,max]|None}."""
    d = d or {}
    gp = [[c.get("MinQuantity", 0), c.get("MaxQuantity", 0)] for c in d.get("FixedCurrencies") or [] if short(c.get("Currency", "")) == "GoldPieces"]
    return dict(fixed=[[short(x["Item"]), x.get("MinQuantity", 1), x.get("MaxQuantity", 1)] for x in d.get("FixedItems") or []],
                tables=[dict(ch=t.get("Chance", 1), t=[[short(x["Item"]), x.get("MinQuantity", 1), x.get("MaxQuantity", 1), x.get("Weight", 1)] for x in t.get("Table") or []])
                        for t in d.get("ItemTables") or []],
                gp=gp[0] if gp else None)

def export_enemy(gd, en):
    e = Enemy(gd, en)
    specials = [dict(ch=ch, atk=export_attack(gd, atk)) for ch, atk in e.specials]
    return dict(name=e.name, levels=e.levels, stats=e.stats, pow=e.power, prot=e.protection, stance=e.stance, style=e.style,
                element=e.element, maxHp=e.max_hp, interval=e.interval, armour=e.armour, maxWard=e.max_ward, lifesteal=e.lifesteal,
                maxHit=e.max_hit, accuracy=e.accuracy, specials=specials, specialTotal=e.special_total, killXp=e.kill_xp_factor,
                cl=e.combat_level, eotHeal=e.eot_heal_pct, drops=_drops(en.get("Drops")),
                onhitDots=[dict(ch=ch, interval=d["ProcInterval"], count=d["ProcCount"], pct=d["DamagePerProc"]["Formula"]["Data"]["Percent"], name=d["DisplayName"]) for ch, d in e.onhit_dots],
                unmodeled=e.unmodeled)

def export_bundle(gd, save, save_path):
    items = {}
    for it in gd.items.values():
        cap = it["Capabilities"]; eq = cap.get("Equipment"); fd = cap.get("Food")
        if not eq and not fd: continue
        o = dict(n=_name(it["DisplayName"]))
        if eq:
            stats = {}
            for s in eq["Stats"]["Stats"]: stats[short(s["Stat"])] = stats.get(short(s["Stat"]), 0) + s["Value"]
            o.update(t=short(eq["Type"]), st=stats, pow=sum(p["Value"] for p in eq["Stats"]["PowerRatings"]),
                     prot=sum(p["Value"] for p in eq["Stats"]["ProtectionRatings"]), req=_req_levels(eq["Requirements"]),
                     occ=[short(s) for s in (eq["OccupiesSlots"] or [])], qty=bool(eq["CanEquipQuantity"]))
            if eq.get("AmmoType"): o["ammoType"] = short(eq["AmmoType"])
            light = 0; texts = []
            for b in (eq.get("Bonuses") or {}).get("Component", []) or []:
                if b["Stat"]["Name"] == "FlatLight": light += b["Value"]
            if light: o["light"] = light
            texts = [t for t in _bonus_texts(eq.get("Bonuses")) if not t.startswith("FlatLight")]
            if texts: o["bonus"] = texts
            if eq.get("Attacks"): o["bonus"] = o.get("bonus", []) + ["고유 특수공격"]
            w = cap.get("Weapon")
            if w:
                o["w"] = dict(type=short(w["Type"]), el=[short(x) for x in (w.get("Elements") or [])] or ["Neutral"],
                              ammo=short(w["RequiredAmmoType"]) if w.get("RequiredAmmoType") else None)
        if fd:
            o["food"] = fd["BaseHealing"]
            fb = (fd.get("Bonuses") or {}).get("Modifiers") if isinstance(fd.get("Bonuses"), dict) else None
            if fb:
                fl = sum(b["Value"] for b in fb.get("Component", []) if b["Stat"]["Name"] == "FlatLight")
                if fl: o["foodLight"] = fl
                texts = [t for t in _bonus_texts(fb) if not t.startswith("FlatLight")]
                if texts: o["bonus"] = o.get("bonus", []) + texts
        items[it["Id"]] = o
    slots = [dict(id=s["Id"], name=s["DisplayName"], fits=short(s["FitsType"])) for s in gd_objects(gd)["EquipmentSlot"]]
    stances = {}
    for sid, st in gd.stances.items():
        stances[sid] = dict(name=st["DisplayName"], style=short(st["CombatStyle"]), acc=short(st["AccuracyStat"]), eva=short(st["EvasionStat"]),
                            xp={short(g["Component"]["Entity"]): g["ExperiencePerDamage"] for g in st["ExperienceGain"]},
                            flatDef=sum(b["Value"] for b in st["Bonuses"]["Component"] if b["Stat"]["Name"] == "FlatCombatLevel"))
    styles = {}
    for sid, s in gd.styles.items():
        f = s["MaxHitFormula"]
        mh = dict(type=short(f["Type"]), levels=[[short(l["Level"]), l["Ratio"]] for l in f["Data"]["Levels"]])
        if short(f["Type"]) == "StrengthBonus": mh["sb"] = short(f["Data"]["StrengthBonusStat"])
        else: mh["M"] = short(f["Data"]["MaxHitStat"]); mh["D"] = short(f["Data"]["DamageBonusStat"])
        styles[sid] = dict(name=s["DisplayName"], accLv=[[short(l["Level"]), l["Ratio"]] for l in s["AccuracyRatingLevels"]],
                           evaLv=[[short(l["Level"]), l["Ratio"]] for l in s["EvasionLevels"]], mh=mh,
                           clr=[[short(r["Level"]), r["Ratio"]] for r in s["CombatLevelRatios"]])
    weapon_types = {k: dict(name=w["DisplayName"], stances=[short(s) for s in w["Stances"]]) for k, w in gd.weapon_types.items()}
    spells = []
    for sp in gd_objects(gd)["MagicSpell"]:
        mhit = sum(s["Value"] for s in sp["Stats"]["Stats"] if short(s["Stat"]) == "SpellMaxHit")
        spells.append(dict(id=sp["Id"], name=sp["DisplayName"], element=short(sp["Element"]) if sp.get("Element") else "Neutral",
                           maxHit=mhit, book=short(sp["Book"]), req=_req_levels(sp["UnlockRequirements"]),
                           runes=[[short(r["Item"]), r.get("Quantity", 1)] for r in sp.get("RuneCosts") or []]))
    sty = list(gd.styles)
    triangle = {f"{p}|{e}": list(gd.triangle_mods(p, e)) for p in sty for e in sty}
    elements = sorted({short(e["Id"]) for e in gd_objects(gd)["Element"]} | {"Neutral"})
    elemental = {f"{p}|{e}": gd.element_mod({p}, e) for p in elements for e in elements}
    enemies = {eid: export_enemy(gd, en) for eid, en in gd.enemies.items()}
    targets = []; seen = set()
    def req_text(reqs):
        out = []
        for r in reqs or []:
            if short(r["Type"]) == "Level": out.append(f"{short(r['Data']['Component']['Entity'])} {r['Data']['Level']}")
            else: out.append(short(r["Type"]))
        return out
    for a in gd.areas:
        if not a["Enemies"]: continue
        for eid in a["Enemies"]:
            e = short(eid)
            if e in seen or e not in gd.enemies: continue
            seen.add(e)
            targets.append(dict(kind="enemy", id=e, name=gd.enemies[e]["DisplayName"], area=a["DisplayName"], category=short(a["Category"]),
                                difficulty=short(a["Difficulty"]), darkness=a["Darkness"], seq=[e], unlock=req_text(a["UnlockRequirements"])))
    for d in gd.dungeons:
        seq = []
        for g in d["Enemies"]:
            seq += [short(g["Enemies"][0]["Enemy"])] * g["Count"]
        targets.append(dict(kind="dungeon", id=d["Id"], name=d["DisplayName"], area=d["DisplayName"], category="Dungeon",
                            difficulty=short(d["Difficulty"]), darkness=d["Darkness"], seq=seq, unlock=req_text(d["UnlockRequirements"]),
                            rewards=_drops(d.get("Rewards"))))
    levels = {k: level_from_xp(v) for k, v in save["xp"].items()}
    for k in ("Attack", "Strength", "Defence", "Ranged", "Magic", "Prayer"): levels.setdefault(k, 1)
    levels.setdefault("Hitpoints", 10)
    player = dict(name=save["name"], levels=levels, equipment={s: list(v) for s, v in save["equipment"].items()},
                  food=list(save["food"]) if save["food"] else None, stanceMap=save["stance_map"], currentHp=save["current_hp"],
                  bank={k: v for k, v in save["bank"].items() if k in items}, bankAll=save["bank"])
    return dict(generatedAt=time.strftime("%Y-%m-%d %H:%M"), version=VERSION, saveFile=os.path.basename(save_path), saveVersion=save["version"],
                player=player, slots=slots, items=items, stances=stances, styles=styles, weaponTypes=weapon_types, spells=spells,
                triangle=triangle, elemental=elemental, enemies=enemies, targets=targets, respawnMs=RESPAWN_MS, xpTable=XP_TABLE,
                profit=export_profit(gd, save))

# ----------------------------------------------------------------------------
# 7. Skilling / profitability export (수익성 계산기)
# ----------------------------------------------------------------------------
PROFIT_SKILLS = [  # (entity id, korean name, engine kind)
    ("Woodcutting", "벌목", "wc"), ("Mining", "채광", "mine"), ("Fishing", "낚시", "fish"), ("Firemaking", "불피우기", "fm"),
    ("Cooking", "요리", "cook"), ("Smithing", "제련", "art"), ("Fletching", "화살 제작", "art"), ("Crafting", "공예", "art"),
    ("Runecrafting", "룬 제작", "art"), ("Herblore", "약초학", "herb"), ("Thieving", "도둑질", "thief"), ("Beastcrafting", "야수 공예", "art"),
    ("Farming", "농사", "farm"), ("Ranching", "목축", "ranch"),
]
SKILLING_STAT_TYPES = {"WoodcuttingAction", "MiningAction", "FishingAction", "FiremakingAction", "CookingAction", "ArtisanAction",
                       "HerbloreAction", "ThievingAction", "Experience", "FiremakingBonfire", "ItemSale", "FishingBait",
                       "FarmingAction", "RanchingAction", "GrainMill"}
SKILLING_GLOBAL_GROUPS = {"GlobalPercentActionInterval", "GlobalFlatActionInterval", "GlobalPercentXpGained"}

def parse_skilling(raw):
    """Toolbelt / pets / shop purchases / mastery-guild tasks / wallet / bonfire from the decoded save."""
    out = dict(toolbelt={}, pets=[], shop={}, guild_tasks={}, gp=0, bonfire=None)
    def is_id(p): return raw[p + 1:p + 12] == b"MelvorBase:"
    for m in re.finditer(rb"\x08Toolbelt", raw):
        try:
            rr = Reader(raw, m.end()); rr.i32(); n = rr.i32()
            if n < 0 or n > 32: continue
            slots = {}
            for _ in range(n):
                if not is_id(rr.p): slots = None; break
                sid = short(rr.str()); rl = rr.i32(); end = rr.p + rl
                qty = rr.i32(); has = rr.u8(); item = short(rr.str()) if has else None
                rr.p = end
                if item: slots[sid] = [item, qty]
            if slots is not None: out["toolbelt"].update(slots)
        except Exception: pass
    for m in re.finditer(rb"\x04Pets", raw):
        try:
            rr = Reader(raw, m.end()); rr.i32(); n = rr.i32()
            if n < 0 or n > 64: continue
            for _ in range(n):
                if not is_id(rr.p): break
                pid = short(rr.str()); rl = rr.i32(); end = rr.p + rl
                if rl >= 1 and raw[rr.p] == 1 and pid not in out["pets"]: out["pets"].append(pid)
                rr.p = end
        except Exception: pass
    for m in re.finditer(rb"\x04Shop", raw):
        try:
            rr = Reader(raw, m.end()); ln = rr.i32(); end = rr.p + ln
            rr.p += 3; rr.i32(); rr.i32(); n = rr.i32()
            if n < 0 or n > 2000 or rr.p + 5 > end: continue
            shop = {}
            for _ in range(n):
                q = rr.i32()
                if not is_id(rr.p): shop = None; break
                shop[short(rr.str())] = q
            if shop: out["shop"] = shop; break
        except Exception: pass
    for m in re.finditer(rb"\x0cMasteryGuild", raw):
        try:
            rr = Reader(raw, m.end()); rr.i32()
            if rr.u8(): rr.str()
            n = rr.i32()
            if n < 0 or n > 2000: continue
            for _ in range(n):
                if not is_id(rr.p): break
                tid = short(rr.str()); rl = rr.i32(); end = rr.p + rl
                gdone = None
                if rr.u8():
                    rr.str(); gl = rr.i32(); g2 = rr.p + gl
                    rr.f64(); gdone = bool(rr.u8()); rr.p = g2
                trig = bool(rr.u8()) if rr.p < end else None
                out["guild_tasks"][tid] = (gdone, trig)
                rr.p = end
        except Exception: pass
    i = raw.find(b"\x06Wallet")
    if i >= 0:
        try:
            rr = Reader(raw, i + 7); rr.i32(); n = rr.i32()
            for _ in range(min(n, 8)):
                q = rr.i64(); cur = short(rr.str())
                if cur == "GoldPieces": out["gp"] = q
        except Exception: pass
    i = raw.find(b"\x07Bonfire")
    if i >= 0:
        try:
            rr = Reader(raw, i + 8); ln = rr.i32(); end = rr.p + ln
            k = raw.find(b"MelvorBase:", rr.p, end)
            if k > 0:
                rr = Reader(raw, k - 1); bid = short(rr.str()); out["bonfire"] = dict(id=bid, active=bool(rr.u8()))
        except Exception: pass
    return out

def parse_astrology(raw, gd):
    """Per-constellation knowledge + unlocked minor/major nodes. Each constellation is stored as
    <id string><i32 region length>[<f64 knowledge><i32 n><n node ids><i32 m><m node ids>]; the id string also
    appears elsewhere in the save, so every occurrence is tried and the one that parses exactly is kept."""
    out = {}
    for c in gd_objects(gd)["AstrologyConstellation"]:
        key = ("MelvorBase:" + c["Id"]).encode(); minors = set(c["MinorNodes"]); majors = set(c["MajorNodes"])
        for mm in re.finditer(re.escape(bytes([len(key)]) + key), raw):
            try:
                rr = Reader(raw, mm.end()); ln = rr.i32(); end = rr.p + ln
                if ln < 16 or ln > 4000: continue
                kn = rr.f64(); n = rr.i32()
                if n < 0 or n > len(minors): continue
                mi = []
                for _ in range(n):
                    sid = rr.str()
                    if sid not in minors: raise ValueError(sid)
                    mi.append(short(sid))
                n2 = rr.i32()
                if n2 < 0 or n2 > len(majors): continue
                ma = []
                for _ in range(n2):
                    sid = rr.str()
                    if sid not in majors: raise ValueError(sid)
                    ma.append(short(sid))
                if rr.p != end: continue
                out[c["Id"]] = dict(knowledge=kn, minor=mi, major=ma); break
            except Exception:
                pass
    return out

def _req_text(reqs):
    out = []
    for r in reqs or []:
        t = short(r["Type"]); d = r.get("Data") or {}
        if t == "Level": out.append(f"{short(d['Component']['Entity'])} Lv {d['Level']}")
        elif t == "MasteryGuildRank": out.append(f"길드 {short(d['Rank'])}")
        elif t == "ShopPurchase": out.append(f"상점 {short(d.get('Purchase') or d.get('ShopPurchase') or '?')}")
        elif t == "ToolbeltItemEquipped": out.append(f"툴벨트 {short(d.get('Item'))}")
        elif t == "ItemStatistic": out.append(f"{short(d.get('Statistic'))} {short(d.get('Item'))} ×{d.get('Value')}")
        elif t == "HuntingAnimalStatistic": out.append(f"{short(d.get('Statistic'))} {short(d.get('Animal'))} ×{d.get('Value')}")
        elif t == "AgilityTechniqueLevel": out.append(f"Agility 기술 {short(d.get('Technique'))} Lv {d.get('Level', '?')}")
        elif t == "AstrologyMajorNodeUnlocked": out.append(f"점성술 {short(d.get('MajorNode'))}")
        else: out.append(t)
    return out

COMBAT_STAT_TYPES = {"Character", "CombatFood", "Experience", "AmmoConsumption", "MagicSpell", "Prayer", "CombatAction", "CombatLoot", "SlayerTasks"}

def _bon_list(bon, types=None):
    """Normalize a Bonuses object into modifier entries (skilling stat types by default, or `types`)."""
    out = []
    if not bon: return out
    types = types or SKILLING_STAT_TYPES
    if isinstance(bon, dict) and isinstance(bon.get("Modifiers"), dict): bon = bon["Modifiers"]
    comps = bon
    if isinstance(bon, dict):
        for g in bon.get("Global") or []:
            if g.get("StatGroup") in SKILLING_GLOBAL_GROUPS: out.append(dict(g=g["StatGroup"], v=g["Value"]))
        comps = bon.get("Component") or []
    for b in comps or []:
        if not isinstance(b, dict) or "Stat" not in b: continue
        t = short(b["Stat"]["StatsType"])
        if t not in types: continue
        lc = b.get("LocalContext") or {}
        e = dict(t=t, s=b["Stat"]["Name"], v=b["Value"])
        comp = lc.get("Component")
        if comp: e["sk"] = short(comp["Entity"])
        for k, kk in (("Category", "cat"), ("Subcategory", "sub"), ("Recipe", "rec"), ("Item", "item"), ("Location", "loc"),
                      ("RecipeType", "rt"), ("Currency", "cur"), ("Animal", "rec"), ("Plot", "plot"), ("CombatStat", "cs"),
                      ("CombatStyle", "style"), ("CombatLevel", "clv"), ("Effect", "eff"), ("Course", "course"), ("Element", "el"),
                      ("AmmoType", "ammo"), ("SlotType", "slot"), ("SlotCategory", "scat"), ("Prayer", "prayer"), ("Event", "event")):
            if lc.get(k) and not str(lc[k]).startswith("Placeholder:"): e[kk] = short(lc[k])
        if b.get("FromContext"): e["from"] = 1
        if b.get("Condition"): e["cond"] = short(b["Condition"]["Type"])
        sc = b.get("Scaling")
        if sc and short(sc.get("Type")) == "Level" and (sc.get("Data") or {}).get("Experience"):
            e["scale"] = short(sc["Data"]["Experience"]["Entity"])  # value is per level of that skill
        elif sc: e["cond"] = "Scaling:" + short(sc.get("Type", "?"))
        out.append(e)
    return out

def _iq(x):  # ItemQuantity / ItemQuantityChance -> compact
    d = dict(item=short(x["Item"]), qty=x.get("Quantity", 1))
    if "Chance" in x: d["ch"] = x["Chance"]
    if "MinQuantity" in x: d["min"] = x["MinQuantity"]; d["max"] = x["MaxQuantity"]; d.pop("qty", None)
    if "Weight" in x: d["w"] = x["Weight"]
    return d

def _task_done(t, st, levels, pets):
    goal_ok = True
    if t.get("Goal"):
        if not st or st[0] is None: return False
        goal_ok = st[0]
    cond_ok = True
    cg = t.get("ConditionGoal")
    if cg:
        ct = short(cg["Type"]); d = cg["Data"]
        if ct == "Level": cond_ok = levels.get(short(d["Component"]["Entity"]), 1) >= d["Level"]
        elif ct == "PetUnlocked": cond_ok = short(d.get("Pet", "")) in pets
        else: cond_ok = False
    trig_ok = True
    if t.get("TriggerGoal"): trig_ok = bool(st and st[1])
    return goal_ok and cond_ok and trig_ok

def export_profit(gd, save):
    O = gd_objects(gd); EC = gd.raw["EntityConfig"]
    levels = {k: level_from_xp(v) for k, v in save["xp"].items()}
    # --- items (all) with sell / shop buy price / toolbelt / equipment skilling bonuses
    # only purchases registered in the Shop entity config are actually sold; the data also defines
    # orphans (GrainStarterPack, Cowhide, tree seeds, old tools...) that never appear in the game
    _reg = {short(x["Id"] if isinstance(x, dict) else x) for x in ((EC.get("MelvorBase:Shop") or {}).get("Purchases") or [])}
    shop_purchases = [s for s in O["ShopPurchase"] if not _reg or s["Id"] in _reg]
    buy = {}
    for s in shop_purchases:
        p = s["Provides"]["Items"]; c = s["Costs"]
        if len(p) == 1 and not c["Items"] and len(c["Currencies"]) == 1 and short(c["Currencies"][0]["Currency"]) == "GoldPieces":
            it = short(p[0]["Item"]); price = c["Currencies"][0]["Quantity"] / p[0]["Quantity"]
            if it not in buy or price < buy[it][0]: buy[it] = (price, _req_text(s["Requirements"]))
    items = {}
    for it in gd.items.values():
        sf = it.get("SellsFor") or {}
        o = dict(n=_name(it["DisplayName"]), sell=sf.get("Quantity", 0) if short(sf.get("Currency", "")) == "GoldPieces" else 0)
        if it["Id"] in buy:
            o["buy"] = buy[it["Id"]][0]
            if buy[it["Id"]][1]: o["buyReq"] = buy[it["Id"]][1]
        cap = it["Capabilities"] or {}
        tb = cap.get("Toolbelt")
        if tb:
            o["tb"] = dict(slot=short(tb["FitsInSlot"]), bon=_bon_list(tb.get("Bonuses")), qty=bool(tb.get("CanEquipQuantity")),
                           cons=bool(tb.get("ConsumesOn")), req=_req_levels(tb.get("Requirements")))
        eq = cap.get("Equipment")
        if eq:
            eb = _bon_list(eq.get("Bonuses"))
            if eb: o["eq"] = eb
        if it.get("Description"): o["d"] = re.sub(r"\[.*?\]", "", it["Description"])[:160]
        items[it["Id"]] = o
    # --- category display names
    cat_names = {}
    for key in ("RecipeCategory", "RecipeSubcategory", "WoodcuttingRecipeCategory", "MiningRecipeCategory", "FishingLocation",
                "ThievingLocation", "ThievingRecipeType", "HerblorePotionGroup", "FarmingCategory", "FarmingMillCategory", "RanchingCategory"):
        for c in O.get(key, []): cat_names[c["Id"]] = c["DisplayName"]
    # --- skills
    tslots = {s["Id"]: s for s in O["ToolbeltSlot"]}
    ranks = {r["Id"]: r for r in O["MasteryGuildRank"]}
    gbon = {b["Id"]: b for b in O["MasteryGuildBonus"]}
    gcat = {c["Id"]: c for c in O["MasteryGuildCategory"]}
    gtask = {t["Id"]: t for t in O["MasteryGuildTask"]}
    pets = {p["Id"]: p for p in O["Pet"]}
    skills = []; slot2skill = {}
    for sid, ko, kind in PROFIT_SKILLS:
        ec = EC["MelvorBase:" + sid]
        slots = []
        for e in sorted(ec["ToolbeltSlots"], key=lambda x: x["Priority"]):
            s = tslots[short(e["Id"])]; slots.append(dict(id=s["Id"], name=s["DisplayName"], type=short(s["FitsType"])))
            slot2skill[s["Id"]] = sid
        rk = sorted((ranks[short(e["Id"])] for e in ec["MasteryGuildRanks"]), key=lambda r: r["PointPercentRequired"])
        rbon = []
        for e in ec["MasteryGuildBonuses"]:
            b = gbon[short(e["Id"])]
            req_rank = next((short(r["Data"]["Rank"]) for r in b["Requirements"] if short(r["Type"]) == "MasteryGuildRank"), None)
            rbon.append(dict(rank=req_rank, name=b["DisplayName"], bon=_bon_list((b.get("Rewards") or {}).get("Bonuses"))))
        tasks = [gtask[short(e["Id"])] for e in ec["MasteryGuildTasks"] if short(e["Id"]) in gtask]
        total = sum(gcat[short(t["Category"])]["BasePoints"] for t in tasks)
        pts = sum(gcat[short(t["Category"])]["BasePoints"] for t in tasks if _task_done(t, save["guild_tasks"].get(t["Id"]), levels, save["pets"]))
        rank = rk[0]["Id"]
        for r in rk:
            if total and pts >= math.ceil(total * r["PointPercentRequired"]): rank = r["Id"]
        pet = pets.get(short(ec["Pets"][0]["Id"])) if ec.get("Pets") else None
        skills.append(dict(id=sid, name=ko, kind=kind, slots=slots,
                           ranks=[dict(id=r["Id"], name=r["DisplayName"], pct=r["PointPercentRequired"]) for r in rk], rankBon=rbon,
                           pet=dict(id=pet["Id"], name=pet["DisplayName"], bon=_bon_list(pet.get("Bonuses"))) if pet else None,
                           guild=dict(pts=pts, total=total, rank=rank), lvl=levels.get(sid, 1)))
    # --- recipes
    def base(r, sid, kind, cat_key="Category"):
        # recipe Ids repeat across skills (Topaz vein vs Topaz cutting, Treant Remains log vs firemaking...), so the
        # app keys recipes by <skill>/<Id>; `gid` keeps the game Id for bonus LocalContext matching
        d = dict(id=sid + "/" + r["Id"], gid=r["Id"], sk=sid, kind=kind, name=r["DisplayName"], xp=r.get("BaseExperience", 0))
        lv = _req_levels(r.get("Requirements"))
        d["lvl"] = lv.get(sid, r.get("Level", 1)); d["reqLv"] = lv
        if r.get(cat_key): d["cat"] = short(r[cat_key]); d["catName"] = cat_names.get(d["cat"], d["cat"])
        if r.get("Subcategory"): d["sub"] = short(r["Subcategory"])
        oth = _req_text([q for q in (r.get("Requirements") or []) if short(q["Type"]) != "Level"])
        if oth: d["reqOther"] = oth
        return d
    recs = []
    for r in O["WoodcuttingRecipe"]:
        d = base(r, "Woodcutting", "wc"); d.update(iv=r["BaseInterval"], hp=r["BaseMaxHealth"], prod=_iq(r["Product"]),
                                                     hit=[_iq(x) for x in r.get("RandomProductsPerHit") or []], cut=[_iq(x) for x in r.get("RandomProductsPerCut") or []])
        recs.append(d)
    for r in O["MiningRecipe"]:
        d = base(r, "Mining", "mine"); d.update(iv=r["BaseInterval"], ch=r["BaseProductChance"], prod=_iq(r["Product"]),
                                                 hit=[_iq(x) for x in r.get("RandomProductsPerHit") or []])
        if r.get("BarItem"): d["bar"] = short(r["BarItem"])
        recs.append(d)
    for r in O["FishingRecipe"]:
        d = base(r, "Fishing", "fish", "Location"); d.update(ivMin=r["BaseMinInterval"], ivMax=r["BaseMaxInterval"], fishCh=r["FishChance"],
                                                           junk=short(r["JunkItem"]) if r.get("JunkItem") else None,
                                                           prods=[_iq(x) for x in r["RandomProducts"]], special=[_iq(x) for x in r.get("SpecialProducts") or []])
        recs.append(d)
    for r in O["FiremakingRecipe"]:
        d = base(r, "Firemaking", "fm"); d.update(iv=r["BaseInterval"], ing=[_iq(x) for x in r["Ingredients"]["Items"]],
                                                   prods=[_iq(x) for x in r["Products"]])
        if r.get("CurrencyReward"): d["cur"] = [short(r["CurrencyReward"]["Currency"]), r["CurrencyReward"]["Quantity"]]
        recs.append(d)
    for r in O["CookingRecipe"]:
        d = base(r, "Cooking", "cook"); d.update(iv=r["BaseInterval"], diff=r["Difficulty"], ing=[_iq(x) for x in r["Ingredients"]["Items"]],
                                                  prods=[_iq(x) for x in r["Products"]])
        recs.append(d)
    art_skill_by_cat = {"CombinationRunes": "Runecrafting"}
    for r in O["ArtisanRecipe"]:
        lv = _req_levels(r.get("Requirements")); sid = next((k for k in lv if k in {s[0] for s in PROFIT_SKILLS}), None) or art_skill_by_cat.get(short(r["Category"]))
        if not sid: continue
        d = base(r, sid, "art"); d.update(iv=r["BaseInterval"], steps=r.get("Steps") or 1, ing=[_iq(x) for x in r["Ingredients"]["Items"]],
                                           prods=[_iq(x) for x in r["Products"]])
        recs.append(d)
    for r in O["HerbloreRecipe"]:
        d = base(r, "Herblore", "herb"); d.update(ivP=r["BasePreparingInterval"], ivH=r["BaseHeatingInterval"], ivS=r["BaseStirringInterval"],
                                                   ivB=r["BaseBottlingInterval"], ing=[_iq(x) for x in r["Ingredients"]["Items"]],
                                                   prods=[_iq(x) for x in r["Products"]])
        if r.get("PotionGroup"): d["sub"] = short(r["PotionGroup"]); d["subName"] = cat_names.get(d["sub"], d["sub"])
        recs.append(d)
    for r in O["ThievingRecipe"]:
        d = base(r, "Thieving", "thief"); cr = r.get("CurrencyReward") or {}
        d.update(iv=r["BaseInterval"], stages=r.get("Stages") or 1, dmg=r.get("Damage", 0), perc=r.get("Perception", 0),
                 rt=short(r["RecipeType"]) if r.get("RecipeType") else None,
                 curCh=r.get("BaseCurrencyLootChance", 0), cur=[cr.get("MinQuantity", 0), cr.get("MaxQuantity", 0)] if cr and short(cr.get("Currency", "")) == "GoldPieces" else None,
                 comCh=r.get("BaseCommonLootChance", 0), common=[_iq(x) for x in r.get("CommonDropTable") or []],
                 rareCh=r.get("BaseRareLootChance", 0), rare=[_iq(x) for x in r.get("RareDropTable") or []],
                 done=[_iq(x) for x in r.get("CompletionDropTable") or []])
        if r.get("AccessRequirements"): d["access"] = _req_text(r["AccessRequirements"])
        recs.append(d)
    # --- farming: one action = one planting cycle (plant -> grow -> harvest, plus regrows for orchards)
    fcats = {c["Id"]: c for c in O["FarmingCategory"]}
    for r in O["FarmingRecipe"]:
        if not r["Product"].get("Quantity"): continue  # flowers only provide bonuses while grown
        c = fcats[short(r["Category"])]
        d = base(r, "Farming", "farm")
        d.update(iv=r["BaseInterval"], regrows=r.get("Regrows") or 0, regrowIv=r.get("RegrowInterval") or 0, prod=_iq(r["Product"]),
                 ing=[_iq(x) for x in r["Ingredients"]["Items"]],
                 dis=(r.get("DiseaseValueAdjuster", 0) + c.get("DiseaseValueAdjuster", 0)) if c.get("AttractsDisease") else 0,
                 pest=(r.get("PestValueAdjuster", 0) + c.get("PestValueAdjuster", 0)) if c.get("AttractsPests") else 0,
                 canWater=bool(c.get("CanWater")), canCompost=bool(c.get("CanCompost")))
        recs.append(d)
    for r in O["GrainMillRecipe"]:
        d = base(r, "Farming", "mill"); d.update(iv=300000, ing=[_iq(x) for x in r["Ingredients"]["Items"]], prod=_iq(r["Product"]))
        recs.append(d)
    # --- ranching: one action = one animal for one hour (product tick = 1 h, food tick = 1 h, treats every 24 h)
    variants = {v["Id"]: v for v in O["RanchingAnimalVariant"]}
    def _vbon(v):
        pq = xq = pi = 0.0
        for b in v.get("SelfBonuses") or []:
            st = short(b["Stat"]["StatsType"]); nm = b["Stat"]["Name"]
            if st == "RanchingAction" and nm == "PercentProductQuantity": pq += b["Value"]
            elif st == "RanchingAction" and nm == "PercentProductInterval": pi += b["Value"]
            elif st == "Experience" and nm == "PercentXPGained": xq += b["Value"]
        return dict(name=v["DisplayName"], pq=pq, xq=xq, pi=pi)
    encs = [e for e in O["RanchingEnclosure"]]
    for a in O["RanchingAnimal"]:
        rr = dict(a); rr["DisplayName"] = a["DisplayName"]["Singular"] if isinstance(a["DisplayName"], dict) else a["DisplayName"]
        d = base(rr, "Ranching", "ranch")
        bv = variants[short(a["BaseVariant"])]
        d.update(cost=sum(c["Quantity"] for c in a["PurchaseCosts"]["Currencies"] if short(c["Currency"]) == "GoldPieces"),
                 costItems=[_iq(x) for x in a["PurchaseCosts"]["Items"]],
                 variantIv=a["BaseVariantInterval"], lifeIv=a["LifespanInterval"], prodIv=3600000, foodIv=3600000, treatIv=86400000,
                 prods=[_iq(x) for x in a["Products"]], eats=[_iq(x) for x in a["Eats"]],
                 treats=[dict(item=short(t["Item"]), qty=t.get("Quantity", 1), sat=t["Satisfaction"]) for t in a.get("Treats") or []],
                 pets=bool(a.get("RequiresPets")), pack=[[p["AnimalCount"], p["Satisfaction"]] for p in a.get("PackSatisfactionBonuses") or []],
                 child=_vbon(bv), variants=[dict(_vbon(variants[short(v["Variant"])]), w=v["Weight"]) for v in a.get("Variants") or []],
                 enc=[dict(id=e["Id"], name=e["DisplayName"], limit=e["AnimalLimit"], cost=[_iq(x) for x in e["Costs"]["Items"]],
                           req=_req_text(e.get("Requirements"))) for e in encs if ("MelvorBase:" + a["Id"]) in (e.get("Animals") or [])])
        recs.append(d)
    farming = dict(composts=[dict(item=it["Id"], bon=_bon_list((it["Capabilities"] or {}).get("Compost", {}).get("CompostModifierTemplate")))
                             for it in gd.items.values() if (it.get("Capabilities") or {}).get("Compost")],
                   water={c["Id"]: sum(b["Value"] for b in (c.get("WateringModifierTemplate") or []) if b["Stat"]["Name"] == "FlatDiseaseProtection")
                          for c in O["FarmingCategory"] if c.get("CanWater")})
    for d in recs:
        if d.get("sub") and "subName" not in d: d["subName"] = cat_names.get(d["sub"], d["sub"])
    # --- shop upgrades with skilling bonuses, bonfires
    shop = []
    for s in shop_purchases:
        bon = _bon_list((s.get("Provides") or {}).get("Bonuses"))
        if not bon: continue
        gp = sum(c["Quantity"] for c in s["Costs"]["Currencies"] if short(c["Currency"]) == "GoldPieces")
        shop.append(dict(id=s["Id"], name=s["DisplayName"], desc=re.sub(r"\[.*?\]", "", s.get("Description") or "")[:200], bon=bon, gp=gp,
                         limit=s.get("DefaultBuyLimit") or 1, req=_req_text(s["Requirements"]), sub=short(s["Subcategory"]) if s.get("Subcategory") else None))
    bonfires = [dict(id=b["Id"], name=b["DisplayName"], bon=_bon_list(b.get("Bonuses")), dur=b.get("MaxDuration"),
                     costs=[_iq(x) for x in ((b.get("Costs") or {}).get("Items") or [])]) for b in O["FiremakingBonfire"]]
    mining = dict(stone=[short(e["Id"]) for e in EC["MelvorBase:Mining"].get("StoneItems", [])],
                  essence=[short(e["Id"]) for e in EC["MelvorBase:Mining"].get("EssenceItems", [])])
    nodes_by = {n["Id"]: n for n in O["AstrologyNode"]}
    def _anode(nid, kind):
        n = nodes_by[short(nid)]
        return dict(id=n["Id"], name=n["DisplayName"], kind=kind, bon=_bon_list(n["Bonuses"]), cbon=_bon_list(n["Bonuses"], COMBAT_STAT_TYPES),
                    txt=[re.sub(r"\s+", " ", t) for t in _bonus_texts(n["Bonuses"])], desc=re.sub(r"\[.*?\]", "", n.get("Description") or ""))
    astro = [dict(id=c["Id"], name=c["DisplayName"], skills=[short(e) for e in c["Entities"]], perMajor=c["MinorNodesPerMajorNode"],
                  minor=[_anode(x, "minor") for x in c["MinorNodes"]], major=[_anode(x, "major") for x in c["MajorNodes"]],
                  req=_req_text(c.get("Requirements")) + _req_text(c.get("SecondaryRequirements")))
             for c in O["AstrologyConstellation"]]
    # thieving distractions: location-scoped bonuses that are active while their requirements are met (no toggle in game)
    dis = {d["Id"]: d for d in O["ThievingDistraction"]}
    def _dis_met(reqs):
        ok = True
        for q in reqs or []:
            t = short(q["Type"]); d = q.get("Data") or {}
            if t == "ShopPurchase": r_ = save["shop"].get(short(d.get("ShopPurchase") or d.get("Purchase") or ""), 0) >= d.get("Amount", 1)
            elif t == "Level": r_ = levels.get(short(d["Component"]["Entity"]), 1) >= d["Level"]
            elif t == "ToolbeltItemEquipped": r_ = short(d.get("Item")) in save["toolbelt"].values()
            else: return None  # item / hunting statistics and agility techniques are not read from the save
            if not r_: ok = False
        return ok
    distract = []
    for loc in O["ThievingLocation"]:
        if not loc.get("AvailableDistractions"): continue
        lst = []
        for did in loc["AvailableDistractions"]:
            d = dis[short(did)]; bon = _bon_list(d["Bonuses"])
            for e in bon: e["sk"] = "Thieving"; e["cat"] = loc["Id"]
            lst.append(dict(id=d["Id"], name=d["DisplayName"], bon=bon, req=_req_text(d["Requirements"]), met=_dis_met(d["Requirements"])))
        distract.append(dict(loc=loc["Id"], name=cat_names.get(loc["Id"], loc["DisplayName"]), items=lst))
    tb = {}
    for slot, v in save["toolbelt"].items():
        sk = slot2skill.get(slot)
        if sk: tb.setdefault(sk, {})[slot] = v
    bank_value = sum(q * items[k]["sell"] for k, q in save["bank"].items() if k in items)
    psave = dict(toolbelt=tb, pets=save["pets"], shop=save["shop"], bonfire=save["bonfire"], gp=save["gp"], bankValue=bank_value,
                 astro=save.get("astro") or {})
    # alternative reward modes (Sacrificial Anvil): per-recipe toggle in the game; the sim offers it per skill/category.
    # Per completion: one roll decides xp×mult / sale×mult (weights), every Step rolls the collectable weight;
    # products are converted to their SellsFor GP (×sale mult) instead of entering the bank.
    anvil = []
    mode_skill = {}
    for ent, cfg in EC.items():
        for m in (cfg.get("RewardModes") or []) if isinstance(cfg, dict) else []:
            mode_skill[short(m["Id"] if isinstance(m, dict) else m)] = short(ent)
    for m in O.get("SacrificialAnvilRewardMode", []):
        node = next((short(q["Data"]["MajorNode"]) for q in (m.get("UnlockRequirements") or []) if short(q["Type"]) == "AstrologyMajorNodeUnlocked"), None)
        anvil.append(dict(id=m["Id"], name=m["DisplayName"], sk=mode_skill.get(m["Id"], "Smithing"), xpW=m["BonusXpWeight"], xpMult=m["BonusXpMultiplier"],
                          saleW=m["BonusSaleValueWeight"], saleMult=m["BonusSaleValueMultiplier"], colW=m["CollectableWeight"],
                          collect=[dict(item=short(c["Item"]), min=c["MinQuantity"], max=c["MaxQuantity"], w=c.get("Weight", 1)) for c in m.get("Collectables") or []],
                          allow=[short(c) for c in m["AllowedCategories"]] if m.get("AllowedCategories") else None,
                          deny=[short(c) for c in m.get("DisallowedCategories") or []], req=_req_text(m.get("UnlockRequirements")), node=node))
    return dict(skills=skills, recipes=recs, items=items, shop=shop, bonfires=bonfires, mining=mining, herbBottles=10, farming=farming,
                astro=astro, distract=distract, anvil=anvil, save=psave)

def gd_objects(gd):
    return gd.raw["Objects"]

def write_app(gd, save, save_path):
    bundle = export_bundle(gd, save, save_path)
    tpl = open(res("app_template.html"), encoding="utf-8").read()
    js = json.dumps(bundle, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    pjs = open(res("profit.js"), encoding="utf-8").read().replace("</script", "<\\/script")
    pcss = open(res("profit.css"), encoding="utf-8").read()
    out = os.path.join(OUT_DIR, "app.html")
    html = tpl.replace("/*__BUNDLE__*/null", js).replace("/*__PROFIT_JS__*/", pjs).replace("/*__PROFIT_CSS__*/", pcss)
    open(out, "w", encoding="utf-8").write(html)
    return out, bundle


# ----------------------------------------------------------------------------
# Self-update (GitHub Releases)
VERSION = "0.3.3"
UPDATE_REPO = "tgYun783/melvor2-simulator"
RELEASES_URL = f"https://github.com/{UPDATE_REPO}/releases"
EXE_NAME = "Melvor2Simulator.exe"

def _ver_tuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", str(v))[:3]) or (0,)

def check_update(timeout=4):
    """Ask GitHub for the latest release: one plain GET, no personal data. Returns a dict for /api/update."""
    import urllib.request
    req = urllib.request.Request(f"https://api.github.com/repos/{UPDATE_REPO}/releases/latest",
                                 headers={"Accept": "application/vnd.github+json", "User-Agent": "Melvor2Simulator/" + VERSION})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        rel = json.load(r)
    tag = rel.get("tag_name") or ""
    asset = next((a for a in rel.get("assets", []) if a.get("name", "").lower().endswith(".zip") and "melvor2simulator" in a.get("name", "").lower()), None)
    return dict(current=VERSION, latest=tag.lstrip("v"), newer=_ver_tuple(tag) > _ver_tuple(VERSION),
                url=rel.get("html_url") or RELEASES_URL, notes=(rel.get("body") or "")[:4000], published=rel.get("published_at"),
                asset=dict(name=asset["name"], url=asset["browser_download_url"], size=asset.get("size", 0)) if asset else None,
                canApply=bool(FROZEN and asset and _writable(HERE)), frozen=FROZEN)

def apply_update(info):
    """Download the release zip and swap the running exe for the new one.
    Windows allows renaming (not overwriting) a running exe: exe -> exe.old, new -> exe. The caller then closes the
    server socket, starts the new exe (relaunch) and exits. The .old file and the update folder are removed by
    cleanup_update() on the next start."""
    import urllib.request, zipfile, subprocess
    if not FROZEN: raise RuntimeError("소스로 실행 중입니다. git pull 하거나 Release 에서 받으세요: " + info.get("url", RELEASES_URL))
    if not _writable(HERE): raise RuntimeError(f"{HERE} 에 쓰기 권한이 없습니다. Release 에서 zip 을 받아 직접 교체하세요: " + info.get("url", RELEASES_URL))
    a = info.get("asset")
    if not a: raise RuntimeError("Release 에 zip 파일이 없습니다.")
    if not a["url"].startswith(f"https://github.com/{UPDATE_REPO}/releases/download/"): raise RuntimeError("예상치 못한 다운로드 주소입니다: " + a["url"])
    work = os.path.join(OUT_DIR, "update"); shutil.rmtree(work, ignore_errors=True); os.makedirs(work)
    zpath = os.path.join(work, a["name"])
    req = urllib.request.Request(a["url"], headers={"User-Agent": "Melvor2Simulator/" + VERSION})
    with urllib.request.urlopen(req, timeout=120) as r, open(zpath, "wb") as fh:
        shutil.copyfileobj(r, fh)
    if a.get("size") and os.path.getsize(zpath) != a["size"]: raise RuntimeError("내려받은 파일 크기가 Release 정보와 다릅니다.")
    with zipfile.ZipFile(zpath) as zf:
        names = zf.namelist()
        if EXE_NAME not in names: raise RuntimeError("zip 안에 " + EXE_NAME + " 가 없습니다.")
        zf.extract(EXE_NAME, work)
        if "README.txt" in names:
            zf.extract("README.txt", work); shutil.copy2(os.path.join(work, "README.txt"), os.path.join(HERE, "README.txt"))
    exe = os.path.join(HERE, EXE_NAME); old = exe + ".old"; new = os.path.join(work, EXE_NAME)
    if os.path.exists(old): os.remove(old)
    os.rename(exe, old)
    try:
        shutil.move(new, exe)
    except Exception:
        os.rename(old, exe); raise
    return dict(ok=True, version=info["latest"], exe=exe)

def relaunch(exe):
    """Start the (new) exe in its own console window with the same arguments; the caller exits right after."""
    import subprocess
    logp = os.path.join(OUT_DIR, "update", "relaunch.log")
    def log(msg):
        try:
            with open(logp, "a", encoding="utf-8") as fh: fh.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        except OSError:
            pass
    # a frozen (PyInstaller onefile) process carries _PYI_* variables that tell a spawned bootloader it is the
    # already-unpacked child of this process; the new exe must start clean, so strip them
    env = {k: v for k, v in os.environ.items() if not k.startswith("_PYI") and k != "_MEIPASS2"}
    args = [exe] + sys.argv[1:]
    base = subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NEW_PROCESS_GROUP
    # the PyInstaller bootloader keeps this process in a kill-on-close job: a plain child would die with us, so break away
    try:
        p = subprocess.Popen(args, cwd=HERE, close_fds=True, env=env, creationflags=base | subprocess.CREATE_BREAKAWAY_FROM_JOB)
        log(f"breakaway popen ok pid={p.pid} args={args}")
        return "breakaway"
    except OSError as e:
        log(f"breakaway failed: {e!r}")
    # the job forbids breakaway: let WMI create the process outside of it
    q = lambda s: s.replace("'", "''")
    ps = (f"Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{{CommandLine='{q(subprocess.list2cmdline(args))}'; "
          f"CurrentDirectory='{q(HERE)}'}} | ConvertTo-Json -Compress")
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], env=env, timeout=60, capture_output=True, text=True,
                       creationflags=subprocess.CREATE_NO_WINDOW)
    log(f"wmi rc={r.returncode} out={r.stdout.strip()[:300]} err={r.stderr.strip()[:300]}")
    return "wmi"

def cleanup_update():
    try:
        old = os.path.join(HERE, EXE_NAME + ".old")
        if os.path.exists(old): os.remove(old)
        shutil.rmtree(os.path.join(OUT_DIR, "update"), ignore_errors=True)
    except OSError:
        pass

def serve(gd, save_path, port, open_browser):
    """Serve Melvor2Sim/ over HTTP and expose a tiny API so the app's "세이브 갱신"
    button can re-read the newest save and rebuild app.html without leaving the browser."""
    import http.server, threading, urllib.parse
    state = dict(save_path=save_path, generated=time.time(), update=None)
    lock = threading.Lock()

    def update_info(force=False):
        if force or state["update"] is None:
            try:
                state["update"] = check_update()
                if state["update"]["newer"]:
                    print(f"새 버전 v{state['update']['latest']} 이 있습니다 (현재 v{VERSION}). 앱 상단의 업데이트 버튼 또는 {state['update']['url']}", flush=True)
            except Exception as e:
                state["update"] = dict(current=VERSION, newer=False, error=str(e), frozen=FROZEN, url=RELEASES_URL)
        return state["update"]
    threading.Thread(target=update_info, daemon=True).start()

    def rebuild():
        with lock:
            sp = find_newest_save()
            save = parse_save(brotli_decode(open(sp, "rb").read()), gd)
            out, bundle = write_app(gd, save, sp)
            state.update(save_path=sp, generated=time.time())
            print(f"[{time.strftime('%H:%M:%S')}] 세이브 갱신: {os.path.basename(sp)}  캐릭터 {save['name']}", flush=True)
            return dict(ok=True, saveFile=os.path.basename(sp), name=save["name"], generatedAt=bundle["generatedAt"])

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=OUT_DIR, **k)
        def log_message(self, fmt, *a):
            pass
        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()
        def _json(self, obj, code=200):
            body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def do_GET(self):
            path = urllib.parse.urlparse(self.path).path
            if path == "/api/status":
                try:
                    sp = find_newest_save(); mt = os.path.getmtime(sp)
                    return self._json(dict(saveFile=os.path.basename(sp), saveMtime=mt, generated=state["generated"],
                                           stale=mt > state["generated"] + 1))
                except Exception as e:
                    return self._json(dict(error=str(e)), 500)
            if path == "/api/update":
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                return self._json(update_info(force=q.get("force", ["0"])[0] == "1"))
            if path in ("", "/"):
                self.path = "/app.html"
            return super().do_GET()
        def do_POST(self):
            path = urllib.parse.urlparse(self.path).path
            if path == "/api/refresh":
                try:
                    return self._json(rebuild())
                except Exception as e:
                    import traceback; traceback.print_exc()
                    return self._json(dict(ok=False, error=str(e)), 500)
            if path == "/api/update/apply":
                try:
                    info = update_info(force=True)
                    if not info.get("newer"): return self._json(dict(ok=False, error="이미 최신 버전입니다."), 400)
                    with lock:
                        print(f"[{time.strftime('%H:%M:%S')}] v{info['latest']} 내려받는 중...", flush=True)
                        res = apply_update(info)
                    print(f"[{time.strftime('%H:%M:%S')}] 교체 완료 — 다시 시작합니다.", flush=True)
                    def _restart():
                        # free the port first, then start the new exe with the same arguments, then leave
                        try:
                            httpd.shutdown(); httpd.server_close()
                        except Exception:
                            pass
                        try:
                            print("새 버전 시작:", relaunch(res["exe"]), flush=True)
                        except Exception as e:
                            print("새 버전을 자동으로 시작하지 못했습니다. 직접 실행해 주세요:", e, flush=True)
                            try:
                                with open(os.path.join(OUT_DIR, "update", "relaunch.log"), "a", encoding="utf-8") as fh: fh.write(f"relaunch error: {e!r}\n")
                            except OSError:
                                pass
                        time.sleep(3)  # give the new process a moment before this one (and its bootloader job) goes away
                        os._exit(0)
                    # handler threads are daemon threads and a Timer inherits that; a daemon thread would be killed as soon as
                    # the main thread leaves serve_forever after httpd.shutdown(), before it gets to relaunch()
                    t = threading.Timer(1.5, _restart); t.daemon = False; t.start()
                    return self._json(dict(ok=True, version=res["version"]))
                except Exception as e:
                    import traceback; traceback.print_exc()
                    return self._json(dict(ok=False, error=str(e)), 500)
            self.send_error(404)

    try:
        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError:
        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        print(f"포트 {port}가 사용 중이어서 다른 포트를 씁니다.")
    url = f"http://127.0.0.1:{httpd.server_address[1]}/app.html"
    print("인터랙티브 앱:", url, flush=True)
    print("서버 실행 중 — 이 창을 닫거나 Ctrl+C로 종료합니다. 앱의 '↺ 세이브 갱신' 버튼이 최신 세이브를 다시 읽습니다.", flush=True)
    if open_browser:
        import webbrowser; webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()

def main():
    ap = argparse.ArgumentParser(description="Melvor Idle 2 combat simulator")
    ap.add_argument("--cli", action="store_true", help="run the Python simulation and write report.html (default: build app.html)")
    ap.add_argument("--no-open", action="store_true", help="do not open app.html in the browser")
    ap.add_argument("--no-serve", action="store_true", help="only write app.html (open as file://; the save-refresh button then needs a rerun of this script)")
    ap.add_argument("--port", type=int, default=8765, help="local server port (default 8765)")
    ap.add_argument("--hours", type=float, default=1.0, help="simulated hours per target (default 1)")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--stance", help="override stance, e.g. Accurate / LongRange / Slash")
    ap.add_argument("--food", help="override food item id, e.g. Trout")
    ap.add_argument("--autoeat-threshold", type=float, default=0.25, help="auto-eat HP fraction (default 0.25)")
    ap.add_argument("--autoeat-efficiency", type=float, default=1.0, help="healing multiplier for auto-eat (default 1.0)")
    ap.add_argument("--light", type=int, default=0, help="player Light stat for dark areas")
    ap.add_argument("--filter", help="only targets whose id/name/area contains this text")
    ap.add_argument("--save", help="path to a .sav file (default: newest)")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--no-html", action="store_true")
    args = ap.parse_args()
    print(f"Melvor2Simulator v{VERSION}" + ("" if OUT_DIR == HERE else f"  (출력 폴더: {OUT_DIR})"), flush=True)
    if FROZEN: cleanup_update()

    gd = GameData(extract_game_data())
    save_path = args.save or find_newest_save()
    save = parse_save(brotli_decode(open(save_path, "rb").read()), gd)
    player = Player(gd, save, args)

    print(f"\n세이브: {os.path.basename(save_path)}  캐릭터: {save['name']}  (저장 포맷 v{save['version']})")
    if not args.cli:
        out, bundle = write_app(gd, save, save_path)
        print(f"장비 {sum(1 for v in save['equipment'].values() if v[1] != -1)}칸, 아이템 {len(bundle['items'])}개, 적 {len(bundle['enemies'])}종, 대상 {len(bundle['targets'])}개를 내장했습니다.")
        if args.no_serve:
            print("인터랙티브 앱:", out)
            if not args.no_open:
                import webbrowser; webbrowser.open("file:///" + out.replace("\\", "/"))
            return
        serve(gd, save_path, args.port, not args.no_open)
        return
    print("레벨:", ", ".join(f"{k} {v}" for k, v in sorted(player.levels.items()) if k in COMBAT_SKILLS + ['Hitpoints', 'Prayer']))
    print(f"전투 레벨 {player.combat_level}  스타일 {player.style}/{player.stance}  무기 종류 {player.weapon_type}  공격 간격 {player.interval}ms")
    print("장비:", ", ".join(f"{s}:{i}{' x'+str(q) if q>1 else ''}" for s, (i, q) in player.equipment.items() if q != -1))
    print(f"최대 HP {player.max_hp}  최대 타격 {player.max_hit_base}  명중 레이팅 {player.accuracy}  Power {player.power}  Protection {player.protection}")
    print(f"음식: {player.food} (회복 {player.food_heal}) 보유 {player.food_qty}개   자동식사 임계 {player.ae_threshold:.0%}, 효율 {player.ae_eff:.0%}")
    if player.unmodeled: print("미반영 장비 효과:", ", ".join(player.unmodeled))

    targets = build_targets(gd, args)
    print(f"\n{len(targets)}개 대상 시뮬레이션 (각 {args.hours}시간)...")
    rows = []; t0 = time.time()
    thresh_hp = round(player.max_hp * player.ae_threshold)
    for i, tg in enumerate(targets):
        r = Sim(gd, player, tg["seq"], args.hours, args.seed + i, darkness=tg["darkness"], name=tg["name"]).run()
        enemies = tg["seq"]
        burst_after = max(math.floor(en.max_burst() * (1 - player_res_vs(gd, player, en))) for en in enemies)
        safe = burst_after <= thresh_hp
        comb = sum(r["xp_h"].get(s, 0) for s in COMBAT_SKILLS)
        notes = sorted(set(sum((en.unmodeled for en in enemies), [])))
        rows.append(dict(kind=tg["kind"], name=tg["name"], id=tg["id"], area=tg["area"], difficulty=tg["difficulty"], darkness=tg["darkness"],
                         unlock=tg["unlock"], enemy_cl=max(en.combat_level for en in enemies), enemy_hp=sum(en.max_hp for en in enemies),
                         enemy_style="/".join(sorted({en.style for en in enemies})), enemy_maxhit=max(en.max_hit for en in enemies),
                         burst=burst_after, safe=safe, combat_xp_h=comb, hp_xp_h=r["xp_h"].get("Hitpoints", 0), xp_h=r["xp_h"],
                         kills_h=r["kills_h"], loops_h=r["loops_h"], food_h=r["food_h"], healed_h=r["healed_h"], dmg_taken_h=r["dmg_taken_h"],
                         deaths_h=r["deaths_h"], p_hit=r["p_hit"], e_hit=r["e_hit"], p_maxhit=r["p_maxhit"], e_res=r["e_res"], p_res=r["p_res"],
                         avg_fight_s=r["avg_fight_s"], xp_per_food=(comb / r["food_h"]) if r["food_h"] > 0 else None, notes=notes,
                         kills=r["kills"], deaths=r["deaths"]))
        if args.verbose:
            print(f"  {tg['name']:32s} kills/h {r['kills_h']:7.1f}  xp/h {comb:9.0f}  food/h {r['food_h']:6.1f}  deaths/h {r['deaths_h']:5.2f}  hit {r['p_hit']:.0%}/{r['e_hit']:.0%}")
    print(f"완료 ({time.time()-t0:.1f}s)")

    rows.sort(key=lambda r: -r["combat_xp_h"])
    print("\n== 전투 XP/시간 상위 (사망 0, 안전) ==")
    print(f"{'대상':34s}{'지역':22s}{'적CL':>5s}{'킬/h':>8s}{'전투XP/h':>10s}{'HP XP/h':>9s}{'음식/h':>8s}{'XP/음식':>9s}{'명중':>6s}{'피격':>6s}")
    shown = 0
    for r in rows:
        if r["deaths_h"] > 0 or not r["safe"]: continue
        print(f"{(r['kind']+' '+r['name'])[:33]:34s}{r['area'][:21]:22s}{r['enemy_cl']:5d}{r['kills_h']:8.1f}{r['combat_xp_h']:10.0f}{r['hp_xp_h']:9.0f}{r['food_h']:8.1f}{fmt(r['xp_per_food'],0):>9s}{r['p_hit']:6.0%}{r['e_hit']:6.0%}")
        shown += 1
        if shown >= 25: break
    print("\n== 위험/사망 발생 대상 (XP 상위 10) ==")
    for r in [x for x in rows if x["deaths_h"] > 0 or not x["safe"]][:10]:
        print(f"{(r['kind']+' '+r['name'])[:33]:34s} 사망/h {r['deaths_h']:5.2f}  최대피해 {r['burst']} vs 임계HP {thresh_hp}  XP/h {r['combat_xp_h']:.0f}")

    out_json = os.path.join(OUT_DIR, "results.json")
    json.dump(dict(player=dict(levels=player.levels, combat_level=player.combat_level, style=player.style, stance=player.stance,
                               equipment=player.equipment, max_hp=player.max_hp, max_hit=player.max_hit_base, accuracy=player.accuracy,
                               food=player.food, food_heal=player.food_heal, food_qty=player.food_qty),
                   rows=rows), open(out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("결과 JSON:", out_json)
    if not args.no_html:
        out_html = os.path.join(OUT_DIR, "report.html")
        write_html(out_html, player, save, rows, args)
        print("HTML 리포트:", out_html)

def write_html(path, player, save, rows, args):
    thresh = round(player.max_hp * player.ae_threshold)
    def td(v): return f"<td>{v}</td>"
    body = []
    for r in rows:
        cls = "dead" if r["deaths_h"] > 0 else ("risky" if not r["safe"] else "")
        xp_detail = ", ".join(f"{k} {v:,.0f}" for k, v in sorted(r["xp_h"].items()) if v > 0)
        body.append(
            f"<tr class='{cls}'>" + td(r["kind"]) + td(r["name"]) + td(r["area"]) + td(r["difficulty"] + (f" (암흑 {r['darkness']})" if r["darkness"] else ""))
            + td(r["enemy_cl"]) + td(r["enemy_style"]) + f"<td data-v='{r['kills_h']}'>{r['kills_h']:.1f}" + (f" (완주 {r['loops_h']:.1f})" if r["kind"] == "던전" else "") + "</td>"
            + f"<td data-v='{r['combat_xp_h']}' title='{xp_detail}'>{r['combat_xp_h']:,.0f}</td>" + f"<td data-v='{r['hp_xp_h']}'>{r['hp_xp_h']:,.0f}</td>"
            + f"<td data-v='{r['food_h']}'>{r['food_h']:.1f}</td>" + f"<td data-v='{r['xp_per_food'] or 0}'>{fmt(r['xp_per_food'],0)}</td>"
            + f"<td data-v='{r['dmg_taken_h']}'>{r['dmg_taken_h']:,.0f}</td>" + f"<td data-v='{r['p_hit']}'>{r['p_hit']:.0%}</td>" + f"<td data-v='{r['e_hit']}'>{r['e_hit']:.0%}</td>"
            + td(f"{r['enemy_maxhit']} / {r['burst']}") + f"<td data-v='{r['deaths_h']}'>{r['deaths_h']:.2f}</td>" + td("안전" if r["safe"] else "위험")
            + td(fmt(r["avg_fight_s"], 1)) + td("<br>".join(r["notes"]) if r["notes"] else "") + "</tr>")
    eq = ", ".join(f"{s}: {i}{' x'+str(q) if q>1 else ''}" for s, (i, q) in player.equipment.items() if q != -1)
    lv = ", ".join(f"{k} {v}" for k, v in sorted(player.levels.items()) if k in COMBAT_SKILLS + ["Hitpoints", "Prayer"])
    html = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>Melvor Idle 2 전투 시뮬레이션</title>
<style>
body{{font-family:Segoe UI,Malgun Gothic,sans-serif;margin:20px;background:#1b1d22;color:#e6e6e6}}
h1{{font-size:20px}} .card{{background:#262a31;border-radius:8px;padding:12px 16px;margin-bottom:14px;line-height:1.6}}
table{{border-collapse:collapse;width:100%;font-size:13px}} th,td{{border-bottom:1px solid #3a3f48;padding:5px 7px;text-align:right;white-space:nowrap}}
th{{cursor:pointer;background:#30353e;position:sticky;top:0}} td:nth-child(-n+6),th:nth-child(-n+6),td:last-child{{text-align:left}}
td:last-child{{white-space:normal;font-size:11px;color:#aab}} tr.dead{{color:#f08080}} tr.risky{{color:#f0c060}}
tr:hover{{background:#2e333c}} .note{{font-size:12px;color:#aab}}
</style></head><body>
<h1>Melvor Idle 2 전투 시뮬레이션 — {save['name']}</h1>
<div class="card"><b>현재 상태</b><br>레벨: {lv} → 전투 레벨 <b>{player.combat_level}</b><br>
스타일: {player.style} / 스탠스 <b>{player.stance}</b> (무기 종류 {player.weapon_type}, 공격 간격 {player.interval}ms)<br>
장비: {eq}<br>최대 HP {player.max_hp}, 최대 타격 {player.max_hit_base}, 명중 레이팅 {player.accuracy}, Power {player.power}, Protection {player.protection}<br>
음식: <b>{player.food}</b> (회복 {player.food_heal}, 보유 {player.food_qty}개) · 자동식사 임계 {player.ae_threshold:.0%} = HP {thresh} 이하, 효율 {player.ae_eff:.0%}<br>
<span class="note">대상별 {args.hours}시간 시뮬레이션. 열 제목을 클릭하면 정렬됩니다. 빨간 행 = 사망 발생, 노란 행 = 한 번의 공격으로 임계 HP를 넘길 수 있어 위험.</span></div>
<table id="t"><thead><tr>
<th>종류</th><th>대상</th><th>지역</th><th>난이도</th><th>적 CL</th><th>적 스타일</th><th>킬/시간 (던전 완주/시간)</th><th>전투 XP/시간</th><th>HP XP/시간</th><th>음식/시간</th><th>XP/음식 1개</th><th>받은 피해/시간</th><th>내 명중</th><th>적 명중</th><th>적 최대타/최대폭발</th><th>사망/시간</th><th>안전</th><th>평균 전투(초)</th><th>미반영 메커니즘</th>
</tr></thead><tbody>{''.join(body)}</tbody></table>
<div class="card"><b>모델 (게임 DLL 디컴파일 코드와 대조 검증됨)</b><br>
• 명중/회피 = floor((레벨+9)×(보너스+64)), 명중률 = 1−회피/(2×명중) 또는 명중/(2×회피) — CharacterStats / TargetCharacterStats<br>
• 최대 타격(근접/원거리) = floor(22 + 레벨 + (레벨+17)×힘보너스/64), 마법 = floor(주문최대타×(1+피해보너스)×(1+(레벨+1)/200)), 최소 타격 1, 균등 분포. HP = HP 레벨×10<br>
• 저항 = clamp(Protection/(상대 Power+Protection), 0~70%)×(1+삼각형 ±15%), 피해 적용 순서: 저항 → Ward(×(1−남은/최대), 명중마다 1 감소) → Armour 차감(차감 후 피해 ≥ Armour면 파괴) → 최소 1<br>
• 전투 삼각형 ±10% 최대타, 원소 상성 ±15% 최대타 (플레이어에게만 적용)<br>
• 자동식사 기본값: 임계 25%(round), 한도 100%, 효율 100%. 임계 이하가 되면 floor((최대HP−현재HP)/회복량), 최소 1개를 먹음. 상점 Auto Eat II/III는 각 +5%p (세이브에 없음). HP 자연회복은 게임에 없음<br>
• 전투 XP = 실제 준 체력 피해 × 스탠스별 XP 배율 + 처치 시 배율×(4×Armour + 50×Ward). 적 공격 선택: 특수공격 확률 합이 1 미만이면 나머지가 일반 공격<br>
• 스폰 대기 3초(BaseSpawnInterval) 후 양쪽 공격 타이머가 동시에 시작. 던전 내 전환도 동일<br>
• 반영된 적 효과: 특수공격(확률·연타·DOT·기절), Rejuvenate, Lifesteal, 타격 시 DOT. 그 외 패시브/효과(TurnCounting 버프, 회피 확률, 면역 등)는 '미반영' 열에 표시<br>
• 미반영: 기도, 물약, 치명타(기본 0%), 암흑 지역의 Light 장비, 사망 후 전투 중단(시뮬레이션은 계속 진행, 사망/시간으로 표시)</div>
<script>
document.querySelectorAll('#t th').forEach((th,i)=>{{th.onclick=()=>{{const tb=document.querySelector('#t tbody');const rows=[...tb.rows];
const asc=th.dataset.asc!=='1';th.dataset.asc=asc?'1':'0';
rows.sort((a,b)=>{{const x=a.cells[i],y=b.cells[i];const xv=x.dataset.v!==undefined?+x.dataset.v:x.textContent,yv=y.dataset.v!==undefined?+y.dataset.v:y.textContent;
return (typeof xv==='number'?(xv-yv):String(xv).localeCompare(String(yv)))*(asc?1:-1);}});rows.forEach(r=>tb.appendChild(r));}}}});
</script></body></html>"""
    open(path, "w", encoding="utf-8").write(html)

if __name__ == "__main__":
    if not os.path.exists(EXE):
        raise SystemExit("Melvor2.exe를 찾을 수 없습니다. 이 프로그램을 게임 폴더 안(예: mods\\melvor2Simulator)에 두거나 MELVOR2_DIR 환경변수를 설정하세요: " + GAME_DIR)
    try:
        main()
    except SystemExit as e:
        if FROZEN and e.code not in (None, 0):
            print(e.code, flush=True); input("\n엔터를 누르면 종료합니다...")
        raise
    except Exception:
        if FROZEN:
            import traceback; traceback.print_exc(); input("\n엔터를 누르면 종료합니다...")
        raise
