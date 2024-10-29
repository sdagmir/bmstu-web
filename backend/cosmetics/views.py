from django.shortcuts import get_object_or_404
from datetime import datetime
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from rest_framework import status
from cosmetics.models import CosmeticOrder, OrderComponent, ChemicalElement
from django.db.models import Q
from cosmetics.serializers import *
from .minio import add_pic, delete_pic


SINGLETON_USER = User(id=1, username="admin")
SINGLETON_MANAGER = User(id=2, username="manager")


@api_view(['GET'])
def get_components_list(request):
    """
    Получение всех химических элементов
    """
    search_query = request.GET.get('component_title', '').lower()

    draft_order = CosmeticOrder.objects.filter(
        user_id=SINGLETON_USER.id, status=CosmeticOrder.STATUS_CHOICES[0][0]).first()

    filter_elements = ChemicalElement.objects.filter(
        title__istartswith=search_query)

    serializer = ComponentSerializer(filter_elements, many=True)

    return Response(
        {
            'elements': serializer.data,
            'count': draft_order.components.count() if draft_order else 0,
            'formulation_id': draft_order.id if draft_order else None
        },
        status=status.HTTP_200_OK
    )


class ChemicalComponent(APIView):
    """
    Класс CRUD операций над химическим элементом
    """
    model_class = ChemicalElement
    serializer_class = ComponentSerializer

    # Возвращает данные о химическом элементе
    def get(self, request, pk, format=None):
        component_data = get_object_or_404(self.model_class, pk=pk)
        serializer = self.serializer_class(component_data)
        return Response(serializer.data)

    # Добавляет новый химический элемент
    def post(self, request, format=None):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Изменение информации об элементе
    def put(self, request, pk, format=None):
        element = self.model_class.objects.filter(pk=pk).first()
        if element is None:
            return Response("Chemical element not found", status=status.HTTP_404_NOT_FOUND)
        serializer = self.serializer_class(
            element, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Удаление элемента вместе с изображением
    def delete(self, request, pk, format=None):
        element = get_object_or_404(self.model_class, pk=pk)
        if element.img_path:
            deletion_result = delete_pic(element.img_path)
            if 'error' in deletion_result:
                return Response(deletion_result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        element.delete()
        return Response({"message": "Элемент и его изображение успешно удалены."}, status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def update_element_image(request, pk):
    """
    Добавление или замена изображения для химического элемента по его ID.
    """
    element = get_object_or_404(ChemicalElement, pk=pk)

    image = request.FILES.get('image')
    if not image:
        return Response({"error": "Файл изображения не предоставлен."}, status=status.HTTP_400_BAD_REQUEST)

    if element.img_path:
        delete_pic(element.img_path)

    result = add_pic(element, image)

    if 'error' in result.data:
        return result

    element.img_path = f"http://localhost:9000/web-img/{element.id}.png"
    element.save()

    return Response({"message": "Изображение успешно добавлено/заменено."}, status=status.HTTP_200_OK)


@api_view(['POST'])
def post_component_to_formulation(request, pk):
    """
    Добавление компонента в состав косметического средства
    """
    component = ChemicalElement.objects.filter(pk=pk).first
    if component is None:
        return Response("Component not found", status=status.HTTP_404_NOT_FOUND)
    formulation_id = get_or_create_formulation(SINGLETON_USER.id)
    data = OrderComponent(order_id=formulation_id, chemical_element_id=pk)
    data.save()
    return Response(status=status.HTTP_200_OK)


def get_or_create_formulation(user_id):
    """
    Получение id косметического средства или создание нового при его отсутствии
    """
    old_formulation = CosmeticOrder.objects.filter(
        user_id=user_id, status=CosmeticOrder.STATUS_CHOICES[0][0]).first()

    if old_formulation is not None:
        return old_formulation.id

    new_formulation = CosmeticOrder(
        user_id=user_id, status=CosmeticOrder.STATUS_CHOICES[0][0])
    new_formulation.save()
    return new_formulation.id


@api_view(['GET'])
def get_created_formulations(request):
    """
    Получение списка сформированных косметических средств
    """
    status_filter = request.query_params.get("status")

    filters = ~Q(status=CosmeticOrder.STATUS_CHOICES[2][0])
    if status_filter is not None:
        filters &= Q(status=status_filter.upper())

    created_formulations = CosmeticOrder.objects.filter(
        filters).select_related("user")
    serializer = CreatedFormulationsSerializer(
        created_formulations, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_cosmetic_formulation(request, pk):
    """
    Получение информации о косметическом средстве по его ID
    """
    filters = Q(pk=pk) & ~Q(status=CosmeticOrder.STATUS_CHOICES[2][0])
    cosmetic_order = CosmeticOrder.objects.filter(filters).first()

    if cosmetic_order is None:
        return Response("CosmeticOrder not found", status=status.HTTP_404_NOT_FOUND)

    serializer = FullCosmeticFormulationSerializer(cosmetic_order)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT'])
def put_cosmetic_formulation(request, pk):
    """
    Изменение названия косметического средства
    """
    cosmetic_order = CosmeticOrder.objects.filter(
        id=pk, status=CosmeticOrder.STATUS_CHOICES[0][0]).first()
    if cosmetic_order is None:
        return Response("Косметическое средство не найдено", status=status.HTTP_404_NOT_FOUND)
    serializer = PutCosmeticFormulationSerializer(
        cosmetic_order, data=request.data, partial=True
    )
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
def form_cosmetic_formulation(request, pk):
    """
    Формирование косметического средства
    """
    cosmetic_order = CosmeticOrder.objects.filter(
        id=pk, status=1).first()
    if cosmetic_order is None:
        return Response("Косметическое средство не найдено", status=status.HTTP_404_NOT_FOUND)

    if cosmetic_order.name is None or cosmetic_order.name == "":
        return Response("Поле 'Название' должно быть заполнено", status=status.HTTP_400_BAD_REQUEST)

    if not are_valid_dosages(pk):
        return Response("Необходимо корректно ввести все дозировки химических элементов", status=status.HTTP_400_BAD_REQUEST)

    cosmetic_order.status = 2
    cosmetic_order.date_formation = datetime.now()
    cosmetic_order.save()

    serializer = CreatedFormulationsSerializer(cosmetic_order)
    return Response(serializer.data, status=status.HTTP_200_OK)


def are_valid_dosages(order_id):
    """
    Проверка: у всех компонентов заявки должна быть указана дозировка
    """
    order_components = OrderComponent.objects.filter(order_id=order_id)
    for component in order_components:
        if component.dosage is None or component.dosage <= 0:
            return False
    return True


@api_view(['PUT'])
def resolve_cosmetic_formulation(request, pk):
    """
    Закрытие заявки на косметическое средство модератором
    """
    cosmetic_order = CosmeticOrder.objects.filter(
        pk=pk, status=2).first()  # 2 - Сформировано
    if cosmetic_order is None:
        return Response("Косметическое средство не найдено или статус неверный", status=status.HTTP_404_NOT_FOUND)

    serializer = ResolveCosmeticFormulationSerializer(
        cosmetic_order, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    serializer.save()

    cosmetic_order.date_completion = datetime.now()
    cosmetic_order.manager = SINGLETON_MANAGER
    cosmetic_order.save()

    serializer = CreatedFormulationsSerializer(cosmetic_order)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['DELETE'])
def delete_cosmetic_formulation(request, pk):
    """
    Удаление косметического средства
    """
    cosmetic_order = CosmeticOrder.objects.filter(id=pk,
                                                  status=1).first()
    if cosmetic_order is None:
        return Response("CosmeticOrder not found", status=status.HTTP_404_NOT_FOUND)

    cosmetic_order.status = 3
    cosmetic_order.save()
    return Response(status=status.HTTP_200_OK)


@api_view(['PUT'])
def put_chemical_element_in_formulation(request, formulation_pk, component_pk):
    """
    Изменение данных о химическом элементе в составе косметического средства
    """
    element_in_order = OrderComponent.objects.filter(
        order_id=formulation_pk, chemical_element_id=component_pk).first()
    if element_in_order is None:
        return Response("Компнонент косметического средства не найден", status=status.HTTP_404_NOT_FOUND)

    serializer = OrderComponentSerializer(
        element_in_order, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_chemical_element_in_formulation(request, formulation_pk, component_pk):
    """
    Удаление химического элемента из состава косметического средства
    """
    element_in_formulation = OrderComponent.objects.filter(
        order_id=formulation_pk, chemical_element_id=component_pk).first()
    if element_in_formulation is None:
        return Response("Компонент не найден", status=status.HTTP_404_NOT_FOUND)

    element_in_formulation.delete()
    return Response(status=status.HTTP_200_OK)


@api_view(['POST'])
def create_user(request):
    """
    Создание пользователя
    """
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def login_user(request):
    """
    Вход
    """
    username = request.POST.get('username')
    password = request.POST.get('password')
    user = authenticate(username=username, password=password)
    if user is not None:
        token, created = Token.objects.get_or_create(user=user)
        return Response({'token': token.key}, status=status.HTTP_200_OK)
    return Response({'error': 'Invalid Credentials'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def logout_user(request):
    """
    Выход
    """
    request.auth.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['PUT'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_user(request):
    """
    Обновление данных пользователя
    """
    user = request.user
    serializer = UserSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
