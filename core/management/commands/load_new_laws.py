import os
import json
from django.core.management.base import BaseCommand
from core.models import LegalDocument
from huggingface_hub import hf_hub_download

class Command(BaseCommand):
    help = 'Load BNS, BNSS, BSA dataset from HuggingFace into Django DB'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Downloading JSON from HuggingFace Hub...'))
        file_path = hf_hub_download(repo_id="GSMS-B/indian-legal-sections-bns-bnss-bsa-2023", repo_type="dataset", filename="bns_bnss_bsa_sections.json")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        self.stdout.write(self.style.SUCCESS(f'Loaded {len(data)} records from JSON.'))

        count = 0
        for item in data:
            act = item.get('act', '').strip()
            doc_type = 'BNS'
            if 'BNSS' in act:
                doc_type = 'BNSS'
            elif 'BSA' in act:
                doc_type = 'BSA'
                
            title = f"Section {item.get('section_number', '')} ({doc_type})"
            full_text = item.get('text', '')
            summary = item.get('section_title', '')
            
            doc, created = LegalDocument.objects.get_or_create(
                title=title,
                doc_type=doc_type,
                defaults={
                    'summary': summary if summary else full_text[:200],
                    'content': full_text
                }
            )
            count += 1
            if count % 200 == 0:
                self.stdout.write(f"Processed {count} records...")
                    
        self.stdout.write(self.style.SUCCESS(f"Successfully processed {count} records into DB!"))
