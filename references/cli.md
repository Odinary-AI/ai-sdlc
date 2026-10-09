# 脚本接口

Python 3.10+，macOS/Linux，标准库。以下 `H` 表示本 Skill 的 `scripts/harness.py` 实际路径；命令中用实际路径替换。本页执行器命令及存储契约约束脚本模式；任务编号约定和独立Git输入快照按各节说明适用于两种模式。模式选择见 [lifecycle.md](lifecycle.md#模式与生效边界)。全局 `--root PROJECT` 放在子命令前。返回码：0 成功或预览，1 检查未满足，2 配置或操作错误（包括已保存任务但摘要待同步的部分成功，见下文）。

| 命令 | 输入与作用 |
|---|---|
| `python3 H --root PROJECT adopt --mapping mapping.json` | 预览，不写文件 |
| `python3 H --root PROJECT adopt --mapping mapping.json --apply` | 创建缺失文件；不覆盖已有文件；输出接入缺口 |
| `python3 H --root PROJECT doctor` | 配置、必要文件、占位符和真实链接检查 |
| `python3 H --root PROJECT begin --spec task.json` | 创建 docs/tasks/任务ID.md 和状态入口摘要 |
| `python3 H --root PROJECT verify TASK-001 unit` | 执行该任务所需的 unit 检查，保存独立 RUN |
| `python3 H --root PROJECT run-after TASK-001 --check unit --action python3 package.py` | 可选：本次指定检查全部有效后执行已授权动作 |
| `python3 H --root PROJECT pause TASK-001 --next '核对在途操作后继续'` | 记录中断与下一动作，不代表停止外部服务 |
| `python3 H --root PROJECT resume TASK-001` | 新进程读取任务、证据、缺口与下一动作；无命令重放 |
| `python3 H --root PROJECT resume TASK-001 --format text` | 中文摘要展示同一任务、证据及下一动作；默认仍为 JSON |
| `python3 H --root PROJECT resume TASK-001 --activate` | 核对现场后恢复为进行中 |
| `python3 H --root PROJECT reconcile-run TASK-001 RUN-ID --outcome stopped --source docs/recovery.md` | 核对现场后追加历史在途 RUN 处置，不改原件或提供通过证据 |
| `python3 H --root PROJECT reconcile-run TASK-001 RUN-ID --damaged --outcome stopped --source docs/recovery.md` | 现场核对后追加损坏回执处置，保留原件；全部当前必需检查须在处置后重验 |
| `python3 H --root PROJECT sync-status TASK-001` | 从指定任务重建状态摘要；不改变任务、执行检查或重放原动作 |
| `python3 H --root PROJECT close TASK-001` | 核对当前交付条件并保存检查结果，不自动标完成 |
| `python3 H --root PROJECT close TASK-001 --format text` | 用中文展示同一验收、检查和证据判定；仍保存交付回执 |
| `python3 H --root PROJECT close TASK-001 --complete --review-source docs/review.md` | 引用真实语义审阅，条件满足时完成，否则阻塞并列缺口 |

## 可选条件衔接

`run-after`是1.4.0起的可选组合入口，不是任务完成判定或统一交付门。`--check ID`可重复，必须非空、不重复且属于当前进行中v2任务的验收范围；未知ID、缺输入或坏配置明确失败，不回退到全部检查或空范围。可选择本次依赖所需的子集，任务close仍核对全部必需验收。检查命令、inputs、rule_sections、optional_tests及判据沿现有配置，不增加统一套件。检查充分性、例外理由和授权真实性由AI/人核对，不能失败后换范围来放行同一义务。

```sh
python3 H --root PROJECT run-after TASK-001 --check unit --check source-format --timeout 60 --action git commit -m '已授权的本地修改'
```

`--action`必须最后出现，其后全部按动作argv传递，cwd为PROJECT，无隐式shell；需要shell时只能显式传入已审阅的shell命令。`--timeout`是动作超时秒数（默认300，大于0且不超过86400）；各检查仍用自身timeout。probe沿可靠退出契约，tests沿已有计数协议，其他报告协议由项目适配器校验并提供可靠退出，普通命令不强制JSON。

每次新执行指定检查，失败、超时、异常、未知或无效报告立即停止。完成后重新读取本次全部RUN并沿assess_check核对回执、日志、报告及输入；后一个检查改变前一个相关输入仍阻止动作，不找旧成功替代。已有未知在途RUN或损坏未处置回执须先沿既有恢复流程核对。无关变化及有效章节裁剪不自动失效。程序只能识别已映射依赖，漏映射的动作脚本、暂存对象或运行环境不会自动被发现；例如git commit前须将实际暂存对象身份纳入项目适用的检查/输入，不能把工作树通过自动称为暂存内容通过。

链条观察保存在`.harness/actions/TASK-ID/ACTION-ID/summary.json`，列调用argv、指定检查的本次RUN、起止时间、是否已启动动作、状态/退出码及原因；动作启动后另有output.log和日志散列。这是执行观察，不是新验收协议或close/Stop通过证据。动作失败返回1，不吞失败；参数/启动前配置错误返回2。普通阻塞返回1，动作成功返回0。中断可能留下checking/running记录，须先核对RUN、动作记录、进程及实际效果，不自动重放，也不通过改写旧记录消除未知；action_started=false但记录running仍不能证明动作未发生（启动与回执写入存在窗口）。动作的超时/进程组清理不撤销已发生的副作用。

检查通过不产生提交、发布、删除或任何新权限；调用者须已获授权。该入口可被直接执行动作绕过，不提供安全隔离、防伪、事务或并发编辑保障。最后指纹核对后仍可能有外部写入；高影响对象应沿项目既有固定提交/快照与并发控制，不把本入口提升为不可绕过门禁。不迁移消费项目模式或强制所有任务采用。

## 扫描覆盖记录

脚本模式的新正式健康扫描在对应TASK正文保留唯一 `harness-scan` JSON块，独立 `schema_version=1`；任务仍使用v2，无需迁移普通或历史任务。完整调查内容可引用附件，不重复覆盖表。格式只记录结果，不规定工具、实现方法和调查顺序。

| 字段 | 内容 |
|---|---|
| scope | 真实检查范围和排除边界 |
| level | full（完整阶段/全项目约定范围）或local（局部专项） |
| claim | scan_complete（调查完成）、healthy（范围内健康通过）、partial（部分结果，任务仍未完成） |
| selection | 以TR/DC/DS/CH/VH/ER/UX/SC为键，每项含applicable布尔值及reason。full必须判断全部八类且前五类适用；local按影响选择并说明理由 |
| items | 以现行条目ID为键，覆盖全部选中适用专项。每项含coverage（具体对象与覆盖方式）及status：ok/finding/not_applicable/incomplete |
| 条目证据与处置 | ok/finding需evidence：项目内非空文件的相对路径数组；not_applicable需reason事实依据；incomplete需reason与next_action。finding还需findings发现ID数组 |
| findings | 以发现ID为键，每项含summary事实与影响、priority（blocking/required/optional）、status（open/resolved）。open需owner及next_action；resolved需resolution_evidence复验证据路径数组 |

项目已有或新增附加检查可在items中使用自己的ID，注明 `additional: true` 及 `basis`（项目依据或新增检查理由），其余状态、证据和发现字段相同。附加项不能抵消共同条目缺失，也不能把未选专项的现行共同ID改称附加项；不限制项目自选检查方法。not_applicable如另有evidence引用，也核对这些文件。

读取当前ID用 `python3 /实际位置/ai-sdlc/scripts/scan_coverage.py --catalog`。只读预检用 `python3 /实际位置/ai-sdlc/scripts/scan_coverage.py --root PROJECT docs/tasks/TASK-001.md`；0表示声明的结构条件满足、1表示覆盖/结论缺口、2表示调用或文件错误。不提供预填“通过”的模板；证据引用不能指向本任务自身，需指向实际源码、规则、附件或原始执行记录。多个条目可共用同一附件；外部观察先保存项目内可核对材料。

resume、close及Stop的共同assess会检查存在的覆盖块；缺条目、坏引用、未完成项阻止完成。scan_complete允许有已记录归属的未修复发现；healthy还要求blocking/required发现解决且有复验证据，optional可保留。not_applicable理由是否成立、证据充分性、调查与授权真实性仍由AI/人核对，不通过词语黑名单代替语义判断。

扫描内容、所选专项正文、引用文件及校验器参与该任务RUN指纹；状态/时间写回不使覆盖内容自我失效。引用其他会随验证自动写回的状态文件可能造成保守失效，优先引用稳定的原始证据。先完成覆盖记录，再运行任务选择的验证；后续有相关变化只重验受影响范围。没有覆盖块的任务保持原接口，省略整个块不被自动识别；项目规则及交付审阅仍负责确认是否需扫描。

## 项目配置

接入映射示例；argv、输入和确认来源必须换成项目实际内容。所有路径相对 PROJECT，检查命令的 cwd 是 PROJECT。`authorities` 保留历史机器字段名，其含义是规则/入口路径映射，不是额外批准机构。

```json
{
  "authorities": {
    "entrypoint": "README.md",
    "agent_policy": "AGENTS.md",
    "requirements": "docs/requirements.md",
    "validation": "TESTING.md",
    "status": "docs/status.md"
  },
  "confirmation_source": "实际用户授权或项目已确认来源",
  "checks": {
    "unit": {
      "purpose": "验证受影响模块的具体行为",
      "argv": ["python3", "scripts/run_tests.py"],
      "kind": "tests",
      "inputs": ["src", "tests", "scripts/run_tests.py"],
      "environment": [],
      "timeout": 300
    }
  }
}
```

配置在 `.harness/project.json`，实际文件包含 schema_version=1、mechanism_version。mechanism_version记录接入时的执行器版本；doctor输出的是当前实际运行的执行器版本，两者可能不同，不表示安装或迁移已经完成。包版本见[Skill元数据](../SKILL.md)，与配置/任务数据格式版本分开。脚本不自动覆盖配置。doctor 诊断全部映射检查；任务命令只检查当前验收引用的检查配置和输入，共同规则及导航仍须就绪。目录输入包含目录内文件清单（忽略 __pycache__ 与 .DS_Store），新删文件也影响指纹；不要把自动变化的输出或整个项目目录当测试输入。选中的环境变量保存哈希，不保存原始值；日志内容由项目负责脱敏。

接入映射及其中的authorities须为JSON对象。首次接入未填写的职责使用默认路径；重复接入只比较明确填写的职责，省略的职责保留已有映射。其他明确填写字段仍与已有配置比较，真实差异拒绝自动覆盖；预览及--apply遵循同一规则。

status不能与requirements、validation或agent_policy映射到同一实际文件（包含规范化路径、符号链接及现有文件的其他别名），接入预览及写入前均拒绝并指出冲突职责；状态写回会改变这些规则文件的整文件指纹。现有文件按实际身份判断，大小写敏感文件系统上的不同文件可分别映射；未建立的路径若仅大小写不同，先建立并核对实际文件再映射，预览不写探针文件来猜测。沿用分文件映射，不自动拆分已有文件。status仅与entrypoint共文件不受此限制。职责载体必须为非空文件；这些文件中的普通本地导航可以指向存在的文件或目录，缺失目标仍报错。

导航检查识别普通Markdown行内链接、尖括号目标、可选标题，以及单行定义的完整/折叠/快捷引用式链接；本地路径按URI路径解码一次，片段不作为文件名。代码围栏、缩进代码、行内代码及HTML注释中的示例不作导航或缺失链接；图片检查本地资源存在性，但不能代替职责导航。外部URI不抓取，文件内标题锚点不验证。不提供完整Markdown渲染、原始HTML导航或框架路由检查；这些入口仍须由项目相应检查支持，不把文本示例当真实入口。

`kind=tests` 时检查程序必须将 JSON 写到环境变量 `AI_PROJECT_HARNESS_REPORT` 指定的新 RUN 路径：

```json
{"total": 12, "failed": 0, "errors": 0, "skipped": 0}
```

计数来自实际测试框架。零测试、任何必需测试跳过、缺报告不通过。`kind=probe` 用于非测试的真实检查命令，以退出码和日志为证；不可用于绕过测试报告要求。验证命令直接执行 argv，不经过 shell；需 shell 的项目显式配置 shell 程序，并审阅副作用。

目录输入递归包含指向项目内目录的符号链接及其文件；链接目标内容、文件执行权限位和文件增删都参与输入指纹。越界、失效或循环链接报告缺口，不静默漏掉依赖；本地目录和多个合法别名仍可使用。不把这项路径检查当作对恶意并发改写文件系统的沙箱隔离。

文件执行权限位（owner/group/other的执行位）保存于输入指纹file_modes；撤销或改变相关执行位使证据失效，诊断定位文件及执行权限，不纳入mtime等无关属性。旧RUN的内容和schema不改写，缺新指纹或执行器变化按原有效性判定重验。

### 可选规则章节与测试范围

检查配置可增加以下字段，均不要求已有项目填写：

```json
{
  "rule_sections": {"requirements": ["验收标准"]},
  "optional_tests": ["test_invoice.Tests.test_platform"]
}
```

`rule_sections`仅接受requirements、validation、agent_policy职责，值为非空、不重复的精确标题数组。支持Markdown ATX标题（`#`至`######`），章节包含标题及其子章节，到下一同级或更高标题结束；代码围栏、缩进代码、多行代码跨度和HTML注释中的标题不作选择对象；行内代码中的注释字面量不影响后续真实标题，标题本身的单行行内代码按字面名称选择。不支持Setext标题、锚点、正则或自动语义等价；标题缺失或同名多处出现时阻塞，先修映射。未配置职责、无法明确相关规则时保持整文件校验；同一文件映射多个职责时取章节并集，其中任一职责未裁剪则整文件绑定。显式inputs中的文件或目录成员始终整文件绑定，包括同目标的合法别名；裁剪不能排除实际代码/资源输入。选择依据按已有配置维护记录说明，不能漏掉相关共同约束。检查定义和选择变化使旧RUN失效，不用裁剪恢复旧成功。

`optional_tests`仅用于tests检查，是执行前已确认可选或平台限定用例的精确ID数组，不支持通配符、数量配额或事后豁免。未配置时所有跳过仍阻塞。有跳过且配置可选范围时，原始报告须增加`skipped_tests`字符串数组，列全部跳过用例的实际ID，长度等于skipped、无重复，全部在optional_tests中才允许；failed/errors必须为0且total大于skipped。失败或异常的可选用例仍不通过；零测试、全跳过、身份缺失/错误及进程失败不能通过。报告计数不减去可选项，日志、报告和范围均保留；自建适配器自行按相同契约接入，不改用probe绕过。

verify向检查进程注入`AI_PROJECT_HARNESS_OPTIONAL_TESTS`，值为当前检查optional_tests的JSON数组，覆盖继承环境中的同名值；随包unittest适配器据此保留跳过身份并判断退出码。环境变量本身不授权，交付时仍按检查配置和原始回执核对。配置schema_version仍为1，任务及RUN格式不变；这两项能力需1.3.0或之后的执行器，旧版本不提供章节/可选范围语义，不用旧工具继续相关任务。

## 任务编号与文件命名

本节约束两种模式的新任务编号与文件命名；文档模式不因此需要执行器或数据块。

新建任务统一使用递增数字 ID，从 `TASK-001` 开始，不足三位补零；超过 `999` 后自然增加位数，例如 `TASK-1000`。接入已有项目时核对已有任务和编号，避免重复或复用已使用的编号。任务文件名与 ID 一致，例如 `docs/tasks/TASK-001.md`；任务名称写在正文标题中，不追加到文件名。

历史四位数字或具名 ID 可继续读取和引用，原始 RUN、交付回执与会话绑定保留原 ID，不因新约定自动改写。需要迁移已有任务时，先核对并处理任务 ID、文件名、状态引用、证据路径和会话绑定，记录新旧对应与依据；没有完成迁移的历史任务继续使用原 ID。本约定由开发 AI 在新建任务时执行；当前 CLI 的字符校验兼容历史 ID，不提供三位编号的自动分配或强制拒绝保障。

## 任务输入及存储

```json
{
  "id": "TASK-001",
  "goal": "实现当前授权目标",
  "scope": "可修改范围和明确非目标",
  "authorization": "真实授权来源",
  "next_action": "实施并验证具体行为",
  "acceptance": [
    {"id": "AC-01", "text": "可观察的结果", "checks": ["unit"], "human_required": false}
  ]
}
```

begin 后唯一状态在 Markdown 的 `harness-task` 块。新任务使用 v2，并建立下述默认字段；未审阅状态不能通过 close。模板 records/task.md 的职责由同一数据块承载，正文仅补事实说明，不重复状态。脚本不会自动迁移非结构化历史。

### 任务状态支持范围

方法状态见[术语表](terminology.md#5-状态必须分字段)。当前脚本的状态写入入口如下；JSON和持久记录保留英文值，status摘要及resume/close文本显示中文。

| 任务状态 | 当前命令支持 |
|---|---|
| 进行中 `in_progress` | begin创建；核对现场后resume --activate继续 |
| 已中断 `interrupted` | pause保存中断及下一动作；不停止外部操作 |
| 阻塞 `blocked` | close --complete发现交付条件缺口时写入；普通close不改任务状态 |
| 已完成 `completed` | close --complete在条件及审阅材料满足时写入 |
| 未开始 `not_started`、已取消 `cancelled` | 可供文档模式记录或历史任务读取/展示；当前没有转入这些状态的命令，update也不能修改state。已取消任务不能通过resume --activate继续 |

需要取消脚本任务时，在原任务正文保留真实决定、已完成事实、在途操作及后续归属；需要保存中断可用pause，但不得把interrupted或completed冒充cancelled，也不手改状态绕过接口。当前执行器不提供取消终态转换；后续新工作另建有明确授权的任务。

### RUN存储与前台执行

人工验收字段见 verification.md。RUN 位于 `.harness/evidence/TASK/RUN/`；新RUN使用schema_version=2，含 summary.json、output.log 与适用的 test-report.json。summary.json 的 receipt_sha256 校验其余字段的规范JSON内容，摘要与校验值单次原子替换；不再另写summary.sha256。旧RUN v1仍按summary.json原始字节及summary.sha256读取，不改历史原件。旧执行器不能消费新RUN v2，恢复/继续执行须使用支持该格式的版本；任务v2和配置v1不变。单文件替换避免拆分提交窗口，不承诺文件系统断电持久性或防篡改。交付检查结果在 `.harness/close/TASK/`。回执原样保留，不删除失败来取得通过。

verify用于前台检查：父进程退出不足以证明整组结束。正常退出后如同组后代仍存在（或组状态无法确认），按下述有界方式停止；确认停止记录interrupted及reason=descendants_after_parent_exit，无法确认则保留running/停止状态未知，不得封存为passed。组长原退出码保留，不由停止后代反推其结果。需要持续运行的服务应在项目中明确启动/健康检查/停止的资源契约，不能用这个前台检查的组长退出码代替服务验收。

超时/正常中断对本次子进程组先发SIGTERM，最多等待2秒；组仍存在时发送SIGKILL，再最多等待2秒确认，不因组长先退出而省略后代清理。确认组消失后记录interrupted及实际退出码；无法确认停止（包括清理被再次中断）时保留running、finished_at为空及停止状态未知的原因，后续成功不能消除此在途缺口，须现场核对后按reconcile-run追加处置。执行器被SIGKILL或机器断电时RUN也可能停在running。resume报告缺口，不能凭旧PID自动杀进程或重做。首版没有后台常驻服务；另建会话或进程组的外部操作不在本次进程组的清理范围内。

## unittest 计数适配器

标准 unittest 项目可复用本包 `scripts/unittest_report.py`。在项目检查的 argv 中配置 `["python3", "该适配器的实际路径", "--start", "tests", "--pattern", "test_*.py"]`，kind 为 tests。适配器从当前项目目录发现并真实运行测试，保存计数；沿用框架的成功判定，预期失败用例的意外成功（unexpected success）计入 failed，零测试、全跳过及未预先列为可选的跳过非通过。有跳过时报告附真实skipped_tests；可选范围及执行器注入环境见上节。可在授权内将适配器复制到项目 scripts 并把它加入 inputs，便于脱离 Skill 安装目录继续运行。

输出位置依次取环境变量 `AI_PROJECT_HARNESS_REPORT`、`--report`，均未指定时在当前目录的 `.harness/reports/` 下生成唯一文件名。指定路径已有文件会被替换；仅将固定可再生产物用于重复输出，保留历史证据时使用新路径。verify 为每次执行注入独立 RUN 内的报告路径，优先于 `--report`。

doctor 的 ready 仅表示文件、配置和 README 导航检查就绪；接入任务完成还需真实规则审阅、适用检查及交付证据。

## 诊断与验收视图

`resume` 的 assessment 和 `close` 结果保留原有 conditions_met、gaps、runs 等字段，额外提供以下派生信息；不新增任务必填字段：

- `check_results`：按检查 ID 索引，含 run_id、execution_status、evidence_status、conditions_met、log 与 diagnostics。execution_status读取最近RUN的overall_status，无RUN时为not_run；evidence_status是当前证据对检查通过的支持状态，取值见下表。log 是项目内日志路径，失败细节结合该 RUN 的 summary.json 与原始日志读取。
- `diagnostics` 中每项含 code、message、action，输入变化时另含 changes（kind、name、change）。首层 gaps 同时列出最多五项变化的类别与名称；完整清单在 diagnostics。只显示环境变量名和变化，不输出变量值或其散列。旧 RUN 仅存检查定义整体摘要，因此该类差异只能定位到检查定义，不能追溯具体配置字段。执行结束时已检测到前后指纹不同并记为失效的 RUN，即使输入之后恢复，仍说明该 RUN 失效。执行期间改变但结束前恢复的输入无法由两次快照识别，执行器不提供持续变化监测。
- `acceptance_results`：按验收项展示 id、text、checks、human_status 与 conditions_met。人工状态 recorded 仅表示来源及标准指纹已记录，不证明确认真实；共同缺口存在时各项机械条件仍未满足。映射齐全不能证明测试语义充分。
- `global_gaps`：共同前置、历史无效/在途回执及审阅材料等缺口。存在无效回执时 runs 可能仍列可读取的旧 RUN，但不能据此当作最新通过，整体与验收项仍受共同缺口阻塞。

RUN字段记录该次执行，不随之后的输入变化改写：overall_status由实际执行产生running/passed/failed/skipped/interrupted/error；未执行模板的not_run不是实际RUN。verification_status仅在执行passed且validity为valid时写verified，其他结果为unverified，不实现方法层的全部验证结论。validity为valid/invalidated/indeterminate，分别表示执行结束时输入一致/已变化/无法判定；valid不证明检查成功、日志完整或此后证据仍适用。

| 当前evidence_status | 含义及与RUN的关系 |
|---|---|
| missing | 没有可供该检查评估的RUN；损坏历史回执还需核对global_gaps |
| stale | 当前输入与RUN不同，或RUN已记录执行期间输入变化；对应当前已失效 |
| unknown | 当前输入不可取得，或RUN未确认输入有效性；对应无法判定 |
| unverified | 尚未形成可支持检查通过的证据；失败或未结束且没有上述输入缺口时可出现，不表示没有执行 |
| invalid | 对可继续评估的RUN发现日志、报告或计数不合格；不等同仅发生输入变化 |
| valid | 本检查最近执行、输入及日志/适用报告满足机械条件；整体任务仍可能存在其他缺口 |

这些值不是validity的一一改名。输入未变的失败检查可同时具有overall_status=failed、verification_status=unverified、validity=valid和当前evidence_status=unverified：失败事实仍保留，但不能支持通过。不得从unverified推断未执行，也不得从一次失败直接判定产品缺陷；原因需结合原始材料审阅。多种缺口同时存在时结合execution_status、diagnostics及global_gaps判断，不由一个字段概括。

JSON 和文本复用同一次评估；默认仍输出 JSON，返回码与既有判定不变。`resume --format text` 只读，`close --format text` 沿用 close 的回执及显式 --complete 副作用。建议动作不是授权，不自动重放检查或改变范围；输入已变化时核对变化，只复验受影响范围。

### 恢复诊断的共同表达

`global_diagnostics`与`global_gaps`逐项同序对应，覆盖共同前置、任务材料、扫描覆盖、审阅和历史回执等缺口；`acceptance_results[].diagnostics`说明必需人工验收缺口。它们与已有`check_results[].diagnostics`共用`code`、`message`、`action`，补充`subject`（kind与id：project/task/check/run/acceptance）和`evidence_refs`（项目内材料位置数组，无材料时为空）。引用是核对位置，可指向预期但缺失的材料，不表示材料有效或语义已核实。旧字段、返回码与通过判定保持。

诊断从原判定生成；无法细分的项目/任务/扫描缺口保留类别级code及原说明，不靠关键词猜测。重要恢复code包括`run_unresolved`、`invalid_run_receipt`、`damaged_run_recheck`、`review_source_missing`、`review_material_changed`、`review_record_changed`，以及`human_confirmation_missing`、`human_source_missing`、`human_scope_missing`、`human_scope_changed`。code帮助定位，不能只看某一诊断列表忽略其他共同缺口、检查或人工验收。

`action`是建议及必要前提，不是执行命令或授权。未知在途结果先核对实际进程、回执与副作用，再决定是否reconcile-run；损坏回执按现场核对追加处置，原件保留；人工验收须取得真实确认并核对范围。JSON与文本均读取同次评估，不自动重试、修改确认或重放操作。诊断仅改善表达，不证明AI恢复效果或用户来源真实性。

## 可移植机制自检

接入或修改相关机制时，可运行 `python3 /实际位置/ai-sdlc/scripts/self_test.py`，也可将该命令映射为项目的 tests 检查。使用与 harness.py 一致的 Python 3.10+；脚本只依赖标准库及同包 harness.py/模板，复制整个 Skill 包后可直接运行。

自检在自动清理的临时项目内验证生命周期成功、中断恢复、缺验收/证据、最新失败、无关/相关/执行中输入变化、坏日志/回执、跳过/零测试/坏报告和超时。stdout 输出实际 unittest 计数，stderr 输出逐项结果；设置 AI_PROJECT_HARNESS_REPORT 时另写指定报告，其余情况下不在调用目录写文件。不通过、零测试或跳过返回非零。

这是一组可复用的机制检查，不是完整开发回归或项目适配证明。优先复用已有等效检查；按风险补查项目命令、输入映射和报告转换，产品测试及真实平台事件仍按项目要求执行。不要求每次业务修改都运行自检。

## v2任务处置与更新

purpose.user_outcome 未提供时复用 goal；显式空白或坏值仍是草稿缺口。purpose.stage_ref 有关联时引用项目内文件，无阶段可省略；stage_reason、next_reason 仅在需要额外解释时补充。document_sync 默认 reviewed=false。AI 每次形成决定、修改后反查与交付前主动维护，不要求用户逐项提醒。

最小无文档影响处置（用户结果沿用 goal，下一动作已能说明目的）：

```json
{"document_sync":{"reviewed":true,"no_change_reason":"本次修复恢复既有规则，规则正文不变","items":[]}}
```

这只是字段片段；完整更新步骤见下方[任务快照更新](#任务快照更新)。`begin/update` 在写入前汇总 decisions 与 document_sync.items 已填写条目的结构错误并给出字段路径；待处置的合法草稿仍可保存，完成条件由 close 核对。resume/close 对 changes、followups、human_items 和 risk_routes 逐项检查必需字段的类型与内容，缺口标出数组下标和字段；一项错误不遮住其他条目。历史记录通过同一入口报缺口，不因本次修复自动改写。人工确认只能按真实来源维护。

- decisions：每项 id、kind（confirmed/authorized/candidate/rejected/observation）、source、summary、rule_ref。kind是事项分类，依次表示人已确认、开发AI授权内决定、候选、拒绝和观察事实。已确认或授权内改变规则且有 rule_ref 时，关联同步处置；候选不能当正式依据。
- document_sync：reviewed、no_change_reason、items。items 每项 id、decision_ids数组、path、status（pending/updated/not_needed）、reason。updated 需文件存在且非空；not_needed 需理由；pending 阻止完成。
- changes：每项 path 为非空项目相对路径、summary 为非空文字；删除文件可记录路径，语义审阅核对实际差异。
- followups：每项 id、summary、owner、trigger、source 均为非空文字。不能转移本次必需验收规避完成要求。
- human_items：每项 id、question、recommendation 为非空文字，materials 为非空的项目内路径数组，acceptance_id 为已知验收 ID 或 null。需要人判断与人已确认分开。
- risk_routes：每项 kind 为 experiment/recovery/side_effect/incident，applicable 为布尔值，reason 为非空文字；适用时 record_ref 需指向项目内非空文件。不适用时可省略 record_ref。风险本身的结果要求加入验收检查。

只有需要独立维护长期决定时才建立决策记录：candidate可对应其proposed状态；confirmed或authorized可在来源与范围成立时支持accepted；rejected保留实际拒绝依据；observation继续作为事实材料，不能自动转为已确认决定。决策后续被取代或停用按原记录的superseded/deprecated维护，不能从kind推断生命周期，也不将旧任务的当时分类批量改写。独立记录与任务互相引用，不复制同一决定正文。

未完整的v2处置可以保存为草稿，但不能通过交付检查。JSON与文本resume均显示可用信息及具体缺口；文本中必需展示字段的显式空白或未完整内容标“未填写”，可省略字段按上述复用约定展示；不把草稿缺口补成有效内容，也不改写任务或重放命令。

close --complete 的 review-source 在v2必须为项目内非空审阅材料，可引用当前任务文件。新记录的 review_kind=file 散列独立文件，task_body 散列当前任务去掉唯一 harness-task 块后的正文；review_record_sha256 另核对受审任务信息，排除状态、时间、下一动作及审阅管理字段。状态派生文件不能作审阅材料。正文、独立材料或受审记录改变后重新审阅并完成；旧记录无新字段时仍沿用原文件散列。reviewed/文件存在只证明处置可检查，不证明内容正确。下一动作或其原因变化不改变执行标准或受审记录；相关规则、源码和检查配置变化仍使旧证据失效。

`python3 H --root PROJECT migrate-task TASK` 预览旧v1任务；加 --apply 保存原件及散列再升级。未知版本拒绝；v1可只读resume及legacy close，继续verify/activate/pause前需迁移。旧RUN不修改，升级后的当前证据重新核对。TASK源JSON仅为创建历史，别当作当前状态。

### 任务快照更新

从 `resume TASK-001` 的 `task` 字段取得完整对象，只应用本次内容修改，保留 `state` 和 `updated_at`；保存为临时 `snapshot.json` 后执行 `python3 H --root PROJECT update TASK-001 --spec snapshot.json`。不能只提交字段片段，也不能通过update改变id、schema、状态、创建时间、迁移或完成审阅字段。快照过期时重新读取并重应用修改，不只替换时间戳。

`verify`保存独立RUN，不改写任务记录；`update`、`pause`、`resume --activate`和`close --complete`等任务写入会更新记录。仅修改document_sync等处置元数据不会改变RUN的任务标准指纹；目标、范围、授权、验收项及所选检查的相关输入变化会使对应RUN失效。已完成任务的受审记录另按其内容重新核对。更新后先看resume/close的缺口，只复验受影响检查。

### 已有人工确认的记录示例

仅当人已真实确认且确认适用于当前任务标准时记录。`resume` 的 JSON 输出同时提供 `task` 和 `assessment.contract`；`close` 的 JSON 输出也提供顶层 `contract`，无需调用方重算散列。下面的 `result` 是本次 `resume` JSON 对象，`actual_source` 是已核对的真实确认来源，`AC-01` 替换为对应验收ID：

```python
task = result["task"]
task["human_acceptance"]["AC-01"] = {
    "status": "accepted",
    "source": actual_source,
    "contract": result["assessment"]["contract"],
}
```

按[任务快照更新](#任务快照更新)保存上述修改。尚未确认时保留待确认；已有指纹不匹配时先核对确认所覆盖的标准及实际变化，必要时重新确认，不能直接换成新指纹求通过。此记录不代替语义审阅，`human_items` 只提供待人问题与材料，不是已确认结果。

### 收尾失败后的恢复示例

`close` 默认只核对并保存回执；`close --complete` 因交付缺口失败才将任务置为 `blocked`。参数或材料错误不表示已改变任务状态，以重新读取的记录为准。

任务是保存事实，状态摘要是派生视图。任务文件成功保存后若摘要写入失败，CLI仍返回2，但stderr JSON为status=partial，并含task_committed=true、task_id、task_state、updated_at、status_synced=false和next_action。此时不要重放begin/update/pause/activate/complete，先读取任务确认，再执行`sync-status TASK-001`。该命令只刷新指定任务的摘要（可重复执行），不改任务状态/时间、审阅绑定或RUN，不执行验证命令。它会重新核对当前证据以生成摘要，成功仅代表摘要同步，不代表任务验收通过。若失败动作是close --complete，partial还含receipt_pending=true；摘要同步后按next_action再运行不带--complete的`close TASK-001`，仅补当前交付检查回执，供Stop等消费者核对，不重复完成动作。摘要标记本身损坏时先修复标记，命令不猜测覆盖人工正文。正常返回结构不变；进程被强制终止而无结果时，仍须先读取现场判断提交情况。

`blocked`本身不阻止按[任务快照更新](#任务快照更新)修改内容。若接着需要运行验证，核对现场后执行 `resume TASK-001 --activate`，再 `verify TASK-001 CHECK_ID`，其中检查ID取自本任务验收。已有证据仍有效且只补齐记录时，不因收尾失败自动重跑检查。

重新交付时可用 `close TASK-001 --complete --review-source docs/tasks/TASK-001.md`；路径必须对应真实非空审阅内容，也可换为项目内独立审阅文件。会话原话不能直接用作该路径，人工验收来源与差异审阅材料是不同职责。

以上是按需要选取的操作示例，不要求每次任务执行固定命令序列。

## 历史在途执行处置

不带 --damaged 时，仅对留在 running 的 RUN 使用 reconcile-run；先核对实际进程、请求身份、目标状态及副作用结局，不能凭旧 PID、新一次成功或正文声明自动认定已结束。--outcome finished / stopped 表示已核对执行结束 / 停止；结局未知不调用解除。--source 指向包含核对事实的项目内材料，可用当前任务正文，不能用状态派生文件。

追加记录位于 .harness/reconciliations/TASK/RUN/，绑定任务、原 RUN 散列、材料散列和结局，不改原执行记录。最近处置损坏或材料、原件变化时不回退旧处置；重新核对后追加新记录。有效处置只解除该历史在途缺口，最新必需检查仍须真实通过。脚本不探测进程是否存活或替人证明材料真实，不停止进程、不重发副作用。

### 损坏回执的现场处置

原summary缺失、不可解析、身份或校验错误等情况下，普通reconcile-run拒绝解除。先核对实际操作身份、进程、目标结果和副作用，确认已结束或停止且现存文件可安全读取后，显式加`--damaged`追加处置；完整回执不能走该入口，未知结局不能解除，缺材料或路径越界仍拒绝。处置v2绑定现存RUN目录文件清单及内容散列（沿目录输入规则忽略__pycache__与.DS_Store）、现场材料和时间；不删除或修补原件。仅创建目录就中断的空RUN也可按现场事实处置。

因损坏回执的check_id不可依赖，处置后当前每个必需检查都须取得started_at晚于最后一次有效损坏处置的新RUN；先前成功及处置记录本身均不能提供通过证据，最新失败仍不能回退。原件增删改、删除原目录、核对材料变化或最新处置损坏仍阻塞，不回退旧处置；重新核对后可追加处置并重验。无法读取或确认副作用的情况保持未解决。此路径不是人工确认自动化，核对事实真实性仍由AI/人负责。

## 可选Git输入快照

`scripts/evidence_snapshot.py`是独立、可选的只读输入清单工具，两种模式均可使用，不改变harness任务、RUN或验收协议。需要Git；不执行检查、不自动加入close，不要求文档模式建立脚本映射。

```sh
python3 /实际位置/ai-sdlc/scripts/evidence_snapshot.py --root /项目根目录 --source worktree --path src --path tests --output /已存在目录/worktree-new.json
python3 /实际位置/ai-sdlc/scripts/evidence_snapshot.py --root /项目根目录 --source index --path src --path tests --output /已存在目录/index-new.json
python3 /实际位置/ai-sdlc/scripts/evidence_snapshot.py --root /项目根目录 --source commit --ref HEAD --path src --path tests --output /已存在目录/commit-new.json
```

`--path`必填、可重复，按仓库相对文件/目录字面前缀选择（不是glob），归一化并去重；不允许根目录、绝对或上级路径。工作树选已跟踪及未忽略的未跟踪文件，已跟踪但删除的文件标missing；不会发现被忽略的新文件。index从当前暂存树读取、commit从解析后的固定提交读取，均不混入工作树内容；index调用Git write-tree可能写Git对象库，不修改暂存内容或分支。未合并索引、非普通文件（含符号链接及子模块）、无文件匹配或读取失败返回2，不生成成功快照。部分选择无匹配会列入unmatched_paths，使用者须核对缺口，不将剩余范围当完整通过。

输出记录source、固定对象identity（工作树为null）、去重paths、files的SHA-256/执行权限或missing、files_sha256及采集起止时间。files_sha256只用于比较文件集合、内容与权限，不包含选择范围、对象来源或未匹配项；比较时同时核对这些字段。输出父目录须已存在，输出必须在选择范围外且不存在；排他创建拒绝覆盖旧文件。工具不读取文件正文到报告，但路径和散列仍应按项目隐私范围保留，不自动上传。

此清单不冻结工作树、不能证明扫描语义或环境相同；捕获期间并发变化可能得到混合状态。暂停相关写入、采证前后重取新快照并按风险核对，不能用两次相同证明中间未变化。检查应实际读取所声明的对象；要检查暂存/提交内容，可在隔离导出目录执行现有检查。不要只检查工作树的git diff后宣称暂存区已验收。历史快照保持原样，工具不替代现行RUN失效检查。

## 可选工程导览工具

独立scripts/project_guide.py随包提供，Python3.10+标准库。文档/脚本模式均可选用，也可继续复用项目文档站或生成器；不加入harness close、不自动接入或更改项目状态。不执行检查/模型/网络请求，不自动发现依赖或判断工程完成。

```sh
python3 /实际Skill位置/scripts/project_guide.py build --root /项目目录
python3 /实际Skill位置/scripts/project_guide.py check --root /项目目录
python3 /实际Skill位置/scripts/project_guide.py inspect --root /项目目录 --view 0 --node reader --direction downstream
```

默认源docs/project-guide.md、输出docs/project-guide.html，可用--source/--output指定项目根内相对路径（输出限.html/.htm）；inspect的--view为围栏出现顺序从0起，方向upstream/downstream，只读已有图；可加--target终点查询from→to的已列有向最短路径，不与upstream组合，无路径返回path=null（不是完整系统无关系的证明）。输入需UTF-8；stdout为结果/结构化查询，坏参数/来源/图返回非零且不替换旧HTML；check只读完整比较当前源、明确来源内容身份及渲染器/外壳。文件变更不自动刷新历史快照，按原授权核对后build。来源对应仅证明可定位和身份，不证明关系含义/真实运行影响或验收。

内容源首先写guide-meta JSON注释，再写唯一#主标题及##板块，板块可加{#id}。普通段落、Markdown链接、三级标题、列表和代码围栏可用；不是完整Markdown方言。html围栏只接受受控展示标签/属性，不接受script、iframe、事件属性或javascript链接。旧受控SVG图可保留，新工具图用engineering-map围栏。正文/图要使用的相关文件应在meta.sources或节点sources明确映射，遗漏依赖程序无法自动发现；普通进一步阅读链接不自动成为内容输入。

```json
{
  "title": "项目工程导览",
  "date": "真实核对日期",
  "version": "本次项目版本",
  "identity": "实际提交或内容范围",
  "scope": "来源与已核对范围；未确认计划明确说明",
  "sources": ["README.md"],
  "required_views": ["collaboration", "architecture"]
}
```

required_views至少保留使用/协作和内部架构两个视角（默认两者），与现行导览要求一致；其他类型按实际理解需要选用，不因工具支持就强制增加。节点和关系均可写basis=observed/inferred/unknown，默认observed是作者声称有依据而非程序认证；即使来源存在仍须语义核对。来源path为根内相对路径，可选line/end_line必须落在真实UTF-8文件内；HTML提供路径及行号说明，行号不保证普通浏览器能自动定位编辑器。

```json
{
  "kind": "architecture",
  "title": "内部结构与关键关系",
  "nodes": [
    {"id": "entry", "label": "执行入口", "description": "实际职责与限制", "sources": [{"path": "README.md"}]},
    {"id": "result", "label": "执行结果", "basis": "unknown"}
  ],
  "edges": [{"from": "entry", "to": "result", "label": "实际关系说明", "basis": "inferred"}]
}
```

kind还支持collaboration/workflow/dataflow/lifecycle。可选node.position={column,row}安排层次（0–100整数，不重叠），role=component/actor/rule/template/core/data/helper/process/optional/result和summary组织节点视觉层级；可选groups[{id,label,members}]标记真实边界，成员不得重复或把非成员圈入边界。edge.category=primary/conditional/optional/feedback/reference及short_label仅表达作者已核对关系，不能凭样式推断事实。端口分散、正交走线和短标签辅助阅读，密集关系仍按节点详情/静态列表回查，不承诺所有图自动达到最佳布局。每图1–200节点、0–1000关系，稳定ID不重复且端点必须存在；上限是工具保护，不是推荐首页密度或理解效果承诺。build校验后以同目录候选原子替换；拒绝输出覆盖源、明确来源、生成器/展示资产、符号链接/硬链接别名及根外路径。输入根是用户指定项目，不支持将不可信网页或任意目录当作项目授权。JS数据和文本转义，静态节点/关系/来源详情仍可阅读；浏览器中选择节点、查询文字、两节点路径和上下游聚焦不运行工程动作。

维护：工具/展示资产及上述可选接口变化时更新本节，消费项目已选输入变化按原验证策略核对；模板/工程事实仍沿各自唯一来源维护，不增第二套流水线或强制JSON台账。
