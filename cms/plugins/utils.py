import operator
from django.forms.widgets import Media
from cms.utils import get_language_from_request
from cms.utils.moderator import get_cmsplugin_queryset
from cms.conf import settings

def get_plugins_recursively(request, obj, placeholder, lang):
    """
    Get plugins for obj, language and placeholder.
    If no plugins are found and the placeholder config in CMS_PLACEHOLDER_CONF
    contains "parent_plugins" with a True value, return the plugins for
    the parent pages recursively. That is plugins are searched until a page
    with plugins is found or the root page is found.
    """
    if not obj:
        return []

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
    """
    Get all plugins for a page, placeholder and language.

    Internally this will cache the plugin results for all placeholders,
    so that ideally only one query will be made for all calls to this.
    
    In case a placeholder hasn't any plugins defined on the page
    get_plugins_recursively is used.

    Returns an iterable with the plugins.
    """
    if not obj:
        return []
    lang = lang or get_language_from_request(request)

    # STAGE ONE - GET AND CACHE ALL PLACEHOLDERS
    cache_key = "_%s_plugins_cache" % lang
    if not hasattr(obj, cache_key):
        plugins = get_cmsplugin_queryset(request).filter(page=obj, language=lang, parent__isnull=True)
        plugins = plugins.order_by('placeholder', 'position').select_related()
        cache_dict = {}
        for plugin in plugins:
            if plugin.placeholder not in cache_dict:
                cache_dict[plugin.placeholder] = []
            cache_dict[plugin.placeholder].append(plugin)
        setattr(obj, cache_key, cache_dict)
    cache_dict = getattr(obj, cache_key)

    # STAGE TWO GET AND CACHE FOR THIS PLACEHOLDER
    # WITH POSSIBLE RECURSION.
    placeholder_cache_key = "_%s_placeholder_%s_plugins_cache" % (lang, placeholder)
    if placeholder in cache_dict:
        setattr(obj, placeholder_cache_key, cache_dict[placeholder])

    if not hasattr(obj, placeholder_cache_key):
        # NOTE: We pass obj.parent since we already _know_ that the current page doesn't
        #       provide the plugins for this placeholder.
        setattr(obj, placeholder_cache_key, get_plugins_recursively(request, obj.parent, placeholder, lang))
    return getattr(obj, placeholder_cache_key)

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