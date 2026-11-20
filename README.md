# ELRS → USB → 電腦：從零開始的使用教學

本專案使用 **RadioMaster Pocket → BETAFPV Nano 2400 RX → Prolific PL2303 → MacBook**，在 Python 讀取 ExpressLRS 遙控器的 16 個 CRSF 通道。未來可接 AMR 上位機，但**目前只有接收與顯示功能，不會讓 AMR 移動**。

本教學針對第一次接觸 ELRS、UART、Python 的使用者撰寫。每個要調整的參數都標示「在接收器改」或「在電腦改」，可直接套用到其他 USB-UART 裝置。

## 0. 我們實際用的硬體

| 角色 | 實機型號／版本 | 需要注意 |
| --- | --- | --- |
| 遙控器／無線發射端 | **RadioMaster Pocket**，需為 **ELRS 2.4 GHz 版** | Pocket 也有 CC2500 版本，不能直接當 ELRS 發射器 |
| 接收器 | **BETAFPV Nano 2400 RX（2.4 GHz）** | 本次 Web UI 顯示 **ExpressLRS 3.6.2** |
| USB 串列轉換器 | **Prolific PL2303 系列** | macOS 顯示 **VID:PID = 067B:2303**；具體 PL2303 晶片子型號與 TTL 電平仍須依模組確認 |
| 電腦 | **MacBook / macOS** | Python 3 + PySerial；使用者測試環境曾為 Python 3.15 |
| 接收器供電 | 依 Nano RX 板上標示及產品規格提供適當電源 | 請先確認電壓和電源電流，不要直接拿 UART 信號腳供電 |

### 系統架構

```text
RadioMaster Pocket ── ELRS 2.4 GHz ──> BETAFPV Nano 2400 RX
                                             │ TX (CRSF UART)
                                             │ GND
                                             ▼
                                  PL2303 USB-to-TTL UART
                                             │ USB
                                             ▼
                                     Mac / Python
                                   monitor_crsf.py
                                             │
                             [未來] 安全監督 + AMR 控制 API
                                             ▼
                                            AMR
```

**重要：PL2303 只是 USB-Serial 晶片系列名稱，不保證你買到的是 TTL 模組。** 市售轉換器可能再加 RS232 收發晶片。確認 PL2303 輸出是非反相、**3.3 V TTL 相容邏輯訊號**後，才可接 Nano RX 的 UART；不可把 RS232 或 RS485 A/B 線直接連 Nano RX。若無法確定，先拍 PCB 正反面、查模組型號，或量測電壓。

## 1. 接線：先斷電，逐條確認

| Nano RX 腳位 | USB-TTL 模組腳位 | 為什麼 |
| --- | --- | --- |
| **TX** | **RXD** | 接收器把 CRSF 資料送到電腦 |
| **GND** | **GND** | 共同的訊號參考地 |
| RX | 暫時不接 | 初期只讀搖桿資料 |
| VCC | 獨立且正確的電源 | 依 Nano RX 規格供電，不要任意把兩路 5V 並聯 |

兩顆裝置都先斷電再接線。此教學沒有要求把 Nano RX 的 RX 接回 PL2303 TXD，也不需要先連接 AMR。接收器有天線時，應正確裝上天線再操作。

## 2. 第一次配對 RadioMaster Pocket

1. 確認 Pocket 是 **ELRS 2.4 GHz** 版本。進入模型設定（長按 `MDL`），確認 `Internal RF → Mode` 使用 `CRSF`；若顯示 `MULTI`，先確認機型是否為 CC2500。
2. 依 ExpressLRS 接收器配對程序，**快速上電三次、第四次保持上電**，觀察 Nano RX 的 LED 進入「雙閃後暫停」模式；操作節奏請以該板子的韌體說明為準。
3. 在 Pocket 進入 `SYS → TOOLS → ExpressLRS → Bind`。
4. **Nano RX LED 恆亮**通常代表無線配對／連線成功。它不代表電腦已收到有效 UART 資料。
5. 如果 Nano RX 一直連續快閃，它可能已進入 Wi-Fi 模式。重新上電並檢查模式；需調整韌體設定時，用 Mac 加入 `ExpressLRS RX` Wi-Fi，開啟 `http://10.0.0.1`。

**切勿公開 Binding Phrase、Wi-Fi 密碼、金鑰或內網機敏資訊。** 不同 ELRS 主要韌體版本可能不相容，請先核對發射端與接收端。

## 3. 接收器 Web UI：這是第一個要修改的地方

本次實測發現：原設定 `420000 baud`，Mac 有收到大量 `FD/FC/F9` 等亂碼，無法解析 CRSF；使用者回報把兩端都設成 **230400 baud** 後成功。這是**本組硬體的實測配置**，不是所有 ELRS 裝置的通用速率。

| Nano RX Web UI 設定 | 本專案建議值 | 在哪裡修改 |
| --- | --- | --- |
| `Serial Protocol` | **CRSF** | Nano RX 的 Web UI |
| `UART Baud` | **230400**（本次成功） | Nano RX 的 Web UI |
| `Use as AirPort Serial device` | **關閉** | Nano RX 的 Web UI |
| `Invert TX Pin` | 若顯示該選項且用一般 UART TTL，通常關閉 | Nano RX 的 Web UI；沒有選項不必自行臆測 |

更改後按 **SAVE**，必要時重新上電。後面電腦執行 `--baud 230400`，兩端值**必須一致**。如果你改用其他轉換器／飛控，可能改回 ELRS 常用 `420000`；請同時修改兩端。

## 4. Mac 環境：第一次只要照貼一次

開啟 Terminal：

```bash
git clone https://github.com/HJMikeWu/ELRS-AMR-Remote-Control.git
cd ELRS-AMR-Remote-Control

python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

看到終端機前綴 `(.venv)` 即已進入虛擬環境。以後重新開 Terminal，只需 `cd ELRS-AMR-Remote-Control && source .venv/bin/activate`。

### 找到 USB 轉換器

```bash
python monitor_crsf.py --list-ports
```

本次 PL2303 會顯示類似：

```text
/dev/cu.usbserial-1220 | USB-Serial Controller | VID:PID=067B:2303
```

曾出現 `/dev/cu.usbserial-1130`，後來 USB Hub／插孔改變後變 `/dev/cu.usbserial-1220`，**這是 macOS 可能重新編號，不是程式故障**。程式預設會根據 `067B:2303` 自動找唯一的 PL2303。

## 5. 開始讀取 16 個通道

先開 Pocket、確認 Nano RX LED 恆亮，再執行：

```bash
python monitor_crsf.py --baud 230400
```

若收到有效 CRSF RC Channels Packed 封包，會看到 `CH01` 到 `CH16` 數值。移動搖桿，確認有對應通道改變。用 **Ctrl+C** 停止。

**有資料不等於通過**：必須看到有效 CRC 的 RC 通道封包，而且通道值要隨搖桿變動。正式驗證請保留畫面截圖及實際鮑率測量。

## 6. 換裝置時，到底改哪裡？

**不需要直接編輯 Python 原始碼。** 程式提供參數：

| 情境 | 要改哪裡 | 指令範例 |
| --- | --- | --- |
| 我用本次 PL2303 | 不用改埠號，預設 VID/PID 自動偵測 | `python monitor_crsf.py --baud 230400` |
| 換 CH340、CP2102、FT232 或其他 USB-UART | 找到新埠號，指定 `--port` | `python monitor_crsf.py --list-ports`，再 `python monitor_crsf.py --port /dev/cu.usbserial-XXXX --baud 230400` |
| 同時插多顆 PL2303 | 明確指定 `--port` | `python monitor_crsf.py --port /dev/cu.usbserial-1220 --baud 230400` |
| RX 的 UART Baud 改為 420000 | **接收器 Web UI** 設為 420000，**電腦**也設 `--baud 420000` | `python monitor_crsf.py --baud 420000` |
| 換 Windows | 在 `--list-ports` 找 COM 名稱 | `python monitor_crsf.py --port COM3 --baud 230400` |
| 換 Linux / Jetson / Raspberry Pi | 找到 `/dev/ttyUSB0` 等裝置 | `python monitor_crsf.py --port /dev/ttyUSB0 --baud 230400` |
| 要換 ELRS 發射器 | 確認同頻段、版本相容，再重新配對 | Python 通常不用改，除非 UART 設定改變 |

上表中的裝置路徑是**示意**，以你電腦實際列出的埠號為準。

### 重要：通道與 AMR 方向不能硬編碼

CH1、CH2 不一定就是轉向和前後，取決於 Pocket 的模型設定、搖桿模式、混控以及 Channel Mapping。先在監控畫面逐一操作搖桿，記錄**哪個 CH 會動、中央值、最大值、最小值、開關位置**，再決定 AMR 控制對應。CRSF 常見通道數值約 172–1811，中立附近約 992，但實際應以量測校正。

## 7. 故障排除：按症狀走

| 現象 | 優先檢查 | 怎麼做 |
| --- | --- | --- |
| `No such file or directory: /dev/cu.usbserial-1130` | USB 埠號變更 | 用 `--list-ports`，不要寫死舊埠 |
| `Expected exactly one PL2303` | 沒插、或插了兩顆 | 重新插 USB；有多顆時用 `--port` |
| `Waiting for valid CRSF RC frames` | UART 不相容／未接到有效 CRSF | 確認 RX LED 恆亮、TX→RXD、GND、兩端相同 baud |
| 原始資料一直是 `FD/FC/F9` | 可能鮑率、電壓、訊號極性問題 | 先確認 TTL 電氣相容，再用本次雙端 230400；仍失敗則量測 UART 波形 |
| 接收器 LED 持續快閃 | 可能 Wi-Fi 模式 | 重新上電、查 ELRS Wi-Fi 設定 |
| CH 有值但搖桿不會動 | 通道映射、模型設定或資料未刷新 |逐一移動搖桿並觀察 RC Frames 數量 |
| 有少量 CRC 符合但沒有 CH | 偶然 CRC 符合或非 RC 封包 | 不要當作通訊成功，需連續有效 RC 封包 |

本次歷史測試：`420000` 接收時 10 秒約 1537 bytes 的異常資料；5 秒 768 bytes，正常／位元組反相均無有效 CRSF 封包。固定 RX 為 420000、只掃描電腦端 baud 的實驗曾在 115200／230400 出現少量 CRC 候選，**不代表已解碼成功**。單純對位元組做 `XOR 0xFF` 也不能修復實體 UART 反相引起的 framing error。

## 8. 想拿來控制 AMR？目前先不要直接接馬達

本專案刻意只讀搖桿。真正驅動 AMR 之前必須加入控制權仲裁、手動使能、搖桿死區、速度和加速度限制、資料逾時停車、獨立 E-stop 和底盤安全控制。**RC 通道資料有效不代表控制系統具備安全性**。應先架空或禁動測試，再在受控場域低速驗證。

## 9. 從零重現檢查清單

- [ ] 確認 Pocket 是 ELRS 2.4 GHz 版
- [ ] 確認 Nano 2400 RX 型號、供電、天線與 ELRS 韌體版本
- [ ] 確認 PL2303 模組是 TTL UART、電壓相容
- [ ] 斷電完成 TX→RXD、GND→GND 接線
- [ ] Nano RX LED 恆亮（無線已連線）
- [ ] Nano Web UI 為 CRSF / 230400，已 SAVE
- [ ] Python 虛擬環境與 pyserial 已安裝
- [ ] `--list-ports` 找得到 USB 序列埠
- [ ] `monitor_crsf.py --baud 230400` 顯示 CH01～CH16
- [ ] 搖桿數值變化符合預期

## 官方參考
- [ExpressLRS Getting Started](https://www.expresslrs.org/quick-start/getting-started/)
- [ExpressLRS Web UI](https://www.expresslrs.org/quick-start/webui/)
- [ExpressLRS Serial Protocols](https://www.expresslrs.org/software/serial-protocols/)

最後更新：2026-11-20。本文件區分「本次使用者實機成功回報」與「尚未做儀器量測驗證」；公開版本不收錄 Binding Phrase。
