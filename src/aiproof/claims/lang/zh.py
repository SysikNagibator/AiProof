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
    Rule(C.FILE_WRITTEN, (r"已创建文件", r"创建了文件", r"文件已创建"), NEG, HEDGE),
    Rule(C.FILE_CHANGED, (r"已更新", r"已修改"), NEG, HEDGE),
    Rule(C.FILE_DELETED, (r"已删除",), NEG, HEDGE),
    Rule(C.FEATURE_DONE, (r"已完成", r"完成了", r"搞定"), NEG, HEDGE),
)
