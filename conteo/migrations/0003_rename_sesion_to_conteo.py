# Generated manually
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('conteo', '0002_alter_sesionconteo_options_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='itemconteo',
            old_name='sesion',
            new_name='conteo',
        ),
    ]

