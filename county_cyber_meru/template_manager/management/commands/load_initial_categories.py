from django.core.management.base import BaseCommand
from template_manager.models import Category

class Command(BaseCommand):
    help = 'Load initial categories for the template system'

    def handle(self, *args, **options):
        categories = [
            {'name': 'Business Cards', 'description': 'Professional business card templates'},
            {'name': 'Wedding Cards', 'description': 'Elegant wedding invitation templates'},
            {'name': 'Flyers', 'description': 'Promotional flyer templates'},
            {'name': 'Posters', 'description': 'Event and promotional posters'},
            {'name': 'Certificates', 'description': 'Award and recognition certificates'},
            {'name': 'Invoices', 'description': 'Professional invoice templates'},
            {'name': 'Letterheads', 'description': 'Company letterhead templates'},
            {'name': 'Labels', 'description': 'Product and shipping labels'},
            {'name': 'Banners', 'description': 'Large format banner templates'},
            {'name': 'Social Media', 'description': 'Social media post templates'},
        ]

        for cat_data in categories:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {category.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Category already exists: {category.name}'))

        self.stdout.write(self.style.SUCCESS('Successfully loaded initial categories'))