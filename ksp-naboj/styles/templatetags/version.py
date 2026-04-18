from django import template
import importlib

register = template.Library()

ksp_naboj = importlib.import_module("ksp-naboj")
VERSION = ksp_naboj.VERSION


@register.simple_tag
def app_version():
    return VERSION
