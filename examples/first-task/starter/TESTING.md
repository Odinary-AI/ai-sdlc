# 练习验证

使用 Python 3.10+ 标准库。教程从完整 Skill 复制 unittest_report.py 到本项目；执行 python3 unittest_report.py --start tests 运行真实测试并生成计数报告。脚本模式通过 verify 执行 mapping.json 的 unit 检查，由执行器指定报告位置。

tests/test_greeting.py 检查普通姓名、两端空白、空输入及非ASCII/内部空格。测试须全部通过，无失败、错误或跳过；先保留原始失败，再修 greeting.py，不修改预期以迁就实现。
