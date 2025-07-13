## JD Ingestion 模块——细粒度拆解 & 技术评估

（目标：把 Notion 里的岗位链接拉下来 → 解析 JD → 产出结构化 JSON，供后续模块使用）

---

### 0. 前置假设

| 条目           | 说明                                        |
| ------------ | ----------------------------------------- |
| Notion DB 名称 | **get-ng-offer**                          |
| 关键字段         | `JD_Link`（URL）、`Company`、`Title`、`Status` |
| 运行环境         | Python 3.11，已用 uv 初始化仓库                   |
| 第三方服务        | 仅 OpenAI API（后续模块用），本阶段 **不需要**           |

---

### 1. 任务树（可直接转成 GitHub Issues）

| 层级   | 任务                                                                 | 预估难度 | 产物 / 验收                                                                                                     |
| ---- | ------------------------------------------------------------------ | ---- | ----------------------------------------------------------------------------------------------------------- |
| 1.1  | **配置管理**：新增 `.env` → `NOTION_TOKEN`、`DATABASE_ID`；`settings.py` 读取 | ☆    | 环境变量可被 `python -c "import settings"` 成功打印                                                                   |
| 1.2  | **Notion SDK 封装**                                                  | ★★   | `notion_service.py`<br> • `fetch_jobs(status='TODO') -> list[JobRow]`<br> • `update_job(page_id, **fields)` |
| 1.3  | **链接抓取 CLI**                                                       | ★    | `jobbot list --status TODO` → 列出待解析 JD，ID+URL                                                               |
| 1.4  | **站点检测器**                                                          | ★    | `detect_site(url) -> Enum('GREENHOUSE','WORKDAY','UNKNOWN')`                                                |
| 1.5  | **Greenhouse 解析器**                                                 | ★★☆  | `greenhouse_parser.py`<br> • 输入 URL，输出 `JDModel`（pydantic）                                                  |
| 1.6  | **Workday 解析器**                                                    | ★★★  | `workday_parser.py`（解析 embedded JSON）                                                                       |
| 1.7  | **数据规范化**                                                          | ★    | `normalize(jd: JDModel) -> JDModel`<br> • 字段空值补 `None`，字符串 `.strip()`                                       |
| 1.8  | **本地持久化**                                                          | ☆    | `data/raw/jd_<page_id>.json`                                                                                |
| 1.9  | **错误处理 & 日志**                                                      | ★    | 自定义异常 + `logs/error.log`                                                                                    |
| 1.10 | **单元测试**                                                           | ★    | 2 个真实 JD（各站点）解析字段完整率 ≥ 90 %                                                                                 |
| 1.11 | **CLI 一键执行**                                                       | ★    | `jobbot pull <page_id> --save`<br> • 正常：写文件+Notion.Status='Parsed'<br> • 失败：Status='Error' + error message  |

> ★=易, ★★=中, ★★★=稍复杂

---

### 2. 关键技术细节

| 环节           | 决策                            | 说明                                                                               |
| ------------ | ----------------------------- | -------------------------------------------------------------------------------- |
| HTTP 请求      | `requests` + `timeout=10s`    | 两家站点无反爬限制，先走静态抓取；后期再考虑 Playwright                                                |
| HTML 解析      | `BeautifulSoup`               | Greenhouse 结构简单：`div[class*=content] h1`、`div.location`、`section#content li`     |
| Workday JSON | `json.loads(script_tag.text)` | 查找 `<script type="application/ld+json">` 或 `data-embed="jobinfo"`                |
| 数据模型         | `pydantic.BaseModel JDModel`  | 字段：company, title, location, requirements\:List, nice\_to\_have\:List, raw\_html |
| CLI          | `Typer`                       | 与整体 jobbot 一致                                                                    |
| 日志           | `structlog`                   | 方便未来云端聚合                                                                         |
| 单测           | `pytest + vcr.py`             | 录制 HTTP 响应，离线跑                                                                   |

---

### 3. 可能输出格式（供下游参考）

```json
{
  "company": "OpenAI",
  "title": "Software Engineer, Infrastructure",
  "location": "San Francisco, CA",
  "requirements": [
    "5+ years building distributed systems",
    "Proficiency in Go or Rust"
  ],
  "nice_to_have": [
    "Experience with Kubernetes at scale"
  ],
  "skills": [
    "Experience with Kubernetes at scale"
  ]
}
```

* **文件名**：`data/raw/jd_<notion_page_id>.json`
* **Notion 回写**：可在页面加 `JD_JSON` 属性（URL 指向 GitHub raw）或直接附件上传；后者省事。

---

### 4. 技术风险 & 缓解

| 风险             | 概率 | 影响     | 缓解                                                             |
| -------------- | -- | ------ | -------------------------------------------------------------- |
| Workday 页面布局差异 | 中  | 解析失败   | 用 `try/except` + 日志；先覆盖 80 % 常见模板                              |
| 网速 / CDN 阻断    | 低  | CLI 报错 | `requests` 设置重试 + timeout；失败回写 Notion.Status='Error'           |
| JD 字段缺失/命名千差万别 | 中  | 匹配度降低  | 解析器对常见同义词做 `or` 匹配，如 `qualifications` / `basic_qualifications` |

---

### 5. 下一步行动指南（给“vibe coding”同学）

1. **拉分支**：`feat/jd-ingestion`
2. **实现 1.1\~1.3**：确保能从 Notion 列出待处理行。
3. **优先撸 Greenhouse 解析（1.5）**：10 行 PoC 可见结构。
4. **跑 pytest**：确保 basic parser 通过。
5. **提交 PR**：触发 CI，合入后再攻克 Workday。

若在解析 XPath、正则提取、Notion API Query 上遇到坑，先提 Issue 讨论——保持节奏轻松、迭代快就是 **vibe coding** 的核心。祝开工顺利 🚀
