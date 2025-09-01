#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Fubon Smart Scraper - 智能版
具備日期判斷、資料狀態記錄、自動重試機制的完整爬蟲
"""

import asyncio
import datetime as dt
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Page
from openpyxl import load_workbook
from openpyxl.styles import numbers

# ====== 基本配置 ======
BASE_DIR = Path("/Users/laihongyi/Documents/爬蟲蒐集資料")
OUT_DIR = BASE_DIR
SNAP_DIR = BASE_DIR / "_snapshots"
LOG_DIR = BASE_DIR / "_logs"
LOG_PATH = LOG_DIR / f"scraper_{dt.datetime.now().strftime('%Y%m%d')}.log"
STATUS_FILE = LOG_DIR / "scraper_status.json"

# 確保目錄存在
for dir_path in [OUT_DIR, SNAP_DIR, LOG_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# 完整的富邦證券排行榜URL配置
FUBON_URLS = {
    # 收盤價（通常當日即有資料）
    "漲幅排行": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_A.djhtm", "type": "price", "delay": 0},
    "跌幅排行": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_B.djhtm", "type": "price", "delay": 0},
    "漲停表": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_AA.djhtm", "type": "price", "delay": 0},
    "跌停表": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_AB.djhtm", "type": "price", "delay": 0},
    
    # 成交量（通常當日即有資料）
    "量大排行": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_D.djhtm", "type": "volume", "delay": 0},
    "量增排行": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_DA.djhtm", "type": "volume", "delay": 0},
    "量縮排行": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_DB.djhtm", "type": "volume", "delay": 0},
    "量增幅排行": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_DC.djhtm", "type": "volume", "delay": 0},
    "量縮幅排行": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_DD.djhtm", "type": "volume", "delay": 0},
    "週轉率排行": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_DE.djhtm", "type": "volume", "delay": 0},
    
    # 成交值（通常當日即有資料）
    "值大排行": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_E.djhtm", "type": "value", "delay": 0},
    "值增排行": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_EA.djhtm", "type": "value", "delay": 0},
    "值縮排行": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_EB.djhtm", "type": "value", "delay": 0},
    "值增幅排行": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_EC.djhtm", "type": "value", "delay": 0},
    "值縮幅排行": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_ED.djhtm", "type": "value", "delay": 0},
    
    # 法人/主力進出（T+1日資料）
    "外資買超排行": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_F.djhtm", "type": "institutional", "delay": 1},
    "外資賣超排行": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_FA.djhtm", "type": "institutional", "delay": 1},
    "外資買賣超排行": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_FB.djhtm", "type": "institutional", "delay": 1},
    "外資買賣超明細": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_FC.djhtm", "type": "institutional", "delay": 1},
    "自營商買超排行": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_G.djhtm", "type": "institutional", "delay": 1},
    "自營商賣超排行": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_GA.djhtm", "type": "institutional", "delay": 1},
    "自營商買賣超排行": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_GB.djhtm", "type": "institutional", "delay": 1},
    "投信買超排行": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_H.djhtm", "type": "institutional", "delay": 1},
    "投信賣超排行": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_HA.djhtm", "type": "institutional", "delay": 1},
    "投信買賣超排行": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_HB.djhtm", "type": "institutional", "delay": 1},
    "主力買超排行": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_I.djhtm", "type": "institutional", "delay": 1},
    "主力賣超排行": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_IA.djhtm", "type": "institutional", "delay": 1},
    
    # 強勢股（需要累積資料）
    "當日強勢股": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZGK_DD.djhtm", "type": "trend", "delay": 0},
    "三日強勢股": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZGK_CC.djhtm", "type": "trend", "delay": 3},
    "五日強勢股": {"url": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZGK_AA.djhtm", "type": "trend", "delay": 5},
}

# HTTP請求設定
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}

# ====== 工具函數 ======
def log(msg: str, level: str = "INFO"):
    """記錄日誌"""
    timestamp = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    msg_with_time = f"[{timestamp}] [{level}] {msg}"
    print(msg_with_time)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(msg_with_time + "\n")

def is_trading_day(date: dt.datetime = None) -> bool:
    """判斷是否為交易日"""
    if date is None:
        date = dt.datetime.now()
    
    # 週末不是交易日
    if date.weekday() >= 5:
        return False
    
    # TODO: 可以加入台灣節假日判斷
    return True

def get_last_trading_day(date: dt.datetime = None) -> dt.datetime:
    """取得最近的交易日"""
    if date is None:
        date = dt.datetime.now()
    
    while not is_trading_day(date):
        date -= dt.timedelta(days=1)
    
    return date

def should_have_data(url_config: dict, current_date: dt.datetime = None) -> Tuple[bool, str]:
    """判斷該類別是否應該有資料"""
    if current_date is None:
        current_date = dt.datetime.now()
    
    data_type = url_config["type"]
    delay_days = url_config["delay"]
    
    # 檢查是否為交易日
    if not is_trading_day(current_date):
        return False, "非交易日"
    
    # 檢查是否為月初
    if current_date.day <= 2 and data_type == "institutional":
        return False, "月初可能尚無法人資料"
    
    # 檢查延遲天數
    if delay_days > 0:
        last_trading = get_last_trading_day(current_date - dt.timedelta(days=1))
        days_since = (current_date - last_trading).days
        if days_since < delay_days:
            return False, f"需要T+{delay_days}日資料"
    
    # 檢查時間（下午3點後較可能有完整資料）
    if current_date.hour < 15 and data_type in ["price", "volume", "value"]:
        return True, "交易時間中，資料可能不完整"
    
    return True, "應有資料"

def save_status(status_data: dict):
    """保存爬取狀態"""
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status_data, f, ensure_ascii=False, indent=2, default=str)

def load_status() -> dict:
    """載入爬取狀態"""
    if STATUS_FILE.exists():
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def clean_numeric_value(value) -> Optional[float]:
    """清理數值欄位"""
    if pd.isna(value) or value is None:
        return None
        
    value_str = str(value).strip()
    if not value_str or value_str in ['--', '-', 'N/A', '']:
        return None
    
    # 處理萬、億單位
    multiplier = 1
    if '萬' in value_str:
        multiplier = 10000
        value_str = value_str.replace('萬', '')
    elif '億' in value_str:
        multiplier = 100000000
        value_str = value_str.replace('億', '')
    
    # 清理特殊字符
    value_str = (value_str.replace(',', '')
                         .replace('+', '')
                         .replace('＋', '')
                         .replace('－', '-')
                         .replace('%', '')
                         .replace('％', '')
                         .replace('張', '')
                         .replace('元', ''))
    
    try:
        return float(value_str) * multiplier
    except (ValueError, TypeError):
        return None

def extract_stock_code_name(text: str) -> Tuple[str, str]:
    """從文字中提取股票代號和名稱"""
    text = str(text).strip()
    match = re.match(r'^([0-9A-Z]{4,6})\s*(.*)$', text)
    if match:
        return match.group(1), match.group(2).strip()
    return "", text

# ====== Playwright爬取函數 ======
def scrape_with_playwright(url: str, name: str, url_config: dict) -> Tuple[Optional[pd.DataFrame], Optional[str], str]:
    """使用Playwright爬取動態渲染的頁面，返回 (DataFrame, 日期, 狀態訊息)"""
    
    # 先檢查是否應該有資料
    should_have, reason = should_have_data(url_config)
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                user_agent=HEADERS["User-Agent"],
                locale="zh-TW",
            )
            page = context.new_page()
            page.set_default_timeout(30000)
            
            log(f"爬取 {name}: {url}")
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(2000)
            
            # 等待表格載入
            try:
                page.wait_for_selector("table", timeout=5000)
            except:
                pass
            
            # 取得頁面內容
            html_content = page.content()
            
            # 保存快照
            snapshot_path = SNAP_DIR / f"{dt.datetime.now().strftime('%Y%m%d')}_{name}.html"
            snapshot_path.write_text(html_content, encoding='utf-8')
            
            # 解析資料
            df, date_str, is_empty = parse_fubon_html(html_content)
            
            context.close()
            browser.close()
            
            if df is not None and not df.empty:
                log(f"✅ {name}: 取得 {len(df)} 筆資料", "SUCCESS")
                return df, date_str, "成功"
            elif is_empty:
                if not should_have:
                    log(f"⚠️ {name}: 無資料（{reason}）", "WARNING")
                    return None, None, f"無資料-{reason}"
                else:
                    log(f"❌ {name}: 應有資料但查無", "ERROR")
                    return None, None, "應有資料但查無"
            else:
                log(f"⚠️ {name}: 解析失敗", "WARNING")
                return None, None, "解析失敗"
                
    except Exception as e:
        log(f"❌ {name}: 錯誤 - {str(e)}", "ERROR")
        return None, None, f"錯誤-{str(e)[:50]}"

def parse_fubon_html(html_content: str) -> Tuple[Optional[pd.DataFrame], Optional[str], bool]:
    """解析富邦證券HTML內容，返回 (DataFrame, 日期, 是否為空資料頁)"""
    soup = BeautifulSoup(html_content, 'lxml')
    
    # 檢查是否為無資料頁面
    text_content = soup.get_text()
    if '查無排行相關資料' in text_content or '無此排行榜資料' in text_content:
        return None, None, True
    
    # 提取日期
    date_str = None
    date_match = re.search(r'(\d{4}/\d{2}/\d{2})', html_content)
    if date_match:
        date_str = date_match.group(1)
    else:
        date_match = re.search(r'日期[:：]\s*(\d{2}/\d{2})', html_content)
        if date_match:
            year = dt.datetime.now().year
            date_str = f"{year}/{date_match.group(1)}"
        else:
            date_str = dt.datetime.now().strftime("%Y/%m/%d")
    
    # 尋找表格
    tables = soup.find_all('table')
    for table in tables:
        df = parse_table(table)
        if df is not None and len(df) > 10:
            return df, date_str, False
    
    # 從純文字提取
    df = extract_from_text(soup.get_text())
    if df is not None and not df.empty:
        return df, date_str, False
    
    return None, date_str, False

def parse_table(table) -> Optional[pd.DataFrame]:
    """解析HTML表格"""
    rows = []
    headers = []
    
    all_rows = table.find_all('tr')
    
    for i, row in enumerate(all_rows):
        cells = row.find_all(['th', 'td'])
        if cells:
            texts = [cell.get_text(strip=True) for cell in cells]
            if any('名次' in str(t) for t in texts) and any('股票' in str(t) or '名稱' in str(t) for t in texts):
                headers = texts
                for data_row in all_rows[i+1:]:
                    data_cells = data_row.find_all(['td'])
                    if data_cells:
                        row_data = [cell.get_text(strip=True) for cell in data_cells]
                        if row_data and re.match(r'^\d+$', str(row_data[0])):
                            rows.append(row_data)
                break
    
    if not rows:
        return None
    
    df = pd.DataFrame(rows)
    
    if headers and len(headers) == len(df.columns):
        df.columns = headers
    else:
        cols = []
        for i in range(len(df.columns)):
            if i == 0:
                cols.append('名次')
            elif i == 1:
                cols.append('股票名稱')
            elif i == 2:
                cols.append('收盤價')
            elif i == 3:
                cols.append('漲跌')
            elif i == 4:
                cols.append('漲跌幅')
            elif i == 5:
                cols.append('成交量')
            elif i == 6:
                cols.append('成交值')
            else:
                cols.append(f'欄位{i+1}')
        df.columns = cols[:len(df.columns)]
    
    return process_dataframe(df)

def extract_from_text(text: str) -> Optional[pd.DataFrame]:
    """從純文字中提取股票資料"""
    lines = text.split('\n')
    data = []
    rank = 1
    
    for line in lines:
        line = line.strip()
        if re.match(r'^\d{4}', line):
            parts = line.split()
            if len(parts) >= 3:
                code_name = parts[0]
                code, name = extract_stock_code_name(code_name)
                if code:
                    row = [str(rank), code, name]
                    row.extend(parts[1:6])
                    data.append(row)
                    rank += 1
    
    if data:
        num_cols = max(len(row) for row in data)
        columns = ['名次', '代號', '股票名稱', '收盤價', '漲跌', '漲跌幅', '成交量', '成交值'][:num_cols]
        
        for row in data:
            while len(row) < num_cols:
                row.append('')
        
        df = pd.DataFrame(data, columns=columns)
        return process_dataframe(df)
    
    return None

def process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """處理和清理DataFrame"""
    if df is None or df.empty:
        return pd.DataFrame()
    
    df = df.copy()
    
    # 處理合併欄位
    if '代號名稱' in df.columns:
        codes = []
        names = []
        for val in df['代號名稱']:
            code, name = extract_stock_code_name(val)
            codes.append(code)
            names.append(name)
        
        idx = list(df.columns).index('代號名稱')
        df = df.drop('代號名稱', axis=1)
        df.insert(idx, '代號', codes)
        df.insert(idx + 1, '股票名稱', names)
    
    elif '代號' not in df.columns and '股票名稱' in df.columns:
        codes = []
        names = []
        for val in df['股票名稱']:
            code, name = extract_stock_code_name(val)
            if code:
                codes.append(code)
                names.append(name)
            else:
                codes.append('')
                names.append(val)
        
        if any(codes):
            df.insert(1, '代號', codes)
            df['股票名稱'] = names
    
    # 清理數值欄位
    numeric_cols = ['名次', '收盤價', '漲跌', '漲跌幅', '成交量', '成交值', 
                    '買超', '賣超', '買賣超', '週轉率']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].apply(clean_numeric_value)
    
    # 過濾有效資料
    if '代號' in df.columns:
        df = df[df['代號'].notna() & (df['代號'].astype(str).str.strip() != '')]
        df = df[df['代號'].astype(str).str.match(r'^\d{4}')]
    
    df = df.reset_index(drop=True)
    
    return df

# ====== 主程式 ======
def main():
    """主要執行函數"""
    current_time = dt.datetime.now()
    log(f"開始執行富邦證券智能爬蟲")
    log(f"執行時間: {current_time}")
    log(f"今天是: {current_time.strftime('%A')} ({['一','二','三','四','五','六','日'][current_time.weekday()]})")
    
    # 判斷交易狀態
    if not is_trading_day(current_time):
        log("⚠️ 今天非交易日，部分資料可能不會更新", "WARNING")
    elif current_time.hour < 9:
        log("⚠️ 尚未開盤，資料為昨日收盤資料", "WARNING")
    elif current_time.hour < 14:
        log("⚠️ 交易進行中，資料可能不完整", "WARNING")
    elif current_time.hour >= 14:
        log("✅ 已收盤，資料應該完整", "INFO")
    
    all_data = {}
    status_record = {
        "執行時間": current_time.isoformat(),
        "是否交易日": is_trading_day(current_time),
        "各類別狀態": {}
    }
    
    # 統計
    success_count = 0
    no_data_expected = 0
    no_data_unexpected = 0
    error_count = 0
    
    # 使用ThreadPoolExecutor並行爬取
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        for name, config in FUBON_URLS.items():
            future = executor.submit(scrape_with_playwright, config["url"], name, config)
            futures[future] = name
            time.sleep(0.5)
        
        # 收集結果
        for future in futures:
            name = futures[future]
            try:
                df, date_str, status_msg = future.result(timeout=60)
                
                status_record["各類別狀態"][name] = {
                    "狀態": status_msg,
                    "資料筆數": len(df) if df is not None else 0,
                    "資料日期": date_str,
                    "類型": FUBON_URLS[name]["type"],
                    "延遲天數": FUBON_URLS[name]["delay"]
                }
                
                if df is not None and not df.empty:
                    df['資料來源'] = name
                    df['抓取時間'] = current_time.strftime("%Y-%m-%d %H:%M:%S")
                    if date_str:
                        df['資料日期'] = date_str
                    all_data[name] = df
                    success_count += 1
                elif "無資料" in status_msg and "T+" in status_msg:
                    no_data_expected += 1
                elif "無資料" in status_msg:
                    no_data_unexpected += 1
                else:
                    error_count += 1
                    
            except Exception as e:
                log(f"❌ {name}: 執行錯誤 - {str(e)}", "ERROR")
                status_record["各類別狀態"][name] = {"狀態": f"錯誤-{str(e)[:50]}"}
                error_count += 1
    
    # 保存狀態
    save_status(status_record)
    
    if not all_data:
        log("❌ 未取得任何資料", "ERROR")
        return
    
    # 生成輸出檔案
    tag = dt.datetime.now().strftime("%Y%m%d")
    output_path = OUT_DIR / f"fubon_smart_{tag}.xlsx"
    
    # 寫入Excel
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # 個別工作表
        for sheet_name, df in all_data.items():
            safe_sheet_name = sheet_name[:31]
            output_cols = []
            for col in ['名次', '代號', '股票名稱', '收盤價', '漲跌', '漲跌幅', 
                       '成交量', '成交值', '買超', '賣超', '買賣超', '週轉率',
                       '資料日期', '資料來源']:
                if col in df.columns:
                    output_cols.append(col)
            
            if output_cols:
                df_output = df[output_cols].copy()
                df_output.to_excel(writer, sheet_name=safe_sheet_name, index=False)
        
        # 總彙總表
        all_summary = []
        for name, df in all_data.items():
            summary_df = df.copy()
            summary_df['分類'] = name
            all_summary.append(summary_df)
        
        if all_summary:
            total_summary = pd.concat(all_summary, ignore_index=True)
            if '漲跌幅' in total_summary.columns and '代號' in total_summary.columns:
                total_summary = total_summary.sort_values('漲跌幅', ascending=False, na_position='last')
                total_summary = total_summary.drop_duplicates(subset=['代號'], keep='first')
            total_summary.to_excel(writer, sheet_name='總彙總', index=False)
    
    # 格式化Excel
    format_excel(output_path)
    
    # 輸出統計
    total_stocks = sum(len(df) for df in all_data.values())
    log("=" * 60)
    log(f"✅ 執行完成！")
    log(f"輸出檔案: {output_path}")
    log(f"成功爬取: {success_count} 個類別")
    log(f"預期無資料: {no_data_expected} 個類別（T+N日或非交易日）")
    log(f"異常無資料: {no_data_unexpected} 個類別")
    log(f"錯誤: {error_count} 個類別")
    log(f"總計取得: {total_stocks} 筆資料")
    
    # 輸出各類別統計
    log("\n各類別統計：")
    type_stats = {}
    for name, df in all_data.items():
        data_type = FUBON_URLS[name]["type"]
        if data_type not in type_stats:
            type_stats[data_type] = 0
        type_stats[data_type] += len(df)
    
    for data_type, count in type_stats.items():
        log(f"  {data_type}: {count} 筆")

def format_excel(file_path: Path):
    """格式化Excel檔案"""
    try:
        wb = load_workbook(file_path)
        
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            
            # 調整欄寬
            column_widths = {
                'A': 8, 'B': 10, 'C': 15, 'D': 12, 
                'E': 10, 'F': 10, 'G': 15, 'H': 15,
                'I': 15, 'J': 15, 'K': 12,
            }
            
            for col, width in column_widths.items():
                if col in ws.column_dimensions:
                    ws.column_dimensions[col].width = width
            
            # 數字格式化
            for row in ws.iter_rows(min_row=2):
                for cell in row:
                    if cell.value is not None:
                        header = ws.cell(1, cell.column).value
                        if header:
                            if any(keyword in str(header) for keyword in ['價', '金額', '成交值']):
                                try:
                                    if isinstance(cell.value, (int, float)):
                                        cell.number_format = '#,##0.00'
                                except:
                                    pass
                            elif any(keyword in str(header) for keyword in ['幅', '率']):
                                try:
                                    if isinstance(cell.value, (int, float)):
                                        if '週轉率' not in str(header):
                                            cell.value = cell.value / 100 if cell.value > 1 else cell.value
                                        cell.number_format = '0.00%'
                                except:
                                    pass
                            elif any(keyword in str(header) for keyword in ['量', '張', '買超', '賣超']):
                                try:
                                    if isinstance(cell.value, (int, float)):
                                        cell.number_format = '#,##0'
                                except:
                                    pass
        
        wb.save(file_path)
        log("Excel格式化完成")
    except Exception as e:
        log(f"Excel格式化錯誤: {e}", "ERROR")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("程式被使用者中斷", "WARNING")
    except Exception as e:
        log(f"執行錯誤: {e}", "ERROR")
        import traceback
        traceback.print_exc()