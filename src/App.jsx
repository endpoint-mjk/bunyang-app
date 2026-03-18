import { useState, useEffect, useCallback, useMemo } from "react";

const TIER = {
  S: { l: "핵심", c: "#7C3AED", bg: "#F5F3FF", d: "강남권 · 주요신도시" },
  A: { l: "유망", c: "#2563EB", bg: "#EFF6FF", d: "준핵심 · 성장 잠재력" },
  B: { l: "보통", c: "#059669", bg: "#ECFDF5", d: "안정적 · 가성비" },
  C: { l: "관망", c: "#9CA3AF", bg: "#F9FAFB", d: "외곽 · 상승률 저조" },
};

const NOW = new Date();
function stat(i) {
  const p = (s) => {
    if (!s) return null;
    const d = s.split("-");
    return new Date(+d[0], +d[1] - 1, +d[2]);
  };
  const s = p(i.ss), e = p(i.se);
  if (!s) return { l: "공고", c: "#9CA3AF", p: 3 };
  const d = Math.ceil((s - NOW) / 864e5);
  if (NOW > e) return { l: "마감", c: "#9CA3AF", p: 4 };
  if (NOW >= s && NOW <= e) return { l: "접수중", c: "#EF4444", p: 0 };
  if (d <= 3) return { l: `D-${d}`, c: "#EF4444", p: 1 };
  return { l: `D-${d}`, c: "#2563EB", p: 2 };
}
function fd(s) {
  if (!s) return "";
  const [, m, d] = s.split("-");
  return `${+m}/${+d}`;
}

function getKbRate(kb, city, dist) {
  if (!kb?.data) return null;
  const key = `${city}_${dist}`;
  if (kb.data[key] !== undefined) return kb.data[key];
  const cityKey = Object.keys(kb.data).find(
    (k) => k.startsWith(city + "_") && dist && k.includes(dist)
  );
  return cityKey ? kb.data[cityKey] : null;
}

// ── Card ─────────────────────────────────────────────────────────────
function Card({ item, saved, onSave, onOpen, dim, kbRate }) {
  const st = stat(item),
    tier = item.tier,
    big = (item.types || []).filter((t) => t.py >= 24);
  return (
    <div
      onClick={() => onOpen(item)}
      style={{
        background: "#fff", borderRadius: 14, padding: "14px 16px",
        marginBottom: 10,
        border: st.c === "#EF4444" && st.l === "접수중" ? "1.5px solid #FCA5A5" : "1px solid #F0F0F0",
        cursor: "pointer", opacity: dim ? 0.4 : 1, position: "relative",
      }}
    >
      {dim && (
        <div style={{ position: "absolute", top: 8, right: 12, fontSize: 10, color: "#bbb", background: "#f5f5f5", padding: "1px 6px", borderRadius: 4 }}>
          조건 미달
        </div>
      )}
      <div style={{ display: "flex", gap: 5, alignItems: "center", flexWrap: "wrap", marginBottom: 5 }}>
        <span style={{ fontSize: 10, fontWeight: 700, color: item.src === "청약홈" ? "#6366F1" : item.src === "LH" ? "#059669" : "#D97706", background: (item.src === "청약홈" ? "#6366F1" : item.src === "LH" ? "#059669" : "#D97706") + "10", padding: "1px 6px", borderRadius: 4 }}>
          {item.src}
        </span>
        <span style={{ fontSize: 10, color: "#888", background: "#F3F4F6", padding: "1px 6px", borderRadius: 4 }}>{item.cat}</span>
        {tier && TIER[tier] && (
          <span style={{ fontSize: 10, fontWeight: 600, color: TIER[tier].c, background: TIER[tier].bg, border: `1px solid ${TIER[tier].c}30`, padding: "1px 7px", borderRadius: 10 }}>
            {tier} {TIER[tier].l}
          </span>
        )}
        <span style={{ fontSize: 11, fontWeight: 600, color: st.c, background: st.c + "14", padding: "2px 8px", borderRadius: 20 }}>
          {st.l === "접수중" ? "\u{1F525} 접수중" : st.l}
        </span>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: 15, color: "#111", marginBottom: 3, lineHeight: 1.3 }}>{item.name}</div>
          <div style={{ fontSize: 12, color: "#777", marginBottom: 6 }}>
            {item.loc} · {(item.units || 0).toLocaleString()}세대
            {kbRate !== null && (
              <>
                {" · "}
                <span style={{ fontWeight: 700, color: kbRate >= 0 ? "#DC2626" : "#2563EB" }}>
                  {kbRate >= 0 ? "▲" : "▼"}{Math.abs(kbRate).toFixed(2)}%
                </span>{" "}주간
              </>
            )}
          </div>
        </div>
        <button onClick={(e) => { e.stopPropagation(); onSave(item.id); }} style={{ background: "none", border: "none", fontSize: 20, cursor: "pointer", padding: 2, lineHeight: 1 }}>
          {saved ? "❤️" : "🤍"}
        </button>
      </div>
      {(item.types || []).length > 0 && (
        <div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>
          {(big.length > 0 ? big : item.types).slice(0, 3).map((t, i) => (
            <span key={i} style={{ fontSize: 11, background: t.py >= 24 ? "#EFF6FF" : "#F8F9FA", border: `1px solid ${t.py >= 24 ? "#BFDBFE" : "#EAEAEA"}`, borderRadius: 6, padding: "3px 7px", color: "#444" }}>
              <b style={{ color: "#111" }}>{t.py}평</b> {t.a}㎡{" "}
              {t.p && <span style={{ color: "#2563EB", fontWeight: 700 }}>{t.p}</span>}
            </span>
          ))}
          {item.types.length > 3 && <span style={{ fontSize: 11, color: "#bbb", padding: "3px 4px" }}>+{item.types.length - 3}</span>}
        </div>
      )}
      {item.ss && (
        <div style={{ fontSize: 11, color: "#aaa", marginTop: 6 }}>
          청약 {fd(item.ss)}~{fd(item.se)}{item.mv && ` · 입주 ${item.mv}`}
        </div>
      )}
    </div>
  );
}

// ── Detail ────────────────────────────────────────────────────────────
function Detail({ item, onClose, saved, onSave, kbRate, kbUpdated }) {
  const st = stat(item), tier = item.tier;
  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 100, background: "#fff", overflowY: "auto" }}>
      <div style={{ background: "linear-gradient(135deg,#0F172A,#1E3A8A)", padding: "52px 20px 24px", color: "#fff", position: "relative" }}>
        <button onClick={onClose} style={{ position: "absolute", top: 16, left: 16, background: "rgba(255,255,255,.15)", border: "none", borderRadius: 20, width: 34, height: 34, color: "#fff", fontSize: 18, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>←</button>
        <button onClick={() => onSave(item.id)} style={{ position: "absolute", top: 16, right: 16, background: "rgba(255,255,255,.15)", border: "none", borderRadius: 20, width: 34, height: 34, fontSize: 16, cursor: "pointer" }}>{saved ? "❤️" : "🤍"}</button>
        <div style={{ display: "flex", gap: 6, marginBottom: 10, flexWrap: "wrap" }}>
          {tier && TIER[tier] && <span style={{ fontSize: 11, fontWeight: 600, color: TIER[tier].c, background: TIER[tier].bg, padding: "2px 8px", borderRadius: 10 }}>{tier} {TIER[tier].l}</span>}
          <span style={{ fontSize: 11, fontWeight: 600, color: "#fff", background: "rgba(255,255,255,.2)", padding: "2px 8px", borderRadius: 10 }}>{st.l === "접수중" ? "\u{1F525} 접수중" : st.l}</span>
        </div>
        <h2 style={{ margin: "0 0 4px", fontSize: 20, fontWeight: 700 }}>{item.name}</h2>
        <p style={{ margin: 0, fontSize: 13, opacity: 0.8 }}>{item.loc}</p>
      </div>

      {kbRate !== null && (
        <div style={{ margin: "16px 20px 0", background: "#F8FAFC", borderRadius: 12, padding: "14px 16px", border: "1px solid #E2E8F0" }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: "#475569", marginBottom: 8 }}>
            KB부동산 시세동향 {kbUpdated && `(${kbUpdated})`}
          </div>
          <div style={{ display: "flex", gap: 12 }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 11, color: "#94A3B8" }}>주간 상승률</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: kbRate >= 0 ? "#DC2626" : "#2563EB" }}>
                {kbRate >= 0 ? "+" : ""}{kbRate.toFixed(2)}%
              </div>
            </div>
            {tier && (
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 11, color: "#94A3B8" }}>투자등급</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: TIER[tier].c }}>{tier} {TIER[tier].l}</div>
              </div>
            )}
          </div>
        </div>
      )}

      <div style={{ padding: "16px 20px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 20 }}>
          {[
            { l: "공급세대", v: `${(item.units || 0).toLocaleString()}세대` },
            { l: "시행사", v: item.bld || "-" },
            { l: "청약기간", v: item.ss ? `${fd(item.ss)}~${fd(item.se)}` : "-" },
            { l: "입주예정", v: item.mv || "-" },
          ].map((s, i) => (
            <div key={i} style={{ background: "#F8F9FB", borderRadius: 10, padding: "12px 14px" }}>
              <div style={{ fontSize: 11, color: "#999", marginBottom: 3 }}>{s.l}</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: "#222" }}>{s.v}</div>
            </div>
          ))}
        </div>

        {(item.types || []).length > 0 && (
          <>
            <h3 style={{ fontSize: 15, fontWeight: 600, margin: "0 0 10px" }}>주택형별 정보</h3>
            <div style={{ border: "1px solid #EAEAEA", borderRadius: 12, overflow: "hidden" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", background: "#F8F9FB", padding: "10px 12px", fontSize: 11, color: "#888", fontWeight: 600 }}>
                <span>평형</span><span>전용</span><span style={{ textAlign: "center" }}>세대수</span><span style={{ textAlign: "right" }}>분양가</span>
              </div>
              {item.types.map((t, i) => (
                <div key={i} style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", padding: "12px", borderTop: "1px solid #F0F0F0", fontSize: 13, background: t.py >= 24 ? "#FAFBFF" : "transparent" }}>
                  <span style={{ fontWeight: 700 }}>{t.py}평</span>
                  <span style={{ color: "#666" }}>{t.a}㎡</span>
                  <span style={{ textAlign: "center", color: "#666" }}>{t.u}세대</span>
                  <span style={{ textAlign: "right", color: "#2563EB", fontWeight: 700 }}>{t.p}</span>
                </div>
              ))}
            </div>
          </>
        )}

        {item.url && (
          <a href={item.url} target="_blank" rel="noopener noreferrer" style={{ display: "block", textAlign: "center", margin: "20px 0", background: "#1E3A8A", color: "#fff", borderRadius: 12, padding: 14, fontSize: 14, fontWeight: 600, textDecoration: "none" }}>
            공고 원문 보기
          </a>
        )}
        <p style={{ fontSize: 11, color: "#ccc", textAlign: "center", marginBottom: 80 }}>* 정확한 정보는 반드시 청약홈에서 확인하세요</p>
      </div>
    </div>
  );
}

// ── Settings ──────────────────────────────────────────────────────────
function Prefs({ P, uP, kbUpdated }) {
  const tog = (k, v) => {
    const a = P[k] || [];
    uP({ ...P, [k]: a.includes(v) ? a.filter((x) => x !== v) : [...a, v] });
  };
  const Chip = ({ l, on, fn }) => (
    <button onClick={fn} style={{ background: on ? "#1E3A8A" : "#fff", color: on ? "#fff" : "#555", border: on ? "1.5px solid #1E3A8A" : "1px solid #E0E0E0", borderRadius: 20, padding: "6px 14px", fontSize: 12, fontWeight: 500, cursor: "pointer", whiteSpace: "nowrap" }}>
      {l}
    </button>
  );
  return (
    <div style={{ padding: "4px 0" }}>
      <div style={{ background: "#fff", borderRadius: 14, padding: 20, marginBottom: 12, border: "1px solid #F0F0F0" }}>
        <h3 style={{ fontSize: 15, fontWeight: 700, margin: "0 0 2px", color: "#111" }}>최소 평수</h3>
        <p style={{ fontSize: 12, color: "#999", margin: "0 0 10px" }}>
          {P.minPy}평 ({Math.round(P.minPy * 3.306)}㎡) 이상만 표시
        </p>
        <input type="range" min={10} max={50} step={1} value={P.minPy} onChange={(e) => uP({ ...P, minPy: +e.target.value })} style={{ width: "100%" }} />
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#bbb" }}>
          <span>10평</span>
          <span style={{ fontWeight: 600, color: "#1E3A8A" }}>{P.minPy}평</span>
          <span>50평</span>
        </div>
      </div>

      <div style={{ background: "#fff", borderRadius: 14, padding: 20, marginBottom: 12, border: "1px solid #F0F0F0" }}>
        <h3 style={{ fontSize: 15, fontWeight: 700, margin: "0 0 2px", color: "#111" }}>투자등급 필터</h3>
        <p style={{ fontSize: 12, color: "#999", margin: "0 0 10px" }}>KB부동산 시세 기반 지역 등급</p>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {Object.entries(TIER).map(([k, v]) => {
            const on = !(P.exT || []).includes(k);
            return (
              <div key={k} onClick={() => tog("exT", k)} style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 12px", borderRadius: 10, cursor: "pointer", background: on ? v.bg : "#FAFAFA", border: `1px solid ${on ? v.c + "30" : "#EEE"}`, opacity: on ? 1 : 0.5 }}>
                <div style={{ width: 28, height: 28, borderRadius: 8, background: on ? v.c : "#D1D5DB", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: 12, fontWeight: 700 }}>{k}</div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: on ? "#222" : "#999" }}>{v.l}</div>
                  <div style={{ fontSize: 11, color: "#999" }}>{v.d}</div>
                </div>
                <div style={{ width: 20, height: 20, borderRadius: 4, border: `2px solid ${on ? v.c : "#D1D5DB"}`, background: on ? v.c : "transparent", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  {on && <span style={{ color: "#fff", fontSize: 12, fontWeight: 700 }}>✓</span>}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div style={{ background: "#fff", borderRadius: 14, padding: 20, marginBottom: 12, border: "1px solid #F0F0F0" }}>
        <h3 style={{ fontSize: 15, fontWeight: 700, margin: "0 0 2px", color: "#111" }}>관심 유형</h3>
        <p style={{ fontSize: 12, color: "#999", margin: "0 0 10px" }}>빈칸이면 전체 표시</p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {["APT", "공공분양", "무순위", "오피스텔"].map((c) => (
            <Chip key={c} l={c} on={(P.cats || []).includes(c)} fn={() => tog("cats", c)} />
          ))}
        </div>
      </div>

      <div style={{ background: "#fff", borderRadius: 14, padding: 20, border: "1px solid #F0F0F0" }}>
        <h3 style={{ fontSize: 15, fontWeight: 700, margin: "0 0 4px", color: "#111" }}>데이터 출처</h3>
        {[
          { n: "청약홈 API", s: "분양정보", c: "#6366F1" },
          { n: "LH 청약센터", s: "공공분양/임대", c: "#059669" },
          { n: "SH 서울주택도시공사", s: "서울 공공주택", c: "#D97706" },
          { n: "KB부동산 데이터허브", s: "주간 상승률", c: "#DC2626" },
        ].map((s, i) => (
          <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderTop: i ? "1px solid #F5F5F5" : "none" }}>
            <span style={{ fontSize: 13, color: "#333" }}>{s.n}</span>
            <span style={{ fontSize: 11, color: s.c, fontWeight: 600 }}>{s.s}</span>
          </div>
        ))}
        {kbUpdated && <div style={{ marginTop: 8, fontSize: 11, color: "#aaa" }}>KB 시세 기준: {kbUpdated}</div>}
      </div>
    </div>
  );
}

// ── App ──────────────────────────────────────────────────────────────
const TABS = [
  { id: "match", ic: "✨", l: "맞춤" },
  { id: "home", ic: "🏠", l: "전체" },
  { id: "saved", ic: "❤️", l: "관심" },
  { id: "prefs", ic: "⚙️", l: "설정" },
];
const DEF_P = { minPy: 24, exT: ["C"], cats: [] };

export default function App() {
  const [tab, setTab] = useState("match");
  const [det, setDet] = useState(null);
  const [raw, setRaw] = useState(null);
  const [kb, setKb] = useState(null);
  const [updated, setUpdated] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sv, setSv] = useState(() => {
    try { const v = localStorage.getItem("bsv"); return v ? new Set(JSON.parse(v)) : new Set(); } catch { return new Set(); }
  });
  const [P, setP] = useState(() => {
    try { const v = localStorage.getItem("bpr"); return v ? { ...DEF_P, ...JSON.parse(v) } : DEF_P; } catch { return DEF_P; }
  });
  const [q, setQ] = useState("");

  useEffect(() => {
    setLoading(true);
    fetch(import.meta.env.BASE_URL + "data.json?t=" + Date.now())
      .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then((d) => {
        setRaw(d.items || []);
        setKb(d.kb || null);
        setUpdated(d.updated || "");
        setLoading(false);
      })
      .catch(() => {
        setError("데이터를 불러올 수 없습니다. GitHub Actions가 아직 실행되지 않았을 수 있어요.");
        setRaw([]);
        setLoading(false);
      });
  }, []);

  const ps = useCallback((k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} }, []);
  const tSv = useCallback((id) => {
    setSv((p) => {
      const n = new Set(p);
      n.has(id) ? n.delete(id) : n.add(id);
      ps("bsv", [...n]);
      return n;
    });
  }, [ps]);
  const uP = useCallback((p) => { setP(p); ps("bpr", p); }, [ps]);

  const data = useMemo(() =>
    (raw || []).map((i) => {
      const tier = i.tier || "B";
      const types = i.types || [];
      const big = types.some((t) => (t.py || 0) >= (P.minPy || 24));
      const catOk = (P.cats || []).length === 0 || (P.cats || []).includes(i.cat);
      const tierOk = !(P.exT || []).includes(tier);
      const kbRate = getKbRate(kb, i.city, i.dist);
      return { ...i, tier, out: !big || !tierOk || !catOk, kbRate };
    }),
    [raw, P, kb]
  );

  const get = useCallback((t) => {
    let r = data;
    if (t === "match") r = r.filter((i) => !i.out);
    if (t === "saved") r = r.filter((i) => sv.has(i.id));
    if (q) {
      const s = q.toLowerCase();
      r = r.filter((i) =>
        (i.name || "").toLowerCase().includes(s) ||
        (i.loc || "").toLowerCase().includes(s) ||
        (i.bld || "").toLowerCase().includes(s) ||
        (i.dist || "").toLowerCase().includes(s)
      );
    }
    r.sort((a, b) => stat(a).p - stat(b).p);
    return r;
  }, [data, sv, q]);

  const mc = useMemo(() => data.filter((i) => !i.out && stat(i).p < 3).length, [data]);
  const items = get(tab);

  // KB 시세 요약 (서울/경기/인천 전체 변동률)
  const kbSummary = useMemo(() => {
    if (!kb?.data) return [];
    const cities = ["서울", "경기", "인천"];
    return cities.map((c) => {
      const key = `${c}_전체`;
      const rate = kb.data[key];
      return rate !== undefined ? { n: c, rate } : null;
    }).filter(Boolean);
  }, [kb]);

  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", fontFamily: "-apple-system,'Noto Sans KR',sans-serif" }}>
      <div style={{ textAlign: "center", color: "#aaa" }}>
        <div style={{ fontSize: 40, marginBottom: 12 }}>🏠</div>
        <div style={{ fontSize: 15, fontWeight: 600, color: "#333", marginBottom: 4 }}>분양알리미</div>
        <div style={{ fontSize: 13 }}>데이터 불러오는 중...</div>
      </div>
    </div>
  );

  return (
    <div style={{ fontFamily: "-apple-system,BlinkMacSystemFont,'Noto Sans KR',sans-serif", background: "#F5F6F8", minHeight: "100vh", maxWidth: 480, margin: "0 auto", position: "relative", paddingBottom: 68 }}>
      {det && (
        <Detail
          item={det}
          onClose={() => setDet(null)}
          saved={sv.has(det.id)}
          onSave={tSv}
          kbRate={getKbRate(kb, det.city, det.dist)}
          kbUpdated={kb?.updated}
        />
      )}

      {/* Header */}
      <div style={{ padding: "14px 20px 10px", background: "#fff", borderBottom: "1px solid #F0F0F0", position: "sticky", top: 0, zIndex: 10 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <div>
            <h1 style={{ margin: 0, fontSize: 20, fontWeight: 800, color: "#0F172A", letterSpacing: "-0.3px" }}>분양알리미</h1>
            <p style={{ margin: 0, fontSize: 11, color: "#94A3B8" }}>
              {updated ? `데이터: ${updated} · ` : ""}
              {P.minPy}평↑ · {["S", "A", "B", "C"].filter((t) => !(P.exT || []).includes(t)).join("/")}등급
            </p>
          </div>
          {mc > 0 && tab !== "match" && (
            <button onClick={() => setTab("match")} style={{ background: "#EF4444", color: "#fff", border: "none", borderRadius: 20, padding: "6px 14px", fontSize: 12, fontWeight: 700, cursor: "pointer" }}>
              {mc}건 맞춤
            </button>
          )}
        </div>

        {/* KB 시세 요약 카드 */}
        {tab !== "prefs" && kbSummary.length > 0 && (
          <div style={{ display: "flex", gap: 8, padding: "0 0 8px", overflowX: "auto" }}>
            {kbSummary.map((c) => (
              <div key={c.n} style={{ flex: "0 0 auto", background: "#F8FAFC", borderRadius: 10, padding: "8px 14px", border: "1px solid #E2E8F0", minWidth: 95 }}>
                <div style={{ fontSize: 11, color: "#64748B", marginBottom: 2 }}>{c.n} 주간</div>
                <span style={{ fontSize: 15, fontWeight: 700, color: c.rate >= 0 ? "#DC2626" : "#2563EB" }}>
                  {c.rate >= 0 ? "+" : ""}{c.rate.toFixed(2)}%
                </span>
              </div>
            ))}
          </div>
        )}

        {error && !raw?.length && (
          <div style={{ background: "#FEF3C7", borderRadius: 10, padding: "10px 14px", marginBottom: 8, fontSize: 12, color: "#92400E" }}>{error}</div>
        )}

        {tab !== "prefs" && tab !== "saved" && (
          <div style={{ position: "relative", marginTop: 4 }}>
            <input type="text" placeholder="단지명, 지역, 건설사 검색" value={q} onChange={(e) => setQ(e.target.value)} style={{ width: "100%", padding: "9px 14px 9px 34px", border: "1px solid #E8E8E8", borderRadius: 10, fontSize: 13, background: "#F8F9FA", outline: "none", boxSizing: "border-box" }} />
            <span style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)", fontSize: 14, opacity: 0.35 }}>🔍</span>
          </div>
        )}
      </div>

      {/* Content */}
      <div style={{ padding: "10px 16px" }}>
        {tab === "prefs" ? (
          <Prefs P={P} uP={uP} kbUpdated={kb?.updated} />
        ) : items.length === 0 ? (
          <div style={{ textAlign: "center", padding: "60px 20px", color: "#bbb" }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>{tab === "saved" ? "💝" : "📋"}</div>
            <div style={{ fontSize: 14, fontWeight: 500, color: "#888", marginBottom: 4 }}>
              {tab === "saved" ? "관심 등록한 공고가 없어요" : raw?.length === 0 ? "아직 수집된 데이터가 없어요" : "조건에 맞는 공고가 없어요"}
            </div>
            <div style={{ fontSize: 12 }}>
              {tab === "saved" ? "하트를 눌러 추가해보세요" : raw?.length === 0 ? "GitHub Actions 실행 후 데이터가 채워집니다" : "설정에서 필터를 조정해보세요"}
            </div>
          </div>
        ) : (
          <>
            <div style={{ fontSize: 12, color: "#999", marginBottom: 6, paddingLeft: 4 }}>
              {tab === "match" && <><span style={{ color: "#1E3A8A", fontWeight: 700 }}>{items.length}건</span> 맞춤 추천</>}
              {tab === "home" && `전체 ${items.length}건`}
              {tab === "saved" && `관심 ${items.length}건`}
            </div>
            {items.map((i) => (
              <Card key={i.id} item={i} saved={sv.has(i.id)} onSave={tSv} onOpen={setDet} dim={tab === "home" && i.out} kbRate={i.kbRate} />
            ))}
          </>
        )}
      </div>

      {/* Tab bar */}
      <div style={{ position: "fixed", bottom: 0, left: "50%", transform: "translateX(-50%)", width: "100%", maxWidth: 480, background: "#fff", borderTop: "1px solid #EBEBEB", display: "flex", zIndex: 50, paddingBottom: "env(safe-area-inset-bottom,0px)" }}>
        {TABS.map((t) => (
          <button key={t.id} onClick={() => { setTab(t.id); setQ(""); }} style={{ flex: 1, border: "none", background: "none", cursor: "pointer", padding: "8px 0 5px", display: "flex", flexDirection: "column", alignItems: "center", gap: 1, opacity: tab === t.id ? 1 : 0.4, position: "relative" }}>
            <span style={{ fontSize: 17 }}>{t.ic}</span>
            <span style={{ fontSize: 10, fontWeight: tab === t.id ? 700 : 400, color: tab === t.id ? "#1E3A8A" : "#888" }}>{t.l}</span>
            {t.id === "match" && mc > 0 && (
              <span style={{ position: "absolute", top: 4, right: "50%", marginRight: -18, background: "#EF4444", color: "#fff", fontSize: 9, fontWeight: 700, borderRadius: 10, padding: "1px 5px", minWidth: 14, textAlign: "center" }}>{mc}</span>
            )}
            {t.id === "saved" && sv.size > 0 && (
              <span style={{ position: "absolute", top: 6, right: "50%", marginRight: -16, width: 6, height: 6, borderRadius: 3, background: "#2563EB" }} />
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
