# Generated by Django 5.1.1 on 2024-10-09 16:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cosmetics', '0004_add_field_manager'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chemicalelement',
            name='img_path',
            field=models.CharField(default='', max_length=255, verbose_name='Путь к изображению'),
        ),
    ]
