import operator
from django.forms.widgets import Media
from cms.utils import get_language_from_request
from cms.utils.moderator import get_cmsplugin_queryset
from cms.conf import settings

def _get_plugins_recursively(request, obj, placeholder, lang):
    """
    Get plugins for obj, language and placeholder.
    If no plugins are found and the placeholder config in CMS_PLACEHOLDER_CONF
    contains "parent_plugins" with a True value, return the plugins for
    the parent pages recursively. That is plugins are searched until a page
    with plugins is found or the root page is found.
    """
    if not obj:
        return None

    recurse = False
    if settings.CMS_PLACEHOLDER_CONF and placeholder in settings.CMS_PLACEHOLDER_CONF:
        recurse = settings.CMS_PLACEHOLDER_CONF[placeholder].get("parent_plugins")

    while True:
        plugins = get_cmsplugin_queryset(request).filter(page=obj, language=lang, parent__isnull=True, placeholder__iexact=placeholder)
        if not recurse:
            break
        if not obj.parent or plugins.count():
            break
        obj = obj.parent
    return plugins.order_by('placeholder', 'position').select_related()

def get_plugins(request, obj, placeholder, lang=None):
    if not obj:
        return []
    lang = lang or get_language_from_request(request)
    cache_key = "_%s_%s_plugins_cache" % (lang, placeholder)
    if not hasattr(obj, cache_key):
        setattr(obj, cache_key, _get_plugins_recursively(request, obj, placeholder, lang))
    return getattr(obj, cache_key)

def get_plugin_media(request, plugin):
    instance, plugin = plugin.get_plugin_instance()
    return plugin.get_plugin_media(request, instance)

def get_plugins_media(request, obj):
    lang = get_language_from_request(request)
    if not obj:
        # current page is unknown
        return []
    if not hasattr(obj, '_%s_plugins_media_cache' % lang):
        plugins = get_plugins(request, obj, lang=lang)
        media_classes = [get_plugin_media(request, plugin) for plugin in plugins]
        if media_classes:
            setattr(obj, '_%s_plugins_media_cache' % lang, reduce(operator.add, media_classes))
        else:
            setattr(obj, '_%s_plugins_media_cache' % lang,  Media())
    return getattr(obj, '_%s_plugins_media_cache' % lang)