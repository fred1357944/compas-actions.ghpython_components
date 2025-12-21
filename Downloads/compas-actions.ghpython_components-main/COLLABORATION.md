# Surface Analysis Tool & Collaboration Guide

本專案包含 Grasshopper Python UserObjects 的原始碼與自動化構建工具。主要功能為六角形曲面分析工具。

## 1. 專案結構

- `components/`: 存放所有 UserObject 的原始碼。
  - `SurfaceAnalysis/`: 六角形曲面分析元件。
    - `code.py`: 核心 Python 邏輯 (使用 RhinoCommon)。
    - `metadata.json`: 元件定義 (輸入、輸出、名稱、圖示)。
    - `icon.png`: 元件圖示 (24x24 px)。
- `componentize_ipy.py`: 構建腳本，負責將源碼打包成 `.ghuser` 檔案。
- `dist/`: 構建完成的 `.ghuser` 檔案存放處 (本地構建)。

## 2. 如何協作與新增元件

若要新增一個新的功能 (例如：結構特性分析)：

1. 在 `components/` 下建立新資料夾，例如 `components/StructuralAnalysis/`。
2. 複製 `SurfaceAnalysis` 中的 `icon.png` (之後可替換) 和 `metadata.json` 作為模板。
3. 修改 `metadata.json`，設定新的名稱、輸入與輸出參數。
4. 建立 `code.py` 並撰寫邏輯。
   - 可使用 `Rhino.Geometry` (as `rg`)。
   - 輸入變數名稱需與 `metadata.json` 中的 `Name` 對應。
   - 輸出變數直接賦值即可。

## 3. 構建說明 (如何產生 .ghuser 檔)

本專案支援本地構建與 GitHub Actions 雲端構建。

### 方法 A: 使用 GitHub Actions (推薦)
這是最簡單的方法，不需要在本地安裝複雜環境。

1. 將修改推送到 GitHub。
2. GitHub Actions 會自動觸發 `build.yml`。
3. 在 GitHub 頁面的 "Actions" 標籤查看進度。
4. 構建完成後，在 "Releases" 或 Artifacts 下載最新的 `.ghuser` 檔案。

### 方法 B: 本地構建 (macOS / Windows)

若需在本地測試，請遵循以下步驟。

#### 前置需求
1. **Conda**: 建議使用 Anaconda 或 Miniconda。
2. **Mono (僅 macOS)**: 由於 Mac 上需要 Mono 來執行 .NET 相關庫。
   ```bash
   brew install mono
   ```

#### 設定環境
1. 建立 Conda 環境：
   ```bash
   conda env create -f environment.yml
   ```
2. 啟動環境：
   ```bash
   conda activate gh_timber
   ```

#### 執行構建
**Windows:**
```bash
python componentize_ipy.py components dist
```

**macOS:**
需要設定 `DYLD_LIBRARY_PATH` 指向 Mono 的安裝路徑 (通常是 Homebrew 路徑)。
```bash
export DYLD_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_LIBRARY_PATH
python componentize_ipy.py components dist
```

構建成功後，`.ghuser` 檔案將位於 `dist/` 資料夾中。

## 4. 常見問題

**Q: macOS 上報錯 `System.DllNotFoundException` 或 `OSError: cannot load library ...`**
A: 這是因為 pythonnet 找不到 Mono。請確保已安裝 `brew install mono` 並且在執行 python 前設定了 `export DYLD_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_LIBRARY_PATH`。

**Q: 如何更改圖示？**
A: 替換 component 資料夾內的 `icon.png` 即可，建議尺寸為 24x24 像素。
