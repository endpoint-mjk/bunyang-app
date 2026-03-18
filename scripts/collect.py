#!/usr/bin/env python3
"""
분양정보 자동 수집기
- 청약홈 공공데이터 API (APT, 오피스텔, 무순위)
- KB부동산 주간 매매 상승률 (PublicDataReader)
- LH/SH 공고 스크래핑
→ data/latest.json 으로 출력
"""
import os, json, logging, requests, sys
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

API_KEY = os.environ.get("DATA_GO_KR_API_KEY", "")
BASE = "https://apis.data.go.kr/1613000/SubscrptInfoSvc"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# ── 투자등급 기본 매핑 (KB 데이터 수집 실패 시 fallback) ──────────────
TIER_MAP = {
    "서울": {
        "S": ["강남구","서초구","송파구","용산구","성동구","마포구","광진구"],
        "A": ["양천구","영등포구","동작구","강동구","서대문구","종로구","중구"],
        "B": ["구로구","금천구","관악구","동대문구","성북구","강서구"],
        "C": ["노원구","도봉구","강북구","중랑구","은평구"],
    },
    "경기": {
        "S": ["성남 분당구","과천시","광명시","하남시"],
        "A": ["안양 동안구","용인 수지구","고양 일산동구","화성 동탄"],
        "B": ["수원시","부천시","의왕시","군포시","안산 상록구"],
        "C": ["김포시","파주시","양주시","이천시","평택시","고양 덕양구"],
    },
    "인천": {
        "S": [],
        "A": ["연수구","남동구","서구 청라","서구"],
        "B": ["미추홀구","부평구"],
        "C": ["계양구","강화군","옹진군"],
    },
}

def get_tier(city, district):
    """지역의 투자등급 반환"""
    city_map = TIER_MAP.get(city, {})
    for tier, districts in city_map.items():
        for d in districts:
            if d in district or district in d:
                return tier
    return "B"  # 기본값


def format_price(amount_str):
    """만원 단위 정수를 '억' 단위 문자열로 변환 (예: 342000 → '34.2억')"""
    if not amount_str:
        return ""
    try:
        amount = int(str(amount_str).replace(",", "").strip())
        if amount <= 0:
            return ""
        eok = amount / 10000
        if eok >= 1:
            if eok == int(eok):
                return f"{int(eok)}억"
            return f"{eok:.1f}억"
        return f"{amount:,}만"
    except (ValueError, TypeError):
        return str(amount_str)


# ── 청약홈 API ────────────────────────────────────────────────────────
def call_api(endpoint, extra_params=None):
    if not API_KEY:
        return []
    params = {"serviceKey": API_KEY, "numOfRows": "100", "pageNo": "1", "type": "json"}
    if extra_params:
        params.update(extra_params)
    try:
        resp = requests.get(f"{BASE}{endpoint}", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("response", {}).get("body", {}).get("items", {})
        if isinstance(items, dict):
            return items.get("item", [])
        return items if isinstance(items, list) else []
    except Exception as ex:
        log.warning(f"API 호출 실패 ({endpoint}): {ex}")
        return []

def parse_apt(raw, category="APT"):
    """API 응답을 통일된 형태로 변환"""
    def g(k1, k2=""):
        return str(raw.get(k1, raw.get(k2, "")) or "")

    name = g("HOUSE_NM", "houseNm")
    if not name:
        return None

    # 지역 파싱
    location = g("HSSPLY_ADRES", "hssplyAdres")
    region = g("SUBSCRPT_AREA_CODE_NM", "sido")

    # 도시/구 추출
    city, district = "", ""
    if "서울" in location or "서울" in region:
        city = "서울"
    elif "경기" in location or "경기" in region:
        city = "경기"
    elif "인천" in location or "인천" in region:
        city = "인천"

    # 구/시 추출 (간단한 파싱)
    for part in location.replace("특별시","").replace("광역시","").replace("도","").split():
        if part.endswith(("구","시")) and len(part) >= 2:
            district = part
            break

    manage_no = g("HOUSE_MANAGE_NO", "houseManageNo")
    tier = get_tier(city, district) if city else "B"

    units = 0
    try:
        units = int(g("TOT_SUPLY_HSHLDCO", "totSuplyHshldco") or 0)
    except:
        pass

    return {
        "id": manage_no or name[:20],
        "src": "청약홈",
        "cat": category,
        "name": name,
        "dist": district,
        "city": city,
        "loc": location or region,
        "ann": g("RCRIT_PBLANC_DE", "rcritPblancDe"),
        "ss": g("RCEPT_BGNDE", "rceptBgnde"),
        "se": g("RCEPT_ENDDE", "rceptEndde"),
        "units": units,
        "bld": g("BSNS_MBY_NM", "bsnsMbyNm"),
        "mv": g("MVNDE", "mvnde"),
        "tier": tier,
        "types": [],
        "url": f"https://www.applyhome.co.kr/ai/aia/selectAPTLttotPblancDetail.do?houseManageNo={manage_no}" if manage_no else "",
    }

def fetch_apt_types(manage_no):
    """주택형별 상세 정보 조회"""
    items = call_api("/getAPTLttotPblancMdl", {"houseManageNo": manage_no})
    types = []
    for raw in items:
        try:
            m2 = float(raw.get("EXCLUSE_AR", raw.get("excluseAr", 0)) or 0)
            py = round(m2 / 3.306)
            raw_price = raw.get("LTTOT_TOP_AMOUNT", raw.get("lttotTopAmount", ""))
            types.append({
                "a": raw.get("HOUSE_TY", raw.get("houseTy", str(int(m2)))),
                "m2": round(m2, 1),
                "py": py,
                "u": int(raw.get("SUPLY_HSHLDCO", raw.get("suplyHshldco", 0)) or 0),
                "p": format_price(raw_price),
            })
        except:
            continue
    return types

def collect_cheongyak():
    """청약홈 전체 수집"""
    results = []

    log.info("📌 APT 분양정보 수집...")
    for raw in call_api("/getAPTLttotPblancList"):
        item = parse_apt(raw, "APT")
        if item:
            if item["id"] and API_KEY:
                item["types"] = fetch_apt_types(item["id"])
            results.append(item)

    log.info("📌 오피스텔 분양정보 수집...")
    for raw in call_api("/getOftlLttotPblancList"):
        item = parse_apt(raw, "오피스텔")
        if item:
            results.append(item)

    log.info("📌 무순위/잔여세대 수집...")
    for raw in call_api("/getRemndrLttotPblancList"):
        item = parse_apt(raw, "무순위")
        if item:
            results.append(item)

    log.info(f"  → 청약홈 총 {len(results)}건")
    return results


# ── KB부동산 상승률 수집 ──────────────────────────────────────────────
def collect_kb():
    """KB부동산 주간 매매 상승률 수집"""
    kb = {"updated": datetime.now().strftime("%Y.%m.%d"), "data": {}}

    try:
        from PublicDataReader import Kbland
        api = Kbland()

        for region_code, region_name in [("11", "서울"), ("41", "경기"), ("28", "인천")]:
            try:
                df = api.get_price_index_change_rate(
                    월간주간구분코드="02",  # 주간
                    매물종별구분="01",      # 아파트
                    매매전세코드="01",      # 매매
                    지역코드=region_code,
                    기간="1",
                )
                if df is not None and len(df) > 0:
                    for _, row in df.iterrows():
                        area = str(row.get("지역명", ""))
                        rate = float(row.get("변동률", 0))
                        kb["data"][f"{region_name}_{area}"] = rate
                    log.info(f"  → KB {region_name}: {len(df)}개 지역")
            except Exception as ex:
                log.warning(f"KB {region_name} 실패: {ex}")
    except ImportError:
        log.warning("PublicDataReader 미설치 → KB 데이터 스킵 (pip install PublicDataReader)")
    except Exception as ex:
        log.warning(f"KB 수집 실패: {ex}")

    return kb


# ── LH 공고 수집 ─────────────────────────────────────────────────────
def collect_lh():
    results = []
    log.info("📌 LH 분양공고 수집...")
    try:
        resp = requests.get(
            "https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancList.do",
            headers=HEADERS, timeout=15,
            params={"PG_SZ": "20", "PAGE_INDEX": "1", "AIS_TP_CD": "06"},
        )
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for row in soup.select("table tbody tr"):
                cols = row.select("td")
                link = row.select_one("a")
                if cols and link:
                    name = link.get_text(strip=True)
                    href = link.get("href", "")
                    region = cols[2].get_text(strip=True) if len(cols) > 2 else ""
                    date = cols[3].get_text(strip=True) if len(cols) > 3 else ""

                    city = ""
                    if "서울" in region: city = "서울"
                    elif "경기" in region: city = "경기"
                    elif "인천" in region: city = "인천"

                    results.append({
                        "id": f"lh_{name[:15]}",
                        "src": "LH", "cat": "공공분양",
                        "name": name, "dist": "", "city": city,
                        "loc": region, "ann": date,
                        "ss": "", "se": "", "units": 0, "bld": "LH",
                        "mv": "", "tier": get_tier(city, region),
                        "types": [],
                        "url": f"https://apply.lh.or.kr{href}" if href.startswith("/") else "https://apply.lh.or.kr",
                    })
    except Exception as ex:
        log.warning(f"LH 수집 실패: {ex}")

    log.info(f"  → LH {len(results)}건")
    return results


# ── SH 공고 수집 ─────────────────────────────────────────────────────
def collect_sh():
    results = []
    log.info("📌 SH 분양공고 수집...")
    try:
        resp = requests.get(
            "https://www.i-sh.co.kr/main/lay2/program/S1T294C297/www/brd/m_247/list.do",
            headers=HEADERS, timeout=15,
        )
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for row in soup.select("table tbody tr, .board-list li"):
                link = row.select_one("a")
                if link:
                    name = link.get_text(strip=True)
                    href = link.get("href", "")
                    results.append({
                        "id": f"sh_{name[:15]}",
                        "src": "SH", "cat": "공공분양",
                        "name": name, "dist": "", "city": "서울",
                        "loc": "서울", "ann": "",
                        "ss": "", "se": "", "units": 0, "bld": "SH",
                        "mv": "", "tier": "B",
                        "types": [],
                        "url": f"https://www.i-sh.co.kr{href}" if href.startswith("/") else "https://www.i-sh.co.kr",
                    })
    except Exception as ex:
        log.warning(f"SH 수집 실패: {ex}")

    log.info(f"  → SH {len(results)}건")
    return results


# ── 메인 ──────────────────────────────────────────────────────────────
def main():
    log.info("=" * 50)
    log.info("🏠 분양정보 자동 수집 시작")
    log.info("=" * 50)

    all_items = []

    # 1. 청약홈
    if API_KEY:
        all_items.extend(collect_cheongyak())
    else:
        log.warning("⚠️ DATA_GO_KR_API_KEY 없음 → 청약홈 스킵")

    # 2. LH
    all_items.extend(collect_lh())

    # 3. SH
    all_items.extend(collect_sh())

    # 4. KB 상승률
    kb = collect_kb()

    # 5. 중복 제거
    seen = set()
    unique = []
    for item in all_items:
        key = f"{item['src']}:{item['name']}"
        if key not in seen:
            seen.add(key)
            unique.append(item)

    # 6. 정렬 (최신 공고일 순)
    unique.sort(key=lambda x: x.get("ann", "") or "", reverse=True)

    # 7. 출력
    output = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "count": len(unique),
        "kb": kb,
        "items": unique,
    }

    out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "latest.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    log.info(f"\n✅ 완료: {len(unique)}건 → {out_path}")
    log.info(f"   KB 데이터: {len(kb.get('data', {}))}개 지역")


if __name__ == "__main__":
    main()
