# Form Filler - 智能表单填充工具

这是一个基于 AI 的智能表单填充工具，专门用于自动化求职申请流程。

## 功能特点

- 🤖 使用 GPT-4 智能识别和分析页面
- 📝 自动提取并填充表单字段
- 🎯 智能匹配个人信息到对应字段
- 📸 自动截图记录每个步骤
- 📊 与 Notion 数据库集成跟踪申请状态
- 🔄 支持多步骤工作流（点击按钮、填写表单等）

## 快速开始

### 1. 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

### 2. 配置环境变量

复制 `.env.example` 到 `.env` 并填写必要的配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，至少需要设置：
- `OPENAI_API_KEY`: OpenAI API 密钥（必需）

### 3. 准备个人信息

编辑 `config/personal_info.yaml` 文件，填写你的个人信息：

```yaml
basic_info:
  first_name: "你的名字"
  last_name: "你的姓氏"
  email: "your-email@example.com"
  phone: "+1 (xxx) xxx-xxxx"
# ... 更多信息
```

### 4. 运行表单填充

#### 方式一：使用示例脚本（推荐）

```bash
python run_form_filler.py
```

#### 方式二：使用 CLI 工具

```bash
# 分析页面类型
python -m form_filler.cli analyze https://example.com/job-application

# 提取表单信息
python -m form_filler.cli extract-forms https://example.com/job-application

# 交互式测试
python -m form_filler.cli interactive
```

#### 方式三：在代码中使用

```python
import asyncio
from form_filler.workflow_manager import WorkflowManager

async def fill_job_application():
    config = {
        'openai_api_key': 'your-api-key',
        'log_dir': 'logs',
        'screenshot_dir': 'screenshots'
    }
    
    workflow = WorkflowManager(config)
    
    result = await workflow.process_job_application(
        url="https://example.com/job-application",
        submit=False,  # 先不自动提交，测试填充
        headless=False  # 显示浏览器窗口
    )
    
    print(f"成功: {result['success']}")
    print(f"填充字段: {len(result['filled_fields'])}")

# 运行
asyncio.run(fill_job_application())
```

## 工作流程

1. **页面分析**
   - 访问目标 URL
   - 提取页面内容、按钮、表单
   - 使用 GPT 分析页面类型

2. **智能决策**
   - 判断页面类型（职位详情、表单页、登录页等）
   - 推荐下一步动作（填表、点击申请按钮等）

3. **表单填充**
   - 提取所有表单字段
   - 使用 GPT 智能匹配个人数据
   - 自动填充各个字段

4. **验证和提交**
   - 验证填充结果
   - 可选择自动提交
   - 保存截图和日志

## 数据文件

### 个人信息配置 (`config/personal_info.yaml`)
包含基本信息、教育背景、工作经验等

### 简历数据 (`data/resume.json`)
可选，用于补充更详细的经历信息

## 输出文件

- `logs/`: 会话日志（JSON 格式）
- `screenshots/`: 各步骤截图
- `errors.jsonl`: 错误记录

## 注意事项

1. **测试模式**：建议先设置 `submit=False` 测试填充效果
2. **浏览器模式**：设置 `headless=False` 可以看到实际操作
3. **API 限制**：注意 OpenAI API 的调用限制
4. **隐私安全**：不要将包含个人信息的文件提交到版本控制

## 常见问题

### 1. 页面加载超时
增加超时时间或检查网络连接

### 2. 字段未正确填充
- 检查 `personal_info.yaml` 中的信息是否完整
- 查看日志了解 GPT 的匹配逻辑

### 3. 无法识别表单
某些动态加载的表单可能需要额外等待时间

## 高级用法

### 批量处理

```python
urls = [
    "https://job1.com/apply",
    "https://job2.com/apply",
    # ...
]

for url in urls:
    result = await workflow.process_job_application(url)
    # 处理结果...
```

### 自定义字段映射

可以在 `SmartFormFiller` 中添加自定义规则来处理特殊字段。

### 集成 Notion

设置 Notion 配置后，可以自动更新申请状态到数据库。

## 开发和调试

启用调试日志：
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

查看 GPT 请求和响应：
检查 `logs/` 目录下的会话日志文件。
