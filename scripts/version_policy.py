"""One independently tracked change per version, beginning with a 1.0.0 baseline."""
import re

LANGUAGES = ('zh-Hant', 'zh-Hans', 'en')
CATEGORIES = {
    'added': ('新增', '新增', 'Added'),
    'removed': ('刪除', '删除', 'Removed'),
    'improved': ('優化', '优化', 'Improved'),
    'other': ('其它', '其它', 'Other'),
}


def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', value):
        raise ValueError('Use an exact three-part version without a v prefix or leading zeros.')
    return tuple(map(int, value.split('.')))


def validate_change(change):
    if not isinstance(change, dict) or not isinstance(change.get('id'), str) or not change['id'].strip():
        raise ValueError('Provide one change object with one independently tracked change.id.')
    if change.get('category') not in CATEGORIES:
        raise ValueError('change.category must be added, removed, improved, or other.')
    major = change.get('majorArchitectureChange', False)
    if not isinstance(major, bool):
        raise ValueError('majorArchitectureChange must be a boolean.')
    if major:
        rationale = change.get('architectureRationale')
        if change['category'] != 'added' or not isinstance(rationale, str) or not rationale.strip():
            raise ValueError('A major bump requires an added feature and a concrete architectureRationale.')
    return change


def next_version(previous, change):
    validate_change(change)
    major, minor, patch = version_tuple(previous)
    if change.get('majorArchitectureChange'):
        return f'{major + 1}.0.0'
    if change['category'] in ('added', 'removed'):
        return f'{major}.{minor + 1}.0'
    return f'{major}.{minor}.{patch + 1}'


def validate_notes(record):
    categories = record.get('noteCategories')
    if not isinstance(categories, list) or not categories or any(c not in CATEGORIES for c in categories):
        raise ValueError('Provide ordered noteCategories for every trilingual item.')
    for index, language in enumerate(LANGUAGES):
        title = record.get('titles', {}).get(language)
        entries = record.get('notes', {}).get(language)
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f'Fill in titles.{language}.')
        if not isinstance(entries, list) or len(entries) != len(categories):
            raise ValueError('All three languages must have the same item count and category order.')
        for entry, category in zip(entries, categories):
            prefix = f'[{CATEGORIES[category][index]}] '
            if not isinstance(entry, str) or not entry.startswith(prefix) or not entry[len(prefix):].strip():
                raise ValueError(f'{language} note must start with {prefix}and describe the change, effect and limitations together.')


def validate_lineage(releases):
    """Validate metadata; actual source isolation still requires diff review and testing."""
    chronological = list(reversed(releases))
    if not chronological or chronological[0]['version'] != '1.0.0':
        raise ValueError('The reconstructed baseline must be 1.0.0.')
    identifiers = set()
    previous = None
    for record in chronological:
        version_tuple(record['version'])
        validate_notes(record)
        change = validate_change(record.get('change'))
        if change['id'] in identifiers:
            raise ValueError('Each independently tracked change must have its own unique ID.')
        identifiers.add(change['id'])
        if previous is not None and record['version'] != next_version(previous, change):
            raise ValueError(f"{record['version']} does not follow the category-based version rule.")
        previous = record['version']
