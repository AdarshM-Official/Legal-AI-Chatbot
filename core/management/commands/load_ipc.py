import os
import pandas as pd
from django.core.management.base import BaseCommand
from core.models import LegalDocument

class Command(BaseCommand):
    help = 'Load IPC dataset from CSV into Django Database'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Absolute path to the IPC CSV file')

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        if not os.path.exists(csv_path):
            self.stderr.write(self.style.ERROR(f"File not found: {csv_path}"))
            return

        self.stdout.write(self.style.SUCCESS(f'Reading CSV: {csv_path}'))
        df = pd.read_csv(csv_path)
        
        col_section = next((c for c in df.columns if 'section' in c.lower()), None)
        col_desc = next((c for c in df.columns if 'desc' in c.lower() or 'offense' in c.lower() or 'detail' in c.lower()), None)

        if not col_section or not col_desc:
            self.stderr.write(self.style.ERROR("Could not automatically map columns."))
            return

        count = 0
        for index, row in df.iterrows():
            section_val = str(row[col_section])
            description = str(row.get('Description', ''))
            offense = str(row.get('Offense', ''))
            punishment = str(row.get('Punishment', ''))
            
            sec_num = section_val.split('_')[-1] if '_' in section_val else section_val
            title = f"Section {sec_num}"
            
            full_content = f"Offense: {offense}\n\nPunishment: {punishment}\n\nDescription: {description}"
            
            doc, created = LegalDocument.objects.get_or_create(
                title=title,
                defaults={
                    'doc_type': 'Statute',
                    'summary': offense if offense else description[:200],
                    'content': full_content
                }
            )
            count += 1
            if count % 100 == 0:
                self.stdout.write(f"Processed {count} records...")
                    
        self.stdout.write(self.style.SUCCESS(f"Successfully processed {count} records into DB!"))
