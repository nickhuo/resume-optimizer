# 使用指南

## 配置个人信息

1. 编辑配置文件 `config/personal_info.yaml`，填写您的真实信息
2. 将您的简历PDF文件放在合适的位置，并在配置文件中填写路径

## 运行脚本

### 基本用法（使用默认配置文件）
```bash
python scripts/fill_rippling_job.py
```

### 指定配置文件
```bash
python scripts/fill_rippling_job.py --config path/to/your/config.yaml
```

### 指定不同的职位URL
```bash
python scripts/fill_rippling_job.py --url "https://ats.rippling.com/..."
```

### 使用无头模式（不显示浏览器）
```bash
python scripts/fill_rippling_job.py --headless
```

### 查看帮助
```bash
python scripts/fill_rippling_job.py --help
```

## 注意事项

1. 脚本会自动识别页面类型：
   - 如果页面没有表单，会查找并点击"Apply"按钮
   - 如果页面有表单，会直接填充表单

2. 脚本会智能跳过不存在的字段，不会因为某个字段不存在而报错

3. 脚本运行后会保存截图：
   - `rippling_filled_form.png` - 填充后的表单截图
   - `rippling_no_form_page.png` - 没有表单的页面截图
   - `error_screenshot.png` - 出错时的截图

4. 脚本目前处于测试模式，找到提交按钮但不会真正提交表单

## 关于GPT集成

当前版本的脚本使用的是硬编码的选择器来填充表单，没有使用GPT进行智能判断。如果需要使用GPT来：
- 智能识别表单字段
- 根据字段标签匹配合适的数据
- 生成更符合职位要求的求职信

可以在后续版本中集成GPT服务。
