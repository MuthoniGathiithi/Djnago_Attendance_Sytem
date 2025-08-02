from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

class Command(BaseCommand):
    help = 'Clean up all test users except the main admin account'

    def handle(self, *args, **options):
        # Get all users except the main admin
        main_admin_email = getattr(settings, 'ADMIN_EMAIL', 'admin@example.com')
        users_to_delete = User.objects.exclude(email=main_admin_email)
        
        # Count users to be deleted
        count = users_to_delete.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No test users to delete.'))
            return
            
        # Ask for confirmation
        confirm = input(f'This will delete {count} users. Are you sure? (yes/no): ')
        if confirm.lower() != 'yes':
            self.stdout.write(self.style.WARNING('Operation cancelled.'))
            return
            
        # Delete the users
        deleted_count, _ = users_to_delete.delete()
        self.stdout.write(
            self.style.SUCCESS(f'Successfully deleted {deleted_count} test users.')
        )
