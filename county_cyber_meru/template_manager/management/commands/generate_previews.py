from django.core.management.base import BaseCommand
from template_manager.models import TemplateDocument
from template_manager.utils import generate_template_preview

class Command(BaseCommand):
    help = 'Generate previews for all existing templates'

    def handle(self, *args, **options):
        templates = TemplateDocument.objects.all()
        
        for template in templates:
            self.stdout.write(f'Generating preview for: {template.title}')
            preview_path = generate_template_preview(template)
            if preview_path:
                template.preview_image = preview_path
                template.save()
                self.stdout.write(self.style.SUCCESS(f'✓ Preview generated for {template.title}'))
            else:
                self.stdout.write(self.style.WARNING(f'✗ Could not generate preview for {template.title}'))