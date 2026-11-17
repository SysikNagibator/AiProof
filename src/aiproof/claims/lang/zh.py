"""Simplified Chinese claim-phrase pack (draft)."""

from __future__ import annotations

from aiproof.claims.model import ClaimType as C
from aiproof.claims.model import Rule

CODE = "zh"
STOPWORDS = ("的", "测试", "提交", "推送", "文件", "完成", "通过")
NEG = ("未", "没有", "还没", "尚未", "不")
HEDGE = ("应该", "可能", "大概", "似乎")

RULES: tuple[Rule, ...] = (
    Rule(C.TESTS_PASS, (r"测试全部通过", r"测试通过", r"所有测试通过"), NEG, HEDGE),
    Rule(C.COMMITTED, (r"已提交", r"提交了"), NEG, HEDGE),
    Rule(C.PUSHED, (r"已推送", r"推送了"), NEG, HEDGE),
    Rule(
        C.FILE_WRITTEN,
        (
            r"已创建文件",
            r"创建了文件",
            r"文件已创建",
            r"(?:创建|写入)了?[^\n]{0,20}\.[A-Za-z0-9]{1,6}",
        ),
        NEG,
        HEDGE,
    ),
    Rule(C.FILE_CHANGED, (r"已更新", r"已修改"), NEG, HEDGE),
    Rule(C.FILE_DELETED, (r"已删除",), NEG, HEDGE),
    Rule(C.FEATURE_DONE, (r"已完成", r"完成了", r"搞定"), NEG, HEDGE),
    Rule(C.TESTS_ADDED, (r"添加了测试", r"新增测试", r"测试已添加"), NEG, HEDGE),
    Rule(C.BUILD_PASSES, (r"构建成功", r"编译通过", r"构建通过"), NEG, HEDGE),
    Rule(C.LINT_PASSES, (r"(?:lint|代码检查)(?:通过|成功)",), NEG, HEDGE),
    Rule(
        C.BUG_FIXED,
        (r"修复了?\s*bug", r"修复了?\s*错误", r"bug\s*已修复", r"错误\s*已修复"),
        NEG,
        HEDGE,
    ),
    Rule(
        C.DEPENDENCY_INSTALLED,
        (
            r"安装了?依赖",
            r"安装了?包",
        ),
        NEG,
        HEDGE,
    ),
    Rule(
        C.MIGRATION_RUN,
        (
            r"执行了?迁移",
            r"迁移已应用",
        ),
        NEG,
        HEDGE,
    ),
)
