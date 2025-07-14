# Resume Builder Module

基于职位描述（JD）智能优化简历的模块，使用 OpenAI API 和 LaTeX 排版。

## 功能特性

- 🤖 **AI 驱动的优化**：使用 GPT-4o-mini 模型分析 JD 并优化简历内容
- 🎯 **关键词匹配**：自动识别 JD 中的技能要求并突出相关经验
- 📊 **相关度评分**：计算简历与职位的匹配度（0-1 分）
- 📝 **LaTeX 专业排版**：生成格式优美的 PDF 简历
- 📈 **优化报告**：生成详细的优化分析报告

## 使用方法

### 1. 一键自动化（推荐）

从 Notion 自动获取 TODO 状态的 JD 并生成优化简历：
```bash
# 处理一个 TODO 工作
python -m resume_builder.cli build-from-notion

# 批量处理多个 TODO 工作
python -m resume_builder.cli build-from-notion --limit 3

# 指定输出目录
python -m resume_builder.cli build-from-notion --output-dir ./resumes

# 使用自定义简历数据
python -m resume_builder.cli build-from-notion --resume my_resume.json
```

### 2. 针对特定 JD 优化

首先解析目标职位的 JD：
```bash
# 从 Notion 拉取并解析 JD
jobbot ingest pull <page_id> --save
```

然后生成优化简历：
```bash
# 使用默认简历数据生成优化简历
python -m resume_builder.cli build <page_id>

# 使用自定义简历数据
python -m resume_builder.cli build <page_id> --resume data/example_resume.json

# 指定输出文件名
python -m resume_builder.cli build <page_id> --output my_optimized_resume.pdf

# 保存中间的 LaTeX 文件（可选）
python -m resume_builder.cli build <page_id> --save-tex
```

### 3. 预览优化建议

在生成 PDF 之前预览优化分析：
```bash
python -m resume_builder.cli preview <page_id>
```

### 4. 高级选项

```bash
# 处理不同状态的工作
python -m resume_builder.cli build-from-notion --status Processing

# 不保存优化报告
python -m resume_builder.cli build-from-notion --no-report

# 保存 LaTeX 源文件
python -m resume_builder.cli build-from-notion --save-tex
```

## 数据格式

### 简历数据 JSON 格式

```json
{
  "name": "Your Name",
  "email": "email@example.com",
  "phone": "123-456-7890",
  "github": "github.com/username",
  "website": "yourwebsite.com",
  "education": [
    {
      "school": "University Name",
      "degree": "Master of Science",
      "field": "Computer Science",
      "location": "City, State",
      "start_date": "Aug 2022",
      "end_date": "May 2024",
      "highlights": ["GPA: 4.0/4.0", "Dean's List"]
    }
  ],
  "experience": [
    {
      "company": "Company Name",
      "title": "Software Engineer",
      "location": "City, State",
      "start_date": "Jun 2023",
      "end_date": "Present",
      "description": "Brief description",
      "bullets": [
        "Achieved X by implementing Y resulting in Z impact",
        "Led development of feature using React and Python"
      ],
      "technologies": ["Python", "React", "AWS"]
    }
  ],
  "projects": [
    {
      "name": "Project Name",
      "bullets": [
        "Built full-stack application using Node.js and MongoDB",
        "Implemented real-time features using WebSocket"
      ],
      "technologies": ["Node.js", "MongoDB", "WebSocket"]
    }
  ],
  "skills": {
    "Programming": ["Python", "JavaScript", "Go"],
    "Frameworks": ["React", "Django", "Express.js"],
    "DevOps": ["Docker", "Kubernetes", "AWS"]
  },
  "footnote": "Additional information"
}
```

## 优化策略

1. **技能匹配**：扫描 JD 中的技能要求，在简历中突出相关技能
2. **经验重排**：根据相关度重新排序工作经验和项目
3. **关键词优化**：在经验描述中自然融入 JD 关键词
4. **量化成果**：强调带有数字的成就（如性能提升、规模等）
5. **动词优化**：使用强有力的动作动词开始每个要点

## 配置要求

### 环境变量

在 `.env` 文件中设置：
```bash
OPENAI_API_KEY=your_openai_api_key
```

### LaTeX 环境

需要安装完整的 TeX 发行版：
- macOS: `brew install --cask mactex`
- Ubuntu: `sudo apt-get install texlive-full`
- Windows: 下载并安装 [MiKTeX](https://miktex.org/)

## 技术架构

```
resume_builder/
├── models/              # 数据模型（Pydantic）
├── services/            # 核心服务
│   ├── resume_optimizer.py    # LLM 优化逻辑
│   └── latex_renderer.py      # LaTeX 渲染
├── templates/           # Jinja2 模板
│   ├── base_resume.tex.j2     # 简历模板
│   └── resume.cls             # LaTeX 样式类
├── utils/               # 工具函数
│   └── latex_compiler.py      # PDF 编译
└── cli.py              # CLI 命令
```

## 示例输出

### 优化报告示例

```json
{
  "job": {
    "company": "OpenAI",
    "title": "Software Engineer",
    "page_id": "abc123"
  },
  "optimization": {
    "relevance_score": 0.85,
    "keyword_matches": {
      "python": 5,
      "machine learning": 3,
      "api": 4
    },
    "suggestions": [
      "Consider highlighting any experience with Docker",
      "Add quantifiable metrics to more experience bullets"
    ],
    "report": {
      "matched_skills": ["python", "api", "fastapi"],
      "missing_skills": ["kubernetes", "terraform"],
      "optimizations_applied": [...]
    }
  }
}
```

## 常见问题

### Q: LaTeX 编译失败
A: 确保安装了完整的 TeX 发行版，并且 `latexmk` 命令可用。

### Q: 如何自定义简历模板？
A: 修改 `templates/base_resume.tex.j2` 文件，使用 Jinja2 语法。

### Q: API 调用费用如何？
A: 使用 GPT-4o-mini 模型，每次优化约消耗 500-1000 tokens，成本约 $0.001-0.002。

## 最新更新

### v2.0 - 自动化增强
- ✅ **一键自动化**：`build-from-notion` 命令自动获取 TODO JD 并优化简历
- ✅ **智能清理**：默认只保留 PDF 和分析报告，自动清理临时文件
- ✅ **批量处理**：支持同时处理多个 Notion 中的 TODO 工作
- ✅ **错误处理**：自动更新 Notion 状态，记录错误信息
- ✅ **状态追踪**：Processing → Parsed 状态自动更新

## 后续计划

- [ ] 支持多种简历模板
- [ ] 添加 A/B 测试功能
- [ ] 集成更多 AI 模型
- [ ] 支持简历版本管理
- [ ] 添加简历评分功能
- [ ] 增强技能提取算法
- [ ] 支持更多招聘网站解析器
