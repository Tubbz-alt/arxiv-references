"""Normalize extracted references."""

from statistics import mean, median
from decimal import Decimal
import re
from typing import Tuple, Union, List, Callable

from references.domain import Reference
from arxiv import taxonomy
from arxiv.base import logging

logger = logging.getLogger(__name__)


def _remove_dots(string: str) -> str:
    """Remove dots while preserving whitespace."""
    return re.sub(r"\.\s*", " ", string).strip()


def _remove_dots_from_author_names(author: dict) -> dict:
    """Remove dots from givennames and fullname."""
    givennames = author.get('givennames')
    fullname = author.get('fullname')
    if givennames is not None:
        author.update({'givennames': _remove_dots(givennames).title()})
    if fullname is not None:
        author.update({'fullname': _remove_dots(fullname).title()})
    return author


def _remove_leading_trailing_nonalpha(string: str) -> str:
    """Remove leading or trailing non-alphanumeric characters."""
    return re.sub(r"[^0-9a-zA-Z]+$", "", re.sub(r"^[^0-9a-zA-Z]+", "", string))


def _fix_arxiv_id(value: Union[list, str]) -> Union[list, str]:
    """Fix common mistakes in arXiv identifiers."""
    if isinstance(value, list):
        return [_fix_arxiv_id(obj) for obj in value]
    for category in taxonomy.ARCHIVES.keys():
        typo = category.replace('-', '')
        if typo in value:
            return value.replace(typo, category)
    return value


NORMALIZERS: List[Tuple[str, Callable]] = [
    ('authors', _remove_dots_from_author_names),
    ('title', _remove_leading_trailing_nonalpha),
    ('source', lambda string: _remove_dots(string).title()),
    ('arxiv_id', _fix_arxiv_id)
]


def normalize_record(record: Reference) -> Reference:
    """
    Perform normalization/cleanup on a per-field basis.

    Parameters
    ----------
    record : :class:`.Reference`

    Returns
    -------
    dict
    """
    for field, normalizer in NORMALIZERS:
        value = getattr(record, field, None)
        if value is None:
            continue
        if isinstance(value, list):
            setattr(record, field, [normalizer(obj) for obj in value])
        else:
            setattr(record, field, normalizer(value))
    return record


def normalize_records(records: List[Reference]) -> List[Reference]:
    """
    Perform normalization/cleanup on a per-field basis.

    Parameters
    ----------
    records : list
        A list of :class:`Reference` instances.

    Returns
    -------
    list
    """
    return [normalize_record(record) for record in records]


def filter_records(records: List[Tuple[Reference, float]],
                   threshold: float = 0.5) -> Tuple[List[Reference], float]:
    """
    Remove low-quality extracted references, and generate a composite score.

    Parameters
    ----------
    records : list
        Items are two-tuples of metadata (``dict``) and record score
        (``float``).
    threshold : float
        Minimum record score to retain.

    Return
    ------
    tuple
        Filtered list of reference metadata (``dict``) and a composite score
        for all retained records (``float``).
    """
    # We need to both filter and update each record with the key 'score'.
    filtered = []
    for ref, score in records:
        ref.score = score
        if score >= threshold:
            filtered.append((ref, score))
    if len(filtered) == 0:
        return [], 0.
    ref_tuple, scores = zip(*filtered)
    references: List[Reference] = list(ref_tuple)
    return references, mean(scores)
