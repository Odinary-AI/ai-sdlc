<!-- guide-meta
{
  "date": "2026-10-09",
  "version": "1.5.3-dev.0",
  "identity": "发布适配源 SHA256 84a70924e32d848949804d388c72ef1f9d12d586d1fe5d7193dce39c77c6a395",
  "scope": "ai-sdlc项目概览参考快照；保留概览与三图，开发任务、实时状态及私有证据不随包。图来源改用包内同概念的规则或实现，不表示本机安装或远端发布已完成。现行规则以包内原文为准。",
  "title": "ai-sdlc · 项目概览与工程全景",
  "sources": [
    "SKILL.md",
    "references/lifecycle.md",
    "references/verification.md",
    "references/maintenance.md",
    "references/cli.md"
  ]
}
-->

# ai-sdlc工程导览

## 目标与边界｜谁使用、解决什么问题 {#purpose}

```html
<p>ai-sdlc为个人开发者和一人公司（OPC）提供AI工程机制，帮助AI跨会话持续推进项目：保留上下文和进度、让局部工作对应整体目标、依据真实结果判断交付，并维持授权与执行边界。</p><p>重点服务一万行以上、持续迭代的项目；这是目标场景，不是规模保证或接入门槛。它提供流程、模板与本机工具，开发方法由AI在项目约束内选择。</p><div class="note">这份工程全景帮助读者理解、接手和找到下一步。无人后台开发、自动合入发布、多用户调度、主观质量自动判定不在现行承诺内。</div><p class="source"><a href="../../SKILL.md">能力与适用边界</a> · <a href="../../SKILL.md">Skill使用入口</a></p>
```

## 核心能力｜能完成的工作与状态边界 {#capabilities}

```html
<div class="pairs"><div><h3>接入、实施与恢复</h3><p>保留项目已有组织，映射真实规则和检查；按原任务及现场恢复，未知操作不盲目重放。</p></div><div><h3>验证、交付与治理</h3><p>运行选定检查、保存真实结果，核对相关输入与当前证据；按风险检查、修复及回顾。</p></div><div><h3>通用工程导览</h3><p>方法与模板随Skill分发；可选标准库工具支持同源HTML、节点、上下游及明确来源核对。文档模式或已有文档站可继续使用。</p></div><div><h3>实际状态分开判断</h3><p>已实现、已验证、任务完成、已安装、已推送和会话已加载不是同一件事。每项结论回查其对应对象与证据。</p></div></div><p class="source"><a href="../../SKILL.md">能力路由</a> · <a href="../../references/cli.md">工具接口与限制</a></p>
```

## 主流程｜从用户结果到工程交付 {#workflow}

```html
<ol><li>用户说明目标、范围与授权；需要Skill时显式调用。</li><li>开发AI读取项目依据、工作区和任务，确定验收及必要检查。</li><li>实施并验证，保存真实结果和剩余未知。</li><li>核对覆盖、差异和有效证据；需要人的决定/验收交给对应负责人。</li><li>按已获授权完成提交、安装或发布等动作，分别回读实际对象。</li></ol>
```
```engineering-map
{
  "kind": "collaboration",
  "title": "使用与协作：目标、执行、验证和反馈",
  "nodes": [
    {
      "id": "owner",
      "label": "项目负责人",
      "description": "确定目标、范围、授权及需要人的决定和验收。",
      "basis": "observed",
      "sources": [
        {
          "path": "SKILL.md"
        }
      ],
      "position": {
        "column": 0,
        "row": 0
      },
      "role": "actor",
      "summary": "目标、授权与人的决定"
    },
    {
      "id": "rules",
      "label": "Skill与已采纳规则",
      "description": "Skill仅显式调用；已采纳项目规则持续有效。",
      "basis": "observed",
      "sources": [
        {
          "path": "references/lifecycle.md"
        }
      ],
      "position": {
        "column": 2,
        "row": 0
      },
      "role": "rule",
      "summary": "显式Skill / 已采纳规则"
    },
    {
      "id": "agent",
      "label": "开发AI",
      "description": "核对现场，实施和选择检查；审阅证据并接续授权工作。",
      "basis": "observed",
      "sources": [
        {
          "path": "references/lifecycle.md"
        }
      ],
      "position": {
        "column": 1,
        "row": 1
      },
      "role": "core",
      "summary": "实施、选择检查与审阅"
    },
    {
      "id": "project",
      "label": "项目记录与当前依据",
      "description": "需求/设计、任务/status和验证来源各有唯一职责。",
      "basis": "observed",
      "sources": [
        {
          "path": "references/cli.md"
        }
      ],
      "position": {
        "column": 0,
        "row": 2
      },
      "role": "data",
      "summary": "任务、设计与现行依据"
    },
    {
      "id": "checks",
      "label": "项目检查与执行器",
      "description": "文档模式复用项目命令；脚本模式执行指定检查、保存RUN。",
      "basis": "observed",
      "sources": [
        {
          "path": "scripts/harness.py"
        }
      ],
      "position": {
        "column": 2,
        "row": 2
      },
      "role": "helper",
      "summary": "真实命令、日志与RUN"
    },
    {
      "id": "review",
      "label": "交付审阅与人的验收",
      "description": "执行结果、证据有效、验收满足及人的确认分别判断。",
      "basis": "observed",
      "sources": [
        {
          "path": "references/verification.md"
        }
      ],
      "position": {
        "column": 1,
        "row": 3
      },
      "role": "result",
      "summary": "证据、覆盖与验收分别判断"
    }
  ],
  "edges": [
    {
      "from": "owner",
      "to": "agent",
      "label": "目标、授权和人的决定",
      "basis": "observed",
      "short_label": "目标与授权",
      "category": "primary"
    },
    {
      "from": "rules",
      "to": "agent",
      "label": "方法与项目约束",
      "basis": "observed",
      "short_label": "工程约束",
      "category": "primary"
    },
    {
      "from": "agent",
      "to": "project",
      "label": "维护范围内事实与任务",
      "basis": "observed",
      "short_label": "维护事实",
      "category": "primary"
    },
    {
      "from": "agent",
      "to": "checks",
      "label": "实施后执行适用检查",
      "basis": "observed",
      "short_label": "实际执行",
      "category": "primary"
    },
    {
      "from": "checks",
      "to": "review",
      "label": "真实记录和结果",
      "basis": "observed",
      "short_label": "真实结果",
      "category": "primary"
    },
    {
      "from": "project",
      "to": "review",
      "label": "范围、验收及相关依据",
      "basis": "observed",
      "short_label": "范围与依据",
      "category": "primary"
    },
    {
      "from": "review",
      "to": "owner",
      "label": "结果、剩余事项和待人确认",
      "basis": "observed",
      "short_label": "结果 / 待人确认",
      "category": "feedback"
    }
  ]
}
```
```html
<p class="muted">下面只切换讲解，不运行命令。</p><div class="buttons" role="group" aria-label="选择任务情景"><button type="button" aria-pressed="true" aria-controls="scene-ready" data-target="scene-ready">条件齐备</button><button type="button" aria-pressed="false" aria-controls="scene-failed" data-target="scene-failed">检查失败</button><button type="button" aria-pressed="false" aria-controls="scene-changed" data-target="scene-changed">输入变化</button><button type="button" aria-pressed="false" aria-controls="scene-resume" data-target="scene-resume">中断恢复</button></div><div><div id="scene-ready" class="panel" data-panel><h3>条件齐备</h3><p>执行通过仍需核对实际覆盖、有效证据、文档和必需人的确认。</p></div><div id="scene-failed" class="panel" data-panel><h3>检查失败</h3><p>保留失败，在授权范围定位和修复；不换更弱检查取得通过。</p></div><div id="scene-changed" class="panel" data-panel><h3>输入变化</h3><p>相关输入变化只重核受影响证据；无关新增不自动失效。</p></div><div id="scene-resume" class="panel" data-panel><h3>中断恢复</h3><p>先核对原任务、在途操作及副作用，再接续；不自动重放。</p></div></div>
```

## 架构与协作｜结构、接口、数据与关键路径 {#structure}

```html
<p>能力包与消费项目数据分开：方法和工具在Skill内；目标、配置、任务、日志及验收证据在项目中。文档模式不要求机器数据块；脚本模式使用唯一任务块、真实RUN及派生status。</p>
```
```engineering-map
{
  "kind": "architecture",
  "title": "内部结构：实际脚本、规则、模板与消费项目数据",
  "nodes": [
    {
      "id": "entry",
      "label": "Skill入口与方法规则",
      "description": "通用方法及正文路由；不是后台调度器。",
      "basis": "observed",
      "sources": [
        {
          "path": "SKILL.md"
        }
      ],
      "position": {
        "column": 0,
        "row": 0
      },
      "role": "rule",
      "summary": "方法路由与工程约束"
    },
    {
      "id": "templates",
      "label": "assets职责模板",
      "description": "core、optional和records按实际职责复用；不会自动创建所有可选文档。",
      "basis": "observed",
      "sources": [
        {
          "path": "references/templates.md"
        }
      ],
      "position": {
        "column": 1,
        "row": 0
      },
      "role": "template",
      "summary": "按实际职责选择与复用"
    },
    {
      "id": "harness",
      "label": "harness核心执行器",
      "description": "adopt/doctor/任务更新、verify、共同assess、resume/close及run-after。",
      "basis": "observed",
      "sources": [
        {
          "path": "scripts/harness.py"
        }
      ],
      "position": {
        "column": 1,
        "row": 1
      },
      "role": "core",
      "summary": "接入、执行与当前证据判定"
    },
    {
      "id": "scan",
      "label": "scan_coverage",
      "description": "读取现行专项ID并核对覆盖结构，调查真实完成仍由语义审阅判断。",
      "basis": "observed",
      "sources": [
        {
          "path": "scripts/scan_coverage.py"
        }
      ],
      "position": {
        "column": 0,
        "row": 1
      },
      "role": "helper",
      "summary": "专项ID与覆盖结构"
    },
    {
      "id": "projectdata",
      "label": "消费项目配置、任务与RUN",
      "description": "在消费项目保存；状态摘要派生，不作为包内数据。",
      "basis": "observed",
      "sources": [
        {
          "path": "references/cli.md"
        }
      ],
      "position": {
        "column": 1,
        "row": 3
      },
      "role": "data",
      "summary": "配置、任务、RUN及状态摘要"
    },
    {
      "id": "stop",
      "label": "可选codex_stop",
      "description": "显式平台绑定；复用共同判定并提示有界补救，不执行项目测试。",
      "basis": "observed",
      "sources": [
        {
          "path": "scripts/codex_stop.py"
        }
      ],
      "position": {
        "column": 2,
        "row": 1
      },
      "role": "optional",
      "summary": "显式平台绑定 / 有界补救"
    },
    {
      "id": "helpers",
      "label": "自检与计数适配",
      "description": "self_test通过子进程核对共同边界；unittest_report输出真实计数。",
      "basis": "observed",
      "sources": [
        {
          "path": "scripts/self_test.py"
        },
        {
          "path": "scripts/unittest_report.py"
        }
      ],
      "position": {
        "column": 2,
        "row": 0
      },
      "role": "helper",
      "summary": "self_test / unittest_report"
    },
    {
      "id": "snapshot",
      "label": "可选Git输入快照",
      "description": "读取Git对象与内容身份，不运行检查、不自动参加close。",
      "basis": "observed",
      "sources": [
        {
          "path": "scripts/evidence_snapshot.py"
        }
      ],
      "position": {
        "column": 0,
        "row": 2
      },
      "role": "optional",
      "summary": "工作树、暂存、固定提交"
    },
    {
      "id": "guide",
      "label": "可选工程导览工具",
      "description": "读取Markdown/明确关系来源，生成离线HTML或只读查询；不发现全部依赖或判定工程验收。",
      "basis": "observed",
      "sources": [
        {
          "path": "scripts/project_guide.py"
        }
      ],
      "position": {
        "column": 2,
        "row": 2
      },
      "role": "optional",
      "summary": "同源展示 / 只读关系查询"
    }
  ],
  "edges": [
    {
      "from": "entry",
      "to": "templates",
      "label": "按职责选择模板",
      "basis": "observed",
      "short_label": "选模板",
      "category": "primary"
    },
    {
      "from": "templates",
      "to": "harness",
      "label": "core用于缺失文件接入",
      "basis": "observed",
      "short_label": "core模板",
      "category": "primary"
    },
    {
      "from": "harness",
      "to": "scan",
      "label": "加载覆盖校验",
      "basis": "observed",
      "short_label": "加载",
      "category": "primary"
    },
    {
      "from": "harness",
      "to": "projectdata",
      "label": "读写配置、任务、RUN及派生摘要",
      "basis": "observed",
      "short_label": "读写项目数据",
      "category": "primary"
    },
    {
      "from": "scan",
      "to": "entry",
      "label": "读取专项正文与ID",
      "basis": "observed",
      "short_label": "读取专项ID",
      "category": "reference"
    },
    {
      "from": "stop",
      "to": "harness",
      "label": "调用同一判定",
      "basis": "observed",
      "short_label": "调用",
      "category": "optional"
    },
    {
      "from": "helpers",
      "to": "harness",
      "label": "通过实际入口自检",
      "basis": "observed",
      "short_label": "实际入口自检",
      "category": "primary"
    },
    {
      "from": "guide",
      "to": "projectdata",
      "label": "只读明确映射的来源；不改任务",
      "basis": "observed",
      "short_label": "明确来源",
      "category": "reference"
    },
    {
      "from": "snapshot",
      "to": "projectdata",
      "label": "可选输入身份材料；不自动互认",
      "basis": "observed",
      "short_label": "输入身份",
      "category": "reference"
    }
  ],
  "groups": [
    {
      "id": "skill",
      "label": "Skill能力包 · 方法、执行器及可选工具",
      "members": [
        "entry",
        "templates",
        "harness",
        "scan",
        "stop",
        "helpers",
        "snapshot",
        "guide"
      ]
    },
    {
      "id": "consumer",
      "label": "消费项目 · 事实与执行证据",
      "members": [
        "projectdata"
      ]
    }
  ]
}
```
```engineering-map
{
  "kind": "workflow",
  "title": "关键执行路径：从实际检查到有效交付",
  "nodes": [
    {
      "id": "scope",
      "label": "目标与验收范围",
      "description": "任务中的目标、授权和验收映射决定本次需要什么证据。",
      "basis": "observed",
      "sources": [
        {
          "path": "references/cli.md"
        }
      ],
      "position": {
        "column": 0,
        "row": 0
      },
      "role": "rule",
      "summary": "目标、授权、验收与相关输入"
    },
    {
      "id": "run",
      "label": "verify真实执行",
      "description": "读取相关输入，执行命令并保留退出、日志、计数、环境和身份。",
      "basis": "observed",
      "sources": [
        {
          "path": "scripts/harness.py"
        }
      ],
      "position": {
        "column": 1,
        "row": 0
      },
      "role": "core",
      "summary": "真实命令及完整执行记录"
    },
    {
      "id": "valid",
      "label": "assess核对当前依据",
      "description": "最近结果、指纹、日志/报告完整性及必需义务参与共同判定。",
      "basis": "observed",
      "sources": [
        {
          "path": "scripts/harness.py"
        }
      ],
      "position": {
        "column": 2,
        "row": 0
      },
      "role": "core",
      "summary": "最近结果、输入和必要义务"
    },
    {
      "id": "close",
      "label": "close与语义审阅",
      "description": "机械条件成立后核对实际差异/覆盖/文档/人的确认，不能自签主观接受。",
      "basis": "observed",
      "sources": [
        {
          "path": "references/verification.md"
        }
      ],
      "position": {
        "column": 2,
        "row": 1
      },
      "role": "result",
      "summary": "实际差异与语义 / 人的确认"
    },
    {
      "id": "recovery",
      "label": "失败或未知时恢复",
      "description": "保留失败；相关变化只重验受影响部分；未知副作用先核对现场。",
      "basis": "observed",
      "sources": [
        {
          "path": "references/lifecycle.md"
        }
      ],
      "position": {
        "column": 0,
        "row": 1
      },
      "role": "process",
      "summary": "定位缺口 / 核对未知操作"
    },
    {
      "id": "delivery",
      "label": "固定源、安装与远端",
      "description": "固定交付范围；安装、发布授权与实际对象核对分别记录，示例不证明这些动作已完成。",
      "basis": "observed",
      "sources": [
        {
          "path": "references/lifecycle.md"
        }
      ],
      "position": {
        "column": 2,
        "row": 2
      },
      "role": "result",
      "summary": "固定包、备份、副本、远端"
    }
  ],
  "edges": [
    {
      "from": "scope",
      "to": "run",
      "label": "确定检查与相关输入",
      "basis": "observed",
      "short_label": "检查",
      "category": "primary"
    },
    {
      "from": "run",
      "to": "valid",
      "label": "实际执行记录",
      "basis": "observed",
      "short_label": "记录",
      "category": "primary"
    },
    {
      "from": "valid",
      "to": "close",
      "label": "当前机械条件支持范围内审阅",
      "basis": "observed",
      "short_label": "条件支持审阅",
      "category": "primary"
    },
    {
      "from": "valid",
      "to": "recovery",
      "label": "失败、失效或结局未知",
      "basis": "observed",
      "short_label": "失败 / 失效 / 未知",
      "category": "conditional"
    },
    {
      "from": "recovery",
      "to": "run",
      "label": "前置恢复后仅重验受影响检查",
      "basis": "observed",
      "short_label": "受影响复验",
      "category": "feedback"
    },
    {
      "from": "close",
      "to": "delivery",
      "label": "已有交付授权及实际对象核对",
      "basis": "observed",
      "short_label": "授权内交付",
      "category": "primary"
    }
  ]
}
```
```html
<p>项目写入限制在根目录内，短事务使用文件锁与原子替换；执行检查时释放锁。超时/中断处理进程组，不能确认清理或副作用时保留未知。恢复摘要不重复执行原动作。Stop适配是可选平台能力，不能宣称不可绕过。</p><p class="source"><a href="../../references/cli.md">接口与存储契约</a> · <a href="../../references/cli.md">实际存储和命令契约</a> · <a href="../../references/codex-hooks.md">平台适配</a></p>
```

## 关键取舍｜为什么采用这些结构 {#choices}

```html
<details open><summary>开发AI主导执行，机制提供工程依据</summary><p>用户决定目标与授权；开发AI选择实施方式；工具保存事实、执行选定检查并核对可机械判断的条件。</p></details><details><summary>项目事实唯一，导览派生</summary><p>需求、设计、任务、状态和验证各有维护位置。导览只摘要回查；图定义、说明和正文同源，不建立第二套任务状态。</p></details><details><summary>按影响验证并复用仍有效证据</summary><p>先界定真实输入与消费者，相关变化重验；测试计数、版本号或节点标记不能代替当前覆盖与身份。</p></details><details><summary>通用功能按需组合</summary><p>导览工具可独立使用，不加入close、不调用模型或联网、不强制新运行平台。参考外部功能设计，保留本机制的最小充分边界。</p></details><p class="source"><a href="../../references/cli.md">接口与存储契约</a> · <a href="../../references/maintenance.md">维护与裁剪</a></p>
```

## 工程态势｜参考快照与后续使用 {#engineering}

```html
<p>本包包含工程导览方法、模板、生成与检查工具，以及这份项目阅读示例。开发仓库的任务、安装回执、测试日志、实时计划和待办不随包；不能从此示例推断最新进度、验证或发布状态。</p><p>后续改进由真实使用反馈和明确授权触发。跨项目净收益、长期效率及普遍AI遵从尚未证明。</p><p class="source"><a href="../../references/maintenance.md">维护与回顾规则</a> · <a href="../../references/verification.md">验证与交付边界</a></p>
```

## 当前限制｜运行、验证与未完成边界 {#limits}

```html
<p>核心运行需要Python3.10+，声明平台macOS/Linux；新导览工具只使用标准库，生成离线HTML，明确输入变化后可只读核对漂移。普通来源链接不自动成为相关输入，实际使用时仍需对照阅读/生成关系补齐映射。</p><p>图的来源路径/行号及内容身份可机械核对，但关系含义、运行影响、项目验收和人的理解仍分别判断。上游/下游只沿本图已列关系；没有自动全语言知识图谱、实时看板、后台同步或云服务。</p><p>安装、推送与客户端加载分别记录，不宣称会话自动重载。工程检查和代表消费样例只支持其范围；其他平台、任意规模和长期理解收益仍未认证。</p><p class="source"><a href="../../references/verification.md">验证规则与证据边界</a> · <a href="../../references/cli.md">运行接口与环境</a></p><footer>独立离线导览 · 正文及图定义来自本Markdown源 · 快照身份与最新状态分别阅读。</footer>
```
