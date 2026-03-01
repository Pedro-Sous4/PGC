from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
    ('core', '0007_empresapagadora')
    ]


    operations = [
        migrations.AddField(
            model_name='credor',
            name='nome_normalizado',
            field=models.CharField(
                max_length=255,
                default='',
                editable=False,
                db_index=True
            ),
        ),
    ]
