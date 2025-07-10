from django import template
register = template.Library()

@register.filter
def get_group(approver_objs, group):
    for approver in approver_objs:
        if approver.group_to_approve_id == group.id:
            return approver
    return None