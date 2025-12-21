# Setup Fixes for GH Timber Componentization

## 問題總結

在 macOS ARM64 (Apple Silicon) 環境下，使用 pythonnet 3.x 與 Rhino 8 的 .NET 8.0 runtime 進行 Grasshopper 組件化時遇到兼容性問題。

## 解決方案

### 1. 環境配置

#### 安裝必要軟件
```bash
# 安裝 .NET 9.0 Runtime（通過 Homebrew）
brew install --cask dotnet

# 創建並配置 conda 環境
conda env create -f environment.yml
conda activate gh_timber
```

#### 設定 env_path.txt
文件路徑：`env_path.txt`

```
/opt/homebrew/Caskroom/miniconda/base/envs/gh_timber/lib/python3.9/site-packages/
```

### 2. Runtime 配置文件

創建 `python.runtimeconfig.json` 以支持 .NET 8.0：

```json
{
  "runtimeOptions": {
    "tfm": "net8.0",
    "rollForward": "LatestMinor",
    "framework": {
      "name": "Microsoft.NETCore.App",
      "version": "8.0.0"
    }
  }
}
```

### 3. componentize_cpy.py 修改

#### 修改點 1: macOS .NET Runtime 設定（行 13-36）

**原始代碼：**
```python
if platform.system() == "Darwin":
    rhino_dotnet_base = "/Applications/Rhino 8.app/Contents/Frameworks/RhCore.framework/Versions/A/Resources/dotnet"
    arch = platform.machine()
    dotnet_root = os.path.join(rhino_dotnet_base, arch)

    if os.path.exists(dotnet_root):
        print(f"Configuring pythonnet to use Rhino 8 .NET runtime from: {dotnet_root}")
        os.environ["DOTNET_ROOT"] = dotnet_root
        os.environ["PYTHONNET_RUNTIME"] = "coreclr"
    else:
        print(f"Error: Rhino 8 .NET runtime not found at {dotnet_root}")
        sys.exit(1)
```

**修正後：**
```python
if platform.system() == "Darwin":
    # Use Rhino .NET 8 (compatible with GH_IO.dll)
    rhino_dotnet_base = "/Applications/Rhino 8.app/Contents/Frameworks/RhCore.framework/Versions/A/Resources/dotnet"
    arch = platform.machine()
    dotnet_root = os.path.join(rhino_dotnet_base, arch)

    if os.path.exists(dotnet_root):
        print(f"Configuring pythonnet to use Rhino 8 .NET runtime from: {dotnet_root}")

        # Set runtime config before importing pythonnet
        script_dir = os.path.dirname(os.path.abspath(__file__))
        runtime_config = os.path.join(script_dir, "python.runtimeconfig.json")
        if os.path.exists(runtime_config):
            os.environ["PYTHONNET_RUNTIME_CONFIG"] = runtime_config

        # Import pythonnet and set runtime manually
        from pythonnet import set_runtime
        from clr_loader import get_coreclr

        rt = get_coreclr(runtime_config=runtime_config, dotnet_root=dotnet_root)
        set_runtime(rt)
    else:
        print(f"Error: Rhino 8 .NET runtime not found at {dotnet_root}")
        sys.exit(1)
```

## 使用方法

### 執行 Componentization

**方法 1: 使用完整路徑（推薦）**
```bash
cd /Users/laihongyi/Downloads/compas-actions.ghpython_components-main
/opt/homebrew/Caskroom/miniconda/base/envs/gh_timber/bin/python componentize_cpy.py components dist --version "0.1.0"
```

**方法 2: 設定 Alias**

在 `~/.zshrc` 或 `~/.bash_profile` 添加：
```bash
alias gh_comp='cd /Users/laihongyi/Downloads/compas-actions.ghpython_components-main && /opt/homebrew/Caskroom/miniconda/base/envs/gh_timber/bin/python componentize_cpy.py components dist --version "0.1.0"'
```

然後執行：
```bash
source ~/.zshrc  # 或 source ~/.bash_profile
gh_comp
```

### 安裝到 Grasshopper

1. 開啟 Grasshopper
2. 點選 `File > Special Folders > User Object Folder`
3. 將 `dist/*.ghuser` 文件複製到該資料夾
4. 重啟 Grasshopper

## 技術說明

### 為什麼需要這些修改？

1. **pythonnet 3.x 版本要求**：
   - pythonnet 3.0.1+ 預設需要 .NET 9.0
   - Rhino 8 只提供 .NET 8.0.14

2. **解決方案**：
   - 通過 `python.runtimeconfig.json` 指定使用 .NET 8.0
   - 在 Python 代碼中手動設定 runtime，繞過 pythonnet 的自動檢測
   - 使用 `get_coreclr` 和 `set_runtime` 直接配置 CLR

3. **為什麼不能使用 Homebrew .NET 9.0**：
   - Rhino 的 GH_IO.dll 是用 .NET 8.0 編譯的
   - .NET 9.0 runtime 無法載入 .NET 8.0 的 DLL
   - 必須使用與 Rhino 相同版本的 .NET runtime

## 相依套件

- Python: 3.9.10
- pythonnet: 3.0.1
- networkx: 3.2.1
- .NET Runtime: 8.0.14 (來自 Rhino 8)
- .NET SDK: 9.0.8 (來自 Homebrew，用於 pythonnet 安裝)

## 故障排除

### conda activate 無效
如果執行 `conda activate gh_timber` 後 `python` 仍指向系統 Python：

**臨時解決方案**：
使用完整路徑執行：
```bash
/opt/homebrew/Caskroom/miniconda/base/envs/gh_timber/bin/python componentize_cpy.py components dist --version "0.1.0"
```

**永久解決方案**：
```bash
conda init
# 然後重啟終端機
```

### ModuleNotFoundError: No module named 'clr'
確保使用 conda 環境的 Python：
```bash
which python  # 應該顯示 conda 環境路徑
```

如果不對，使用完整路徑。

### .NET Runtime 錯誤
確認 Rhino 8 已安裝且路徑正確：
```bash
ls -la "/Applications/Rhino 8.app/Contents/Frameworks/RhCore.framework/Versions/A/Resources/dotnet/arm64"
```

## 文件清單

修改或新增的文件：
- ✅ `env_path.txt` - Conda 環境路徑配置
- ✅ `python.runtimeconfig.json` - .NET Runtime 配置
- ✅ `componentize_cpy.py` - 修改 macOS .NET runtime 初始化邏輯

---

最後更新：2025-12-21
