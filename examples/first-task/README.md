# 首个任务：修复问候函数并恢复工作

先按[使用入口](../../README.md)安装完整包。本教程在新建的临时目录练习，采用脚本模式，不修改真实项目。先失败、再修复，最后暂停和恢复同一个任务；它演示执行器行为，不证明 AI 或新用户一定能正确使用。

需要 macOS/Linux shell 和 Python 3.10+。本页的 `sh` 代码块按顺序在同一个终端执行；也可以把本页交给已显式调用的 AI 执行。不要在自己的项目中复制练习授权、需求或配置。示例需求唯一正文在 [requirements.md](starter/requirements.md)。

## 1. 准备练习目录

从已安装 Skill 的项目根开始。若采用其他安装位置，将第一行改为那个完整包的绝对路径；不使用开发仓库的私有 Python。终端中的 `python3` 及它启动的子进程应指向同一个满足要求的解释器。

```sh
export AI_SDLC_PACKAGE="$PWD/.agents/skills/ai-sdlc"
set -eu
python3 -c 'import sys; assert sys.version_info >= (3, 10), "需要 Python 3.10+"'
test -f "$AI_SDLC_PACKAGE/scripts/harness.py"
H="$AI_SDLC_PACKAGE/scripts/harness.py"
exercise=$(mktemp -d "${TMPDIR:-/tmp}/ai-sdlc-first.XXXXXX")
cp -R "$AI_SDLC_PACKAGE/examples/first-task/starter/." "$exercise/"
cp "$AI_SDLC_PACKAGE/scripts/unittest_report.py" "$exercise/unittest_report.py"
cd "$exercise"
printf '练习目录：%s\n' "$PWD"
```

记下打印的目录，稍后恢复使用。目录中已有这个练习所需的规则、需求、测试和映射，便于把注意力放在任务流程；真实项目的内容应由 AI 核对后准备，而不是直接使用夹具。

## 2. 接入并看见真实失败

先预览，再应用；`doctor` 应显示就绪。这里就绪是因为练习已经提供真实内容，空模板不会自动满足条件。

```sh
python3 -B "$H" adopt --mapping mapping.json
python3 -B "$H" adopt --mapping mapping.json --apply
python3 -B "$H" doctor
python3 -B "$H" begin --spec task-spec.json
if python3 -B "$H" verify TASK-001 unit; then
  printf '%s\n' '初始实现应失败，请检查是否使用了原始练习。' >&2
  exit 1
else
  test "$?" -eq 1
fi
if python3 -B "$H" close TASK-001; then
  printf '%s\n' '失败的检查不应满足交付条件。' >&2
  exit 1
else
  test "$?" -eq 1
fi
```

应看到原始测试失败，缺陷是未处理两端空白和空姓名（报告 total=4、failed=3，其中空姓名的两个 subTest 分别计为失败）；失败日志保存在 `.harness/evidence/TASK-001/`。`close` 此时不满足交付条件，不能把失败改成完成。配置错误的退出码2也不算本教程期待的测试失败。

## 3. 修复并验证

若由 AI 练习，可以让它先读需求、日志及 `greeting.py`，自行完成修复：

> 使用 $ai-sdlc，在刚创建的练习目录继续 TASK-001。保留需求和测试，修复空白与空姓名行为，执行 unit。通过后记录实际改动并暂停，下一步是恢复核对与交付。

下面给出可复跑的参考实现；它只替换临时练习的 `greeting.py`，不要求实际项目采用同样实现。

```sh
cat > greeting.py <<'PY'
def greeting(name):
    cleaned = name.strip()
    return f"Hello, {cleaned or 'stranger'}!"
PY
python3 -B "$H" verify TASK-001 unit
cat >> docs/tasks/TASK-001.md <<'EOF'

## 本次练习执行

按requirements.md将姓名两端空白去除，空姓名使用stranger；保留内部空格和非ASCII字符。测试保持原预期，原始失败RUN保留。修复后的unit通过；下一步恢复核对与交付。本记录只描述本练习，不代表业务项目或真人验收。
EOF
python3 -B "$H" pause TASK-001 --next '读取当前任务与有效证据，对照需求审阅后完成练习'
```

应看到4项通过、无跳过，任务处于中断状态；状态入口指向原任务，旧失败仍保留。测试通过与任务关闭不是同一步。

## 4. 恢复并交付

实际使用时，可在 Codex 打开同一练习目录的新会话，明确提供完整 Skill 路径（临时目录不一定继承原项目的 Skill 发现），输入：

> 使用给定路径的 ai-sdlc，读取本练习的 README、status 和 TASK-001，先核对当前现场与证据，不重复接入或重做任务。继续下一动作，满足交付条件后结束练习。

在终端复跑时，下面的每次命令也是独立进程；这只验证新进程恢复，不等同于新 AI 会话或真人试用。若另开终端，需要重新设定 `AI_SDLC_PACKAGE`、`H`，并进入上面打印的练习目录，不要重新执行第1步创建另一个练习。

```sh
python3 -B "$H" resume TASK-001 --format text
python3 -B "$H" resume TASK-001 --activate
cat > review.md <<'EOF'
# 练习审阅

对照requirements.md与实际差异：修复只改变greeting函数，strip去除两端空白；空结果回退stranger，内部空格与非ASCII字符保留。原有四项测试不变，最新unit报告全部通过，原始失败仍可追溯。规则与需求无需修改。本示范审阅仅覆盖当前练习；实际项目须审阅自己的差异和证据，不能照抄这段文字代替审阅。
EOF
python3 -B "$H" close TASK-001 --complete --review-source review.md --format text
```

应看到任务已完成、当前检查有效；检查日志、任务正文、审阅依据各自可定位。无需创建第二个 TASK，也无需再次 adopt。若报告证据失效，先看哪些输入发生了变化，不能挑选旧成功结果。

## 练习结束后

临时目录保留以供查看，教程不自动删除。确认不再需要记录后，可以删除刚创建的这个练习目录；包安装目录和真实项目不随之删除。接入自己的项目回到[使用入口](../../README.md#开始第一个任务)，按实际规则选择模式。

首次使用试用还需未参与开发的人操作：只给完整包和本页，观察安装发现、原始失败、修复及新会话恢复是否能完成，并记录具体卡点、作者介入及实际耗时。无需提交私有项目数据；内部命令实跑不替代这项观察，也不据此承诺固定上手时间。
