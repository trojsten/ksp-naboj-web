from django import forms, template

register = template.Library()


@register.inclusion_tag("forms/field.html")
def render_field(field):
    return {"field": field}


@register.inclusion_tag("forms/form.html")
def render_form(form):
    return {"form": form}


@register.simple_tag()
def field_class(field, error=False):
    # Note: error states are written out in full form
    # and not built from orignal classess to allow
    # TailwindCSS to correctly pick them up.
    widget = field.field.widget

    if isinstance(widget, forms.Textarea):
        return "textarea" if not error else "textarea textarea-error"
    if isinstance(widget, forms.Select):
        return "select" if not error else "select select-error"

    return "input" if not error else "input input-error"
    # textarea
