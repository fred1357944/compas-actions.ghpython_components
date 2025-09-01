#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
檢查富邦證券URL狀態的診斷工具
"""

import datetime as dt
from playwright.sync_api import sync_playwright
import time

# 要檢查的URL
CHECK_URLS = {
    # 正常的（應該有資料）
    "漲幅排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_A.djhtm",
    
    # 有問題的法人類
    "投信買超排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_H.djhtm",
    "自營商買超排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_G.djhtm",
    "主力買超排行": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_I.djhtm",
    
    # 有問題的強勢股類
    "三日強勢股": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZGK_CC.djhtm",
    "五日強勢股": "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZGK_AA.djhtm",
}

def check_url(url, name):
    """檢查單個URL的狀態"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            locale='zh-TW'
        )
        page = context.new_page()
        
        print(f"\n{'='*60}")
        print(f"檢查: {name}")
        print(f"URL: {url}")
        print(f"時間: {dt.datetime.now()}")
        
        try:
            # 訪問頁面
            response = page.goto(url, wait_until='networkidle')
            time.sleep(2)
            
            # 取得狀態
            status = response.status if response else "Unknown"
            print(f"HTTP狀態: {status}")
            
            # 取得內容
            content = page.content()
            text = page.inner_text('body')
            
            print(f"頁面大小: {len(content)} bytes")
            
            # 分析內容
            if len(content) < 100:
                print("❌ 頁面內容過少，可能是錯誤頁面")
            
            if '查無排行相關資料' in text:
                print("❌ 頁面顯示: 查無排行相關資料")
                print("原因分析: 可能是非交易日或該類別暫無資料")
                
                # 嘗試找到日期選項
                date_options = page.query_selector_all('option')
                if date_options:
                    print(f"找到 {len(date_options)} 個日期選項")
                    for opt in date_options[:5]:
                        print(f"  - {opt.inner_text()}")
                        
            elif '無此排行榜資料' in text:
                print("❌ 頁面顯示: 無此排行榜資料")
                print("原因分析: 此URL可能已廢棄或需要特定參數")
                
            elif '請先登入' in text or 'login' in text.lower():
                print("❌ 需要登入")
                
            else:
                # 檢查表格
                tables = page.query_selector_all('table')
                print(f"表格數量: {len(tables)}")
                
                # 檢查是否有股票資料
                if '2330' in text or '台積電' in text:
                    print("✅ 找到股票資料")
                    
                # 顯示部分內容
                lines = text.split('\n')
                data_lines = [l for l in lines if any(c.isdigit() for c in l)][:5]
                if data_lines:
                    print("資料樣本:")
                    for line in data_lines:
                        print(f"  {line[:80]}")
            
            # 檢查JavaScript錯誤
            js_errors = []
            page.on("pageerror", lambda err: js_errors.append(str(err)))
            if js_errors:
                print(f"JavaScript錯誤: {js_errors}")
                
        except Exception as e:
            print(f"❌ 錯誤: {str(e)}")
            
        finally:
            browser.close()

def main():
    print("富邦證券URL診斷報告")
    print(f"執行時間: {dt.datetime.now()}")
    print(f"今天是: {dt.datetime.now().strftime('%A')}")
    
    # 判斷是否為交易日
    weekday = dt.datetime.now().weekday()
    if weekday >= 5:  # 週六=5, 週日=6
        print("⚠️ 注意: 今天是週末，某些資料可能不會更新")
    
    # 檢查每個URL
    for name, url in CHECK_URLS.items():
        check_url(url, name)
    
    print("\n" + "="*60)
    print("診斷完成")
    print("\n可能的解決方案:")
    print("1. 某些資料只在交易日更新（週一到週五）")
    print("2. 法人買賣資料可能有時間延遲（T+1日）")
    print("3. 強勢股資料可能需要累積多日才會產生")
    print("4. 可以考慮使用其他替代資料源")

if __name__ == "__main__":
    main()