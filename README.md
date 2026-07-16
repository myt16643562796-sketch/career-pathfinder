# Career Pathfinder — AI 岗位选择助手

帮助学生找到适合自己的岗位。覆盖**私企大厂、学术路线（读研读博/高校/研究院）、体制内路线（考公/考编/选调/国企）**三条路径。

## 功能

- **画像采集**：通过 MBTI 式侧面场景问题刻画学生画像（不是直接问"你内向吗"）
- **实时市场数据**：搜索脉脉/小红书/牛客/知乎等平台上的从业者真实分享
- **10 项深度剖析**：JD 人话翻译、真实日常、薪资、坑点预警、35 岁护城河评估
- **个性化后续步骤**：分阶段学习路线 + 基于画像的优势/劣势 + 针对人格弱项的改变方法

## 安装

### Claude Code

```
/plugin marketplace add myt16643562796-sketch/career-pathfinder
/plugin install career-pathfinder@career-pathfinder
```

### OpenSkills（跨平台：Cursor / Windsurf / Codex 等）

```bash
npm i -g openskills
openskills install myt16643562796-sketch/career-pathfinder
```

### 手动安装

```bash
mkdir -p ~/.claude/skills/career-pathfinder
cp skills/career-pathfinder/SKILL.md ~/.claude/skills/career-pathfinder/SKILL.md
```

## 使用

在 Claude Code 对话中提到职业选择相关话题即可自动触发，例如：

- "我是信管专业的学生，帮我看看适合什么岗位"
- "飞书 FDE 这个岗位是干嘛的？"
- "售前和 FDE 选哪个？"
- "我该读博还是去大厂？"
- "考公和进国企哪个更适合我？"

## 适用人群

- 本科/硕士/博士在读学生
- 对职业方向迷茫的应届生
- 在多个 offer 或路径之间纠结的人

## License

MIT
