from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Check current database connection'

    def handle(self, *args, **kwargs):
        db_engine = connection.settings_dict['ENGINE']
        db_name = connection.settings_dict['NAME']
        self.stdout.write(self.style.SUCCESS(f'--- Database Connection Info ---'))
        self.stdout.write(f'Current Engine: {db_engine}')
        self.stdout.write(f'Current DB Name: {db_name}')
        self.stdout.write(self.style.SUCCESS(f'-------------------------------'))