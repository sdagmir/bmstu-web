from django.shortcuts import get_object_or_404
from datetime import datetime
from dateutil.parser import parse
import uuid
import random
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import authenticate
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.decorators import parser_classes
from cosmetics.models import CosmeticOrder, OrderComponent, ChemicalElement
from django.db.models import Q
from cosmetics.serializers import *
from .minio import add_pic, delete_pic
from .auth import AuthBySessionID, AuthBySessionIDIfExists, IsAuth, IsManagerAuth
from .redis import session_storage
import requests

ASYNC_SERVICE_URL = "http://localhost:8081/calculate"


@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter(
            name='title',
            in_=openapi.IN_QUERY,
            description='Фильтр по названию химического элемента (начинается с)',
            type=openapi.TYPE_STRING,
            required=False
        )
    ],
    responses={
        200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'elements': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(
                                type=openapi.TYPE_INTEGER,
                                description='Уникальный идентификатор элемента'
                            ),
                            'title': openapi.Schema(
                                type=openapi.TYPE_STRING,
                                description='Название химического элемента'
                            ),
                            'img_path': openapi.Schema(
                                type=openapi.TYPE_STRING,
                                description='Путь к изображению элемента'
                            ),
                            'volume': openapi.Schema(
                                type=openapi.TYPE_INTEGER,
                                description='Объем химического элемента'
                            ),
                            'unit': openapi.Schema(
                                type=openapi.TYPE_STRING,
                                description='Единица измерения объема'
                            ),
                            'price': openapi.Schema(
                                type=openapi.TYPE_STRING,
                                description='Цена химического элемента'
                            ),
                            'short_description': openapi.Schema(
                                type=openapi.TYPE_STRING,
                                description='Краткое описание химического элемента'
                            ),
                            'description': openapi.Schema(
                                type=openapi.TYPE_STRING,
                                description='Полное описание химического элемента'
                            ),
                        }
                    )
                ),
                'count': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='Количество элементов в корзине'
                ),
                'formulation_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='ID черновика заявки, если существует'
                ),
            },
        ),
    },
)
@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([AuthBySessionIDIfExists])
def get_components_list(request):
    """
    Получение всех химических элементов с пагинацией
    """
    user = request.user

    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 30))

    search_query = request.GET.get('title', '')
    if not search_query:
        filter_elements = ChemicalElement.objects.all()
    else:
        filter_elements = ChemicalElement.objects.filter(
            title=search_query
        )

    total_count = filter_elements.count()

    paginator = PageNumberPagination()
    paginator.page_size = page_size
    paginated_elements = paginator.paginate_queryset(filter_elements, request)

    items_in_cart = 0
    draft_order = None
    if user is not None:
        draft_order = CosmeticOrder.objects.filter(
            formulation_chemist_id=user.pk,
            status=CosmeticOrder.STATUS_CHOICES[0][0]
        ).first()

        if draft_order is not None:
            items_in_cart = draft_order.components.count()

    serializer = ComponentSerializer(paginated_elements, many=True)

    return paginator.get_paginated_response({
        'elements': serializer.data,
        'items_in_cart': items_in_cart,
        'formulation_id': draft_order.id if draft_order else None,
        'total_count': total_count
    })


class ChemicalComponent(APIView):
    """
    Класс CRUD операций над химическим элементом
    """
    model_class = ChemicalElement
    serializer_class = ComponentSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsManagerAuth()]

    @swagger_auto_schema(
        operation_description="Получение данных о химическом элементе по его ID",
        responses={
            200: openapi.Response(
                description="Успешно",
                schema=ComponentSerializer()
            ),
            404: openapi.Response(description="Химический элемент не найден"),
        }
    )
    def get(self, request, pk, format=None):
        component_data = get_object_or_404(self.model_class, pk=pk)
        serializer = self.serializer_class(component_data)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Добавление нового химического элемента",
        request_body=ComponentSerializer,
        responses={
            201: openapi.Response(description="Создан", schema=ComponentSerializer()),
            400: openapi.Response(description="Ошибка валидации данных"),
        }
    )
    def post(self, request, format=None):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_description="Изменение данных о химическом элементе",
        request_body=ComponentSerializer,
        responses={
            200: openapi.Response(description="Успешно", schema=ComponentSerializer()),
            404: openapi.Response(description="Элемент не найден"),
            400: openapi.Response(description="Ошибка валидации данных"),
        }
    )
    def put(self, request, pk, format=None):
        element = self.model_class.objects.filter(pk=pk).first()
        if element is None:
            return Response("Химический элемент не найден", status=status.HTTP_404_NOT_FOUND)
        serializer = self.serializer_class(
            element, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_description="Удаление химического элемента и его изображения",
        responses={
            204: openapi.Response(description="Элемент удален"),
            404: openapi.Response(description="Элемент не найден"),
            500: openapi.Response(description="Ошибка удаления изображения"),
        }
    )
    def delete(self, request, pk, format=None):
        element = get_object_or_404(self.model_class, pk=pk)
        if element.img_path:
            deletion_result = delete_pic(element.img_path)
            if 'error' in deletion_result:
                return Response(deletion_result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        element.delete()
        return Response({"message": "Элемент и его изображение успешно удалены."}, status=status.HTTP_204_NO_CONTENT)


# Замена/добавление изображения
@swagger_auto_schema(
    method='post',
    operation_summary="Добавление или замена изображения для элемента",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'image': openapi.Schema(type=openapi.TYPE_FILE, description="Файл изображения")
        }
    ),
    responses={
        200: "Изображение успешно добавлено/заменено",
        400: "Файл изображения не предоставлен",
        404: "Химический элемент не найден"
    }
)
@api_view(['POST'])
@permission_classes([IsManagerAuth])
def update_element_image(request, pk):
    element = get_object_or_404(ChemicalElement, pk=pk)
    image = request.FILES.get('image')
    if not image:
        return Response({"error": "Файл изображения не предоставлен."}, status=status.HTTP_400_BAD_REQUEST)

    if element.img_path:
        delete_pic(element.img_path)

    result = add_pic(element, image)
    if 'error' in result.data:
        return result

    element.img_path = f"/web-img/{element.id}.png"
    element.save()

    return Response({"message": "Изображение успешно добавлено/заменено."}, status=status.HTTP_200_OK)


# Добавление компонента в состав
@swagger_auto_schema(
    method='post',
    operation_summary="Добавление химического элемента в состав",
    responses={
        200: "Компонент успешно добавлен",
        404: "Химический элемент не найден"
    }
)
@api_view(['POST'])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def post_component_to_formulation(request, pk):
    component = ChemicalElement.objects.filter(pk=pk).first()
    if not component:
        return Response("Химический элемент не найден", status=status.HTTP_404_NOT_FOUND)

    formulation_id = get_or_create_formulation(request.user.id)
    data = OrderComponent(order_id=formulation_id, chemical_element_id=pk)
    data.save()
    return Response(status=status.HTTP_200_OK)


def get_or_create_formulation(chemist_id):
    """
    Получение id косметического средства или создание нового при его отсутствии
    """
    old_formulation = CosmeticOrder.objects.filter(
        formulation_chemist_id=chemist_id, status=CosmeticOrder.STATUS_CHOICES[0][0]
    ).first()

    if old_formulation:
        return old_formulation.id

    new_formulation = CosmeticOrder(
        formulation_chemist_id=chemist_id, status=CosmeticOrder.STATUS_CHOICES[0][0]
    )
    new_formulation.save()
    return new_formulation.id


# Список сформированных средств
@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter('status', openapi.IN_QUERY,
                          description="Фильтр по статусу", type=openapi.TYPE_STRING),
        openapi.Parameter(
            'formation_start', openapi.IN_QUERY, description="Начало периода формирования (дата)", type=openapi.FORMAT_DATE
        ),
        openapi.Parameter(
            'formation_end', openapi.IN_QUERY, description="Конец периода формирования (дата)", type=openapi.FORMAT_DATE
        ),
    ],
    responses={200: CreatedFormulationsSerializer(many=True)}
)
@api_view(['GET'])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def get_created_formulations(request):
    status_filter = request.query_params.get("status")
    formation_start = request.query_params.get("formation_start")
    formation_end = request.query_params.get("formation_end")

    filters = ~Q(status=CosmeticOrder.STATUS_CHOICES[2][0]) & ~Q(
        status=CosmeticOrder.STATUS_CHOICES[0][0])
    if status_filter:
        filters &= Q(status=status_filter.upper())
    if formation_start:
        filters &= Q(date_formation__gte=parse(formation_start))
    if formation_end:
        filters &= Q(date_formation__lte=parse(formation_end))

    if not request.user.is_staff:
        filters &= Q(formulation_chemist=request.user)

    formulations = CosmeticOrder.objects.filter(
        filters).select_related("formulation_chemist")
    serializer = CreatedFormulationsSerializer(formulations, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='get',
    operation_description="Получение информации о косметическом средстве по его ID.",
    responses={
        status.HTTP_200_OK: FullCosmeticFormulationSerializer,
        status.HTTP_404_NOT_FOUND: "Косметическое средство не найдено",
    },
    manual_parameters=[
        openapi.Parameter(
            'pk',
            in_=openapi.IN_PATH,
            description="ID косметического средства",
            type=openapi.TYPE_INTEGER,
            required=True
        )
    ]
)
@api_view(['GET'])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def get_cosmetic_formulation(request, pk):
    """
    Получение информации о косметическом средстве по его ID.

    Возвращает полную информацию о косметическом средстве, включая компоненты,
    статус, дату создания, формирования и завершения.

    Args:
        pk (int): Идентификатор косметического средства.

    Returns:
        Response: Полная информация о косметическом средстве или сообщение об ошибке.
    """
    filters = Q(pk=pk) & ~Q(
        # Исключаем удаленные заявки
        status=CosmeticOrder.STATUS_CHOICES[2][0])
    cosmetic_order = CosmeticOrder.objects.filter(filters).first()

    if cosmetic_order is None:
        return Response(
            {"error": "Косметическое средство не найдено"},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = FullCosmeticFormulationSerializer(cosmetic_order)
    return Response(serializer.data, status=status.HTTP_200_OK)

# Обновление названия косметического средства


@swagger_auto_schema(
    method='put',
    operation_summary="Изменение названия косметического средства",
    request_body=PutCosmeticFormulationSerializer,
    responses={
        200: PutCosmeticFormulationSerializer(),
        400: "Ошибка в данных",
        404: "Косметическое средство не найдено"
    }
)
@api_view(['PUT'])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def put_cosmetic_formulation(request, pk):
    cosmetic_order = CosmeticOrder.objects.filter(
        id=pk, status=CosmeticOrder.STATUS_CHOICES[0][0]
    ).first()
    if not cosmetic_order:
        return Response("Косметическое средство не найдено", status=status.HTTP_404_NOT_FOUND)

    serializer = PutCosmeticFormulationSerializer(
        cosmetic_order, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Формирование средства
@swagger_auto_schema(
    method='put',
    operation_summary="Формирование косметического средства",
    responses={
        200: CreatedFormulationsSerializer(),
        400: "Ошибка в данных",
        404: "Косметическое средство не найдено"
    }
)
@api_view(['PUT'])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def form_cosmetic_formulation(request, pk):
    cosmetic_order = CosmeticOrder.objects.filter(id=pk, status=1).first()
    if not cosmetic_order:
        return Response("Косметическое средство не найдено", status=status.HTTP_404_NOT_FOUND)

    if not cosmetic_order.name:
        return Response("Поле 'Название' должно быть заполнено", status=status.HTTP_400_BAD_REQUEST)

    if not are_valid_dosages(pk):
        return Response("Некорректные дозировки химических элементов", status=status.HTTP_400_BAD_REQUEST)

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


# Закрытие заявки технологом
@swagger_auto_schema(
    method='put',
    operation_summary="Закрытие заявки на косметическое средство технологом",
    request_body=ResolveCosmeticFormulationSerializer,
    responses={
        200: CreatedFormulationsSerializer,
        400: "Ошибка в данных",
        404: "Косметическое средство не найдено"
    }
)
@api_view(['PUT'])
@permission_classes([IsManagerAuth])
@authentication_classes([AuthBySessionID])
def resolve_cosmetic_formulation(request, pk):
    cosmetic_order = CosmeticOrder.objects.filter(pk=pk, status=2).first()
    if not cosmetic_order:
        return Response("Сформированное косметическое средство не найдено", status=status.HTTP_404_NOT_FOUND)

    serializer = ResolveCosmeticFormulationSerializer(
        cosmetic_order, data=request.data, partial=True
    )
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    serializer.save()

    response = requests.post(
        ASYNC_SERVICE_URL,
        json={"order_id": cosmetic_order.id},
    )

    if response.status_code != 200:
        return Response("Ошибка асинхронного сервиса", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    cosmetic_order.date_completion = datetime.now()
    cosmetic_order.technologist = request.user
    cosmetic_order.save()

    serializer = CreatedFormulationsSerializer(cosmetic_order)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT'])
@permission_classes([AllowAny])
def update_adverse_effects(request):
    order_id = request.data.get("order_id")
    adverse_effects_count = request.data.get("adverse_effects_count")

    if not order_id or adverse_effects_count is None:
        return Response("Неверные данные", status=status.HTTP_400_BAD_REQUEST)

    cosmetic_order = CosmeticOrder.objects.filter(id=order_id).first()
    if not cosmetic_order:
        return Response("Косметическое средство не найдено", status=status.HTTP_404_NOT_FOUND)

    if cosmetic_order.status == 5:  # Статус "отклонено"
        cosmetic_order.adverse_effects_count = 0
        message = "Заявка отклонена, коэффициент побочных эффектов установлен в 0."
    else:
        cosmetic_order.adverse_effects_count = adverse_effects_count
        message = "Успешное обновление коэффициента побочных эффектов."
    cosmetic_order.save()
    return Response({"message": message})


@swagger_auto_schema(
    method='delete',
    operation_summary="Удаление косметического средства",
    responses={
        200: "Косметическое средство успешно удалено",
        404: "Косметическое средство не найдено"
    }
)
@api_view(['DELETE'])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def delete_cosmetic_formulation(request, pk):
    """
    Удаление косметического средства.
    """
    cosmetic_order = CosmeticOrder.objects.filter(
        id=pk, status=1).first()  # 1 - Черновик
    if not cosmetic_order:
        return Response("Косметическое средство не найдено", status=status.HTTP_404_NOT_FOUND)

    cosmetic_order.status = 3  # 3 - Удалено
    cosmetic_order.save()
    return Response(status=status.HTTP_200_OK)


# Изменение данных химического элемента в составе
@swagger_auto_schema(
    method='put',
    operation_summary="Изменение данных о химическом элементе в составе косметического средства",
    request_body=OrderComponentSerializer,
    responses={
        200: OrderComponentSerializer,
        400: "Ошибка в данных",
        404: "Компонент косметического средства не найден"
    }
)
@api_view(['PUT'])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def put_chemical_element_in_formulation(request, formulation_pk, component_pk):
    """
    Изменение данных о химическом элементе в составе косметического средства.
    """
    element_in_order = OrderComponent.objects.filter(
        order_id=formulation_pk, chemical_element_id=component_pk
    ).first()
    if not element_in_order:
        return Response("Компонент косметического средства не найден", status=status.HTTP_404_NOT_FOUND)

    serializer = OrderComponentSerializer(
        element_in_order, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Удаление химического элемента из состава
@swagger_auto_schema(
    method='delete',
    operation_summary="Удаление химического элемента из состава",
    responses={200: "Элемент успешно удален", 404: "Элемент не найден"}
)
@api_view(['DELETE'])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def delete_chemical_element_in_formulation(request, formulation_pk, component_pk):
    element_in_formulation = OrderComponent.objects.filter(
        order_id=formulation_pk, chemical_element_id=component_pk
    ).first()
    if not element_in_formulation:
        return Response("Компонент не найден", status=status.HTTP_404_NOT_FOUND)

    element_in_formulation.delete()
    return Response(status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    manual_parameters=[
        openapi.Parameter(
            'username',
            openapi.IN_FORM,
            type=openapi.TYPE_STRING,
            description='Username',
            required=True
        ),
        openapi.Parameter(
            'email',
            openapi.IN_FORM,
            type=openapi.TYPE_STRING,
            description='Email',
            required=True
        ),
        openapi.Parameter(
            'password',
            openapi.IN_FORM,
            type=openapi.TYPE_STRING,
            description='Password',
            required=True
        ),
    ],
    responses={
        201: openapi.Response(
            description="User created successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'username': openapi.Schema(type=openapi.TYPE_STRING),
                    'email': openapi.Schema(type=openapi.TYPE_STRING),
                },
            ),
        ),
        400: openapi.Response(description="Bad Request"),
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([FormParser])
def create_user(request):
    """
    Создание пользователя
    """
    if request.content_type == 'application/json':
        data = request.data  # Использование JSON
    else:
        data = {
            'username': request.POST.get('username'),
            'email': request.POST.get('email'),
            'password': request.POST.get('password'),
        }

    serializer = UserSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(method='post',
                     responses={
                         status.HTTP_200_OK: "OK",
                         status.HTTP_400_BAD_REQUEST: "Bad Request",
                     },
                     manual_parameters=[
                         openapi.Parameter('username',
                                           type=openapi.TYPE_STRING,
                                           description='username',
                                           in_=openapi.IN_FORM,
                                           required=True),
                         openapi.Parameter('password',
                                           type=openapi.TYPE_STRING,
                                           description='password',
                                           in_=openapi.IN_FORM,
                                           required=True)
                     ])
@api_view(['POST'])
@parser_classes((FormParser,))
@permission_classes([AllowAny])
def login_user(request):
    """
    Вход
    """
    # # Получаем текущий session_id из куки
    # session_id = request.COOKIES.get("session_id")
    # # Если существует текущий session_id, завершаем предыдущую сессию
    # if session_id and session_storage.exists(session_id):
    #     session_storage.delete(session_id)

    # Аутентификация пользователя
    username = request.POST.get('username')
    password = request.POST.get('password')

    user = authenticate(username=username, password=password)
    if user is not None:
        email = user.email
        # Создаем новый session_id
        session_id = str(uuid.uuid4())
        session_storage.set(session_id, username)
        response = Response({
            'username': username,
            'email': email,
        }, status=status.HTTP_201_CREATED)
        response.set_cookie("session_id", session_id, samesite="lax")
        return response
    # Возвращаем ошибку, если учетные данные неверны
    return Response({'error': 'Invalid Credentials'}, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(method='post',
                     responses={
                         status.HTTP_204_NO_CONTENT: "No content",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                     })
@api_view(['POST'])
@permission_classes([IsAuth])
def logout_user(request):
    """
    Выход
    """
    session_id = request.COOKIES["session_id"]
    if session_storage.exists(session_id):
        session_storage.delete(session_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    return Response(status=status.HTTP_403_FORBIDDEN)


@swagger_auto_schema(method='put',
                     request_body=UserSerializer,
                     responses={
                         status.HTTP_200_OK: UserSerializer(),
                         status.HTTP_400_BAD_REQUEST: "Bad Request",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                     })
@api_view(['PUT'])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def update_user(request):
    """
    Обновление данных пользователя
    """
    serializer = UserSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
