from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.contrib.admin.views.decorators import staff_member_required


@method_decorator(staff_member_required, name='dispatch')
class ContentGeneratorWidgetView(TemplateView):
    """Отображает виджет генерации контента в айфрейме без передачи GET-параметров в контекст."""
    template_name = 'custom_admin/content_generator_widget.html'
