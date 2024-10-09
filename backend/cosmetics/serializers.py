from rest_framework import serializers
from django.contrib.auth.models import User

from .models import CosmeticOrder, OrderComponent, ChemicalElement


class ComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChemicalElement
        fields = '__all__'


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


class CreatedFormulationsSerializer(serializers.ModelSerializer):
    client = ClientSerializer()

    class Meta:
        model = CosmeticOrder
        fields = '__all__'


class OrderComponentSerializer(serializers.ModelField):
    class Meta:
        model = OrderComponent
        fields = '__all__'


class PutCosmeticFormulationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CosmeticOrder
        fields = '__all__'
        read_only_fields = ["pk", "date_created", "date_formation",
                            "date_completion", "user", "manager", "status"]


class ResolveCosmeticFormulationSerializer(serializers.ModelSerializer):
    def validate(self, data):
        if data.get('status') not in (2, 3):  # 2 - Завершено, 3 - Отклонено
            raise serializers.ValidationError("Invalid status")
        return data

    class Meta:
        model = CosmeticOrder
        fields = '__all__'
        read_only_fields = ["pk", "date_created", "date_formation",
                            "date_completion", "user", "manager", "category"]

# Сериализатор для ChemicalElement


class ChemicalElementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChemicalElement
        fields = ['pk', 'title', 'img_path', 'volume', 'unit',
                  'price', 'short_description', 'description']


# Сериализатор для компонента в заявке (OrderComponent)
class FormulationComponentSerializer(serializers.ModelSerializer):
    chemical_element = ChemicalElementSerializer()

    class Meta:
        model = OrderComponent
        fields = ['chemical_element', 'dosage']


# Полный сериализатор для заявки (CosmeticOrder)
class FullCosmeticFormulationSerializer(serializers.ModelSerializer):
    components = FormulationComponentSerializer(source='components', many=True)

    class Meta:
        model = CosmeticOrder
        fields = ['pk', 'date_created', 'status', 'category',
                  'manager', 'date_formation', 'date_completion', 'components']


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            email=validated_data.get('email', '')
        )
        return user

    def update(self, instance, validated_data):
        instance.email = validated_data.get('email', instance.email)
        if 'password' in validated_data:
            instance.set_password(validated_data['password'])
        instance.save()
        return instance
