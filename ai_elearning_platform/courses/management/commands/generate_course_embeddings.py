from django.core.management.base import BaseCommand
from courses.models import Course
from core.ai_utils import generate_embedding # Import your utility
import time

class Command(BaseCommand):
    help = 'Generates or updates embeddings for all courses using OpenAI.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-update',
            action='store_true',
            help='Force update embeddings even if they already exist.',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to generate course embeddings...'))
        
        courses_to_process = Course.objects.all()
        if not options['force_update']:
            courses_to_process = courses_to_process.filter(embedding__isnull=True)

        if not courses_to_process.exists():
            self.stdout.write(self.style.SUCCESS('No courses found needing new embeddings (or --force-update not used).'))
            return

        updated_count = 0
        failed_count = 0

        for course in courses_to_process:
            self.stdout.write(f"Processing course: '{course.title}' (ID: {course.id})")
            content_to_embed = course.get_content_for_embedding()
            if not content_to_embed:
                self.stdout.write(self.style.WARNING(f"  - No content to embed for course '{course.title}'. Skipping."))
                continue

            embedding_vector = generate_embedding(content_to_embed)

            if embedding_vector:
                course.embedding = embedding_vector
                course.save(update_fields=['embedding']) # Only update the embedding field
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f"  - Embedding generated and saved for '{course.title}'."))
            else:
                failed_count += 1
                self.stdout.write(self.style.ERROR(f"  - Failed to generate embedding for '{course.title}'."))
            
            # OpenAI API has rate limits. Add a small delay.
            # For text-embedding-ada-002, free tier is 3 RPM, paid is 3000 RPM. Adjust as needed.
            time.sleep(1) # Adjust based on your API tier and number of courses. 
                           # For many courses and free tier, this might need to be 20s.

        self.stdout.write(self.style.SUCCESS(f'Finished generating embeddings.'))
        self.stdout.write(self.style.SUCCESS(f'Successfully updated: {updated_count} courses.'))
        if failed_count > 0:
            self.stdout.write(self.style.WARNING(f'Failed to update: {failed_count} courses.'))