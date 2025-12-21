# Quick Start Guide - 重啟後快速開始

## 從零開始（電腦重啟後）

### 1. 開啟終端機

打開 Terminal.app

### 2. 初始化 Conda（首次或重啟後）

```bash
# 如果 conda 指令找不到，執行這個
conda init

# 然後重啟終端機，或執行
source ~/.zshrc  # 如果使用 zsh
# 或
source ~/.bash_profile  # 如果使用 bash
```

### 3. 進入專案資料夾

```bash
cd /Users/laihongyi/Downloads/compas-actions.ghpython_components-main
```

### 4. 啟動 Conda 環境

```bash
conda activate gh_timber
```

你應該會看到終端機提示符前面出現 `(gh_timber)`

### 5. 開始開發

#### 開發流程

1. **編輯組件**
   - 在 `components/` 資料夾中修改你的 Python 組件代碼

2. **產生 .ghuser 文件**
   ```bash
   /opt/homebrew/Caskroom/miniconda/base/envs/gh_timber/bin/python componentize_cpy.py components dist --version "0.1.0"
   ```

   或使用簡短版本（需先設定 alias，見下方）：
   ```bash
   gh_comp
   ```

3. **複製到 Grasshopper**
   - 在 Grasshopper 中：`File > Special Folders > User Object Folder`
   - 將 `dist/*.ghuser` 複製進去
   - 重啟 Grasshopper

4. **測試組件**
   - 在 Grasshopper 中找到你的組件並測試

## 設定快捷指令（一次性設定）

### 方法 1: 設定 Alias（推薦）

編輯你的 shell 配置文件：

```bash
# 如果使用 zsh（macOS 預設）
nano ~/.zshrc

# 如果使用 bash
nano ~/.bash_profile
```

在文件最後加入：

```bash
# GH Timber Development
alias gh_comp='cd /Users/laihongyi/Downloads/compas-actions.ghpython_components-main && /opt/homebrew/Caskroom/miniconda/base/envs/gh_timber/bin/python componentize_cpy.py components dist --version "0.1.0"'
alias gh_dev='cd /Users/laihongyi/Downloads/compas-actions.ghpython_components-main && conda activate gh_timber'
```

保存後執行：
```bash
source ~/.zshrc  # 或 source ~/.bash_profile
```

**以後使用：**
```bash
gh_dev    # 進入專案並啟動環境
gh_comp   # 產生組件文件
```

### 方法 2: 創建執行腳本

創建一個執行腳本：

```bash
cat > ~/gh_componentize.sh << 'EOF'
#!/bin/bash
cd /Users/laihongyi/Downloads/compas-actions.ghpython_components-main
/opt/homebrew/Caskroom/miniconda/base/envs/gh_timber/bin/python componentize_cpy.py components dist --version "$1"
EOF

chmod +x ~/gh_componentize.sh
```

**使用：**
```bash
~/gh_componentize.sh "0.1.0"
```

## 常用指令速查表

### Conda 環境管理

```bash
# 查看所有環境
conda env list

# 啟動環境
conda activate gh_timber

# 退出環境
conda deactivate

# 更新環境（當 environment.yml 修改後）
conda env update -f environment.yml
```

### 開發工作流

```bash
# 1. 進入專案
cd /Users/laihongyi/Downloads/compas-actions.ghpython_components-main

# 2. 啟動環境
conda activate gh_timber

# 3. 產生組件
/opt/homebrew/Caskroom/miniconda/base/envs/gh_timber/bin/python componentize_cpy.py components dist --version "0.1.0"

# 4. 查看產生的文件
ls -lh dist/
```

### 檢查環境狀態

```bash
# 檢查 Python 版本和路徑
which python
python --version

# 檢查已安裝的套件
conda list

# 檢查 pythonnet 是否正確安裝
python -c "from pythonnet import set_runtime; print('pythonnet OK')"
```

## 故障排除

### 問題 1: `conda: command not found`

**解決：**
```bash
# 初始化 conda
/opt/homebrew/Caskroom/miniconda/base/bin/conda init

# 重啟終端機或
source ~/.zshrc
```

### 問題 2: `conda activate` 後 Python 還是系統版本

**檢查：**
```bash
which python
```

**如果顯示 `/usr/bin/python3`，使用完整路徑：**
```bash
/opt/homebrew/Caskroom/miniconda/base/envs/gh_timber/bin/python componentize_cpy.py components dist --version "0.1.0"
```

### 問題 3: ModuleNotFoundError: No module named 'pythonnet'

**確認使用正確的 Python：**
```bash
/opt/homebrew/Caskroom/miniconda/base/envs/gh_timber/bin/python -c "import pythonnet; print('OK')"
```

如果還是錯誤，重新安裝：
```bash
/opt/homebrew/Caskroom/miniconda/base/envs/gh_timber/bin/pip install --force-reinstall pythonnet==3.0.1
```

## 典型開發流程範例

### 早上開始工作

```bash
# 1. 開啟終端機
# 2. 進入專案
cd /Users/laihongyi/Downloads/compas-actions.ghpython_components-main

# 3. 啟動環境（如果有設定 alias）
gh_dev

# 或手動
conda activate gh_timber
```

### 開發迭代

```bash
# 編輯代碼...
# 使用你喜歡的編輯器編輯 components/ 中的文件

# 產生組件
gh_comp  # 如果有設定 alias

# 或完整指令
/opt/homebrew/Caskroom/miniconda/base/envs/gh_timber/bin/python componentize_cpy.py components dist --version "0.1.0"

# 複製到 Grasshopper
# 在 Grasshopper: File > Special Folders > User Object Folder
# 複製 dist/*.ghuser

# 重啟 Grasshopper 測試
```

### 結束工作

```bash
# 退出環境（可選）
conda deactivate
```

## 更新版本號

當你準備發布新版本時：

```bash
# 修改版本號
gh_comp  # 或
/opt/homebrew/Caskroom/miniconda/base/envs/gh_timber/bin/python componentize_cpy.py components dist --version "0.2.0"
```

## 備註

- ✅ env_path.txt 已配置，無需每次修改
- ✅ python.runtimeconfig.json 已配置，無需每次修改
- ✅ componentize_cpy.py 已修正，無需每次修改
- 🔄 只需專注於開發 `components/` 中的組件代碼

---

最後更新：2025-12-21
