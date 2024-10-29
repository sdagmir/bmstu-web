from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.db import connection
from cosmetics.models import CosmeticOrder, OrderComponent, ChemicalElement
from django.db.models import Q


USER = 1


def components(request):
    """
    Отображение страницы со списком всех компонентов
    """
    # Получаем данные из строки поиска
    search_query = request.GET.get('component_title', '').lower()

    # Получаем заявку пользователя в статусе черновик, если такая существует
    draft_order = CosmeticOrder.objects.filter(
        user=USER, status=CosmeticOrder.STATUS_CHOICES[0][0]).first()

    # Фильтруем химические элементы по заголовку, начинающемуся с поискового запроса
    filter_elements = ChemicalElement.objects.filter(
        title__istartswith=search_query)

    # Рендерим html-шаблон, передавая данные
    return render(request, 'components_list.html', {
        'data': {
            'elements': filter_elements,
            'search_query': search_query,
            'count': draft_order.components.count() if draft_order else 0,
            'formulation_id': draft_order.id if draft_order else 0
        }
    })


def component(request, id):
    """
    Отображение страницы с подробным описанием выбранного элемента
    """
    component_data = get_object_or_404(ChemicalElement, id=id)

    return render(request, 'component.html', {'component': component_data})


def cosmetic_composition(request, request_id):
    """
    Отображение страницы косметического средства
    """
    # Получаем заявку, исключая заявки с удалённым статусом
    cosmetic_order = CosmeticOrder.objects.filter(
        ~Q(status=CosmeticOrder.STATUS_CHOICES[2][0]), id=request_id).first()

    # Если заявка удалена или не найдена, перенаправляем на главную страницу
    if cosmetic_order is None:
        return redirect('components')

    # Если заявка найдена, продолжаем с рендерингом страницы
    order_components = OrderComponent.objects.filter(
        order=cosmetic_order).select_related('chemical_element')

    detailed_cosmetic_order = [
        {
            'id_component': component.chemical_element.id,
            'title': component.chemical_element.title,
            'img_path': component.chemical_element.img_path,
            'unit': component.chemical_element.unit
        }
        for component in order_components
    ]

    return render(request, 'cosmetic_composition.html', {
        'data': {
            'id': cosmetic_order.id,
            'details': detailed_cosmetic_order,
            'name': cosmetic_order.name
        }
    })


def get_or_create_formulation(user_id):
    """
    Получение id косметического средства или создание нового при его отсутствии
    """
    old_formulation = CosmeticOrder.objects.filter(
        user_id=USER, status=CosmeticOrder.STATUS_CHOICES[0][0]).first()

    if old_formulation is not None:
        return old_formulation.id

    new_formulation = CosmeticOrder(
        user_id=USER, status=CosmeticOrder.STATUS_CHOICES[0][0])
    new_formulation.save()
    return new_formulation.id


def add_component(request):
    """
    Добавление выбранного компонента в состав косметического средства
    """
    if request.method != "POST":
        return redirect('components')

    data = request.POST
    component_id = data.get("add_to_basket")

    if component_id is not None:
        formulation_id = get_or_create_formulation(USER)
        element = OrderComponent(order_id=formulation_id,
                                 chemical_element_id=component_id, dosage=0)
        element.save()

    return components(request)


def delete_cosmetic_composition(request_id):
    """
    Удаление косметического средства в целом
    """
    sql = "UPDATE cosmetic_order SET status = 3 WHERE id =%s"

    with connection.cursor() as cursor:
        cursor.execute(sql, (request_id,))


def delete_cosmetic(request, id):
    """
    Удаление косметики
    """
    if request.method != "POST":
        return redirect('cosmetic_composition')

    data = request.POST
    action = data.get("request_action")

    if action == "delete_cosmetic_composition":
        delete_cosmetic_composition(id)
        return redirect('components')

    elif action.startswith("delete_component_"):
        component_id = action.split("_")[2]
        print(component_id)
        component = OrderComponent.objects.get(
            chemical_element_id=component_id)
        component.delete()

    return cosmetic_composition(request, id)
