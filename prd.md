## 1. 项目目标

* **半自动化投递 Pipeline**，支持 2025 年北美 SDE / AI / DS / DE 岗位批量申请。
* **数据统一源**：Notion 数据库（JD & 投递记录）。
* **自动化层**：Playwright 脚本完成 80 % 以上表单填充，剩余 20 % 由人工点击 “Submit”。
* **智能内容层**：通过 **OpenAI API**（GPT-4o 或同等级）完成 JD⇆简历 匹配、关键词补全、bullet 重写等。
* **日志与监控**：所有步骤结果回写 Notion，并保存截图或错误栈。

---

## 2. 总体架构

```
┌────────────┐       ┌──────────────────────┐
│  浏览器扩展├──────►│ Notion API (JD 采集) │
└────────────┘       └────────────┬─────────┘
                                  │
                    ┌─────────────▼──────────┐
                    │   Orchestrator CLI     │
                    │  (Python / Typer)      │
                    └─────────┬──────────────┘
      ┌────────────┬──────────┼──────────┬─────────────┐
      │            │          │          │             │
┌─────▼──────┐┌────▼──────┐┌──▼───┐┌─────▼─────┐┌──────▼──────┐
│ JD 抽取 &  ││ 简历模板 ││OpenAI││Playwright ││ 通知中心  │
│ 关键词分析 ││ (LaTeX) ││  API ││ 自动填表 ││ (桌面/邮件)│
└────────────┘└──────────┘└──────┘└──────────┘└──────────────┘
```

* **Orchestrator CLI**：单入口命令行 (`jobbot apply <JD_ID>`)，负责串联各模块。
* **JD 抽取 & 关键词分析**：用正则 + GPT 调用提取岗位要求关键词。
* **简历模板渲染**：JSON→LaTeX→PDF，保证 1 页、字符/行数限制。
* **Playwright 自动填表**：分三阶段 selector 方案（语义→fallback→LLM 自愈）。
* **通知中心**：失败截图、待填字段通过邮件/Telegram/桌面通知推送。

---

## 3. 关键模块接口约定

### 3.1 Notion 表结构

Notion 数据库名称是：get-ng-offer


| 字段           | 描述                                    | 类型        |
| ------------ | ------------------------------------- | --------- |
| `JD_ID`     | 岗位在数据库中的 ID                                | Number       |
| `JD_Link`    | 职位原始链接                                | URL       |
| `Company`    | 公司                                    | Text      |
| `Title`      | 岗位标题                                  | Text      |
| `Status`     | `TODO / Filling / Submitted / Failed` | Select    |
| `LLM_Notes`  | LLM 生成的注意事项                           | Rich Text |
| `Last_Error` | 最近一次错误信息                              | Rich Text |
| `Resume_PDF` | 上传后的 PDF 文件                           | Files     |
| `My_Notes`   | 我对该岗位的笔记                           | Rich Text     |
| `Created_Time` | 该岗位的保存日期                           | Date     |

### 3.2 Orchestrator CLI

```bash
# 单 JD 自动化
jobbot apply <notion_page_id> --dry-run

# 批量（筛选 Status=TODO）
jobbot batch --limit 10
```

### 3.3 GPT Prompt（示例）

```text
系统：你是一名北美软件工程招聘顾问……
用户：岗位描述：<<<{JD_TEXT}>>>  我的原始简历片段：<<<{RESUME_SNIPPETS}>>>
任务：1) 提取匹配度最高的 5 个技术关键词  
      2) 输出 3 条 20 词以内的 bullet，用于替换“项目经历”中的第一段  
      3) 确保整份简历控制在 1 页
格式：
{
  "keywords": [...],
  "bullets": [...]
}
```

---

## 4. Roadmap（四阶段）

| 阶段                           | 时间        | 目标产出                                                                                   | 负责人 |
| ---------------------------- | --------- | -------------------------------------------------------------------------------------- | --- |
| **Phase 0：环境搭建**             | Day 1-2   | • 创建 Notion 数据库<br>• 搭建 Orchestrator CLI 雏形<br>• 成功拉取 JD 并存库                           | @你  |
| **Phase 1：内容智能 MVP**         | Day 3-5   | • 完成 JD→关键词→bullet GPT 调用<br>• LaTeX 模板 JSON 化；可生成定制 PDF                               | @你  |
| **Phase 2：Playwright 填表 v0** | Day 6-10  | • 实现语义 selector + fallback 链<br>• 支持 Greenhouse / Workday 两站点<br>• Dry-run 日志回写 Notion | @你  |
| **Phase 3：稳定性 & 通知**         | Day 11-14 | • LLM selector 自愈 POC<br>• 异常截图推送 Telegram<br>• CI 回归测试（GitHub Actions）                | @你  |

> **注**：若某阶段延期，后续顺延；大家只需对齐 “Phase 完成物” 即可。

---

## 5. TODO 列表（可直接复制为 GitHub Issues）

### 5.1 Phase 0

* [ ] ✅ 初始化 Python 项目 (`poetry`/`pipx`)，创建基础包 `jobbot/*`
* [ ] ✅ 集成 Notion SDK，封装 `NotionClient.get_jd(page_id)`
* [ ] ✅ CLI：`jobbot apply <page_id> --dry-run` 打印 JD 原文

### 5.2 Phase 1

* [ ] 🔲 `jd_parser.py`：正则拆分 “岗位职责 / 任职资格”
* [ ] 🔲 `gpt_service.py`：封装 `call_openai(system_msg, user_msg)`，支持重试
* [ ] 🔲 `resume_renderer.py`：

  * 输入：`resume.json + bullet_updates`
  * 输出：`out/Resume_<company>.pdf`
* [ ] 🔲 单元测试：确保 bullet ≤ 20 词且行数 ≤ 2

### 5.3 Phase 2

* [ ] 🔲 `playwright_runner.py`：基础浏览器上下文（无头 / 有头切换）
* [ ] 🔲 Selector Map YAML：`selectors/greenhouse.yaml`, `selectors/workday.yaml`
* [ ] 🔲 实现 fallback 链（`.or()`）
* [ ] 🔲 `jobbot apply` 实际填表（`--submit` 标志控制是否自动点 Submit）
* [ ] 🔲 成功后更新 Notion.Status = "Submitted"

### 5.4 Phase 3

* [ ] 🔲 `selector_healer.py`：失败时抓取 DOM 片段→GPT 生成新 CSS/XPath
* [ ] 🔲 Telegram Bot：`notify(message, screenshot_path)`
* [ ] 🔲 GitHub Actions：每日跑 `jobbot test --site greenhouse`
* [ ] 🔲 生成周报 Markdown，自动附到 Notion 页面

---

## 6. 技术栈与依赖版本

| 组件         | 版本锁定     | 说明                               |
| ---------- | -------- | -------------------------------- |
| Python     | 3.11 LTS | 统一解释器                            |
| OpenAI SDK | 1.x      | GPT-4o / GPT-4o-mini             |
| Jinja2     | 3.x      | LaTeX 模板渲染                       |
| Notion SDK | 0.14+    | 官方客户端                            |
| Typer      | 0.12     | CLI                              |
| pytest     | 8.x      | 测试                               |
| pre-commit | latest   | 黑名单 / isort / flake8             |

---

## 7. 风险与缓解

| 风险                 | 可能后果            | 缓解措施                                                                   |
| ------------------ | --------------- | ---------------------------------------------------------------------- |
| 表单 DOM 大改版         | Selector 全面失效   | 实施三层 selector 盾；CI 每日跑冒烟脚本                                             |
| CAPTCHA / 文件检查     | 无法全自动提交         | 脚本停在 Submit 前；人工介入                                                     |
| GPT 产出不稳定          | Bullet 超行数 / 乱码 | 加规则后检验 + 重试；必要时手动编辑                                                    |
| LaTeX 字体嵌入 >500 KB | PDF 上传被拒        | 使用 `xelatex -interaction=batchmode -output-driver="xdvipdfmx -z 9"` 压缩 |

---

## 8. 下一步行动

1. **今天内**：完成 Phase 0，验证 JD 拉取 & CLI scaffold。
2. **本周**：推进 Phase 1，产出第一版定制 PDF 并贴到 Notion。
3. 有任意 blockers，直接在 Issue 里 @我。

> **备注**：如需修改架构或时间线，请先开 Discussion 说明理由，确保下游 LLM 和工程流保持同步。
