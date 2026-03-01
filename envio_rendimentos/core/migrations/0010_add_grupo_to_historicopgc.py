# Generated manually: add 'grupo' FK to HistoricoPGC and backfill from Credor
from django.db import migrations, models
import django.db.models.deletion


def backfill_grupo_from_credor(apps, schema_editor):
    Historico = apps.get_model('core', 'HistoricoPGC')
    Credor = apps.get_model('core', 'Credor')
    for h in Historico.objects.filter(grupo__isnull=True):
        try:
            if h.credor_id:
                c = Credor.objects.filter(pk=h.credor_id).only('grupo').first()
                if c and c.grupo_id:
                    h.grupo_id = c.grupo_id
                    h.save(update_fields=['grupo'])
        except Exception:
            # be conservative: skip on any error
            continue


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_emaillog'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicopgc',
            name='grupo',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='historicos', to='core.grupo'),
        ),
        migrations.RunPython(backfill_grupo_from_credor, migrations.RunPython.noop),
    ]
