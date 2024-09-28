# Generated by Django 5.1.1 on 2024-09-28 13:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cosmetics', '0001_initial'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='ordercomponent',
            unique_together={('order', 'chemical_element')},
        ),
        migrations.AlterModelTable(
            name='chemicalelement',
            table='chemical_element',
        ),
        migrations.AlterModelTable(
            name='cosmeticorder',
            table='cosmetic_order',
        ),
        migrations.AlterModelTable(
            name='ordercomponent',
            table='order_component',
        ),
    ]
