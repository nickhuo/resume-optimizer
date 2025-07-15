# 智能表单自动填充系统技术方案

## 1. 系统概述

本系统基于 Playwright 自动化与 GPT-3.5 LLM，实现职位申请表单的自动识别、导航与智能填充。核心目标是提升表单填写效率，降低人工干预频率，并通过异常收集实现自学习优化。

## 2. 技术架构

- **自动化引擎**：Playwright（多浏览器支持）
- **AI 能力**：GPT-3.5-turbo（成本可控）
- **数据格式**：JSON Lines（错误日志采集）
- **配置管理**：YAML（站点定制化）

## 3. 主要功能模块

### 3.1 页面类型判定与 CTA 导航

- **页面判定**：通过 LLM 分析页面标题、主文本、表单数量、URL 关键词，输出页面类型（详情页、表单页、登录页、外部跳转）。
- **CTA 定位与点击**：
  - 收集所有可见按钮/链接文本，LLM 输出排序及置信度。
  - 置信度低于 0.6 视为无可靠 CTA，需人工介入。
  - 依序尝试点击，最多 3 次，每次后重新判定页面类型。

#### CTA 识别优先级
1. 文本含“Apply/开始申请/立即投递”
2. aria-label/data-action 含 apply
3. URL 包含 /apply, /candidate
4. 页面唯一高对比色按钮

### 3.2 多场景跳转处理

- **同页锚点**：监听 URL 变化或 <form> 出现，5 秒超时。
- **新标签页**：捕获新 Page 并切换上下文。
- **iFrame 嵌入**：检测 frame.url，切换至目标 frame。
- **外部 ATS 跳转**：按新域名重新加载配置，需登录时暂停人工。
- **登录/SSO**：判定为 login_page 时通知人工登录，后续重试。

### 3.3 字段解析与自动填充

- 抓取所有 label/aria-label/placeholder/name/role 及邻近 DOM。
- LLM 批量输出字段语义（semantic_key）、控件类型（control_type）、唯一选择器（selector）。
- Playwright 按类型调用对应填充函数，监听 change/blur 校验有效性。
- 异常场景进入 Error Reporter，记录截图与失败样本。

### 3.4 Prompt 模板与 Token 控制

- 设计标准 Prompt，输入页面元素数组，输出字段映射 JSON。
- 单页 Token 控制 ≤ 1k，单次费用 < $0.003。

### 3.5 自学习与优化闭环

- **在线采集**：所有失败 selector+label 记录至 errors.jsonl。
- **人工复核**：定期标注正解，扩充 few-shot 或更新 YAML。
- **模型微调**：样本积累 >1k 时考虑微调 LLM，提升稳定性与降低成本。

## 4. 风险与异常处理

- **Selector 误判**：执行前 locator.count()==1 校验，提交前截图复核。
- **Token 超限**：仅抓取标签文本及最近 5 层 DOM。
- **API 限流**：统一在 gpt_service 层做指数回退与并发控制。
- **验证码**：检测 recaptcha iframe，自动暂停人工。
- **成本控制**：CTA 判定+字段解析单职位 < $0.004。

## 5. 使用说明

- 下游 LLM 直接按本方案实现 cta_navigator.py 与 llm_filler.py，无需重复论证。
- 所有异常场景务必写入 Error Reporter，便于后续自学习与优化。

---

如需进一步细化某一模块或补充代码示例，请告知！