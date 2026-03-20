#!/usr/bin/env python3
"""
분양정보 자동 수집기
- 청약홈 공공데이터 API (APT, 무순위)
- KB부동산 주간 매매 상승률 (PublicDataReader)
- LH/SH 공고 스크래핑
→ data/latest.json 으로 출력
"""
import os, json, logging, requests, re, time
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
    city_map = TIER_MAP.get(city, {})
    for tier, districts in city_map.items():
        for d in districts:
            if d in district or district in d:
                return tier
    return "B"


def format_price(amount_str):
    """만원 단위 정수를 '억' 단위 문자열로 변환"""
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


# ── 필터링 ───────────────────────────────────────────────────────────
CUTOFF_DAYS = 30

# 모집공고가 아닌 게시글 제외 키워드
EXCLUDE_TITLE_KW = [
    "당첨자", "당첨결과", "결과발표", "명단발표", "선정명단", "명단 발표",
    "순위확인", "자격확인", "부적격",
    "정정공고", "정정)", "변경공고",
    "취소", "해제", "철회",
    "계약안내", "계약대상", "잔금",
    "채용", "인력", "위탁",
    "보상", "이주", "설계",
    "예비입주자 선정",
]

# 임대 관련 키워드 (분양만 수집하므로 제외)
RENTAL_KW = [
    "매입임대", "장기전세", "국민임대", "행복주택", "영구임대", "공공임대",
    "장기안심", "보증금지원", "사회주택", "임대주택",
]


def parse_date(date_str):
    """날짜 문자열을 datetime으로 변환"""
    if not date_str:
        return None
    try:
        clean = re.sub(r'[.\s]', '-', date_str.strip()).rstrip('-')
        return datetime.strptime(clean, "%Y-%m-%d")
    except:
        return None


def is_active_or_recent(ann_date, end_date=None, days=CUTOFF_DAYS):
    """접수 마감 전이거나 공고일이 최근 N일 이내인 공고만 포함"""
    now = datetime.now()
    # 접수 마감일이 아직 안 지났으면 포함
    se = parse_date(end_date)
    if se and se >= now:
        return True
    # 공고일 기준 N일 이내면 포함
    ann = parse_date(ann_date)
    if ann:
        return (now - ann).days <= days
    # 날짜 정보 없으면 일단 포함
    return True


def is_bunyang_recruitment(name):
    """분양 모집공고인지 확인 (결과/과정/임대/채용 제외)"""
    if any(kw in name for kw in EXCLUDE_TITLE_KW):
        return False
    if any(kw in name for kw in RENTAL_KW):
        return False
    return True


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

    location = g("HSSPLY_ADRES", "hssplyAdres")
    region = g("SUBSCRPT_AREA_CODE_NM", "sido")

    city, district = "", ""
    if "서울" in location or "서울" in region:
        city = "서울"
    elif "경기" in location or "경기" in region:
        city = "경기"
    elif "인천" in location or "인천" in region:
        city = "인천"

    for part in location.replace("특별시","").replace("광역시","").replace("도","").split():
        if part.endswith(("구","시")) and len(part) >= 2:
            district = part
            break

    manage_no = g("HOUSE_MANAGE_NO", "houseManageNo")
    tier = get_tier(city, district) if city else "C"

    units = 0
    try:
        units = int(g("TOT_SUPLY_HSHLDCO", "totSuplyHshldco") or 0)
    except:
        pass

    # 청약 일정 정보 (자격 대신 일정 추출)
    spsply_start = g("SPSPLY_RCEPT_BGNDE", "spsplyRceptBgnde")
    spsply_end = g("SPSPLY_RCEPT_ENDDE", "spsplyRceptEndde")
    gnrl_rk1 = g("GNRL_RNK1_CRSPAREA_RCPTDE", "gnrlRnk1CrspareaRcptde")
    gnrl_rk2 = g("GNRL_RNK2_CRSPAREA_RCPTDE", "gnrlRnk2CrspareaRcptde")

    qual_parts = []
    if spsply_start:
        qual_parts.append(f"특별공급 {spsply_start}~{spsply_end}")
    if gnrl_rk1:
        qual_parts.append(f"1순위 {gnrl_rk1}")
    if gnrl_rk2:
        qual_parts.append(f"2순위 {gnrl_rk2}")

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
        "qual": " / ".join(qual_parts),
        "url": f"https://www.applyhome.co.kr/ai/aia/selectAPTLttotPblancDetail.do?houseManageNo={manage_no}" if manage_no else "",
    }


def fetch_apt_types(manage_no):
    """APT 주택형별 상세 정보 조회"""
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


def fetch_remndr_types(manage_no):
    """무순위/잔여세대 주택형별 상세 정보 조회"""
    items = call_api("/getRemndrLttotPblancMdl", {"houseManageNo": manage_no})
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
    """청약홈 전체 수집 (APT + 무순위, 1주일 이내 모집공고만)"""
    results = []

    log.info("📌 APT 분양정보 수집...")
    for raw in call_api("/getAPTLttotPblancList"):
        item = parse_apt(raw, "APT")
        if not item:
            continue
        if not is_bunyang_recruitment(item["name"]):
            log.info(f"  ↳ 제외 (비모집): {item['name'][:40]}")
            continue
        if not is_active_or_recent(item["ann"], item.get("se")):
            continue
        if item["id"] and API_KEY:
            item["types"] = fetch_apt_types(item["id"])
        results.append(item)

    log.info("📌 무순위/잔여세대 수집...")
    for raw in call_api("/getRemndrLttotPblancList"):
        item = parse_apt(raw, "무순위")
        if not item:
            continue
        if not is_bunyang_recruitment(item["name"]):
            log.info(f"  ↳ 제외 (비모집): {item['name'][:40]}")
            continue
        if not is_active_or_recent(item["ann"], item.get("se")):
            continue
        if item["id"] and API_KEY:
            item["types"] = fetch_remndr_types(item["id"])
        results.append(item)

    log.info(f"  → 청약홈 총 {len(results)}건")
    return results


# ── KB부동산 상승률 수집 ──────────────────────────────────────────────
def collect_kb():
    kb = {"updated": datetime.now().strftime("%Y.%m.%d"), "data": {}}
    try:
        from PublicDataReader import Kbland
        api = Kbland()
        for region_code, region_name in [("11", "서울"), ("41", "경기"), ("28", "인천")]:
            try:
                df = api.get_price_index_change_rate(
                    월간주간구분코드="02", 매물종별구분="01",
                    매매전세코드="01", 지역코드=region_code, 기간="1",
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
        log.warning("PublicDataReader 미설치 → KB 데이터 스킵")
    except Exception as ex:
        log.warning(f"KB 수집 실패: {ex}")
    return kb


# ── LH 공고 수집 ─────────────────────────────────────────────────────
def scrape_lh_detail(url):
    """LH 상세 페이지에서 주택형/자격 정보 추출 시도"""
    result = {"types": [], "qual": "", "units": 0}
    try:
        time.sleep(0.5)
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return result
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text()

        # 총 세대수 추출
        m = re.search(r'총\s*(\d[\d,]*)\s*세대', text)
        if m:
            result["units"] = int(m.group(1).replace(",", ""))

        # 테이블에서 주택형 정보 탐색
        for table in soup.select("table"):
            headers = [th.get_text(strip=True) for th in table.select("th")]
            header_text = " ".join(headers)
            if any(kw in header_text for kw in ["전용면적", "주택형", "공급면적", "전용"]):
                for row in table.select("tbody tr"):
                    cells = [td.get_text(strip=True) for td in row.select("td")]
                    if len(cells) < 2:
                        continue
                    try:
                        m2, units, price, house_type = 0, 0, "", ""
                        for h, c in zip(headers, cells):
                            if "전용" in h and not m2:
                                m2 = float(re.sub(r'[^\d.]', '', c) or 0)
                            elif ("세대" in h or "호수" in h) and not units:
                                units = int(re.sub(r'[^\d]', '', c) or 0)
                            elif ("분양가" in h or "금액" in h or "가격" in h) and not price:
                                price = c
                            elif ("주택형" in h or "타입" in h or "형별" in h) and not house_type:
                                house_type = c
                        if m2 > 0:
                            py = round(m2 / 3.306)
                            result["types"].append({
                                "a": house_type or str(int(m2)),
                                "m2": round(m2, 1), "py": py,
                                "u": units, "p": format_price(price),
                            })
                    except:
                        continue

        # 자격 조건 추출 시도
        for section in soup.select("table, div, section"):
            section_text = section.get_text()
            if "자격" in section_text or "대상" in section_text:
                for row in section.select("tr"):
                    th = row.select_one("th")
                    td = row.select_one("td")
                    if th and td:
                        th_text = th.get_text(strip=True)
                        if any(kw in th_text for kw in ["자격", "대상", "조건", "신청자격"]):
                            result["qual"] = td.get_text(strip=True)[:200]
                            break
                if result["qual"]:
                    break

    except Exception as ex:
        log.warning(f"LH 상세 파싱 실패: {ex}")
    return result


def collect_lh():
    results = []
    log.info("📌 LH 분양공고 수집...")
    try:
        resp = requests.get(
            "https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancList.do",
            headers=HEADERS, timeout=15,
            params={"mi": "1027"},
        )
        if resp.status_code != 200:
            log.warning(f"LH 목록 요청 실패: {resp.status_code}")
            return results

        soup = BeautifulSoup(resp.text, "html.parser")
        for row in soup.select("table tbody tr"):
            cols = row.select("td")
            link = row.select_one("a")
            if not cols or not link:
                continue

            name = link.get_text(strip=True)
            if not name or not is_bunyang_recruitment(name):
                continue

            # 컬럼에서 정보 추출
            region, date_str, deadline = "", "", ""
            for col in cols:
                text = col.get_text(strip=True)
                if re.match(r'\d{4}[.\-]\d{2}[.\-]\d{2}', text):
                    if not date_str:
                        date_str = text
                    elif not deadline:
                        deadline = text
                elif any(loc in text for loc in ["서울", "경기", "인천", "부산", "대구", "광주",
                         "대전", "울산", "세종", "충청", "전라", "경상", "강원", "제주", "전국"]):
                    if not region:
                        region = text

            norm_date = date_str.replace(".", "-") if date_str else ""
            norm_deadline = deadline.replace(".", "-") if deadline else ""
            if not is_active_or_recent(norm_date, norm_deadline):
                continue

            # 상세페이지 ID 추출
            pan_id = link.get("data-id1", "")
            ccr = link.get("data-id2", "")
            upp = link.get("data-id3", "05")
            ais = link.get("data-id4", "")

            detail_url = "https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancInfo.do"
            if pan_id:
                detail_url += f"?panId={pan_id}&ccrCnntSysDsCd={ccr}&uppAisTpCd={upp}&aisTpCd={ais}&mi=1027"

            city = ""
            if "서울" in region: city = "서울"
            elif "경기" in region: city = "경기"
            elif "인천" in region: city = "인천"

            district = ""
            for part in region.replace("특별시","").replace("광역시","").split():
                if part.endswith(("구","시")) and len(part) >= 2:
                    district = part
                    break

            item = {
                "id": f"lh_{pan_id or name[:15]}",
                "src": "LH", "cat": "공공분양",
                "name": name, "dist": district, "city": city,
                "loc": region, "ann": norm_date,
                "ss": "", "se": deadline.replace(".", "-") if deadline else "",
                "units": 0, "bld": "LH",
                "mv": "", "tier": get_tier(city, district or region) if city else "C",
                "types": [], "qual": "",
                "url": detail_url,
            }

            # 상세 페이지 스크래핑 시도
            if pan_id:
                try:
                    detail = scrape_lh_detail(detail_url)
                    if detail["types"]:
                        item["types"] = detail["types"]
                    if detail["qual"]:
                        item["qual"] = detail["qual"]
                    if detail["units"]:
                        item["units"] = detail["units"]
                except Exception as ex:
                    log.warning(f"LH 상세 실패 ({name[:20]}): {ex}")

            results.append(item)

    except Exception as ex:
        log.warning(f"LH 수집 실패: {ex}")

    log.info(f"  → LH {len(results)}건")
    return results


# ── SH 공고 수집 ─────────────────────────────────────────────────────
def scrape_sh_detail(base_url, seq):
    """SH 상세 페이지에서 정보 추출 시도"""
    result = {"types": [], "qual": "", "units": 0, "ann": ""}
    try:
        time.sleep(0.5)
        view_url = base_url.replace("list.do", "view.do")
        resp = requests.post(view_url, headers=HEADERS, timeout=15, data={"seq": seq})
        if resp.status_code != 200:
            return result

        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text()

        # 등록일 추출
        for dt_el in soup.select(".view_head .date, .bbs_view .date, dd"):
            dt_text = dt_el.get_text(strip=True)
            m = re.search(r'(\d{4}[-./]\d{2}[-./]\d{2})', dt_text)
            if m:
                result["ann"] = m.group(1).replace(".", "-").replace("/", "-")
                break

        # 세대수
        m = re.search(r'총?\s*(\d[\d,]*)\s*세대', text)
        if m:
            result["units"] = int(m.group(1).replace(",", ""))

        # 테이블에서 주택형 정보
        for table in soup.select("table"):
            headers = [th.get_text(strip=True) for th in table.select("th")]
            header_text = " ".join(headers)
            if any(kw in header_text for kw in ["전용면적", "주택형", "공급면적", "전용", "평형"]):
                for row in table.select("tbody tr"):
                    cells = [td.get_text(strip=True) for td in row.select("td")]
                    if len(cells) < 2:
                        continue
                    try:
                        m2, units, price, house_type = 0, 0, "", ""
                        for h, c in zip(headers, cells):
                            if "전용" in h and not m2:
                                m2 = float(re.sub(r'[^\d.]', '', c) or 0)
                            elif ("세대" in h or "호수" in h) and not units:
                                units = int(re.sub(r'[^\d]', '', c) or 0)
                            elif ("분양가" in h or "금액" in h) and not price:
                                price = c
                            elif ("주택형" in h or "타입" in h) and not house_type:
                                house_type = c
                        if m2 > 0:
                            py = round(m2 / 3.306)
                            result["types"].append({
                                "a": house_type or str(int(m2)),
                                "m2": round(m2, 1), "py": py,
                                "u": units, "p": format_price(price),
                            })
                    except:
                        continue

        # 자격 조건
        for section in soup.select("table, div"):
            for row in section.select("tr"):
                th = row.select_one("th")
                td = row.select_one("td")
                if th and td:
                    th_text = th.get_text(strip=True)
                    if any(kw in th_text for kw in ["자격", "대상", "조건", "신청자격"]):
                        result["qual"] = td.get_text(strip=True)[:200]
                        break
            if result["qual"]:
                break

    except Exception as ex:
        log.warning(f"SH 상세 파싱 실패: {ex}")
    return result


def collect_sh():
    results = []
    log.info("📌 SH 분양공고 수집...")

    sh_urls = [
        "https://www.i-sh.co.kr/main/lay2/program/S1T294C297/www/brd/m_247/list.do",
        "https://www.i-sh.co.kr/main/lay2/program/S1T294C298/www/brd/m_248/list.do",
    ]

    # 분양 모집공고에 포함되어야 할 키워드
    BUNYANG_KW = ["분양", "공급", "모집공고", "입주자모집"]

    for sh_url in sh_urls:
        try:
            resp = requests.get(sh_url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            for row in soup.select("table tbody tr"):
                cols = row.select("td")
                link = row.select_one("a")
                if not link:
                    continue

                name = link.get_text(strip=True)
                if name.startswith("NEW"):
                    name = name[3:].strip()

                # 분양 모집공고만 (임대/결과/채용 등 제외)
                if not is_bunyang_recruitment(name):
                    continue
                if not any(kw in name for kw in BUNYANG_KW):
                    continue

                # 날짜 추출 (테이블 컬럼에서)
                date_str = ""
                for col in cols:
                    text = col.get_text(strip=True)
                    m = re.search(r'(\d{4}[-./]\d{2}[-./]\d{2})', text)
                    if m:
                        date_str = m.group(1).replace(".", "-").replace("/", "-")
                        break

                # seq 추출 (링크 onclick 또는 href에서)
                seq = ""
                href = link.get("href", "")
                onclick = link.get("onclick", "")
                # href에서 seq 추출
                m = re.search(r'seq=(\d+)', href)
                if m:
                    seq = m.group(1)
                # onclick에서 seq 추출
                if not seq:
                    m = re.search(r"getDetailView\('?(\d+)'?\)", onclick)
                    if m:
                        seq = m.group(1)
                # JavaScript:void 패턴
                if not seq:
                    m = re.search(r"(\d{4,})", onclick or href)
                    if m:
                        seq = m.group(1)

                detail_url = f"https://www.i-sh.co.kr{href}" if href.startswith("/") else ""

                item = {
                    "id": f"sh_{seq or name[:15]}",
                    "src": "SH", "cat": "공공분양",
                    "name": name, "dist": "", "city": "서울",
                    "loc": "서울", "ann": date_str,
                    "ss": "", "se": "", "units": 0, "bld": "SH",
                    "mv": "", "tier": "B",
                    "types": [], "qual": "",
                    "url": detail_url or "https://www.i-sh.co.kr",
                }

                # 상세 페이지 스크래핑 시도
                if seq:
                    try:
                        detail = scrape_sh_detail(sh_url, seq)
                        if detail["types"]:
                            item["types"] = detail["types"]
                        if detail["qual"]:
                            item["qual"] = detail["qual"]
                        if detail["units"]:
                            item["units"] = detail["units"]
                        if detail["ann"] and not item["ann"]:
                            item["ann"] = detail["ann"]
                    except Exception as ex:
                        log.warning(f"SH 상세 실패 ({name[:20]}): {ex}")

                if not is_active_or_recent(item["ann"], item.get("se")):
                    continue

                results.append(item)

        except Exception as ex:
            log.warning(f"SH 수집 실패 ({sh_url}): {ex}")

    log.info(f"  → SH {len(results)}건")
    return results


# ── 메인 ──────────────────────────────────────────────────────────────
def main():
    log.info("=" * 50)
    log.info("🏠 분양정보 자동 수집 시작 (최근 %d일)", CUTOFF_DAYS)
    log.info("=" * 50)

    all_items = []

    if API_KEY:
        all_items.extend(collect_cheongyak())
    else:
        log.warning("⚠️ DATA_GO_KR_API_KEY 없음 → 청약홈 스킵")

    all_items.extend(collect_lh())
    all_items.extend(collect_sh())

    kb = collect_kb()

    # 중복 제거
    seen = set()
    unique = []
    for item in all_items:
        key = f"{item['src']}:{item['name']}"
        if key not in seen:
            seen.add(key)
            unique.append(item)

    # 정렬 (최신 공고일 순)
    unique.sort(key=lambda x: x.get("ann", "") or "", reverse=True)

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
