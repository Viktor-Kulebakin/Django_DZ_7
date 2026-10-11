from rest_framework import serializers
from django.contrib.auth.models import User
from .models import EmployeeProfile, EmployeeImage, Skill, EmployeeSkill

class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'name']

class EmployeeSkillSerializer(serializers.ModelSerializer):
    """Сериализатор промежуточной таблицы для вывода уровня навыка"""
    id = serializers.ReadOnlyField(source='skill.id')
    name = serializers.ReadOnlyField(source='skill.name')

    class Meta:
        model = EmployeeSkill
        fields = ['id', 'name', 'level']

class EmployeeImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeImage
        fields = ['id', 'image', 'position']

class EmployeeProfileSerializer(serializers.ModelSerializer):
    # Используем related_name='images' из вашей модели
    images = EmployeeImageSerializer(many=True, read_only=True)
    # Выводим навыки в подробном формате (название + уровень)
    skills_detail = EmployeeSkillSerializer(source='employeeskill_set', many=True, read_only=True)

    class Meta:
        model = EmployeeProfile
        fields = [
            'id', 'user', 'first_name', 'last_name', 'middle_name', 
            'gender', 'role', 'desk_number', 'date_joined', 
            'description', 'images', 'skills_detail'
        ]
        
    def validate(self, attrs):
        # DRF автоматически вызывает clean() моделей, если вsave() прописан full_clean(),
        # но перехват ValidationError на уровне сериализатора делает ответы красивыми.
        return attrs
