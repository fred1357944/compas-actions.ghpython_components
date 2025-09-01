#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Fubon Complete Scraper - 完整版
爬取富邦證券所有排行榜資料
"""

import asyncio
import datetime as dt
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
LOG_PATH = BASE_DIR / "_complete_run.log"

# 完整的富邦證券排行榜URL配置
FUBON_URLS = {
    # 收盤價
    "漲幅排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_A.djhtm",
    "跌幅排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_B.djhtm",
    "漲停表": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_AA.djhtm",
    "跌停表": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_AB.djhtm",
    
    # 成交量
    "量大排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_D.djhtm",
    "量增排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_DA.djhtm",
    "量縮排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_DB.djhtm",
    "量增幅排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_DC.djhtm",
    "量縮幅排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_DD.djhtm",
    "週轉率排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_DE.djhtm",
    
    # 成交值
    "值大排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_E.djhtm",
    "值增排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_EA.djhtm",
    "值縮排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_EB.djhtm",
    "值增幅排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_EC.djhtm",
    "值縮幅排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_ED.djhtm",
    
    # 法人/主力進出
    "外資買超排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_F.djhtm",
    "外資賣超排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_FA.djhtm",
    "外資買賣超排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_FB.djhtm",
    "外資買賣超明細": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_FC.djhtm",
    "自營商買超排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_G.djhtm",
    "自營商賣超排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_GA.djhtm",
    "自營商買賣超排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_GB.djhtm",
    "自營商買賣超明細表": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_GC.djhtm",
    "自營商進出金額明細表": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_GD.djhtm",
    "投信買超排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_H.djhtm",
    "投信賣超排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_HA.djhtm",
    "投信買賣超排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_HB.djhtm",
    "投信買賣超明細": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_HC.djhtm",
    "主力買超排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_I.djhtm",
    "主力賣超排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_IA.djhtm",
    "主力買賣超排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_IB.djhtm",
    "券商進出排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_J.djhtm",
    
    # 強勢股（不同時間範圍）
    "當日強勢股": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZGK_DD.djhtm",
    "三日強勢股": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZGK_CC.djhtm",
    "五日強勢股": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZGK_AA.djhtm",
    "十日強勢股": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZGK_BB.djhtm",
    "二十日強勢股": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZGK_EE.djhtm",
}

# HTTP請求設定
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}

# ====== 工具函數 ======
def log(msg: str):
    """記錄日誌"""
    timestamp = dt.datetime.now().strftime('%H:%M:%S')
    msg_with_time = f"[{timestamp}] {msg}"
    print(msg_with_time)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(msg_with_time + "\n")

def ensure_dirs():
    """確保目錄存在"""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SNAP_DIR.mkdir(parents=True, exist_ok=True)

def today_tag() -> str:
    """取得今天日期標籤"""
    return dt.datetime.now().strftime("%Y%m%d")

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
    # 匹配格式：「2330台積電」或「2330 台積電」
    match = re.match(r'^([0-9A-Z]{4,6})\s*(.*)$', text)
    if match:
        return match.group(1), match.group(2).strip()
    return "", text

# ====== Playwright爬取函數 ======
def scrape_with_playwright(url: str, name: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """使用Playwright爬取動態渲染的頁面"""
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
            snapshot_path = SNAP_DIR / f"{today_tag()}_{name}.html"
            snapshot_path.write_text(html_content, encoding='utf-8')
            
            # 解析資料
            df, date_str = parse_fubon_html(html_content)
            
            context.close()
            browser.close()
            
            if df is not None and not df.empty:
                log(f"✅ {name}: 取得 {len(df)} 筆資料")
                return df, date_str
            else:
                log(f"⚠️ {name}: 未找到有效資料")
                return None, None
                
    except Exception as e:
        log(f"❌ {name}: 錯誤 - {str(e)}")
        return None, None

def parse_fubon_html(html_content: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """解析富邦證券HTML內容"""
    soup = BeautifulSoup(html_content, 'lxml')
    
    # 檢查是否為無資料頁面
    text_content = soup.get_text()
    if '查無排行相關資料' in text_content or '無此排行榜資料' in text_content:
        return None, None
    
    # 提取日期
    date_str = None
    date_match = re.search(r'(\d{4}/\d{2}/\d{2})', html_content)
    if date_match:
        date_str = date_match.group(1)
    else:
        # 嘗試從其他格式提取日期（例如：08/29）
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
        if df is not None and len(df) > 10:  # 至少要有10筆資料
            return df, date_str
    
    # 從純文字提取
    df = extract_from_text(soup.get_text())
    if df is not None and not df.empty:
        return df, date_str
    
    return None, date_str

def parse_table(table) -> Optional[pd.DataFrame]:
    """解析HTML表格"""
    rows = []
    headers = []
    
    # 提取所有行
    all_rows = table.find_all('tr')
    
    # 尋找標題行
    for i, row in enumerate(all_rows):
        cells = row.find_all(['th', 'td'])
        if cells:
            texts = [cell.get_text(strip=True) for cell in cells]
            # 檢查是否為標題行
            if any('名次' in str(t) for t in texts) and any('股票' in str(t) or '名稱' in str(t) for t in texts):
                headers = texts
                # 從下一行開始提取資料
                for data_row in all_rows[i+1:]:
                    data_cells = data_row.find_all(['td'])
                    if data_cells:
                        row_data = [cell.get_text(strip=True) for cell in data_cells]
                        # 檢查是否為有效資料行
                        if row_data and re.match(r'^\d+$', str(row_data[0])):
                            rows.append(row_data)
                break
    
    if not rows:
        return None
    
    df = pd.DataFrame(rows)
    
    # 設定欄位名稱
    if headers and len(headers) == len(df.columns):
        df.columns = headers
    else:
        # 根據資料內容推斷欄位
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
        # 尋找股票代號模式
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
    
    # 處理「代號名稱」合併欄位
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
    
    # 分離代號和名稱（如果在同一欄）
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
    
    # 重設索引
    df = df.reset_index(drop=True)
    
    return df

# ====== 主程式 ======
def main():
    """主要執行函數"""
    ensure_dirs()
    
    try:
        LOG_PATH.unlink()
    except:
        pass
    
    log(f"開始爬取富邦證券完整排行榜資料（共 {len(FUBON_URLS)} 個類別）...")
    
    all_data = {}
    success_count = 0
    fail_count = 0
    
    # 使用ThreadPoolExecutor並行爬取（限制並發數避免過載）
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        for name, url in FUBON_URLS.items():
            future = executor.submit(scrape_with_playwright, url, name)
            futures[future] = name
            time.sleep(0.5)  # 避免請求過快
        
        # 收集結果
        for future in futures:
            name = futures[future]
            try:
                df, date_str = future.result(timeout=60)
                if df is not None and not df.empty:
                    df['資料來源'] = name
                    df['抓取時間'] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if date_str:
                        df['資料日期'] = date_str
                    all_data[name] = df
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                log(f"❌ {name}: 執行錯誤 - {str(e)}")
                fail_count += 1
    
    if not all_data:
        log("❌ 未取得任何資料")
        return
    
    # 生成輸出檔案
    tag = today_tag()
    output_path = OUT_DIR / f"fubon_all_data_{tag}.xlsx"
    
    # 寫入Excel（分類組織）
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # 寫入各個工作表
        categories = {
            '收盤價': ['漲幅排行', '跌幅排行', '漲停表', '跌停表'],
            '成交量': ['量大排行', '量增排行', '量縮排行', '量增幅排行', '量縮幅排行', '週轉率排行'],
            '成交值': ['值大排行', '值增排行', '值縮排行', '值增幅排行', '值縮幅排行'],
            '外資': ['外資買超排行', '外資賣超排行', '外資買賣超排行', '外資買賣超明細'],
            '自營商': ['自營商買超排行', '自營商賣超排行', '自營商買賣超排行', '自營商買賣超明細表', '自營商進出金額明細表'],
            '投信': ['投信買超排行', '投信賣超排行', '投信買賣超排行', '投信買賣超明細'],
            '主力': ['主力買超排行', '主力賣超排行', '主力買賣超排行', '券商進出排行'],
            '強勢股': ['當日強勢股', '三日強勢股', '五日強勢股', '十日強勢股', '二十日強勢股']
        }
        
        # 個別工作表
        for sheet_name, df in all_data.items():
            safe_sheet_name = sheet_name[:31]
            
            # 選擇要輸出的欄位
            output_cols = []
            for col in ['名次', '代號', '股票名稱', '收盤價', '漲跌', '漲跌幅', 
                       '成交量', '成交值', '買超', '賣超', '買賣超', '週轉率',
                       '資料日期', '資料來源']:
                if col in df.columns:
                    output_cols.append(col)
            
            if output_cols:
                df_output = df[output_cols].copy()
                df_output.to_excel(writer, sheet_name=safe_sheet_name, index=False)
        
        # 分類彙總表
        for category, items in categories.items():
            category_data = []
            for item in items:
                if item in all_data:
                    df_item = all_data[item].copy()
                    df_item['細分類'] = item
                    category_data.append(df_item)
            
            if category_data:
                category_df = pd.concat(category_data, ignore_index=True)
                category_df.to_excel(writer, sheet_name=f'彙總_{category}', index=False)
        
        # 總彙總表
        all_summary = []
        for name, df in all_data.items():
            summary_df = df.copy()
            summary_df['分類'] = name
            all_summary.append(summary_df)
        
        if all_summary:
            total_summary = pd.concat(all_summary, ignore_index=True)
            
            # 移除重複的股票（保留漲跌幅最大的）
            if '漲跌幅' in total_summary.columns and '代號' in total_summary.columns:
                total_summary = total_summary.sort_values('漲跌幅', ascending=False, na_position='last')
                total_summary = total_summary.drop_duplicates(subset=['代號'], keep='first')
            
            total_summary.to_excel(writer, sheet_name='總彙總', index=False)
    
    # 格式化Excel
    format_excel(output_path)
    
    # 統計資訊
    total_stocks = sum(len(df) for df in all_data.values())
    log(f"✅ 完成！輸出檔案: {output_path}")
    log(f"成功: {success_count} 個類別，失敗: {fail_count} 個類別")
    log(f"總計取得 {total_stocks} 筆資料")
    
    # 輸出各類別統計
    log("\n各類別資料統計：")
    for category, items in categories.items():
        count = sum(len(all_data.get(item, pd.DataFrame())) for item in items)
        log(f"  {category}: {count} 筆")

def format_excel(file_path: Path):
    """格式化Excel檔案"""
    try:
        wb = load_workbook(file_path)
        
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            
            # 調整欄寬
            column_widths = {
                'A': 8,   # 名次
                'B': 10,  # 代號
                'C': 15,  # 股票名稱
                'D': 12,  # 收盤價
                'E': 10,  # 漲跌
                'F': 10,  # 漲跌幅
                'G': 15,  # 成交量
                'H': 15,  # 成交值
                'I': 15,  # 買超/賣超
                'J': 15,  # 買賣超
                'K': 12,  # 週轉率
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
                            # 價格和金額欄位
                            if any(keyword in str(header) for keyword in ['價', '金額', '成交值']):
                                try:
                                    if isinstance(cell.value, (int, float)):
                                        cell.number_format = '#,##0.00'
                                except:
                                    pass
                            # 百分比欄位
                            elif any(keyword in str(header) for keyword in ['幅', '率']):
                                try:
                                    if isinstance(cell.value, (int, float)):
                                        if '週轉率' not in str(header):
                                            cell.value = cell.value / 100 if cell.value > 1 else cell.value
                                        cell.number_format = '0.00%'
                                except:
                                    pass
                            # 數量欄位
                            elif any(keyword in str(header) for keyword in ['量', '張', '買超', '賣超']):
                                try:
                                    if isinstance(cell.value, (int, float)):
                                        cell.number_format = '#,##0'
                                except:
                                    pass
        
        wb.save(file_path)
        log("Excel格式化完成")
    except Exception as e:
        log(f"Excel格式化錯誤: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("程式被使用者中斷")
    except Exception as e:
        log(f"執行錯誤: {e}")
        import traceback
        traceback.print_exc()