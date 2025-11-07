from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ("HCUser", "0005_alter_homechoiceuser_managers"),
    ]

    operations = [
        migrations.AddField(
            model_name="homechoiceuser",
            name="contact_number",
            field=models.CharField(
                blank=True,
                help_text="Nambari ya mawasiliano ya Kenya inayoanza na +254.",
                max_length=13,
                null=True,
                validators=[
                    django.core.validators.RegexValidator(
                        message="Nambari ya mawasiliano lazima ianze na +254 na iwe na jumla ya tarakimu 13.",
                        regex="^\\+254\\d{9}$",
                    )
                ],
            ),
        ),
    ]

