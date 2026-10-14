"""Finished goods and material issues share the same SQL tables."""

from app.modules.material_issuing.models import IssueItem, IssueNote

FinishedGoodsDispatch = IssueNote
DispatchItem = IssueItem
