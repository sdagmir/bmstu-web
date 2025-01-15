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
    formulation_chemist = serializers.CharField(
        source='formulation_chemist.username')
    technologist = serializers.CharField(
        source='technologist.username', allow_null=True)

    class Meta:
        model = CosmeticOrder
        fields = [
            'id', 'formulation_chemist', 'technologist', 'status', 'date_created', 'name',
            'date_formation', 'date_completion', 'adverse_effects_count'
        ]


class OrderComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderComponent
        fields = ['dosage']


class PutCosmeticFormulationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CosmeticOrder
        fields = '__all__'
        read_only_fields = [
            "pk", "date_created", "date_formation", "date_completion",
            "formulation_chemist", "technologist", "status", "components"
        ]


class ResolveCosmeticFormulationSerializer(serializers.ModelSerializer):
    def validate(self, data):
        if data.get('status') not in (4, 5):  # 4 - Завершено, 5 - Отклонено
            raise serializers.ValidationError("Invalid status")
        return data

    class Meta:
        model = CosmeticOrder
        fields = '__all__'
        read_only_fields = [
            "pk", "date_created", "date_formation", "date_completion",
            "formulation_chemist", "technologist", "name", "adverse_effects_count"
        ]


class ChemicalElementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChemicalElement
        fields = ['pk', 'title', 'img_path', 'volume', 'unit', 'price']


class FormulationComponentSerializer(serializers.ModelSerializer):
    chemical_element = ChemicalElementSerializer()

    class Meta:
        model = OrderComponent
        fields = ['chemical_element', 'dosage']


class FullCosmeticFormulationSerializer(serializers.ModelSerializer):
    components = FormulationComponentSerializer(many=True)
    formulation_chemist = serializers.CharField(
        source='formulation_chemist.username')
    technologist = serializers.CharField(
        source='technologist.username', allow_null=True)

    class Meta:
        model = CosmeticOrder
        fields = [
            'pk', 'formulation_chemist', 'technologist', 'date_created', 'status', 'name',
            'date_formation', 'date_completion', 'adverse_effects_count', 'components'
        ]


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
