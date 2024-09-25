# Generated by Django 5.1.1 on 2024-09-25 13:14

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ChemicalElement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=30, verbose_name='Название')),
                ('img_path', models.CharField(max_length=255, verbose_name='Путь к изображению')),
                ('volume', models.FloatField(verbose_name='Объем')),
                ('unit', models.CharField(max_length=10, verbose_name='Единица измерения')),
                ('price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Цена')),
                ('short_description', models.CharField(max_length=255, verbose_name='Краткое описание')),
                ('description', models.TextField(verbose_name='Полное описание')),
            ],
            options={
                'verbose_name': 'Химический элемент',
                'verbose_name_plural': 'Химические элементы',
            },
        ),
        migrations.CreateModel(
            name='CosmeticOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.IntegerField(choices=[(1, 'Черновик'), (2, 'Сформировано'), (3, 'Удалено'), (4, 'Завершено'), (5, 'Отклонено')], default=1, verbose_name='Статус')),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='orders', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Косметическая заявка',
                'verbose_name_plural': 'Косметические заявки',
            },
        ),
        migrations.CreateModel(
            name='OrderComponent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dosage', models.FloatField(verbose_name='Дозировка')),
                ('chemical_element', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cosmetics.chemicalelement', verbose_name='Химический элемент')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='components', to='cosmetics.cosmeticorder')),
            ],
            options={
                'verbose_name': 'Компонент заявки',
                'verbose_name_plural': 'Компоненты заявки',
            },
        ),
    ]
