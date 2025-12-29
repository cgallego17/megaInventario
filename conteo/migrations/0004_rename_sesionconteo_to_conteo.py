# Generated manually
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('conteo', '0003_rename_sesion_to_conteo'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='SesionConteo',
            new_name='Conteo',
        ),
    ]
