# Generated by Django 5.2.1 on 2025-06-02 22:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0008_question_explanation_question_points'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='preferred_categories',
            field=models.ManyToManyField(blank=True, related_name='user_profiles_preferring', to='courses.coursecategory', verbose_name='Preferred Learning Categories'),
        ),
    ]
