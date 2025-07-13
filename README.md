# Semi-Apply Job Automation Tool

半自動化投遞 Pipeline，支持 2025 年北美 SDE / AI / DS / DE 崗位批量申請。

## 🎯 項目目標

- **數據統一源**：Notion 數據庫（JD & 投遞記錄）
- **自動化層**：Playwright 腳本完成 80% 以上表單填充
- **智能內容層**：通過 OpenAI API 完成 JD⇆簡歷匹配、關鍵詞補全、bullet 重寫
- **日誌與監控**：所有步驟結果回寫 Notion，並保存截圖或錯誤棧

## 🚀 快速開始

### 環境要求

- Python 3.11+
- Notion API Token
- OpenAI API Key（後續階段需要）

### 安裝步驟

1. 克隆項目
```bash
git clone https://github.com/yourusername/semi-apply.git
cd semi-apply
```

2. 創建虛擬環境
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows
```

3. 安裝依賴
```bash
pip install -r requirements.txt
```

4. 配置環境變量
```bash
cp .env.example .env
# 編輯 .env 文件，填入你的 Notion Token 和 Database ID
```

### 使用方法

#### 1. 查看配置
```bash
python jobbot.py ingest config
```

#### 2. 列出待處理的職位
```bash
python jobbot.py ingest list --status TODO
```

#### 3. 檢測職位網站類型
```bash
python jobbot.py ingest detect "https://boards.greenhouse.io/company/jobs/123456"
```

#### 4. 測試所有組件
```bash
python jobbot.py ingest test
```

## 📁 項目結構

```
semi-apply/
├── ingestion/              # 數據採集模塊
│   ├── cli.py             # CLI 命令
│   ├── settings.py        # 配置管理
│   ├── models/            # 數據模型
│   │   └── job.py         # 職位數據模型
│   ├── services/          # 服務層
│   │   └── notion_service.py  # Notion API 封裝
│   ├── parsers/           # 網站解析器（待實現）
│   └── utils/             # 工具函數
│       └── site_detector.py   # 網站檢測器
├── data/                  # 數據存儲
│   └── raw/              # 原始 JD JSON 文件
├── logs/                  # 日誌文件
├── jobbot.py             # 主 CLI 入口
├── requirements.txt       # Python 依賴
└── README.md             # 本文件
```

## 🔧 配置說明

### Notion 設置

1. 創建 Notion Integration：https://www.notion.so/my-integrations
2. 獲取 Integration Token
3. 將 Integration 添加到你的數據庫
4. 獲取數據庫 ID（在數據庫 URL 中）

### 環境變量

```env
# Notion Configuration
NOTION_TOKEN=your_notion_integration_token
DATABASE_ID=your_notion_database_id

# Application Settings
LOG_LEVEL=INFO
REQUEST_TIMEOUT=10
```

## 📊 Notion 數據庫結構

| 字段 | 描述 | 類型 |
|------|------|------|
| JD_ID | 崗位在數據庫中的 ID | Number |
| JD_Link | 職位原始鏈接 | URL |
| Company | 公司 | Text |
| Title | 崗位標題 | Text |
| Status | TODO / Processing / Parsed / Error / Filling / Submitted / Failed | Select |
| LLM_Notes | LLM 生成的注意事項 | Rich Text |
| Last_Error | 最近一次錯誤信息 | Rich Text |
| My_Notes | 個人筆記 | Rich Text |
| Created_Time | 創建時間 | Date |

## 🛠️ 開發路線圖

### Phase 0: 環境搭建 ✅
- [x] 配置管理 (settings.py)
- [x] Notion SDK 封裝
- [x] CLI 基礎框架
- [x] 站點檢測器

### Phase 1: 內容智能 MVP 🚧
- [ ] JD 解析器 (Greenhouse, Workday)
- [ ] GPT 服務集成
- [ ] 簡歷模板渲染
- [ ] PDF 生成

### Phase 2: Playwright 填表 📋
- [ ] 自動填表框架
- [ ] Selector 映射配置
- [ ] Fallback 鏈實現

### Phase 3: 穩定性與通知 🔔
- [ ] LLM selector 自愈
- [ ] 異常截圖與通知
- [ ] CI/CD 集成

## 🤝 貢獻指南

1. Fork 項目
2. 創建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 開啟 Pull Request

## 📄 許可證

MIT License - 詳見 [LICENSE](LICENSE) 文件

## 👨‍💻 作者

Nick Huo

---

**注意**：本工具僅供學習和個人使用，請遵守各招聘網站的使用條款。
