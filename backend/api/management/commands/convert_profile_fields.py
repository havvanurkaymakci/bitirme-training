# api/management/commands/convert_profile_fields.py

from django.core.management.base import BaseCommand
from api.models import Profile

class Command(BaseCommand):
    help = 'Convert existing text fields to JSON fields for medical_conditions, allergies, and dietary_preferences'

    def handle(self, *args, **options):
        self.stdout.write('Starting profile field conversion...')
        
        profiles = Profile.objects.all()
        converted_count = 0
        
        for profile in profiles:
            updated = False
            
            # Convert medical_conditions from text to list
            if isinstance(profile.medical_conditions, str) and profile.medical_conditions:
                # Split by comma and clean up
                conditions_list = [condition.strip() for condition in profile.medical_conditions.split(',') if condition.strip()]
                profile.medical_conditions = conditions_list
                updated = True
                self.stdout.write(f'  Medical conditions converted for {profile.full_name}: {conditions_list}')
            elif profile.medical_conditions is None:
                profile.medical_conditions = []
                updated = True
            
            # Convert allergies from text to list
            if isinstance(profile.allergies, str) and profile.allergies:
                allergies_list = [allergy.strip() for allergy in profile.allergies.split(',') if allergy.strip()]
                profile.allergies = allergies_list
                updated = True
                self.stdout.write(f'  Allergies converted for {profile.full_name}: {allergies_list}')
            elif profile.allergies is None:
                profile.allergies = []
                updated = True
            
            # Convert dietary_preferences from text to list
            if isinstance(profile.dietary_preferences, str) and profile.dietary_preferences:
                preferences_list = [pref.strip() for pref in profile.dietary_preferences.split(',') if pref.strip()]
                profile.dietary_preferences = preferences_list
                updated = True
                self.stdout.write(f'  Dietary preferences converted for {profile.full_name}: {preferences_list}')
            elif profile.dietary_preferences is None:
                profile.dietary_preferences = []
                updated = True
            
            if updated:
                profile.save()
                converted_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Successfully updated profile for {profile.full_name}')
                )
        
        if converted_count == 0:
            self.stdout.write(
                self.style.WARNING('No profiles needed conversion.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully converted {converted_count} profiles!')
            )