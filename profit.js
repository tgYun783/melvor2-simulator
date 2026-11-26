/* ===================================================================================
 * 수익성 계산기 (profit tab)
 * - 데이터: B.profit (melvor2_sim.py export_profit)
 * - 공식: 디컴파일한 *ActionStats / *ActionComponent 를 기대값으로 옮김
 * =================================================================================== */
(function () {
  if (!window.M2) return;
  var B = M2.B, LS = M2.LS, esc = M2.esc, ccfg = function () { return M2.cfg() || {}; };
  var PB = B.profit; if (!PB) return;
  var ITEMS = PB.items, RECIPES = PB.recipes, SKILLS = PB.skills;
  var SK = {}; SKILLS.forEach(function (s) { SK[s.id] = s; });
  var REC = {}; RECIPES.forEach(function (r) { REC[r.id] = r; });
  var H = 3600000; // ms per hour
  var KIND_KO = { wc: "벌목", mine: "채광", fish: "낚시", fm: "불피우기", cook: "요리", art: "제작", herb: "약초학", thief: "도둑질", farm: "농사", mill: "제분소", ranch: "목축" };
  var FARM = { compost: {}, water: (PB.farming || {}).water || {} }; ((PB.farming || {}).composts || []).forEach(function (c) { FARM.compost[c.item] = c; });
  var STAT_KO = {
    CompostPreservationChance: "퇴비 보존 확률", FlatDiseaseProtection: "병해 보호 +", FlatPestProtection: "해충 보호 +", FlatRegrows: "재수확 횟수 +",
    PercentBonusesWhileGrowing: "성장 중 보너스 %", FlatAutomationLevel: "자동화 레벨", FlatAutomationCost: "자동화 비용 +", PercentAutomationCost: "자동화 비용 %",
    FlatProductInterval: "산출 간격(고정)", PercentProductInterval: "산출 간격 %", FlatLifespanInterval: "수명(고정)", PercentLifespanInterval: "수명 %",
    FlatBaseVariantInterval: "성장 기간(고정)", PercentBaseVariantInterval: "성장 기간 %", FlatEatsQuantity: "먹이 소모 +", PercentEatsQuantity: "먹이 소모 %",
    FlatMaintenanceInterval: "유지보수 간격(고정)", PercentMaintenanceInterval: "유지보수 간격 %", FlatFoodConsumptionterval: "급식 간격(고정)", PercentFoodConsumptionInterval: "급식 간격 %",
    FoodPreservationChance: "먹이 보존 확률", EnclosureMaintenanceSkipChance: "유지보수 건너뛰기", FlatHappiness: "행복도 +",
    FlatInterval: "행동 간격(고정)", PercentInterval: "행동 간격", DoublingChance: "2배 획득 확률", PreservationChance: "재료 보존 확률",
    FlatProductQuantity: "산출 수량 +", PercentProductQuantity: "산출 수량 %", PercentIngredientCost: "재료 소모량", SkipStepChance: "단계 건너뛰기",
    FlatSteps: "단계 수", FlatMaxHealth: "나무 체력", PercentMaxHealth: "나무 체력 %", DoubleDamageChance: "2배 피해 확률", InstantCutChance: "즉시 벌목 확률",
    WeakSpotChance: "약점 확률", FlatOnHitItemChance: "타격당 아이템 확률", PercentOnHitItemChance: "타격당 아이템 확률 %", FlatOnCutItemChance: "벌목당 아이템 확률",
    FlatOnHitItemQuantity: "타격당 아이템 수량", FlatOnCutItemQuantity: "벌목당 아이템 수량", PercentIncreaseRockBreakChance: "채굴 성공 확률 %",
    FlatMinimumProspecting: "최소 탐사", AdditionalProductQuantityChance: "추가 1개 확률", ShatterChance: "분쇄 확률", BarItemChance: "주괴 확률",
    StoneItemChance: "석재 확률", EssenceItemChance: "정수 확률", PercentMinInterval: "최소 간격", PercentMaxInterval: "최대 간격", FlatMinInterval: "최소 간격(고정)",
    FlatMaxInterval: "최대 간격(고정)", FlatFishChance: "물고기 확률 +", IncreasedFishChance: "물고기 확률 %", JunkRerollChance: "쓰레기 재굴림", JunkToGP: "쓰레기→GP",
    IncreasedSpecialProductChance: "특수 아이템 확률 %", FlatSpecialProductChance: "특수 아이템 확률 +", SecondSpecialItemChance: "2번째 특수 아이템",
    FlatProductChance: "산출 확률 +", IncreasedProductChance: "산출 확률 %", PercentCurrencyReward: "GP 보상 %", FlatCurrencyReward: "GP 보상 +",
    FlatProficiency: "숙련도 +", FlatDifficulty: "난이도", PreservationChanceOnFail: "실패 시 보존", PercentPreparingInterval: "준비 시간", PercentHeatingInterval: "가열 시간",
    PercentStirringInterval: "교반 시간", PercentBottlingInterval: "병입 시간", FlatStealth: "은신 +", PercentStealth: "은신 %", FlatPerception: "감지 +", PercentPerception: "감지 %",
    FlatFortune: "행운", FlatFortuneUnderSuccess: "행운(성공률<100%)", PercentCommonLootChance: "일반 전리품 확률", PercentRareLootChance: "희귀 전리품 확률",
    PercentCurrencyLootChance: "GP 전리품 확률", StunAvoidanceChance: "기절 회피", PercentStunInterval: "기절 시간", DamageAvoidanceChance: "피해 회피",
    SameAreaPickpocketChance: "같은 지역 추가 소매치기", SkipStageChance: "단계 건너뛰기", FlatStages: "단계 수", PercentXPGained: "XP %", FlatXPGained: "XP +",
    FlatBonfireUnlocked: "화톳불 해금", PercentPricePerItem: "판매가 %", FlatPricePerItem: "판매가 +",
    FlatCombatStatValue: "", PercentAccuracyRating: "명중 레이팅 %", FlatProtectionRating: "Protection", FlatCombatLevel: "전투 레벨",
    PercentHealing: "음식 회복 %", AmmoPreservationChance: "탄약 보존 확률", RunePreservationChance: "룬 보존 확률", CostPreservationChance: "기도 비용 보존",
    FlatPrayerCost: "기도 비용 +", BuriableDoublingChance: "매장물 2배 확률", FlatSpawnInterval: "리스폰 간격(고정)", PercentRewardCurrency: "과제 보상 %",
    PercentRerollCost: "과제 재굴림 비용", PercentExtensionCost: "과제 연장 비용", AttackDamageNegationChance: "피해 무효 확률", ApplicationChance: "효과 적용 확률",
    PercentDamageTaken: "받는 피해 %", KeepObstacleRewardOnFail: "실패 시 보상 유지", PercentMaxTrackingInterval: "최대 추적 시간", TrappingReattemptChance: "덫 재시도 확률"
  };
  var pfmt = function (v, d) { return v == null || isNaN(v) ? "–" : Number(v).toLocaleString("ko-KR", { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 }); };
  var gp = function (v) { return (v < 0 ? "−" : "") + pfmt(Math.abs(v), Math.abs(v) < 10 ? 1 : 0); };
  var iname = function (id) { return ITEMS[id] ? ITEMS[id].n : id; };
  var sell = function (id) { return ITEMS[id] ? ITEMS[id].sell || 0 : 0; };
  var buyPrice = function (id) { return ITEMS[id] && ITEMS[id].buy != null ? ITEMS[id].buy : null; };
  var rankIdx = function (sk, rid) { var i = SK[sk].ranks.map(function (r) { return r.id; }).indexOf(rid); return i < 0 ? 0 : i; };
  function bonText(b) {
    if (b.g) return (b.g === "GlobalPercentXpGained" ? "전체 XP" : b.g === "GlobalPercentActionInterval" ? "전체 행동 간격" : b.g) + " " + (b.v > 0 ? "+" : "") + Math.round(b.v * 1000) / 10 + "%";
    var isPct = /Percent|Chance|Increased/.test(b.s) && !/Flat(Product|OnHit|OnCut|Special)Quantity|FlatSteps|FlatStages|FlatMaxHealth|FlatProficiency|FlatDifficulty|FlatStealth|FlatPerception|FlatFortune|FlatInterval|FlatMinInterval|FlatMaxInterval|FlatCurrencyReward|FlatMinimumProspecting/.test(b.s);
    var v = isPct ? (Math.round(b.v * 1000) / 10) + "%" : (b.s.indexOf("Interval") >= 0 ? (b.v / 1000) + "s" : String(b.v));
    var recOf = function (gid, sk) { return RECIPES.filter(function (r) { return r.gid === gid && (!sk || r.sk === sk); })[0]; };
    var scope = b.rec ? (recOf(b.rec, b.sk) ? recOf(b.rec, b.sk).name : b.rec) : b.cat ? b.cat : b.sub ? b.sub : b.item ? iname(b.item) : b.loc ? b.loc : b.rt ? b.rt : b.cs ? b.cs : b.style ? b.style : b.clv ? b.clv : b.el ? b.el : "";
    var sk = b.sk && SK[b.sk] ? SK[b.sk].name : (b.sk === "Combat" ? "" : (b.sk || ""));
    var lab = (STAT_KO[b.s] != null ? STAT_KO[b.s] : b.s).replace(/\s\+$/, "");
    return ((sk ? sk + " " : "") + (scope ? "[" + scope + "] " : "") + lab + " " + (b.v > 0 ? "+" : "") + v).replace(/\s+/g, " ").trim() + (b.scale ? " × " + b.scale + " 레벨" : "") + (b.cond ? " (조건부: " + b.cond + ")" : "");
  }

  /* ---------------------------------- config ---------------------------------- */
  function defaultPcfg() {
    var lv = {}, tb = {}, pets = {}, shop = {}, rank = {};
    SKILLS.forEach(function (s) {
      lv[s.id] = s.lvl; rank[s.id] = s.guild.rank; tb[s.id] = {};
      var st = (PB.save.toolbelt || {})[s.id] || {};
      s.slots.forEach(function (sl) { tb[s.id][sl.id] = st[sl.id] ? st[sl.id][0] : null; });
      if (s.pet) pets[s.pet.id] = PB.save.pets.indexOf(s.pet.id) >= 0;
    });
    PB.shop.forEach(function (p) { shop[p.id] = PB.save.shop[p.id] || 0; });
    var astro = {};
    (PB.astro || []).forEach(function (c) {
      var sv = (PB.save.astro || {})[c.id] || { minor: [], major: [] }; astro[c.id] = { minor: {}, major: {} };
      c.minor.forEach(function (n) { astro[c.id].minor[n.id] = sv.minor.indexOf(n.id) >= 0; });
      c.major.forEach(function (n) { astro[c.id].major[n.id] = sv.major.indexOf(n.id) >= 0; });
    });
    var distract = {};
    (PB.distract || []).forEach(function (L) { distract[L.loc] = {}; L.items.forEach(function (d) { distract[L.loc][d.id] = d.met === true; }); });
    return { levels: lv, tb: tb, pets: pets, shop: shop, rank: rank, bonfire: { id: PB.save.bonfire ? PB.save.bonfire.id : null, active: !!(PB.save.bonfire && PB.save.bonfire.active) },
      astro: astro, distract: distract, farm: { water: true, compost: null }, ranch: { fed: true, treats: true, pets: true, count: 1 }, anvil: {}, src: {}, onlyOk: true };
  }
  var pcfg = LS.get("pcfg", null) || defaultPcfg();
  // keep shape in sync with the data (new slots / purchases)
  (function () { var d = defaultPcfg(); ["levels", "pets", "shop", "rank"].forEach(function (k) { pcfg[k] = Object.assign({}, d[k], pcfg[k] || {}); }); pcfg.tb = pcfg.tb || {}; SKILLS.forEach(function (s) { pcfg.tb[s.id] = Object.assign({}, d.tb[s.id], pcfg.tb[s.id] || {}); }); pcfg.src = pcfg.src || {}; pcfg.bonfire = pcfg.bonfire || d.bonfire; if (pcfg.onlyOk == null) pcfg.onlyOk = true;
    pcfg.farm = Object.assign({}, d.farm, pcfg.farm || {}); pcfg.ranch = Object.assign({}, d.ranch, pcfg.ranch || {}); pcfg.anvil = pcfg.anvil || {};
    pcfg.distract = pcfg.distract || {}; Object.keys(d.distract).forEach(function (k) { pcfg.distract[k] = Object.assign({}, d.distract[k], pcfg.distract[k] || {}); });
    pcfg.astro = pcfg.astro || {}; Object.keys(d.astro).forEach(function (k) { var o = pcfg.astro[k] || {}; pcfg.astro[k] = { minor: Object.assign({}, d.astro[k].minor, o.minor || {}), major: Object.assign({}, d.astro[k].major, o.major || {}) }; }); })();
  var P0 = defaultPcfg();

  /* ------------------------------- modifier system ------------------------------ */
  var ENTS = [];
  function rebuildEnts() {
    ENTS = [];
    function add(list, mult, src) { (list || []).forEach(function (e) { ENTS.push({ e: e, m: mult, src: src }); }); }
    SKILLS.forEach(function (s) {
      var tb = pcfg.tb[s.id] || {};
      s.slots.forEach(function (sl) { var id = tb[sl.id]; if (id && ITEMS[id] && ITEMS[id].tb) add(ITEMS[id].tb.bon, 1, iname(id)); });
      if (s.pet && pcfg.pets[s.pet.id]) add(s.pet.bon, 1, "펫 " + s.pet.name);
      var ri = rankIdx(s.id, pcfg.rank[s.id]);
      s.rankBon.forEach(function (rb) { if (rankIdx(s.id, rb.rank) <= ri) add(rb.bon, 1, "길드 " + rb.name); });
    });
    PB.shop.forEach(function (p) { var q = pcfg.shop[p.id] || 0; if (q > 0) add(p.bon, q, "상점 " + p.name); });
    if (pcfg.bonfire && pcfg.bonfire.active && pcfg.bonfire.id) { var bf = PB.bonfires.filter(function (b) { return b.id === pcfg.bonfire.id; })[0]; if (bf) add(bf.bon, 1, "화톳불 " + bf.name); }
    (PB.astro || []).forEach(function (c) { var sel = pcfg.astro[c.id] || { minor: {}, major: {} }; c.minor.concat(c.major).forEach(function (n) { if (sel[n.kind][n.id]) add(n.bon, 1, "점성술 " + c.name + " " + n.name); }); });
    (PB.distract || []).forEach(function (L) { var sel = pcfg.distract[L.loc] || {}; L.items.forEach(function (d) { if (sel[d.id]) add(d.bon, 1, "방해 " + d.name); }); });
    // skilling bonuses on equipped combat gear (combat tab config)
    var eq = ccfg().equipment || {};
    Object.keys(eq).forEach(function (s) { var id = eq[s]; if (id && ITEMS[id] && ITEMS[id].eq) add(ITEMS[id].eq, 1, "장비 " + iname(id)); });
  }
  var NON_CTX = { t: 1, s: 1, v: 1, sk: 1, g: 1, cond: 1, from: 1, scale: 1 };
  function lvlOf(sk) { if (pcfg.levels[sk] != null) return pcfg.levels[sk]; var cl = (M2.cfg() || {}).levels || {}; return cl[sk] || 1; }
  function matches(e, ctx) {
    if (e.sk && e.sk !== ctx.sk) return false;
    for (var k in e) { if (NON_CTX[k]) continue; if (e[k] != null && e[k] !== ctx[k]) return false; }
    return !e.cond;
  }
  function mod(type, stat, ctx, sources) {
    var s = 0;
    for (var i = 0; i < ENTS.length; i++) {
      var e = ENTS[i].e; if (e.g || e.t !== type || e.s !== stat || !matches(e, ctx)) continue;
      var m = ENTS[i].m * (e.scale ? lvlOf(e.scale) : 1);
      s += e.v * m; if (sources) sources.push({ src: ENTS[i].src + (e.scale ? " (×" + e.scale + " Lv " + lvlOf(e.scale) + ")" : ""), v: e.v * m });
    }
    return s;
  }
  function glob(group) { var s = 0; for (var i = 0; i < ENTS.length; i++) if (ENTS[i].e.g === group) s += ENTS[i].e.v * ENTS[i].m; return s; }

  /* --------------------------------- rate engine -------------------------------- */
  // Each computeX returns per-cycle quantities: {t (ms), outs {item: qty}, ins {item: qty}, gp, xp, hp, lines:[{k,v,src}], notes:[]}
  function R0() { return { t: 0, outs: {}, ins: {}, gp: 0, xp: 0, hp: 0, lines: [], notes: [] }; }
  function addq(o, k, v) { if (!v) return; o[k] = (o[k] || 0) + v; }
  function used(res, label, type, stat, ctx, fmtFn) { var src = []; var v = mod(type, stat, ctx, src); if (src.length) res.lines.push({ k: label || STAT_KO[stat] || stat, v: fmtFn ? fmtFn(v) : v, src: src }); return v; }
  var pc = function (v) { return (Math.round(v * 1000) / 10) + "%"; };
  function xpOf(res, sk, base) {
    var f = used(res, "XP +", "Experience", "FlatXPGained", { sk: sk }), p = used(res, "XP %", "Experience", "PercentXPGained", { sk: sk }, pc);
    var g = glob("GlobalPercentXpGained"); if (g) res.lines.push({ k: "전체 XP % (화톳불 등)", v: pc(g), src: [] });
    return (base + f) * (1 + p + g);
  }
  function interval(res, type, base, ctx, flatName, pctName, order) { // order 'add-first' = floor((b+f)*(1+p)), 'mul-first' = floor(b*(1+p)+f)
    var f = used(res, null, type, flatName || "FlatInterval", ctx, function (v) { return (v / 1000) + "s"; }) + (flatName ? 0 : glob("GlobalFlatActionInterval"));
    var p = used(res, null, type, pctName || "PercentInterval", ctx, pc) + (pctName ? 0 : glob("GlobalPercentActionInterval"));
    return order === "mul-first" ? Math.floor(base * (1 + p) + f) : Math.floor((base + f) * (1 + p));
  }
  function ingredients(res, r, type, ctx, consumeProb) {
    var pc_ = used(res, null, type, "PercentIngredientCost", ctx, pc);
    (r.ing || []).forEach(function (q) { addq(res.ins, q.item, Math.max(1, Math.floor(q.qty * (1 + pc_))) * consumeProb); });
  }
  function craftedProducts(res, r, type, ctx, dbl, mult, mode) { // mode 'cumulative' (cooking/herblore pick one) | 'each' (artisan rolls each) | 'all'
    var prods = (r.prods || []).slice().sort(function (a, b) { return (a.ch == null ? 1 : a.ch) - (b.ch == null ? 1 : b.ch); });
    var cum = 0;
    prods.forEach(function (p) {
      var c = { sk: ctx.sk, cat: ctx.cat, sub: ctx.sub, rec: ctx.rec, item: p.item };
      var fq = mod(type, "FlatProductQuantity", c), pq = mod(type, "PercentProductQuantity", c);
      var qty = Math.max(1, Math.floor((p.qty + fq) * (1 + pq)));
      var ch = p.ch == null ? 1 : p.ch, prob;
      if (mode === "cumulative") { prob = Math.max(0, Math.min(1, ch + cum) - cum); cum += ch; } else prob = ch;
      addq(res.outs, p.item, prob * qty * (1 + dbl) * mult);
      if (fq || pq) res.lines.push({ k: iname(p.item) + " 수량", v: qty + "개", src: [] });
    });
  }
  function expectedHitsTree(hp, inst, weak, dd) {
    var dw = 3 + Math.floor(0.1 * hp), E = [0];
    for (var h = 1; h <= hp; h++) {
      if (h <= 1) { E[h] = 1 + E[h - 1]; continue; }
      var g = function (x) { return E[Math.max(0, x)]; };
      E[h] = 1 + (1 - inst) * (weak * (dd * g(h - 2 * dw) + (1 - dd) * g(h - dw)) + (1 - weak) * (dd * g(h - 2) + (1 - dd) * g(h - 1)));
    }
    return E[hp];
  }
  function expectedActionsSteps(n, skip) { var E = [0, 1]; for (var h = 2; h <= n; h++) E[h] = 1 + skip * E[h - 2] + (1 - skip) * E[h - 1]; return E[n]; }
  function expectedHitsRock(p, m) {
    if (p <= 0) return Infinity; if (p >= 1) return 1;
    var K = Math.max(1, Math.ceil((0.9999 - m) / p)), e = 0, surv = 1;
    for (var k = 1; k < K; k++) { e += k * p * surv; surv *= (1 - p); }
    return e + K * surv;
  }
  function tableEV(table, fortune, dbl) { // weighted drop table -> {item: expected qty}
    var W = 0, out = {}; table.forEach(function (d) { W += d.w || 1; });
    table.forEach(function (d) { var q = Math.floor((d.min + d.max) / 2 * (1 + fortune / 100)); addq(out, d.item, (d.w || 1) / W * q * (1 + dbl)); });
    return out;
  }

  /* alternative reward modes (Sacrificial Anvil) */
  function anvilUnlocked(m) {
    if (!m.node) return true;
    return (PB.astro || []).some(function (c) { return c.major.some(function (n) { return n.id === m.node; }) && pcfg.astro[c.id] && pcfg.astro[c.id].major[m.node]; });
  }
  function anvilCfg(m) { return pcfg.anvil[m.id] || { on: false, smelt: false }; }
  function anvilFor(r) {
    if (r.kind !== "art") return null;
    for (var i = 0; i < (PB.anvil || []).length; i++) {
      var m = PB.anvil[i], a = anvilCfg(m);
      if (m.sk !== r.sk || !a.on || !anvilUnlocked(m)) continue;
      if (m.allow && m.allow.indexOf(r.cat) < 0) continue;
      if ((m.deny || []).indexOf(r.cat) >= 0) continue;
      if (r.cat === "Smelting" && !a.smelt) continue;
      return m;
    }
    return null;
  }
  function oneIn(v) { return v > 0 ? "1/" + pfmt(Math.round(1 / v)) : "0"; }
  function anvilEV(m) { var W = m.xpW + m.saleW + m.colW; return { xp: 1 + (m.xpMult - 1) * m.xpW / W, sale: 1 + (m.saleMult - 1) * m.saleW / W, col: m.colW / W }; }

  function compute(r, lv) {
    var res = R0(), sk = r.sk, ctx = { sk: sk, cat: r.cat, sub: r.sub, rec: r.gid, loc: r.kind === "fish" ? r.cat : undefined, rt: r.rt };
    var T;
    if (r.kind === "wc") {
      T = "WoodcuttingAction";
      var iv = interval(res, T, r.iv, ctx);
      var hp = Math.ceil((r.hp + used(res, null, T, "FlatMaxHealth", ctx)) * (1 + used(res, null, T, "PercentMaxHealth", ctx, pc)));
      var dbl = used(res, null, T, "DoublingChance", ctx, pc), dd = used(res, null, T, "DoubleDamageChance", ctx, pc), inst = used(res, null, T, "InstantCutChance", ctx, pc), weak = used(res, null, T, "WeakSpotChance", ctx, pc);
      var E = expectedHitsTree(hp, inst, weak, dd);
      res.t = E * iv; res.info = { iv: iv, hp: hp, hits: E };
      var qty = r.prod.qty + Math.floor(used(res, null, T, "FlatProductQuantity", ctx));
      addq(res.outs, r.prod.item, qty * (1 + dbl));
      function items(list, per, fl, pct, fq) {
        list.forEach(function (d) { var c = { sk: sk, cat: r.cat, rec: r.gid, item: d.item }; var ch = (d.ch + mod(T, fl, c)) * (1 + mod(T, pct, c)); var q = d.qty + Math.floor(mod(T, fq, c)); addq(res.outs, d.item, ch * q * (1 + dbl) * per); });
      }
      items(r.hit || [], E, "FlatOnHitItemChance", "PercentOnHitItemChance", "FlatOnHitItemQuantity");
      items(r.cut || [], 1, "FlatOnCutItemChance", "PercentOnCutItemChance", "FlatOnCutItemQuantity");
      res.xp = xpOf(res, sk, r.xp);
    } else if (r.kind === "mine") {
      T = "MiningAction";
      var iv2 = interval(res, T, r.iv, ctx);
      var p = Math.max(0, Math.min(1, r.ch * (1 + used(res, null, T, "PercentIncreaseRockBreakChance", ctx, pc))));
      var m = used(res, null, T, "FlatMinimumProspecting", ctx);
      var dbl2 = used(res, null, T, "DoublingChance", ctx, pc), add = used(res, null, T, "AdditionalProductQuantityChance", ctx, pc), sh = used(res, null, T, "ShatterChance", ctx, pc);
      var E2 = expectedHitsRock(p, m); res.t = E2 * iv2; res.info = { iv: iv2, p: p, hits: E2 };
      var q2 = r.prod.qty + Math.floor(used(res, null, T, "FlatProductQuantity", ctx));
      addq(res.outs, r.prod.item, (q2 + add) * (1 + dbl2) * (1 + 2 * sh));
      if (r.bar) { var bc = used(res, null, T, "BarItemChance", ctx, pc); addq(res.outs, r.bar, bc * (1 + dbl2)); }
      (PB.mining.stone || []).forEach(function (it) { var c = used(res, "석재 확률 (" + iname(it) + ")", T, "StoneItemChance", ctx, pc); addq(res.outs, it, c * (1 + dbl2) * E2); });
      (PB.mining.essence || []).forEach(function (it) { var c = used(res, "정수 확률 (" + iname(it) + ")", T, "EssenceItemChance", ctx, pc); addq(res.outs, it, c * (1 + dbl2) * E2); });
      (r.hit || []).forEach(function (d) { var c = { sk: sk, cat: r.cat, rec: r.gid, item: d.item }; var ch = (d.ch + mod(T, "FlatOnHitItemChance", c)) * (1 + mod(T, "PercentOnHitItemChance", c)); addq(res.outs, d.item, ch * d.qty * (1 + dbl2) * E2); });
      res.xp = xpOf(res, sk, r.xp) * (1 + sh);
    } else if (r.kind === "farm") {
      T = "FarmingAction"; var fc = pcfg.farm || {};
      // compost is chosen per planting; its template bonuses apply to this plot only -> add them for this computation
      var compost = r.canCompost && fc.compost && FARM.compost[fc.compost] ? fc.compost : null, pushed = [];
      if (compost) FARM.compost[compost].bon.forEach(function (e) { var en = { e: e, m: 1, src: "퇴비 " + iname(compost) }; ENTS.push(en); pushed.push(en); });
      var ivF = interval(res, T, r.iv, ctx);
      var reg = Math.max(0, r.regrows + Math.floor(used(res, null, T, "FlatRegrows", ctx)));
      var fIv = mod(T, "FlatInterval", ctx) + glob("GlobalFlatActionInterval"), pIv = mod(T, "PercentInterval", ctx) + glob("GlobalPercentActionInterval");
      var rgIv = reg ? Math.floor((r.regrowIv + fIv) * (1 + pIv)) : 0;
      var water = r.canWater && fc.water !== false, wProt = water ? (FARM.water[r.cat] || 0) : 0;
      var disP = used(res, null, T, "FlatDiseaseProtection", ctx) + wProt;
      if (wProt) res.lines.push({ k: "물주기 병해 보호", v: wProt, src: [{ src: "물주기", v: wProt }] });
      var pestP = used(res, null, T, "FlatPestProtection", ctx);
      var disE = Math.max(0, r.dis - disP), pestE = Math.max(0, r.pest - pestP), adj = 1 - (disE + pestE) / 100;
      var fqF = used(res, null, T, "FlatProductQuantity", ctx), pqF = used(res, null, T, "PercentProductQuantity", ctx, pc);
      var qtyF = Math.max(1, Math.floor((r.prod.qty + fqF) * (1 + pqF) * adj));
      var dblF = used(res, null, T, "DoublingChance", ctx, pc), presF = used(res, null, T, "PreservationChance", ctx, pc);
      var harvests = 1 + reg;
      res.t = ivF + reg * rgIv;
      addq(res.outs, r.prod.item, qtyF * harvests * (1 + dblF));
      ingredients(res, r, T, ctx, 1 - presF);
      if (compost) { var cpF = used(res, null, T, "CompostPreservationChance", ctx, pc); addq(res.ins, compost, 1 - cpF); }
      res.xp = xpOf(res, sk, r.xp) * harvests;
      res.info = { iv: ivF, regrows: reg, regrowIv: rgIv, adj: adj, qty: qtyF, dis: disE, pest: pestE, compost: compost, water: water, canWater: r.canWater, canCompost: r.canCompost };
      res.notes.push("구획 1개 기준. 1행동 = 심기 → 수확" + (reg ? " + 재수확 " + reg + "회" : "") + " (다른 활동과 동시에 진행). 구획 구매비·자동화 비용 미반영");
      pushed.forEach(function (en) { ENTS.splice(ENTS.indexOf(en), 1); });
    } else if (r.kind === "mill") {
      T = "GrainMill";
      var ivM = interval(res, T, r.iv, ctx, "FlatInterval", "PercentInterval"); res.t = ivM; res.info = { iv: ivM };
      var fqM = used(res, null, T, "FlatProductQuantity", ctx), pqM = used(res, null, T, "PercentProductQuantity", ctx, pc);
      addq(res.outs, r.prod.item, Math.max(1, Math.floor((r.prod.qty + fqM) * (1 + pqM))));
      ingredients(res, r, T, ctx, 1);
      res.xp = xpOf(res, sk, r.xp);
      res.notes.push("제분소는 다른 활동과 동시에 돌아갑니다 (재료는 제분소 창고에 넣어 두어야 함)");
    } else if (r.kind === "ranch") {
      T = "RanchingAction"; var rc = pcfg.ranch || {};
      var cnt = Math.max(1, Math.floor(rc.count || 1)), fed = rc.fed !== false, treatsOn = rc.treats !== false, petted = rc.pets !== false;
      var hunger = fed ? 1 : 0, sat = (hunger >= 0.5 ? 0.5 : 0) + 0.4, treatSat = 0, packSat = 0;
      if (treatsOn) r.treats.forEach(function (t) { treatSat += t.sat; });
      if (r.pets && petted) sat += 0.04;
      r.pack.forEach(function (p) { if (cnt >= p[0]) packSat += p[1]; });
      sat += treatSat + packSat;
      var flatH = used(res, null, T, "FlatHappiness", ctx);
      var happy = Math.max(0, hunger * 0.3 + 0.3 + sat * 0.4 + flatH);
      var vIv = Math.floor((r.variantIv + used(res, null, T, "FlatBaseVariantInterval", ctx)) * (1 + used(res, null, T, "PercentBaseVariantInterval", ctx, pc)));
      var life = Math.max(1, Math.floor((r.lifeIv + used(res, null, T, "FlatLifespanInterval", ctx)) * (1 + used(res, null, T, "PercentLifespanInterval", ctx, pc))));
      var W = 0, adultPQ = 0, adultXQ = 0; r.variants.forEach(function (v) { W += v.w; adultPQ += v.w * v.pq; adultXQ += v.w * v.xq; }); if (W) { adultPQ /= W; adultXQ /= W; }
      var tc = Math.min(vIv, life) / life;
      var pqR = used(res, null, T, "PercentProductQuantity", ctx, pc), fqR = used(res, null, T, "FlatProductQuantity", ctx), dblR = used(res, null, T, "DoublingChance", ctx, pc);
      var lifeMult = tc * Math.max(0, 1 + pqR + r.child.pq) + (1 - tc) * Math.max(0, 1 + pqR + adultPQ);
      res.t = r.prodIv;
      if (hunger > 0) r.prods.forEach(function (p) { addq(res.outs, p.item, Math.max(0, p.qty + fqR) * lifeMult * happy * (1 + dblR)); });
      if (fed && r.eats.length) {
        var fIvR = Math.max(1, Math.floor((r.foodIv + used(res, null, T, "FlatFoodConsumptionterval", ctx)) * (1 + used(res, null, T, "PercentFoodConsumptionInterval", ctx, pc))));
        var fpR = used(res, null, T, "FoodPreservationChance", ctx, pc), feR = used(res, null, T, "FlatEatsQuantity", ctx), peR = used(res, null, T, "PercentEatsQuantity", ctx, pc);
        r.eats.forEach(function (q) { addq(res.ins, q.item, Math.max(1, Math.floor((q.qty + feR) * (1 + peR))) * (1 - fpR) * (r.prodIv / fIvR)); });
      }
      if (treatsOn) r.treats.forEach(function (t) { addq(res.ins, t.item, t.qty * r.prodIv / r.treatIv); });
      var picR = used(res, null, T, "PercentIngredientCost", ctx, pc);
      res.gp -= Math.max(1, Math.floor(r.cost * (1 + picR))) * r.prodIv / life;
      (r.costItems || []).forEach(function (q) { addq(res.ins, q.item, Math.max(1, Math.floor(q.qty * (1 + picR))) * r.prodIv / life); });
      // enclosure upkeep: maintenance drops 1% per (modified) hour unless skipped; repairing at 75% costs max(1, floor(c/1000)*25) per cost item
      var enc = (r.enc || []).filter(function (e) { return e.limit >= cnt; })[0] || (r.enc || [])[r.enc.length - 1] || null;
      if (enc) {
        var mIv = Math.max(1, Math.floor((3600000 + used(res, null, T, "FlatMaintenanceInterval", ctx)) * (1 + used(res, null, T, "PercentMaintenanceInterval", ctx, pc))));
        var skip = Math.min(1, used(res, null, T, "EnclosureMaintenanceSkipChance", ctx, pc));
        var repairH = 25 * (mIv / 3600000) / Math.max(1e-6, 1 - skip);
        enc.cost.forEach(function (q) { addq(res.ins, q.item, Math.max(1, Math.floor(q.qty / 1000) * 25) / repairH * (r.prodIv / 3600000) / cnt); });
      }
      var xpBase = xpOf(res, sk, r.xp);
      res.xp = happy * (xpBase + r.xp * (tc * r.child.xq + (1 - tc) * adultXQ));
      res.info = { happy: happy, sat: sat, treatSat: treatSat, packSat: packSat, life: life, vIv: vIv, tc: tc, adultPQ: adultPQ, cnt: cnt, enc: enc ? enc.name : null, fed: fed };
      res.notes.push("동물 1마리 · 1시간 기준 (다른 활동과 동시에 진행). 구매비 " + pfmt(r.cost) + " GP는 수명 " + pfmt(life / 3600000) + "h로 나눠 반영, 땅·축사 건설비는 미반영");
      if (r.pets) res.notes.push("쓰다듬기는 48시간마다 수동 (만족도 +4%)" + (petted ? "" : " — 현재 꺼짐"));
      if (!fed) res.notes.push("급식 꺼짐: 굶으면 산출이 0이 되므로 결과 0");
    } else if (r.kind === "fish") {
      T = "FishingAction";
      var mn = Math.floor((r.ivMin + used(res, null, T, "FlatMinInterval", ctx)) * (1 + used(res, null, T, "PercentMinInterval", ctx, pc)));
      var mx = Math.floor((r.ivMax + used(res, null, T, "FlatMaxInterval", ctx)) * (1 + used(res, null, T, "PercentMaxInterval", ctx, pc)));
      if (mx < mn) mx = mn; res.t = (mn + mx) / 2; res.info = { ivMin: mn, ivMax: mx };
      var f = Math.max(0, Math.min(1, (r.fishCh + used(res, null, T, "FlatFishChance", ctx, pc)) * (1 + used(res, null, T, "IncreasedFishChance", ctx, pc))));
      var jr = used(res, null, T, "JunkRerollChance", ctx, pc), dbl3 = used(res, null, T, "DoublingChance", ctx, pc);
      var pJunk = (1 - f) * (1 - jr), pFish = 1 - pJunk; res.info.fish = pFish;
      var W = 0; r.prods.forEach(function (d) { W += d.w || 1; });
      r.prods.forEach(function (d) { addq(res.outs, d.item, pFish * (d.w || 1) / W * (d.min + d.max) / 2 * (1 + dbl3)); });
      if (r.junk && pJunk > 0) { var j2g = used(res, null, T, "JunkToGP", ctx, pc); if (j2g > 0) res.gp += pJunk * (1 + dbl3) * sell(r.junk) * j2g; else addq(res.outs, r.junk, pJunk * (1 + dbl3)); }
      var sp = (r.special || []).map(function (d) { var c = { sk: sk, loc: r.cat, rec: r.gid, item: d.item }; return { item: d.item, qty: d.qty + Math.floor(mod(T, "FlatSpecialProductQuantity", c)), ch: Math.max(0, Math.min(1, d.ch + mod(T, "FlatSpecialProductChance", c) + d.ch * mod(T, "IncreasedSpecialProductChance", c))) }; }).sort(function (a, b) { return a.ch - b.ch; });
      var prev = 0, pAny = sp.length ? sp[sp.length - 1].ch : 0, second = used(res, null, T, "SecondSpecialItemChance", ctx, pc);
      sp.forEach(function (d) { addq(res.outs, d.item, (d.ch - prev) * d.qty * (1 + dbl3) * (1 + pAny * second)); prev = d.ch; });
      res.xp = xpOf(res, sk, r.xp);
      res.notes.push("미끼(Bait) 보너스·소모는 미반영");
    } else if (r.kind === "fm") {
      T = "FiremakingAction";
      res.t = interval(res, T, r.iv, ctx);
      var pres = used(res, null, T, "PreservationChance", ctx, pc), dbl4 = used(res, null, T, "DoublingChance", ctx, pc);
      ingredients(res, r, T, ctx, 1 - pres);
      r.prods.forEach(function (d) { var c = { sk: sk, cat: r.cat, rec: r.gid, item: d.item }; var ch = Math.max(0, Math.min(1, d.ch + mod(T, "FlatProductChance", c) + d.ch * mod(T, "IncreasedProductChance", c))); var q = d.qty + Math.floor(mod(T, "FlatProductQuantity", c)); addq(res.outs, d.item, ch * q * (1 + dbl4)); });
      if (r.cur) { var cc = { sk: sk, cat: r.cat, rec: r.gid, cur: r.cur[0] }; var g = Math.max(1, Math.floor(r.cur[1] * (1 + used(res, null, T, "PercentCurrencyReward", cc, pc)) + used(res, null, T, "FlatCurrencyReward", cc))); if (r.cur[0] === "GoldPieces") res.gp += g * (1 + dbl4); }
      res.xp = xpOf(res, sk, r.xp);
    } else if (r.kind === "cook") {
      T = "CookingAction";
      res.t = interval(res, T, r.iv, ctx, null, null, "mul-first");
      var prof = Math.max(0, lv + used(res, null, T, "FlatProficiency", ctx)), diff = Math.max(0, r.diff + used(res, null, T, "FlatDifficulty", ctx));
      var S = Math.max(0, Math.min(1, (69 + prof) / (69 + diff))); res.info = { success: S, prof: prof, diff: diff };
      var pres2 = used(res, null, T, "PreservationChance", ctx, pc), pf = used(res, null, T, "PreservationChanceOnFail", ctx, pc), dbl5 = used(res, null, T, "DoublingChance", ctx, pc);
      ingredients(res, r, T, ctx, 1 - (pres2 + (1 - pres2) * (1 - S) * pf));
      craftedProducts(res, r, T, ctx, dbl5, S, "cumulative");
      res.xp = xpOf(res, sk, r.xp) * S;
    } else if (r.kind === "art") {
      T = "ArtisanAction";
      var iv6 = interval(res, T, r.iv, ctx, null, null, "mul-first");
      var steps = Math.max(1, r.steps + used(res, null, T, "FlatSteps", ctx)), skip = used(res, null, T, "SkipStepChance", ctx, pc);
      var E6 = expectedActionsSteps(steps, skip); res.t = E6 * iv6; res.info = { iv: iv6, steps: steps, actions: E6 };
      var pres3 = used(res, null, T, "PreservationChance", ctx, pc), dbl6 = used(res, null, T, "DoublingChance", ctx, pc);
      ingredients(res, r, T, ctx, 1 - pres3);
      craftedProducts(res, r, T, ctx, dbl6, 1, "each");
      res.xp = xpOf(res, sk, r.xp);
      var am = anvilFor(r);
      if (am) { // products -> GP at sell price (×sale mult), XP ×mult, collectable roll per base Step
        var ev = anvilEV(am), gpA = 0;
        Object.keys(res.outs).forEach(function (k) { gpA += res.outs[k] * sell(k); }); res.outs = {};
        res.gp += gpA * ev.sale; res.xp *= ev.xp;
        var cw = 0; am.collect.forEach(function (c) { cw += c.w || 1; });
        am.collect.forEach(function (c) { addq(res.outs, c.item, (r.steps || 1) * ev.col * (c.w || 1) / cw * (c.min + c.max) / 2); });
        res.info.anvil = { name: am.name, sale: ev.sale, xp: ev.xp, col: (r.steps || 1) * ev.col };
        res.lines.push({ k: am.name + " · 제품 → GP", v: "판매가 ×" + pfmt(ev.sale, 3), src: [] });
        res.lines.push({ k: am.name + " · XP", v: "×" + pfmt(ev.xp, 3), src: [] });
        res.lines.push({ k: am.name + " · 수집품", v: oneIn((r.steps || 1) * ev.col) + " 완성", src: [] });
      }
    } else if (r.kind === "herb") {
      T = "HerbloreAction";
      var ivP = interval(res, T, r.ivP, ctx, "FlatPreparingInterval", "PercentPreparingInterval", "mul-first"), ivH = interval(res, T, r.ivH, ctx, "FlatHeatingInterval", "PercentHeatingInterval", "mul-first");
      var ivS = interval(res, T, r.ivS, ctx, "FlatStirringInterval", "PercentStirringInterval", "mul-first"), ivB = interval(res, T, r.ivB, ctx, "FlatBottlingInterval", "PercentBottlingInterval", "mul-first");
      var nb = PB.herbBottles || 10; res.t = ivP + ivH + ivS + nb * ivB; res.info = { ivP: ivP, ivH: ivH, ivS: ivS, ivB: ivB, bottles: nb };
      var pres4 = used(res, null, T, "PreservationChance", ctx, pc), dbl7 = used(res, null, T, "DoublingChance", ctx, pc);
      ingredients(res, r, T, ctx, (1 - pres4) * nb);
      craftedProducts(res, r, T, ctx, dbl7, nb, "cumulative");
      res.xp = xpOf(res, sk, r.xp) * nb;
    } else if (r.kind === "thief") {
      T = "ThievingAction";
      var iv8 = interval(res, T, r.iv, ctx), stunIv = Math.floor((2000 + used(res, null, T, "FlatStunInterval", ctx)) * (1 + used(res, null, T, "PercentStunInterval", ctx, pc)));
      var stealth = Math.max(0, Math.floor((lv + used(res, null, T, "FlatStealth", ctx)) * (1 + used(res, null, T, "PercentStealth", ctx, pc))));
      var perc = Math.max(0, Math.floor((r.perc + used(res, null, T, "FlatPerception", ctx)) * (1 + used(res, null, T, "PercentPerception", ctx, pc))));
      var S8 = Math.min(1, (100 + stealth) / (100 + perc));
      var stunAv = used(res, null, T, "StunAvoidanceChance", ctx, pc), dmgAv = used(res, null, T, "DamageAvoidanceChance", ctx, pc), dbl8 = used(res, null, T, "DoublingChance", ctx, pc);
      var stages = Math.max(1, r.stages + used(res, null, T, "FlatStages", ctx)), skipSt = used(res, null, T, "SkipStageChance", ctx, pc);
      res.t = iv8 + (1 - S8) * (1 - stunAv) * stunIv; res.hp = (1 - S8) * (1 - dmgAv) * (1 + r.dmg) / 2;
      res.info = { iv: iv8, success: S8, stealth: stealth, perc: perc, stunIv: stunIv, stages: stages };
      var fortune = used(res, null, T, "FlatFortune", ctx) + (S8 < 1 ? used(res, null, T, "FlatFortuneUnderSuccess", ctx) : 0);
      if (r.cur) { var ccur = { sk: sk, cat: r.cat, rec: r.gid, rt: r.rt, cur: "GoldPieces" }; var fc = used(res, null, T, "FlatCurrencyReward", ccur), pcr = used(res, null, T, "PercentCurrencyReward", ccur, pc); var mn8 = Math.max(0, Math.floor((r.cur[0] + fc) * (1 + pcr))), mx8 = Math.max(0, Math.floor((r.cur[1] + fc) * (1 + pcr))); var cch = Math.max(0, Math.min(1, r.curCh * (1 + used(res, null, T, "PercentCurrencyLootChance", ctx, pc)))); res.gp += S8 * cch * (mn8 + mx8) / 2; }
      var comCh = Math.max(0, Math.min(1, r.comCh * (1 + used(res, null, T, "PercentCommonLootChance", ctx, pc)))), rareCh = Math.max(0, Math.min(1, r.rareCh * (1 + used(res, null, T, "PercentRareLootChance", ctx, pc))));
      var ev; ev = tableEV(r.common || [], fortune, dbl8); Object.keys(ev).forEach(function (k) { addq(res.outs, k, S8 * comCh * ev[k]); });
      ev = tableEV(r.rare || [], fortune, dbl8); Object.keys(ev).forEach(function (k) { addq(res.outs, k, S8 * rareCh * ev[k]); });
      var perSucc = (1 + skipSt) / stages; ev = tableEV(r.done || [], fortune, dbl8); Object.keys(ev).forEach(function (k) { addq(res.outs, k, S8 * perSucc * ev[k]); });
      res.xp = xpOf(res, sk, r.xp) * S8 * perSucc;
      var sa = used(res, null, T, "SameAreaPickpocketChance", ctx, pc); if (sa) res.notes.push("같은 지역 추가 소매치기 확률 미반영");
      if (r.access) res.notes.push("필요: " + r.access.join(", "));
    }
    return res;
  }

  /* ------------------------------ hourly rates + chain ------------------------------ */
  var RATES = {}, PRODUCERS = {};
  function levelOk(r) {
    if ((pcfg.levels[r.sk] || 1) < r.lvl) return false;
    for (var k in r.reqLv) { var have = pcfg.levels[k] != null ? pcfg.levels[k] : (ccfg().levels && ccfg().levels[k] != null ? ccfg().levels[k] : 1); if (have < r.reqLv[k]) return false; }
    return true;
  }
  function recomputeAll() {
    rebuildEnts(); RATES = {}; PRODUCERS = {};
    RECIPES.forEach(function (r) {
      var c = compute(r, pcfg.levels[r.sk] || 1), f = c.t > 0 ? H / c.t : 0, outs = {}, ins = {};
      Object.keys(c.outs).forEach(function (k) { outs[k] = c.outs[k] * f; }); Object.keys(c.ins).forEach(function (k) { ins[k] = c.ins[k] * f; });
      var ok = levelOk(r);
      RATES[r.id] = { r: r, c: c, perH: f, outs: outs, ins: ins, gpH: c.gp * f, xpH: c.xp * f, hpH: c.hp * f, ok: ok };
      if (ok) Object.keys(outs).forEach(function (k) { if (outs[k] > 0.01) (PRODUCERS[k] = PRODUCERS[k] || []).push(r.id); });
    });
    Object.keys(PRODUCERS).forEach(function (k) { PRODUCERS[k].sort(function (a, b) { return RATES[b].outs[k] - RATES[a].outs[k]; }); });
  }
  function srcOf(item) { var s = pcfg.src[item]; if (!s) return "bank"; if (s === "shop" && buyPrice(item) == null) return "bank"; if (s.indexOf("make:") === 0 && !(PRODUCERS[item] || []).some(function (x) { return x === s.slice(5); })) return (PRODUCERS[item] || []).length ? "make:" + PRODUCERS[item][0] : "bank"; if (s === "make" ) return (PRODUCERS[item] || []).length ? "make:" + PRODUCERS[item][0] : "bank"; return s; }
  // value of running recipe `rid` for `scale` hours, sourcing inputs per pcfg.src; returns {value, time, parts}
  function chain(rid, scale, depth, visited, override) {
    var R = RATES[rid], value = R.gpH * scale, time = scale, parts = [];
    Object.keys(R.outs).forEach(function (k) { value += R.outs[k] * sell(k) * scale; });
    Object.keys(R.ins).forEach(function (k) {
      var need = R.ins[k] * scale, src = override && override.item === k ? override.src : srcOf(k), cost = 0, sub = null;
      if (src === "shop") cost = need * buyPrice(k);
      else if (src.indexOf("make:") === 0 && depth < 4 && visited.indexOf(rid) < 0) {
        var pid = src.slice(5), y = RATES[pid] ? RATES[pid].outs[k] : 0;
        if (y > 0 && pid !== rid) { sub = chain(pid, need / y, depth + 1, visited.concat([rid])); value += sub.value - need * sell(k); time += sub.time; }
        else cost = need * sell(k);
      } else { src = "bank"; cost = need * sell(k); }
      value -= cost; parts.push({ item: k, need: need, src: src, cost: cost, sub: sub });
    });
    return { value: value, time: time, parts: parts };
  }
  var ROWS = [];
  function evaluateAll() {
    ROWS = RECIPES.map(function (r) {
      var R = RATES[r.id], ch = chain(r.id, 1, 0, []), outV = Math.max(0, R.gpH); Object.keys(R.outs).forEach(function (k) { outV += R.outs[k] * sell(k); });
      var inV = Math.max(0, -R.gpH); ch.parts.forEach(function (p) { inV += p.cost; });
      var main = Object.keys(R.outs).filter(function (k) { return R.outs[k] >= 0.01; }).sort(function (a, b) { return R.outs[b] * sell(b) - R.outs[a] * sell(a); })[0];
      return { id: r.id, r: r, R: R, ok: R.ok, perH: R.perH, outV: outV, inV: inV, net: ch.value, time: ch.time, netH: ch.time > 0 ? ch.value / ch.time : 0, xpH: R.xpH, main: main, chain: ch };
    });
  }

  /* ------------------------------------- UI ------------------------------------- */
  var pui = { q: "", skill: "", view: "table", sortKey: "netH", sortAsc: false, sel: null };
  var $p = function (s) { return document.querySelector(s); };
  function pchanged(skipLs) { if (!skipLs) LS.set("pcfg", pcfg); recomputeAll(); evaluateAll(); renderPSide(); renderPMain(); renderPDetail(); if (!skipLs && M2.astroSync) M2.astroSync(); }

  function renderPSide() {
    // levels
    var g = $p("#plevels"); g.innerHTML = "";
    SKILLS.forEach(function (s) {
      var l = document.createElement("label"); var was = s.lvl; if (pcfg.levels[s.id] !== was) l.className = "ch";
      l.innerHTML = "<span class=nm>" + s.name + "</span>"; var inp = document.createElement("input"); inp.type = "number"; inp.min = 1; inp.max = 120; inp.value = pcfg.levels[s.id];
      inp.title = "세이브 " + was; inp.addEventListener("change", function () { pcfg.levels[s.id] = Math.max(1, Math.min(120, parseInt(inp.value) || 1)); pchanged(); });
      l.appendChild(inp); g.appendChild(l);
    });
    $p("#plvHint").textContent = SKILLS.filter(function (s) { return pcfg.levels[s.id] !== s.lvl; }).length ? "세이브와 다름" : "세이브 기준";
    // bonuses per skill
    var box = $p("#pbonus"); var openState = {}; box.querySelectorAll("details.skb").forEach(function (d) { openState[d.dataset.sk] = d.open; }); box.innerHTML = "";
    SKILLS.forEach(function (s) {
      var d = document.createElement("details"); d.className = "skb"; d.dataset.sk = s.id; if (openState[s.id]) d.open = true;
      var active = 0;
      var body = document.createElement("div"); body.className = "b";
      // toolbelt
      body.innerHTML = "<div class=sub-h>툴벨트</div>";
      s.slots.forEach(function (sl) {
        var cur = pcfg.tb[s.id][sl.id] || null, saveV = P0.tb[s.id][sl.id] || null; if (cur) active++;
        var row = document.createElement("div"); row.className = "tbslot" + (cur !== saveV ? " ch" : "");
        row.innerHTML = "<span class=sn title='" + esc(sl.name) + "'>" + esc(sl.name) + "</span>";
        var sel = document.createElement("select");
        var cands = Object.keys(ITEMS).filter(function (id) { return ITEMS[id].tb && ITEMS[id].tb.slot === sl.type; });
        cands.sort(function (a, b) { var oa = owned(a) ? 0 : 1, ob = owned(b) ? 0 : 1; return oa - ob || iname(a).localeCompare(iname(b)); });
        var o0 = document.createElement("option"); o0.value = ""; o0.textContent = "– 없음 –"; sel.appendChild(o0);
        cands.forEach(function (id) { var o = document.createElement("option"); o.value = id; var it = ITEMS[id]; o.textContent = (owned(id) ? "✓ " : "") + it.n + (it.tb.bon.length ? " · " + it.tb.bon.map(bonText).join(", ") : "") + (it.tb.cons ? " (소모성)" : ""); o.title = it.d || ""; if (id === cur) o.selected = true; sel.appendChild(o); });
        sel.addEventListener("change", function () { pcfg.tb[s.id][sl.id] = sel.value || null; pchanged(); });
        row.appendChild(sel); body.appendChild(row);
      });
      // pet / guild
      var h2 = document.createElement("div"); h2.className = "sub-h"; h2.textContent = "펫 · 길드"; body.appendChild(h2);
      if (s.pet) {
        var pl = document.createElement("label"); pl.className = "shopup"; var pcb = document.createElement("input"); pcb.type = "checkbox"; pcb.checked = !!pcfg.pets[s.pet.id]; if (pcb.checked) active++;
        pcb.addEventListener("change", function () { pcfg.pets[s.pet.id] = pcb.checked; pchanged(); });
        pl.appendChild(pcb); var sp = document.createElement("span"); sp.innerHTML = "펫 " + esc(s.pet.name) + "<span class=bt>" + esc(s.pet.bon.map(bonText).join(", ") || "보너스 없음") + "</span>"; pl.appendChild(sp); body.appendChild(pl);
      }
      var gr = document.createElement("div"); gr.className = "tbslot"; gr.innerHTML = "<span class=sn>길드 랭크</span>";
      var gsel = document.createElement("select");
      s.ranks.forEach(function (rk, i) { var o = document.createElement("option"); o.value = rk.id; var bons = s.rankBon.filter(function (b) { return b.rank === rk.id; }).map(function (b) { return b.bon.map(bonText).join(", "); }).join(", "); o.textContent = rk.name + " (" + Math.round(rk.pct * 100) + "%)" + (bons ? " · " + bons : ""); if (rk.id === pcfg.rank[s.id]) o.selected = true; gsel.appendChild(o); });
      gsel.addEventListener("change", function () { pcfg.rank[s.id] = gsel.value; pchanged(); });
      gr.appendChild(gsel); body.appendChild(gr);
      var gh = document.createElement("div"); gh.className = "note"; gh.textContent = "세이브 추정: " + s.guild.pts + " / " + s.guild.total + " pt (조건형 과제는 미확인 → 낮게 잡힐 수 있음)"; body.appendChild(gh);
      if (rankIdx(s.id, pcfg.rank[s.id]) > 0) active++;
      // shop upgrades
      var ups = PB.shop.filter(function (p) { return p.bon.some(function (b) { return b.sk === s.id; }); });
      if (ups.length) {
        var h3 = document.createElement("div"); h3.className = "sub-h"; h3.textContent = "상점 업그레이드"; body.appendChild(h3);
        ups.forEach(function (p) {
          var l = document.createElement("label"); l.className = "shopup"; var cb = document.createElement("input"); cb.type = "checkbox"; cb.checked = (pcfg.shop[p.id] || 0) > 0; if (cb.checked) active++;
          cb.addEventListener("change", function () { pcfg.shop[p.id] = cb.checked ? 1 : 0; pchanged(); });
          l.appendChild(cb); var sp2 = document.createElement("span");
          sp2.innerHTML = esc(p.name) + (PB.save.shop[p.id] ? " <span class=good title='세이브에서 구매됨'>✓</span>" : "") + "<span class=gp>" + (p.gp ? pfmt(p.gp) + " GP" : "") + (p.req.length ? " · " + esc(p.req.join(", ")) : "") + "</span><span class=bt>" + esc(p.bon.map(bonText).join(", ")) + "</span>";
          l.appendChild(sp2); body.appendChild(l);
        });
      }
      // astrology
      var cons = (PB.astro || []).filter(function (c) { return c.skills.indexOf(s.id) >= 0 || c.minor.concat(c.major).some(function (n) { return n.bon.some(function (b) { return b.sk === s.id; }); }); });
      cons.forEach(function (c) {
        var sel = pcfg.astro[c.id], sv = (PB.save.astro || {})[c.id] || { minor: [], major: [], knowledge: 0 };
        var h6 = document.createElement("div"); h6.className = "sub-h"; h6.textContent = "점성술 · " + c.name; h6.title = c.req.join(", "); body.appendChild(h6);
        var nodeText = function (n) { return n.bon.length ? n.bon.map(bonText).join(", ") : n.cbon.length ? "전투: " + n.cbon.map(bonText).join(", ") : (n.txt.length ? n.txt.join(", ") : n.desc || n.name); };
        var groups = [], gi = {};  // minor nodes with identical bonuses -> one 0..k selector
        c.minor.forEach(function (n) { var k = nodeText(n); if (gi[k] == null) { gi[k] = groups.length; groups.push({ k: k, nodes: [] }); } groups[gi[k]].nodes.push(n); });
        groups.forEach(function (g) {
          var cur = g.nodes.filter(function (n) { return sel.minor[n.id]; }).length, saved = g.nodes.filter(function (n) { return sv.minor.indexOf(n.id) >= 0; }).length; if (cur) active++;
          var row = document.createElement("div"); row.className = "tbslot astro" + (cur !== saved ? " ch" : "");
          row.innerHTML = "<span class=sn title='" + esc(g.k) + "'>" + esc(g.k) + (saved ? " <span class=good title='세이브 해금 " + saved + "개'>✓" + saved + "</span>" : "") + "</span>";
          var gsel2 = document.createElement("select"); for (var i = 0; i <= g.nodes.length; i++) { var o = document.createElement("option"); o.value = i; o.textContent = i + " / " + g.nodes.length; if (i === cur) o.selected = true; gsel2.appendChild(o); }
          gsel2.addEventListener("change", function () { g.nodes.forEach(function (n, i) { sel.minor[n.id] = i < +gsel2.value; }); pchanged(); });
          row.appendChild(gsel2); body.appendChild(row);
        });
        c.major.forEach(function (n) {
          var l = document.createElement("label"); l.className = "shopup"; var cb = document.createElement("input"); cb.type = "checkbox"; cb.checked = !!sel.major[n.id]; if (cb.checked) active++;
          cb.addEventListener("change", function () { sel.major[n.id] = cb.checked; pchanged(); });
          l.appendChild(cb); var sp4 = document.createElement("span"); sp4.innerHTML = esc(n.name) + (sv.major.indexOf(n.id) >= 0 ? " <span class=good title='세이브에서 해금됨'>✓</span>" : "") + "<span class=bt>" + esc(nodeText(n)) + "</span>"; if (n.desc) sp4.title = n.desc; l.appendChild(sp4); body.appendChild(l);
        });
        var kn = document.createElement("div"); kn.className = "note"; kn.textContent = "세이브: 지식 " + pfmt(Math.floor(sv.knowledge || 0)) + " · 소노드 " + sv.minor.length + "/" + c.minor.length + " · 대노드 " + sv.major.length + "/" + c.major.length + (c.req.length ? " · 요구: " + c.req.join(", ") : ""); body.appendChild(kn);
      });
      if (s.id === "Thieving") (PB.distract || []).forEach(function (L) {
        var sel = pcfg.distract[L.loc] = pcfg.distract[L.loc] || {};
        var h7 = document.createElement("div"); h7.className = "sub-h"; h7.textContent = "방해 요소 · " + L.name; h7.title = "조건을 충족하면 게임에서 자동으로 적용되는 장소별 보너스"; body.appendChild(h7);
        L.items.forEach(function (d) {
          var l = document.createElement("label"); l.className = "shopup"; var cb = document.createElement("input"); cb.type = "checkbox"; cb.checked = !!sel[d.id]; if (cb.checked) active++;
          cb.addEventListener("change", function () { sel[d.id] = cb.checked; pchanged(); });
          var mark = d.met === true ? " <span class=good title='세이브 기준 조건 충족'>✓</span>" : d.met === false ? " <span class=muted title='세이브 기준 조건 미충족'>✗</span>" : " <span class=muted title='세이브에서 확인 불가 (아이템 통계 등) — 게임에서 확인 후 체크'>?</span>";
          l.appendChild(cb); var sp7 = document.createElement("span");
          sp7.innerHTML = esc(d.name) + mark + "<span class=bt>" + esc(d.bon.map(function (b) { var c = Object.assign({}, b); delete c.cat; return bonText(c); }).join(", ")) + "</span>";
          if (d.req.length) sp7.title = "요구: " + d.req.join(", "); l.appendChild(sp7); body.appendChild(l);
        });
      });
      (PB.anvil || []).filter(function (m) { return m.sk === s.id; }).forEach(function (m) {
        var a = pcfg.anvil[m.id] = pcfg.anvil[m.id] || { on: false, smelt: false }, ok = anvilUnlocked(m), ev = anvilEV(m);
        var h8 = document.createElement("div"); h8.className = "sub-h"; h8.textContent = m.name; h8.title = "게임에서는 레시피별 토글. 제품을 창고 대신 판매가 GP로 받고, " + pc(m.xpW / (m.xpW + m.saleW + m.colW)) + "로 XP ×" + m.xpMult + ", " + pc(m.saleW / (m.xpW + m.saleW + m.colW)) + "로 GP ×" + m.saleMult + ", 단계마다 " + oneIn(m.colW / (m.xpW + m.saleW + m.colW)) + "로 수집품"; body.appendChild(h8);
        var l1 = document.createElement("label"); l1.className = "shopup"; var c1 = document.createElement("input"); c1.type = "checkbox"; c1.checked = !!a.on; c1.disabled = !ok; if (a.on && ok) active++;
        c1.addEventListener("change", function () { a.on = c1.checked; pchanged(); }); l1.appendChild(c1);
        var s1 = document.createElement("span"); s1.innerHTML = "사용 (장비 제작)" + (ok ? "" : " <span class=muted title='요구: " + esc(m.req.join(", ")) + "'>🔒</span>") + "<span class=bt>제품을 GP로 희생: 기대 판매가 ×" + pfmt(ev.sale, 3) + ", XP ×" + pfmt(ev.xp, 3) + ", 수집품 " + oneIn(ev.col) + " 단계</span>"; l1.appendChild(s1); body.appendChild(l1);
        var l2 = document.createElement("label"); l2.className = "shopup"; var c2 = document.createElement("input"); c2.type = "checkbox"; c2.checked = !!a.smelt; c2.disabled = !ok || !a.on;
        c2.addEventListener("change", function () { a.smelt = c2.checked; pchanged(); }); l2.appendChild(c2);
        var s2 = document.createElement("span"); s2.innerHTML = "제련(바)에도 적용<span class=bt>켜면 바도 GP가 되어 다른 레시피의 '직접 생산' 재료로 쓸 수 없음</span>"; l2.appendChild(s2); body.appendChild(l2);
        if (!ok) { var n8 = document.createElement("div"); n8.className = "note"; n8.textContent = "요구: " + m.req.join(", ") + " — 위 점성술 섹션에서 해당 대노드를 체크하면 사용할 수 있습니다."; body.appendChild(n8); }
      });
      if (s.id === "Firemaking") {
        var h4 = document.createElement("div"); h4.className = "sub-h"; h4.textContent = "화톳불"; body.appendChild(h4);
        var br = document.createElement("div"); br.className = "tbslot"; var bsel = document.createElement("select");
        var ob = document.createElement("option"); ob.value = ""; ob.textContent = "– 꺼짐 –"; bsel.appendChild(ob);
        PB.bonfires.forEach(function (b) { var o = document.createElement("option"); o.value = b.id; o.textContent = b.name + " · " + b.bon.map(bonText).join(", "); if (pcfg.bonfire.active && pcfg.bonfire.id === b.id) o.selected = true; bsel.appendChild(o); });
        bsel.addEventListener("change", function () { pcfg.bonfire = { id: bsel.value || null, active: !!bsel.value }; pchanged(); });
        br.appendChild(bsel); body.appendChild(br); if (pcfg.bonfire.active) active++;
      }
      if (s.id === "Farming") {
        var h5 = document.createElement("div"); h5.className = "sub-h"; h5.textContent = "구획 관리"; body.appendChild(h5);
        var wl = document.createElement("label"); wl.className = "shopup"; var wcb = document.createElement("input"); wcb.type = "checkbox"; wcb.checked = pcfg.farm.water !== false;
        wcb.addEventListener("change", function () { pcfg.farm.water = wcb.checked; pchanged(); }); wl.appendChild(wcb);
        var ws = document.createElement("span"); ws.innerHTML = "물주기<span class=bt>심을 때마다 물을 줌 (무료, 병해 보호 +15)</span>"; wl.appendChild(ws); body.appendChild(wl);
        var cr = document.createElement("div"); cr.className = "tbslot"; cr.innerHTML = "<span class=sn>퇴비</span>"; var csel = document.createElement("select");
        var oc = document.createElement("option"); oc.value = ""; oc.textContent = "– 없음 –"; csel.appendChild(oc);
        Object.keys(FARM.compost).forEach(function (id) { var o = document.createElement("option"); o.value = id; o.textContent = iname(id) + " · " + FARM.compost[id].bon.map(bonText).join(", ") + " (창고 " + pfmt((B.player.bankAll || {})[id] || 0) + ")"; if (pcfg.farm.compost === id) o.selected = true; csel.appendChild(o); });
        csel.addEventListener("change", function () { pcfg.farm.compost = csel.value || null; pchanged(); });
        cr.appendChild(csel); body.appendChild(cr); if (pcfg.farm.compost) active++;
        var cn = document.createElement("div"); cn.className = "note"; cn.textContent = "퇴비는 심기 1회당 1개 소모되며 재료 비용으로 들어갑니다 (수급 경로 변경 가능)."; body.appendChild(cn);
      }
      if (s.id === "Ranching") {
        var h6 = document.createElement("div"); h6.className = "sub-h"; h6.textContent = "사육 조건"; body.appendChild(h6);
        [["fed", "급식", "먹이를 계속 공급 (먹이는 재료 비용)"], ["treats", "간식", "24시간마다 간식 공급 (만족도 +, 재료 비용)"], ["pets", "쓰다듬기", "48시간마다 수동 (만족도 +4%)"]].forEach(function (o) {
          var l = document.createElement("label"); l.className = "shopup"; var cb = document.createElement("input"); cb.type = "checkbox"; cb.checked = pcfg.ranch[o[0]] !== false;
          cb.addEventListener("change", function () { pcfg.ranch[o[0]] = cb.checked; pchanged(); }); l.appendChild(cb);
          var sp3 = document.createElement("span"); sp3.innerHTML = esc(o[1]) + "<span class=bt>" + esc(o[2]) + "</span>"; l.appendChild(sp3); body.appendChild(l);
        });
        var nr = document.createElement("div"); nr.className = "tbslot"; nr.innerHTML = "<span class=sn>축사당 마리 수</span>"; var ni = document.createElement("input"); ni.type = "number"; ni.min = 1; ni.max = 70; ni.value = pcfg.ranch.count || 1; ni.style.width = "64px";
        ni.addEventListener("change", function () { pcfg.ranch.count = Math.max(1, Math.min(70, parseInt(ni.value) || 1)); pchanged(); }); nr.appendChild(ni);
        var nn = document.createElement("span"); nn.className = "bt"; nn.textContent = "같은 동물 수에 따른 무리 만족도, 축사 유지비 분담에 사용"; nr.appendChild(nn); body.appendChild(nr);
      }
      d.innerHTML = "<summary>" + esc(s.name) + " <span class=muted>Lv " + pcfg.levels[s.id] + "</span><span class=cnt>" + (active ? "보너스 " + active + "개" : "보너스 없음") + "</span></summary>";
      d.appendChild(body); box.appendChild(d);
    });
    // source overrides summary
    var ov = Object.keys(pcfg.src).filter(function (k) { return pcfg.src[k] && pcfg.src[k] !== "bank"; });
    $p("#psrcList").innerHTML = ov.length ? ov.map(function (k) { var s = srcOf(k); return "<div class=row style='justify-content:space-between'><span>" + esc(iname(k)) + " → " + esc(s === "shop" ? "상점 구매" : s.indexOf("make:") === 0 ? "직접 생산 (" + (REC[s.slice(5)] ? REC[s.slice(5)].name : s.slice(5)) + ")" : "창고") + "</span><button class='small ghost' data-rs='" + esc(k) + "'>↺</button></div>"; }).join("") : "<div class=note>모든 재료를 창고 판매가로 계산합니다. 상세 패널에서 재료별 수급 경로를 바꾸면 여기 모입니다.</div>";
    $p("#psrcList").querySelectorAll("[data-rs]").forEach(function (b) { b.addEventListener("click", function () { delete pcfg.src[b.dataset.rs]; pchanged(); }); });
  }
  function owned(id) { if ((B.player.bankAll || {})[id] > 0) return true; var tb = PB.save.toolbelt || {}; for (var s in tb) for (var sl in tb[s]) if (tb[s][sl][0] === id) return true; return false; }

  var PCOLS = [
    { k: "name", l: "활동", left: true, f: function (x) { return "<b>" + esc(x.r.name) + "</b>" + (x.R.c.info && x.R.c.info.anvil ? " <span class=it title='" + esc(x.R.c.info.anvil.name) + "'>⚒</span>" : "") + (x.r.catName ? "<span class=it> · " + esc(x.r.catName) + "</span>" : "") + (x.r.reqOther ? "<span class=it> · " + esc(x.r.reqOther.join(", ")) + "</span>" : ""); } },
    { k: "sk", l: "스킬", left: true, f: function (x) { return SK[x.r.sk].name; } },
    { k: "lvl", l: "Lv", f: function (x) { return x.r.lvl; } },
    { k: "perH", l: "행동/h", f: function (x) { return pfmt(x.perH, x.perH < 1 ? 2 : x.perH < 10 ? 1 : 0); }, tip: "완성(벌목/채굴/제작/병입 10회/소매치기/농사 심기~수확 1주기/동물 1마리 1시간) 횟수 / 시간" },
    { k: "main", l: "주 산출/h", left: true, f: function (x) { return x.main ? pfmt(x.R.outs[x.main], x.R.outs[x.main] < 10 ? 1 : 0) + " <span class=it>" + esc(iname(x.main)) + "</span>" : (x.R.gpH ? "<span class=it>GP</span>" : "–"); } },
    { k: "outV", l: "산출 가치/h", f: function (x) { return gp(x.outV); }, tip: "산출 아이템 판매가 합 + 직접 획득 GP" },
    { k: "inV", l: "재료 비용/h", f: function (x) { return x.inV ? gp(x.inV) : "–"; }, tip: "창고(판매가) 또는 상점 구매 기준. 직접 생산은 비용 0, 시간으로 환산" },
    { k: "netH", l: "순 창고가치/h", f: function (x) { return gp(x.netH); }, cls: function (x) { return x.netH < 0 ? "neg" : x.netH > 0 ? "pos" : ""; }, tip: "(산출 가치 − 재료 비용) ÷ (활동 시간 + 재료 직접 생산 시간)" },
    { k: "xpH", l: "XP/h", f: function (x) { return pfmt(x.xpH); } },
    { k: "vpx", l: "가치/XP", f: function (x) { return x.xpH > 0 ? pfmt(x.netH / x.xpH, 2) : "–"; } },
    { k: "time", l: "시간 배수", f: function (x) { return x.time > 1.0005 ? "×" + pfmt(x.time, 2) : "–"; }, tip: "재료를 직접 생산할 때 활동 1시간당 총 소요 시간" }
  ];
  function sortVal(x, k) { if (k === "name") return x.r.name; if (k === "sk") return x.r.sk; if (k === "lvl") return x.r.lvl; if (k === "main") return x.main ? x.R.outs[x.main] : 0; if (k === "vpx") return x.xpH > 0 ? x.netH / x.xpH : -1e18; return x[k]; }
  function pfiltered() {
    var q = pui.q.trim().toLowerCase();
    var list = ROWS.filter(function (x) {
      if (pcfg.onlyOk && !x.ok) return false;
      if (pui.skill && x.r.sk !== pui.skill) return false;
      if (q) { var hay = (x.r.name + " " + SK[x.r.sk].name + " " + (x.r.catName || "") + " " + Object.keys(x.R.outs).filter(function (k) { return x.R.outs[k] >= 0.005; }).map(iname).join(" ") + " " + Object.keys(x.R.ins).map(iname).join(" ")).toLowerCase(); if (hay.indexOf(q) < 0) return false; }
      return true;
    });
    list.sort(function (a, b) { var va = sortVal(a, pui.sortKey), vb = sortVal(b, pui.sortKey); var c = typeof va === "string" ? va.localeCompare(vb) : (va - vb); return pui.sortAsc ? c : -c; });
    return list;
  }
  function renderPMain() {
    var list = pfiltered(); $p("#pcount").textContent = list.length + " / " + ROWS.length + "개";
    var best = list.filter(function (x) { return x.netH > 0; })[0];
    $p("#pstats").innerHTML = [
      { k: "창고 가치 (세이브)", v: gp(PB.save.bankValue) + " <span class=muted style='font-size:11px'>+ GP " + pfmt(PB.save.gp) + "</span>" },
      { k: "최고 순가치/h (필터 내)", v: best ? gp(best.netH) + " <span class=muted style='font-size:11px'>" + esc(best.r.name) + "</span>" : "–" },
      { k: "적용 중 보너스", v: ENTS.length + "개" }
    ].map(function (c) { return "<div class=card><div class=k>" + c.k + "</div><div class=v>" + c.v + "</div></div>"; }).join("");
    $p("#ptableWrap").classList.toggle("hidden", pui.view !== "table"); $p("#pchartWrap").classList.toggle("hidden", pui.view !== "chart");
    if (pui.view === "chart") { renderPChart(list); return; }
    var th = $p("#pt thead"); th.innerHTML = "<tr>" + PCOLS.map(function (c) { return "<th class='" + (c.left ? "l " : "") + (c.k === pui.sortKey ? "on" : "") + "' data-k='" + c.k + "' title='" + (c.tip || "") + "'>" + c.l + (c.k === pui.sortKey ? "<span class=arr>" + (pui.sortAsc ? "▲" : "▼") + "</span>" : "") + "</th>"; }).join("") + "</tr>";
    th.querySelectorAll("th").forEach(function (h) { h.addEventListener("click", function () { var k = h.dataset.k; if (pui.sortKey === k) pui.sortAsc = !pui.sortAsc; else { pui.sortKey = k; pui.sortAsc = (k === "name" || k === "sk" || k === "lvl"); } renderPMain(); }); });
    var tb = $p("#pt tbody"); tb.innerHTML = "";
    list.forEach(function (x) {
      var tr = document.createElement("tr"); if (!x.ok) tr.className = "lock"; if (x.id === pui.sel) tr.classList.add("sel");
      tr.innerHTML = PCOLS.map(function (c) { return "<td class='" + (c.left ? "l " : "") + (c.cls ? c.cls(x) : "") + "'>" + c.f(x) + "</td>"; }).join("");
      tr.addEventListener("click", function () { pui.sel = x.id; renderPMain(); renderPDetail(); });
      tb.appendChild(tr);
    });
  }
  function renderPChart(list) {
    var top = list.slice().sort(function (a, b) { return b.netH - a.netH; }).slice(0, 25);
    var svg = $p("#pchart"); var W = Math.max(600, svg.parentNode.clientWidth - 40), rowH = 22, padL = 230, padR = 90, Hh = top.length * rowH + 30;
    svg.setAttribute("width", W); svg.setAttribute("height", Hh);
    var max = Math.max(1, Math.max.apply(null, top.map(function (x) { return Math.abs(x.netH); })));
    var sx = function (v) { return (W - padL - padR) * Math.abs(v) / max; };
    var h = "";
    top.forEach(function (x, i) {
      var y = 20 + i * rowH, w = Math.max(1, sx(x.netH));
      h += "<text class=lbl x='" + (padL - 8) + "' y='" + (y + 14) + "' text-anchor='end'>" + esc(x.r.name.length > 28 ? x.r.name.slice(0, 27) + "…" : x.r.name) + " <tspan fill='var(--faint)'>" + esc(SK[x.r.sk].name) + "</tspan></text>";
      h += "<rect class='bar" + (x.netH < 0 ? " neg" : "") + "' x='" + padL + "' y='" + (y + 4) + "' width='" + w + "' height='" + (rowH - 8) + "' rx='3'/>";
      h += "<text class=val x='" + (padL + w + 6) + "' y='" + (y + 14) + "'>" + gp(x.netH) + "</text>";
      h += "<rect class=hit data-id='" + esc(x.id) + "' x='0' y='" + y + "' width='" + W + "' height='" + rowH + "'/>";
    });
    h += "<text x='" + padL + "' y='12' fill='var(--faint)'>순 창고가치 / 시간 (GP) — 상위 " + top.length + "개</text>";
    svg.innerHTML = h;
    svg.querySelectorAll("rect.hit").forEach(function (r) { r.addEventListener("click", function () { pui.sel = r.dataset.id; renderPDetail(); }); });
  }

  function srcLabel(s, item) { if (s === "shop") return "상점 구매 " + pfmt(buyPrice(item), buyPrice(item) < 1 ? 2 : 0) + " GP"; if (s.indexOf("make:") === 0) { var r = REC[s.slice(5)]; return "직접 생산: " + (r ? r.name : s.slice(5)); } return "창고 (판매가 " + pfmt(sell(item)) + ")"; }
  function renderPDetail() {
    var d = $p("#pdetail"); var x = ROWS.filter(function (y) { return y.id === pui.sel; })[0];
    if (!x) { d.classList.add("hidden"); return; }
    d.classList.remove("hidden");
    var r = x.r, R = x.R, c = R.c, s = SK[r.sk];
    var h = "<div class=pd><div style='display:flex;justify-content:space-between;align-items:flex-start'><div><h2>" + esc(r.name) + "</h2><div class=meta>" + esc(s.name) + " Lv " + r.lvl + (r.catName ? " · " + esc(r.catName) : "") + (r.subName ? " · " + esc(r.subName) : "") + (r.reqOther ? " · " + esc(r.reqOther.join(", ")) : "") + (!x.ok ? " · <span class=crit>레벨 부족</span>" : "") + "</div></div><button class='ghost small' id='pdClose'>✕</button></div>";
    var cyc = c.t / 1000;
    var kv = [["순 창고가치/h", gp(x.netH) + " GP"], ["산출 가치/h", gp(x.outV) + " GP"], ["재료 비용/h", gp(x.inV) + " GP"], ["XP/h", pfmt(x.xpH)],
      ["1사이클", pfmt(cyc, cyc < 10 ? 2 : 1) + "s → " + pfmt(x.perH, x.perH < 10 ? 1 : 0) + "/h"]];
    if (c.info) {
      if (c.info.success != null) kv.push(["성공률", pc(c.info.success) + (c.info.prof != null ? " (숙련 " + c.info.prof + " / 난이도 " + c.info.diff + ")" : c.info.stealth != null ? " (은신 " + c.info.stealth + " / 감지 " + c.info.perc + ")" : "")]);
      if (c.info.hits != null) kv.push(["타격/완성", pfmt(c.info.hits, 2) + " × " + c.info.iv + "ms" + (c.info.hp ? " (체력 " + c.info.hp + ")" : c.info.p != null ? " (성공 " + pc(c.info.p) + ")" : "")]);
      if (c.info.actions != null) kv.push(["행동/완성", pfmt(c.info.actions, 2) + " × " + c.info.iv + "ms (" + c.info.steps + "단계)"]);
      if (c.info.anvil) kv.push([c.info.anvil.name, "제품 → GP ×" + pfmt(c.info.anvil.sale, 3) + " · XP ×" + pfmt(c.info.anvil.xp, 3) + " · 수집품 " + oneIn(c.info.anvil.col) + " 완성"]);
      if (c.info.ivMin != null) kv.push(["간격", c.info.ivMin / 1000 + "–" + c.info.ivMax / 1000 + "s, 물고기 " + pc(c.info.fish)]);
      if (c.info.bottles) kv.push(["배치", (c.info.ivP + c.info.ivH + c.info.ivS) / 1000 + "s + 병입 " + c.info.bottles + "×" + c.info.ivB / 1000 + "s"]);
      if (c.info.stunIv != null) kv.push(["실패 시", "기절 " + c.info.stunIv / 1000 + "s, HP 손실 " + pfmt(R.hpH) + "/h"]);
      if (r.kind === "farm") {
        kv.push(["성장 시간", pfmt(c.info.iv / 60000) + "분" + (c.info.regrows ? " + 재수확 " + c.info.regrows + "회 × " + pfmt(c.info.regrowIv / 60000) + "분" : "")]);
        kv.push(["수확량/회", pfmt(c.info.qty) + " (병해 " + pfmt(c.info.dis) + " / 해충 " + pfmt(c.info.pest) + " → ×" + pfmt(c.info.adj, 2) + ")"]);
        kv.push(["관리", (c.info.canWater ? (c.info.water ? "물주기 ✓" : "물주기 ✗") : "물 불필요") + " · " + (c.info.canCompost ? (c.info.compost ? "퇴비 " + iname(c.info.compost) : "퇴비 없음") : "퇴비 불가")]);
      }
      if (r.kind === "mill") kv.push(["간격", c.info.iv / 1000 + "s (제분소 기본 5분)"]);
      if (r.kind === "ranch") {
        kv.push(["행복도", pc(c.info.happy) + " (만족도 " + pc(c.info.sat) + (c.info.treatSat ? ", 간식 +" + pc(c.info.treatSat) : "") + (c.info.packSat ? ", 무리 +" + pc(c.info.packSat) : "") + ")"]);
        kv.push(["수명 · 성장", pfmt(c.info.life / 3600000) + "h · 성체까지 " + pfmt(c.info.vIv / 3600000) + "h (유년기 " + pc(c.info.tc) + ", 산출 −50%)"]);
        kv.push(["성체 변이 기대", "산출 " + (c.info.adultPQ >= 0 ? "+" : "") + pc(c.info.adultPQ) + " (가중 평균)"]);
        kv.push(["축사", (c.info.enc || "없음") + " · " + c.info.cnt + "마리"]);
      }
    }
    if (x.time > 1.0005) kv.push(["체인 시간", "활동 1h + 재료 생산 " + pfmt((x.time - 1) * 60) + "분"]);
    h += "<div class=kv>" + kv.map(function (p) { return "<div><div class=k>" + p[0] + "</div><div class=v>" + p[1] + "</div></div>"; }).join("") + "</div>";
    // outputs
    h += "<h3>산출 (시간당)</h3><table>";
    var trace = Object.keys(R.outs).filter(function (k) { return R.outs[k] < 0.005; }), traceV = 0; trace.forEach(function (k) { traceV += R.outs[k] * sell(k); });
    Object.keys(R.outs).filter(function (k) { return R.outs[k] >= 0.005; }).sort(function (a, b) { return R.outs[b] * sell(b) - R.outs[a] * sell(a); }).forEach(function (k) { h += "<tr><td>" + esc(iname(k)) + "</td><td class=r>" + pfmt(R.outs[k], R.outs[k] < 10 ? 2 : 1) + "</td><td class=r>× " + pfmt(sell(k)) + "</td><td class=r>" + gp(R.outs[k] * sell(k)) + "</td></tr>"; });
    if (trace.length) h += "<tr><td title='" + esc(trace.map(function (k) { return iname(k) + " " + (R.outs[k] * 1e6).toFixed(1) + "/백만h"; }).join(", ")) + "'>희귀 산출 " + trace.length + "종 (기대값)</td><td class=r>&lt;0.01</td><td></td><td class=r>" + gp(traceV) + "</td></tr>";
    if (R.gpH) h += "<tr><td>" + (R.gpH < 0 ? "GP (구매비를 수명으로 분할)" : c.info && c.info.anvil ? "GP (" + esc(c.info.anvil.name) + ": 제품 판매가 ×" + pfmt(c.info.anvil.sale, 3) + ")" : "GP (직접 획득)") + "</td><td></td><td></td><td class=r>" + gp(R.gpH) + "</td></tr>";
    h += "</table>";
    // inputs with sourcing
    var ins = Object.keys(R.ins);
    if (ins.length) {
      h += "<h3>재료 수급 (시간당)</h3><div class=note style='margin:0 0 6px'>재료마다 어디서 가져올지 고르면 순가치가 다시 계산됩니다. 칩은 각 선택지일 때의 <b>순 창고가치/h</b>입니다.</div><table>";
      ins.forEach(function (k) {
        var cur = srcOf(k), opts = [{ v: "bank", l: srcLabel("bank", k) }];
        if (buyPrice(k) != null) opts.push({ v: "shop", l: srcLabel("shop", k) + (ITEMS[k].buyReq ? " (" + ITEMS[k].buyReq.join(", ") + ")" : "") });
        (PRODUCERS[k] || []).filter(function (p) { return p !== r.id; }).slice(0, 8).forEach(function (p) { opts.push({ v: "make:" + p, l: "직접 생산: " + REC[p].name + " (" + SK[REC[p].sk].name + ", " + pfmt(RATES[p].outs[k], 1) + "/h)" }); });
        var part = x.chain.parts.filter(function (p) { return p.item === k; })[0];
        h += "<tr><td><b>" + esc(iname(k)) + "</b><br><span class=src>필요 " + pfmt(R.ins[k], R.ins[k] < 10 ? 2 : 1) + "/h · 보유 " + pfmt((B.player.bankAll || {})[k] || 0) + "</span></td><td colspan=3>";
        h += "<select data-src='" + esc(k) + "'>" + opts.map(function (o) { return "<option value='" + esc(o.v) + "'" + (o.v === cur ? " selected" : "") + ">" + esc(o.l) + "</option>"; }).join("") + "</select>";
        h += "<div class=cmp>" + opts.map(function (o) { var alt = chain(r.id, 1, 0, [], { item: k, src: o.v }); var v = alt.time > 0 ? alt.value / alt.time : 0; return "<span class='" + (o.v === cur ? "on" : "") + "' data-alt='" + esc(k) + "|" + esc(o.v) + "' title='" + esc(o.l) + "'>" + (o.v === "bank" ? "창고" : o.v === "shop" ? "상점" : "생산·" + esc(REC[o.v.slice(5)].name)) + " " + gp(v) + "</span>"; }).join("") + "</div>";
        if (part && part.cost) h += "<div class=src>비용 " + gp(part.cost) + " GP/h</div>";
        h += "</td></tr>";
      });
      h += "</table>";
      var chainParts = x.chain.parts.filter(function (p) { return p.sub; });
      if (chainParts.length) { h += "<h3>생산 체인</h3>"; h += chainLines(x.chain, 0); }
    }
    // bonuses
    h += "<h3>적용된 보너스</h3>";
    if (c.lines.length) { h += "<table>" + c.lines.map(function (l) { return "<tr><td>" + esc(l.k) + "</td><td class=r>" + esc(String(l.v)) + "</td><td class=src>" + esc((l.src || []).map(function (s) { return s.src; }).join(", ")) + "</td></tr>"; }).join("") + "</table>"; }
    else h += "<div class=note>이 활동에 적용되는 보너스가 없습니다.</div>";
    var notes = c.notes.slice(); if (r.kind === "thief") notes.push("HP 손실은 음식 비용으로 환산하지 않음");
    notes.push("소모성 툴벨트 아이템(물약 등)의 소모 비용은 미반영");
    h += "<div class=warnbox>" + notes.map(esc).join("<br>") + "</div></div>";
    d.innerHTML = h;
    $p("#pdClose").addEventListener("click", function () { pui.sel = null; renderPMain(); renderPDetail(); });
    d.querySelectorAll("select[data-src]").forEach(function (sel) { sel.addEventListener("change", function () { if (sel.value === "bank") delete pcfg.src[sel.dataset.src]; else pcfg.src[sel.dataset.src] = sel.value; pchanged(); }); });
    d.querySelectorAll(".cmp span").forEach(function (sp) { sp.addEventListener("click", function () { var a = sp.dataset.alt.split("|"); if (a[1] === "bank") delete pcfg.src[a[0]]; else pcfg.src[a[0]] = a[1]; pchanged(); }); });
  }
  function chainLines(ch, depth) {
    var h = "";
    ch.parts.forEach(function (p) {
      if (!p.sub) return; var pid = p.src.slice(5), R = RATES[pid];
      h += "<div class=chain style='margin-left:" + (10 + depth * 14) + "px'>↳ " + esc(iname(p.item)) + " " + pfmt(p.need, 1) + "개 ← <b>" + esc(REC[pid].name) + "</b> " + pfmt(p.sub.time * 60, 1) + "분 (" + pfmt(R.outs[p.item], 1) + "/h)" + (p.sub.value - p.need * sell(p.item) ? ", 부산물·비용 " + gp(p.sub.value - p.need * sell(p.item)) + " GP" : "") + "</div>";
      h += chainLines(p.sub, depth + 1);
    });
    return h;
  }

  /* ---------------------------------- wiring ---------------------------------- */
  function initProfitUI() {
    var sks = $p("#pskill"); SKILLS.forEach(function (s) { var o = document.createElement("option"); o.value = s.id; o.textContent = s.name; sks.appendChild(o); });
    sks.addEventListener("change", function () { pui.skill = sks.value; renderPMain(); });
    $p("#pq").addEventListener("input", function (e) { pui.q = e.target.value; renderPMain(); });
    $p("#ponlyOk").checked = !!pcfg.onlyOk; $p("#ponlyOk").addEventListener("change", function (e) { pcfg.onlyOk = e.target.checked; LS.set("pcfg", pcfg); renderPMain(); });
    $p("#pviewSeg").querySelectorAll("button").forEach(function (b) { b.addEventListener("click", function () { pui.view = b.dataset.v; $p("#pviewSeg").querySelectorAll("button").forEach(function (x) { x.classList.toggle("on", x === b); }); renderPMain(); }); });
    $p("#presetSave2").addEventListener("click", function () { var n = prompt("프리셋 이름"); if (!n) return; var ps = LS.get("ppresets", {}); ps[n] = JSON.parse(JSON.stringify(pcfg)); LS.set("ppresets", ps); fillPPresets(); });
    $p("#presetDel2").addEventListener("click", function () { var n = $p("#presetSel2").value; if (!n) return; var ps = LS.get("ppresets", {}); delete ps[n]; LS.set("ppresets", ps); fillPPresets(); });
    $p("#presetSel2").addEventListener("change", function () { var n = $p("#presetSel2").value; var ps = LS.get("ppresets", {}); if (n && ps[n]) { pcfg = ps[n]; pchanged(); } });
    $p("#presetReset2").addEventListener("click", function () {
      var fallback = function () { var keep = { src: pcfg.src, onlyOk: pcfg.onlyOk }; pcfg = defaultPcfg(); pcfg.src = keep.src || {}; pcfg.onlyOk = keep.onlyOk; pchanged(); };
      if (M2.refreshSave) M2.refreshSave(fallback); else fallback();
    });
    fillPPresets();
    // tabs
    document.querySelectorAll(".tabs button").forEach(function (b) { b.addEventListener("click", function () { showTab(b.dataset.tab); }); });
    var t = LS.get("tab", "combat"); showTab(t);
    window.addEventListener("resize", function () { if (pui.view === "chart" && !$p("#profitTab").classList.contains("hidden")) renderPMain(); });
    // combat equipment affects skilling bonuses -> refresh when the combat config changes
    var lastEq = JSON.stringify(ccfg().equipment || {});
    setInterval(function () { var now = JSON.stringify(ccfg().equipment || {}); if (now !== lastEq) { lastEq = now; pchanged(true); } }, 1500);
  }
  function fillPPresets() { var sel = $p("#presetSel2"); var ps = LS.get("ppresets", {}); sel.innerHTML = "<option value=''>프리셋 불러오기…</option>" + Object.keys(ps).map(function (k) { return "<option>" + esc(k) + "</option>"; }).join(""); }
  function showTab(t) {
    document.querySelectorAll(".tabs button").forEach(function (b) { b.classList.toggle("on", b.dataset.tab === t); });
    $p("#combatTab").classList.toggle("hidden", t !== "combat"); $p("#profitTab").classList.toggle("hidden", t !== "profit");
    document.querySelector(".runbar").classList.toggle("hidden", t !== "combat"); $p("#bankBar").classList.toggle("hidden", t !== "profit");
    LS.set("tab", t);
    if (t === "profit" && pui.view === "chart") renderPMain();
  }
  initProfitUI();
  pchanged(true);
  $p("#bankBar").innerHTML = "창고 가치 <b>" + gp(PB.save.bankValue) + "</b> GP · 보유 GP <b>" + pfmt(PB.save.gp) + "</b>";
  window.Profit = { compute: compute, chain: chain, rates: function () { return RATES; }, rows: function () { return ROWS; }, pcfg: function () { return pcfg; }, recompute: function () { pchanged(true); } };
})();
