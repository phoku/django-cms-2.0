from cms.utils.moderator import get_cmsplugin_queryset
from cms.utils import get_language_from_request
from cms import settings
from django.conf import settings as django_settings
from cms.plugin_pool import plugin_pool
from cms.plugins.utils import get_plugins
from django.template.defaultfilters import title
from django.template.loader import render_to_string
from cms.plugin_rendering import render_plugins
import copy

def render_plugins_for_context(placeholder_name, page, context_to_copy, width=None):
    """
    renders plugins for the given named placedholder and page using shallow copies of the 
    given context
    """
    context = copy.copy(context_to_copy) 
    l = get_language_from_request(context['request'])
    request = context['request']
    plugins = get_plugins(request, page, placeholder_name)
    template = page.template
    extra_context = settings.CMS_PLACEHOLDER_CONF.get("%s %s" % (template, placeholder_name), {}).get("extra_context", None)
    if not extra_context:
        extra_context = settings.CMS_PLACEHOLDER_CONF.get(placeholder_name, {}).get("extra_context", None)
    if extra_context:
        context.update(extra_context)
    if width:
        # this may overwrite previously defined key [width] from settings.CMS_PLACEHOLDER_CONF
        try:
            width = int(width)
            context.update({'width': width,})
        except ValueError:
            pass
    c = []
    edit = False
    if ("edit" in request.GET or request.session.get("cms_edit", False)) and \
            'cms.middleware.toolbar.ToolbarMiddleware' in django_settings.MIDDLEWARE_CLASSES and \
            request.user.is_staff and request.user.is_authenticated() and \
            page.has_change_permission(request):
        edit = True
    if edit:
        installed_plugins = plugin_pool.get_all_plugins(placeholder_name, page)
        name = settings.CMS_PLACEHOLDER_CONF.get("%s %s" % (template, placeholder_name), {}).get("name", None)
        if not name:
            name = settings.CMS_PLACEHOLDER_CONF.get(placeholder_name, {}).get("name", None)
        if not name:
            name = placeholder_name
        name = title(name)
        c.append(render_to_string("cms/toolbar/add_plugins.html", {'installed_plugins':installed_plugins,
                                                               'language':l,
                                                               'placeholder_label':name,
                                                               'placeholder_name':placeholder_name,
                                                               'page':page,
                                                               }))
        from cms.middleware.toolbar import toolbar_plugin_processor
        processors = (toolbar_plugin_processor,)
    else:
        processors = None 
        
    c.extend(render_plugins(plugins, context, placeholder_name, processors))
    
    return "".join(c)
