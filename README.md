# ELRS AMR Remote Control — RadioMaster Pocket + Nano 2400 RX + PL2303

以 RadioMaster Pocket (ELRS 2.4 GHz) 遙控器，透過 BETAFPV Nano 2400 RX 接收 CRSF UART，再由 PL2303 USB-Serial 與 macOS Python / PySerial 讀取通道。目標為後續整合 AMR 上位機，**本專案目前僅提供遙控資料監看，不會驅動 AMR**。

> 實測紀錄：2026-11，ExpressLRS RX 韌體 3.6.2；使用者回報把接收器與程式設定為 **230400 baud** 後已解決先前無法解碼的問題。當時沒有保存最後一份通道輸出紀錄或儀器波形，因此 230400 是「本次實機成功設定」，**不是**所有 PL2303 / ELRS 裝置的通用預設值。ELRS 原始設定為 CRSF / 420000 baud。

## 1. 硬體與訊號路徑

```text
RadioMaster Pocket (確認為 ELRS 2.4 GHz 版本)
          │ ExpressLRS 無線
          ▼
BETAFPV Nano 2400 RX (ELRS v3.6.2)
          │ CRSF UART TX
          ▼
PL2303 USB-to-TTL UART (必須確認是 TTL，而非 RS232 版本)
          │ USB
          ▼
Mac / Python (PySerial + CRSF decoder)
          │ 未來：經過命令轉換、控制權仲裁與安全監督
          ▼
AMR 控制器
```

**重要電氣安全：PL2303 是 USB-Serial 晶片名稱，不代表成品一定輸出 TTL。** USB-to-RS232 轉換器的電平可能損壞 Nano RX。連線前確認模組有 TTL UART 訊號、邏輯電壓相容（通常 3.3 V），並用萬用表／示波器驗證。PL2303 的 VCC 供電腳與 TX/RX 邏輯電壓是不同概念。

最小接線（兩端先斷電）：

| Nano 2400 RX | PL2303（已確認 TTL 版本） | 說明 |
|---|---|---|
| TX | RXD | 只讀 CRSF 通道 |
| GND | GND | 必須共地 |
| RX | 不接 | 初期不需要回傳遙測 |
| VCC | 依接收器標示供電 | 不要直接並接兩個電源；確認 5V 供電額定能力 |

確認接收器天線已安裝、供電正確，再讓接收器上電。不要直接把 RS485 A/B 接到 Nano RX UART。

## 2. RadioMaster Pocket 配對

1. 確認 Pocket 為 **ELRS 2.4 GHz** 版本，而非 CC2500 版本；模型設定的 Internal RF 使用 CRSF，ExpressLRS 腳本可正常開啟。
2. 接收器先斷電。依 ExpressLRS 接收器的「快速上電三次」程序進入 Bind（雙閃、暫停），實際操作以該韌體版本官方說明為準。
3. Pocket 中進入 `SYS → TOOLS → ExpressLRS → Bind`。
4. 接收器 LED 恆亮代表無線連線建立；這**不等於** USB UART 已完成驗證。
5. 遙控器與接收器應使用相容的 ELRS 主要韌體版本；若兩者設有不同 Binding Phrase，可能無法手動配對。**不要把 Binding Phrase、Wi-Fi 密碼或其他憑證推上公開 GitHub。**

若接收器一直連續快閃，常見為 Wi-Fi 模式；可斷電後重新上電觀察。進入 Wi-Fi 設定時可連接 `ExpressLRS RX`（若仍為原廠預設，密碼請參考官方文件），開啟 `http://10.0.0.1`。

## 3. 設定 RX 的 UART

進入 Nano RX 的 ExpressLRS Web UI，確認：

- `Serial Protocol = CRSF`
- 本次 PL2303 實驗成功設定：`UART Baud = 230400`
- `Use as AirPort Serial device`：關閉，避免改為不同用途的序列功能
- 若有 `Invert TX Pin` 選項，配合一般非反相 TTL UART，通常應關閉；若選項不存在，不要自行假設已啟用

儲存後按需重啟接收器。**RX UART 與 Python 必須設定相同鮑率**；不要把 ELRS 無線封包更新率與 UART baud 混為一談。若改用其他 USB-UART 或飛控，可能需要恢復 420000 baud。

## 4. macOS 建立測試環境

```bash
mkdir -p ~/Desktop/Ju_CodeWork/pl2303_remote
cd ~/Desktop/Ju_CodeWork/pl2303_remote
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install pyserial
python -m serial.tools.list_ports -v
```

已驗證的 PL2303 VID:PID：`067B:2303`。在 macOS 出現 `/dev/cu.usbserial-1130`，重新插拔／換 Hub 後可能變為 `/dev/cu.usbserial-1220`，**不可將序列埠名稱寫死**。本儲存庫的 `monitor_crsf.py` 會依 VID:PID 自動偵測。

下載／clone 本 repo 後：

```bash
git clone https://github.com/HJMikeWu/ELRS-AMR-Remote-Control.git
cd ELRS-AMR-Remote-Control
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python monitor_crsf.py --baud 230400
```

移動 Pocket 的搖桿、切換開關，確認 CH1–CH16 的數值變化。使用 `Ctrl+C` 結束監控。

## 5. 診斷過程與教訓

本次測試：

| 階段 | 結果 | 解讀 |
|---|---|---|
| PL2303 裝置辨識 | `VID:PID=067B:2303` | macOS 正常列出 USB Serial |
| Python 開啟 115200 / 420000 | 兩者 PASS | **只證明驅動接受設定，不證明真實波特率正確** |
| RX 原本設定 | CRSF / 420000 | 接收器設定截圖已確認 |
| 420000 原始資料 | 大量 `FD FC F9 FE` 等、沒有可解 CRSF | 可能為鮑率不匹配、電平或極性問題 |
| 位元組反相診斷 | 正常及反相均 0 個有效候選 | 軟體 XOR 0xFF 不會修復 UART 實體位元反相造成的取樣錯誤 |
| 不同 PC 鮑率掃描，RX 仍固定 420000 | 115200: 3174 bytes/2 CRC 候選；230400: 6325/15；400000–500000: 約 462/0 | 僅掃描位元組中的偶然 CRC 符合不算有效 CRSF，不能因此判定正確鮑率 |
| 兩端調整 | 使用者回報改為 230400 後「搞定」 | 本次可行設定，後續仍建議保留實際通道輸出與波形證據 |

若畫面只顯示 `Waiting for valid CRSF data...`，請依序查：
1. 接收器 LED 是否恆亮，且 RX 設定為 CRSF。
2. 供電、共地、Nano TX → PL2303 RXD；確認 PL2303 **確為 TTL**。
3. `python -m serial.tools.list_ports -v` 是否仍有 VID/PID 067B:2303。
4. 接收器與 Python 鮑率一致；先重現本次 `230400` 組合。
5. 若仍失敗，用示波器／邏輯分析儀直接量測 RX TX 腳的 idle 電壓、位元寬度、極性與實際鮑率，而非無限制試不同 baud。

## 6. AMR 整合前的安全界線

**目前程式僅為監控工具，不能直接控制實車。** 後續需要：
- 只在明確啟用人工遙控時才接受搖桿命令，並定義控制權仲裁。
- 搖桿死區、速度上限、加速度限制與命令合法性檢查。
- 無有效 CRSF 資料或控制程序失聯時，在車載控制器實作逾時停止（watchdog），不能僅靠上位機 UI 顯示。
- 保留獨立的實體 E-stop、安全迴路及障礙物安全機制；遙控器的開關不可替代安全等級的緊急停止設備。
- 實車前先在底盤架空或禁動環境測試所有失效情境。

## 官方參考
- [ExpressLRS Quick Start](https://www.expresslrs.org/quick-start/getting-started/)
- [ExpressLRS Web UI](https://www.expresslrs.org/quick-start/webui/)
- [ExpressLRS Serial Protocols](https://www.expresslrs.org/software/serial-protocols/)

文件紀錄實驗配置及障礙排除，不把未量測數據視為正式驗證。
