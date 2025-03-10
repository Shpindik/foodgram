import json

from django.core.management.base import BaseCommand

from ...models import Tag


class Command(BaseCommand):
    help = 'Загрузить в базу данных список тегов из json.'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Путь к json файлу.')

    def handle(self, *args, **options):
        json_file_path = options['json_file']
        try:
            with open(json_file_path, encoding='utf-8') as file:
                data = json.load(file)
            tags = [Tag(name=item["name"], slug=item["slug"]) for item in data]
            Tag.objects.bulk_create(tags)
            self.stdout.write(self.style.SUCCESS(
                f'Загружено тегов: {len(tags)}'))
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(f'Файл не найден: {json_file_path}'))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка при загрузке: {str(e)}'))
