#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Fubon Ranking Scraper — WFGY Dual Mode (Mirror + Clean)

- 抓取：收盤價/成交量/成交值排行 + 三大法人買超排行
- Mirror：完全鏡射頁面欄名/欄序/字面值（千分位、% 不動）
- Clean：正規化欄位、數字清洗、百分比格式化，並輸出彙總_精簡
- 同次執行預設輸出兩份檔：*_mirror.xlsx 與 *_clean.xlsx
"""

import argparse
import datetime as dt
import random
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import Frame, Page
from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

# ====== 基本配置 ======
BASE_DIR = Path("/Users/laihongyi/Documents/爬蟲蒐集資料")
OUT_DIR = BASE_DIR
SNAP_DIR = BASE_DIR / "_snapshots"
LOG_PATH = BASE_DIR / "_last_run.log"
# 多個目標URL配置
TARGET_URLS = {
    "漲幅排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_A.djhtm",
    "跌幅排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_B.djhtm",
    "成交量排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_D.djhtm",
    "成交值排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_E.djhtm",
}

# 簡化的任務配置 - 直接從URL爬取
DEFAULT_TASKS = [
    ("漲幅排行", "收盤價_漲幅排行"),
    ("跌幅排行", "收盤價_跌幅排行"),
    ("成交量排行", "成交量_排行"),
    ("成交值排行", "成交值_排行"),
]

# ====== Clean 模式的欄位規範 ======
NUM_LIKE_COLS = {
    "名次",
    "收盤價",
    "漲跌",
    "漲跌幅",
    "成交量",
    "成交值",
    "買超",
    "賣超",
    "買賣超",
    "買超張數",
    "賣超張數",
    "買超金額",
    "賣超金額",
}
HEADER_NORMALIZE_MAP = [
    (r"^名次$|^名次[\s\S]*$", "名次"),
    (r"^(證券)?代號$", "代號"),
    (r"^(證券)?名稱$|^股票名稱$", "名稱"),
    (r"^收盤(價)?$|^收市$", "收盤價"),
    (r"^漲跌$", "漲跌"),
    (r"^漲跌幅$|^漲幅(\%)?$", "漲跌幅"),
    (r"^成交量(\(張\))?$", "成交量"),
    (r"^成交(值|金額|額)$", "成交值"),
    (r"^買超$", "買超"),
    (r"^賣超$", "賣超"),
    (r"^買賣超$", "買賣超"),
]

RE_DATE = re.compile(r"日期[:：]\s*([0-9]{4}/[0-9]{2}/[0-9]{2}|[0-9]{2}/[0-9]{2})")


# ====== 小工具 ======
def log(msg: str):
    msg2 = f"[{dt.datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(msg2)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(msg2 + "\n")


def ensure_dirs():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SNAP_DIR.mkdir(parents=True, exist_ok=True)


def today_tag() -> str:
    return dt.datetime.now().strftime("%Y%m%d")


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headful", action="store_true", help="以可見瀏覽器執行")
    ap.add_argument(
        "--timeout", type=int, default=40, help="頁面操作逾時秒數（預設40）"
    )
    ap.add_argument("--retries", type=int, default=2, help="任務失敗重試次數（預設2）")
    ap.add_argument("--limit", type=int, default=0, help="每表只保留前N名（0=全部）")
    ap.add_argument("--mirror-only", action="store_true", help="僅輸出 mirror.xlsx")
    ap.add_argument("--clean-only", action="store_true", help="僅輸出 clean.xlsx")
    return ap.parse_args()


# ====== HTML → DataFrame ======
def html_table_to_df(table_tag) -> pd.DataFrame:
    """改進的表格解析，處理富邦證券特殊格式"""
    rows = []
    headers = []
    
    # 先嘗試找標題行
    for tr in table_tag.find_all("tr"):
        ths = tr.find_all("th")
        if ths:
            headers = [th.get_text(strip=True) for th in ths]
            break
    
    # 解析資料行
    for tr in table_tag.find_all("tr"):
        tds = tr.find_all("td")
        if tds:
            row = [td.get_text(strip=True) for td in tds]
            # 忽略全空行
            if any(cell != "" for cell in row):
                rows.append(row)
    
    if not rows:
        return pd.DataFrame()
    
    df = pd.DataFrame(rows)
    
    # 富邦證券的表格可能沒有th標籤，需要從第一行推斷
    if not headers and len(df) > 0:
        # 檢查第一行是否為標題
        first_row = df.iloc[0]
        if any("名次" in str(v) or "代號" in str(v) or "名稱" in str(v) for v in first_row):
            headers = first_row.tolist()
            df = df.iloc[1:].reset_index(drop=True)
    
    if headers and len(headers) == df.shape[1]:
        df.columns = [str(h) for h in headers]
    else:
        # 根據內容推斷欄位名稱
        cols = []
        for i in range(df.shape[1]):
            if i == 0 and df.iloc[:, i].str.match(r'^\d+$').all():
                cols.append("名次")
            elif i == 1 and df.iloc[:, i].str.contains(r'^\d{4}').any():
                cols.append("代號名稱")
            elif i == 2 and df.iloc[:, i].str.match(r'^[\d\.]+$').any():
                cols.append("收盤價")
            elif i == 3:
                cols.append("漲跌")
            elif i == 4 and "%" in str(df.iloc[0, i]):
                cols.append("漲跌幅")
            elif i == 5:
                cols.append("成交量")
            else:
                cols.append(f"欄位{i+1}")
        df.columns = cols
    
    return df


def pick_main_table_from_html(
    html: str,
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table")
    best = None
    best_rows = -1
    for t in tables:
        df = html_table_to_df(t)
        if df.empty:
            continue
        rows, cols = len(df), df.shape[1]
        # 主表一般 row>=10 & col>=5 且行數最大
        if rows >= 10 and cols >= 5 and rows > best_rows:
            best_rows = rows
            best = df
    # 抓日期
    text = soup.get_text(" ", strip=True)
    m = RE_DATE.search(text)
    d = m.group(1) if m else None
    if d and re.fullmatch(r"[0-9]{2}/[0-9]{2}", d):
        d = f"{dt.datetime.now().strftime('%Y')}/{d}"
    return best, d


def find_content_frame(page: Page) -> Frame:
    cand = []
    for fr in page.frames:
        try:
            h = fr.content()
            if "<table" in h.lower():
                cand.append((len(h), fr))
        except:
            pass
    if not cand:
        return page.main_frame
    cand.sort(reverse=True, key=lambda x: x[0])
    return cand[0][1]


# ====== DOM 操作 ======
def js_click_text(page: Page, text: str):
    page.evaluate(
        """
        (txt) => {
          const nodes = Array.from(document.querySelectorAll('a, span, div, li, button'));
          const n = nodes.find(n => n.textContent && n.textContent.trim().includes(txt));
          if (n) n.click();
        }
        """,
        text,
    )


def click_left_menu(page: Page, group_text: str, item_text: str):
    js_click_text(page, group_text)
    time.sleep(0.2 + random.random() * 0.3)
    js_click_text(page, item_text)


# ====== Clean 模式清洗 ======
def normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    cols = []
    for c in df.columns:
        name = str(c).strip()
        for pat, std in HEADER_NORMALIZE_MAP:
            if re.search(pat, name):
                name = std
                break
        cols.append(name)
    out = df.copy()
    out.columns = cols
    return out


def split_code_name(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    def extract_code_series(s: pd.Series) -> pd.Series:
        s = s.astype(str)
        return s.str.extract(r"^\s*([0-9A-Z\-]{3,})")[0]

    if "代號" not in df.columns and "名稱" in df.columns:
        code = extract_code_series(df["名稱"])
        if code.notna().sum() > 0:
            df.insert(1, "代號", code)
            df["名稱"] = (
                df["名稱"]
                .astype(str)
                .str.replace(r"^\s*[0-9A-Z\-]{3,}\s*", "", regex=True)
            )

    if (
        "代號" in df.columns
        and (df["代號"].isna() | (df["代號"].astype(str).str.strip() == "")).any()
    ):
        if "名稱" in df.columns:
            fill_code = extract_code_series(df["名稱"])
            df["代號"] = (
                df["代號"]
                .astype(str)
                .where(df["代號"].astype(str).str.strip() != "", fill_code)
            )

    if "代號" not in df.columns:
        for col in df.columns:
            try:
                cand = extract_code_series(df[col])
                if cand.notna().sum() > 0:
                    df.insert(0, "代號", cand)
                    break
            except Exception:
                continue

    return df


def to_num(x) -> Optional[float]:
    """改進的數字轉換，處理更多格式"""
    if x is None:
        return None
    s = str(x).strip()
    if s in ("", "--", "-", "N/A"):
        return None
    
    # 處理萬、億單位
    multiplier = 1
    if "萬" in s:
        multiplier = 10000
    elif "億" in s:
        multiplier = 100000000
    
    # 移除千分位符號和特殊字元
    s = (
        s.replace(",", "")
        .replace("+", "")
        .replace("＋", "")
        .replace("－", "-")
        .replace("%", "")
        .replace("％", "")
        .replace("張", "")
        .replace("元", "")
        .replace("萬", "")
        .replace("億", "")
    )
    
    try:
        value = float(s)
        return value * multiplier
    except:
        return None


def clean_rank_table(df: pd.DataFrame) -> pd.DataFrame:
    df = normalize_headers(df)
    df = split_code_name(df)

    keep = [
        c
        for c in [
            "名次",
            "代號",
            "名稱",
            "收盤價",
            "漲跌",
            "漲跌幅",
            "成交量",
            "成交值",
            "買超",
            "賣超",
            "買賣超",
        ]
        if c in df.columns
    ]
    if keep:
        df = df[keep].copy()

    if "名次" in df.columns:
        df = df[pd.to_numeric(df["名次"], errors="coerce").notna()]

    for c in df.columns:
        if c in NUM_LIKE_COLS:
            df[c] = df[c].map(to_num)

    if "名次" in df.columns:
        df = df.sort_values(
            "名次", key=lambda s: pd.to_numeric(s, errors="coerce")
        ).reset_index(drop=True)

    rename = {
        "名次": "rank",
        "代號": "code",
        "名稱": "name",
        "收盤價": "close",
        "漲跌": "change",
        "漲跌幅": "change_pct",
        "成交量": "volume",
        "成交值": "value",
        "買超": "buy_excess",
        "賣超": "sell_excess",
        "買賣超": "net_excess",
    }
    return df.rename(columns=rename)


# ====== 任務執行 ======
def scrape_direct_url(
    page: Page, url: str, timeout_s: int
) -> Tuple[pd.DataFrame, Optional[str], str]:
    """直接從URL爬取資料，不需要點擊選單"""
    page.goto(url, wait_until="networkidle")
    page.wait_for_timeout(2000)
    
    # 取得頁面HTML
    html = page.content()
    
    # 解析表格
    df_raw, d = pick_main_table_from_html(html)
    
    if df_raw is None or df_raw.empty:
        # 嘗試尋找frame
        fr = find_content_frame(page)
        if fr != page.main_frame:
            html = fr.content()
            df_raw, d = pick_main_table_from_html(html)
    
    if df_raw is None or df_raw.empty:
        raise RuntimeError(f"未擷取到表：{url}")
    
    return df_raw, d, html


# ====== Excel 輸出 ======
def write_excel_mirror(path: Path, sheets: Dict[str, pd.DataFrame]):
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)


def write_excel_clean(path: Path, sheets: Dict[str, pd.DataFrame]):
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name, df in sheets.items():
            sheet = name[:31]
            df_out = df.copy()
            if "change_pct" in df_out.columns:
                df_out["change_pct"] = df_out["change_pct"].apply(
                    lambda v: None if pd.isna(v) else (v / 100.0 if v > 1 else v)
                )
            df_out.to_excel(writer, index=False, sheet_name=sheet)

    from openpyxl import load_workbook
    from openpyxl.styles import numbers

    wb = load_workbook(path)
    for name, df in sheets.items():
        ws = wb[name[:31]]
        cols = list(df.columns)

        def col_idx(cname: str) -> int:
            return cols.index(cname) + 1 if cname in cols else -1

        fmt_comma = numbers.FORMAT_NUMBER_COMMA_SEPARATED1
        for cname in (
            "close",
            "change",
            "volume",
            "value",
            "buy_excess",
            "sell_excess",
            "net_excess",
        ):
            j = col_idx(cname)
            if j > 0:
                for i in range(2, ws.max_row + 1):
                    ws.cell(i, j).number_format = fmt_comma
        j_pct = col_idx("change_pct")
        if j_pct > 0:
            for i in range(2, ws.max_row + 1):
                ws.cell(i, j_pct).number_format = "0.00%"
    wb.save(path)


# ====== 主流程 ======
def main():
    ensure_dirs()
    args = parse_args()
    try:
        LOG_PATH.unlink()
    except:
        pass

    tag = today_tag()
    out_xlsx_mirror = OUT_DIR / f"daily_fubon_{tag}_mirror.xlsx"
    out_xlsx_clean = OUT_DIR / f"daily_fubon_{tag}_clean.xlsx"
    log(f"Start → 富邦證券排行榜爬取")

    tasks = DEFAULT_TASKS
    sheets_mirror: Dict[str, pd.DataFrame] = {}
    sheets_clean: Dict[str, pd.DataFrame] = {}
    summary_rows: List[pd.DataFrame] = []
    first_date = None
    html_snaps: Dict[str, str] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not args.headful,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
            locale="zh-TW",
        )
        page = context.new_page()
        page.set_default_timeout(args.timeout * 1000)

        for task_name, sheet_name in tasks:
            if task_name not in TARGET_URLS:
                log(f"⚠️ 跳過未配置的任務：{task_name}")
                continue
            
            url = TARGET_URLS[task_name]
            tries = 0
            success = False
            last_err = None
            while tries <= args.retries and not success:
                tries += 1
                try:
                    log(f"抓取：{task_name} (try {tries})")
                    df_raw, d, snap = scrape_direct_url(page, url, args.timeout)

                    # 限制前 N 名（Mirror/Clean 同步）
                    if args.limit > 0 and len(df_raw) > args.limit:
                        df_raw = df_raw.head(args.limit).copy()

                    # 日期欄（Mirror：加在最左側；Clean：後面再加）
                    df_mirror = df_raw.copy()
                    if d and df_mirror.shape[1] > 0:
                        # 若第一列看起來像 header 已在 html_table_to_df 處理
                        df_mirror.insert(0, "日期", d)

                    sheets_mirror[sheet_name] = df_mirror

                    # Clean
                    df_clean = clean_rank_table(df_raw)
                    if d and "date" not in df_clean.columns:
                        df_clean.insert(0, "date", d)
                    sheets_clean[sheet_name] = df_clean

                    # 彙總
                    base = [
                        c
                        for c in [
                            "date",
                            "code",
                            "name",
                            "close",
                            "change",
                            "change_pct",
                            "volume",
                            "value",
                        ]
                        if c in df_clean.columns
                    ]
                    if base:
                        tmp = df_clean[base].copy()
                        tmp["source"] = sheet_name
                        summary_rows.append(tmp)

                    if d and not first_date:
                        first_date = d
                    html_snaps[sheet_name] = snap
                    success = True
                except Exception as e:
                    last_err = e
                    page.wait_for_timeout(800 + random.randint(0, 400))
            if not success:
                log(f"❌ 失敗：{task_name} → {last_err}")

        context.close()
        browser.close()

    # 彙總_精簡（Clean 專用，容錯）
    if summary_rows:
        summary = pd.concat(summary_rows, ignore_index=True).drop_duplicates()
        if "code" not in summary.columns or summary["code"].isna().all():
            if "name" in summary.columns:
                fill_code = (
                    summary["name"].astype(str).str.extract(r"^\s*([0-9A-Z\-]{3,})")[0]
                )
                summary["code"] = summary.get("code")
                summary["code"] = summary["code"].where(
                    summary["code"].notna()
                    & (summary["code"].astype(str).str.strip() != ""),
                    fill_code,
                )
        if "code" in summary.columns:
            summary = summary[summary["code"].notna()]
        want = [
            "date",
            "code",
            "name",
            "close",
            "change",
            "change_pct",
            "volume",
            "value",
            "source",
        ]
        summary = summary[[c for c in want if c in summary.columns]]
        sheets_clean["彙總_精簡"] = summary

    # 保存快照
    for name, html in html_snaps.items():
        (SNAP_DIR / f"{tag}_{name}.html").write_text(html, encoding="utf-8")

    # 依參數輸出
    if not args.clean_only:
        if sheets_mirror:
            write_excel_mirror(out_xlsx_mirror, sheets_mirror)
            log(f"✅ 輸出（Mirror）：{out_xlsx_mirror}")
        else:
            log("⚠️ 無可輸出的 Mirror 表")
    if not args.mirror_only:
        if sheets_clean:
            write_excel_clean(out_xlsx_clean, sheets_clean)
            log(f"✅ 輸出（Clean）：{out_xlsx_clean}")
        else:
            log("⚠️ 無可輸出的 Clean 表")

    if (args.mirror_only and not sheets_mirror) or (
        args.clean_only and not sheets_clean
    ):
        raise SystemExit("本次未取得任何表，請查看 _last_run.log 與 _snapshots/。")


if __name__ == "__main__":
    try:
        main()
    except PWTimeout as e:
        log(f"⏱️ Timeout: {e}")
        sys.exit(2)
    except Exception as e:
        log(f"💥 Fatal: {e}")
        sys.exit(1)
