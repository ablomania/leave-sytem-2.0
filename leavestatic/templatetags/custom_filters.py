from django import template

register = template.Library()

@register.filter
def to_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
    

# from django import template
# register = template.Library()

@register.filter
def get_group(approver_objs, group):
    for approver in approver_objs:
        if approver.group_to_approve_id == group.id:
            return approver
    return None


@register.filter
def any_active(approver_objs):
    return any(getattr(a, 'is_active', False) for a in approver_objs)


@register.filter
def active_only(staff_list):
    return [s for s in staff_list if getattr(s, 'is_active', False)]


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)