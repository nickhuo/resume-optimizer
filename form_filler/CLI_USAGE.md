# Form Filler CLI 使用指南

Form Filler CLI是一个用于分析和提取网页表单信息的命令行工具。

## 基本使用方法

```bash
python -m form_filler.cli [命令] [选项] [参数]
```

## 可用命令

### 1. `extract-forms` - 提取表单信息

**最常用的命令**，用于分析网页上的表单结构和字段信息。

#### 语法
```bash
python -m form_filler.cli extract-forms [选项] URL
```

#### 选项
- `--debug` - 显示详细的调试信息
- `--timeout INTEGER` - 页面加载超时时间（毫秒），默认60秒

#### 使用示例

1. **基础使用**
```bash
python -m form_filler.cli extract-forms "https://example.com/jobs/apply"
```

2. **开启调试模式**
```bash
python -m form_filler.cli extract-forms "https://example.com/jobs/apply" --debug
```

3. **设置更长超时时间**
```bash
python -m form_filler.cli extract-forms "https://slow-site.com/apply" --timeout 120000
```

#### 输出信息
- 表单数量和基本信息
- 每个字段的详细信息：
  - 标签/名称
  - 字段类型（text, email, select等）
  - 必填/选填状态
  - 选择器信息
- 验证码检测

---

### 2. `analyze` - 分析页面类型和CTA按钮

分析页面类型并识别Apply按钮。**需要设置OpenAI API Key**。

#### 语法
```bash
python -m form_filler.cli analyze [选项] URL
```

#### 选项
- `--screenshot` - 保存页面截图
- `--timeout INTEGER` - 页面加载超时时间（毫秒），默认60秒

#### 使用示例

1. **基础分析**
```bash
export OPENAI_API_KEY="your-api-key-here"
python -m form_filler.cli analyze "https://careers.company.com/jobs/123"
```

2. **保存截图**
```bash
python -m form_filler.cli analyze "https://careers.company.com/jobs/123" --screenshot
```

#### 输出信息
- 页面类型（job_detail, form_page, login_page等）
- 置信度评分
- LLM推理过程
- CTA按钮候选列表
- 操作建议

---

### 3. `interactive` - 交互式测试模式

进入交互式模式，可以连续测试多个URL。

#### 语法
```bash
python -m form_filler.cli interactive [选项]
```

#### 选项
- `--headless` / `--no-headless` - 是否使用无头模式（默认开启）

#### 使用示例

1. **无头模式**（推荐）
```bash
python -m form_filler.cli interactive
```

2. **显示浏览器窗口**
```bash
python -m form_filler.cli interactive --no-headless
```

#### 交互流程
1. 输入URL进行分析
2. 查看分析结果
3. 选择是否查看详细信息
4. 选择是否保存截图
5. 输入`quit`退出

---

### 4. `stats` - 错误统计信息

显示系统运行过程中的错误统计。

#### 语法
```bash
python -m form_filler.cli stats
```

#### 输出信息
- 总错误数
- 错误文件位置
- 错误类型分布

---

## 实用技巧

### 1. 处理慢速网站
```bash
# 增加超时时间到2分钟
python -m form_filler.cli extract-forms "https://slow-site.com" --timeout 120000
```

### 2. 调试表单识别问题
```bash
# 开启调试模式查看详细信息
python -m form_filler.cli extract-forms "https://example.com/form" --debug
```

### 3. 批量测试多个URL
```bash
# 使用交互模式
python -m form_filler.cli interactive
```

### 4. 保存分析结果
```bash
# 重定向输出到文件
python -m form_filler.cli extract-forms "https://example.com" > form_analysis.txt
```

## 常见问题

### Q: 页面加载超时怎么办？
A: 使用`--timeout`参数增加超时时间，或者网络问题导致的超时会自动降级到更快的加载策略。

### Q: 为什么有些网站提取不到表单？
A: 可能原因：
- 表单是动态生成的
- 需要登录才能看到表单
- 使用了复杂的JavaScript框架

### Q: 如何处理验证码？
A: 系统会自动检测验证码并给出警告，需要人工处理。

### Q: analyze命令报错？
A: 确保已设置OpenAI API Key：
```bash
export OPENAI_API_KEY="your-api-key-here"
```

## 示例工作流

### 场景1：分析新的求职网站
```bash
# 1. 先提取表单信息
python -m form_filler.cli extract-forms "https://newsite.com/apply"

# 2. 如果有API Key，分析页面类型
python -m form_filler.cli analyze "https://newsite.com/jobs/123" --screenshot

# 3. 检查是否有错误
python -m form_filler.cli stats
```

### 场景2：调试表单识别问题
```bash
# 开启调试模式，设置更长超时
python -m form_filler.cli extract-forms "https://problematic-site.com" --debug --timeout 90000
```

### 场景3：批量测试多个网站
```bash
# 使用交互模式
python -m form_filler.cli interactive --no-headless
```

---

## 进阶用法

### 环境变量设置
```bash
# OpenAI API Key（用于页面分析）
export OPENAI_API_KEY="your-api-key"

# 设置日志级别
export LOG_LEVEL="DEBUG"
```

### 与其他工具集成
```bash
# 结合shell脚本批量处理
cat urls.txt | while read url; do
    python -m form_filler.cli extract-forms "$url" --debug > "output_$(basename $url).txt"
done
```

---

需要更多帮助？查看各命令的详细帮助：
```bash
python -m form_filler.cli [command] --help
```
