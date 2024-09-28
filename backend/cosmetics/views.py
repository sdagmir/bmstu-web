from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from cosmetics.models import CosmeticOrder, OrderComponent, ChemicalElement
from django.db.models import Q


USER = User.objects.get(pk=1)


def components(request):
    # Получаем данные из строки поиска
    search_query = request.GET.get('q', '').lower()

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

    component_data = get_object_or_404(ChemicalElement, id=id)

    return render(request, 'component.html', {'component': component_data})


def cosmetic_composition(request, request_id):

    cosmetic_order = CosmeticOrder.objects.filter(
        ~Q(status=CosmeticOrder.STATUS_CHOICES[0][0]), id=request_id).first()

    if cosmetic_order is None:
        detailed_cosmetic_order = []
    else:
        order_components = OrderComponent.objects.filter(
            order=cosmetic_order).select_related('chemical_element')

        detailed_cosmetic_order = [
            {
                'id': component.id,
                'id_component': component.chemical_element.id,
                'dosage': component.dosage,
                'title': component.chemical_element.title,
                'img_path': component.chemical_element.img_path,
                'unit': component.chemical_element.unit
            }
            for component in order_components
        ]

    return render(request, 'order_draft.html', {'data': detailed_cosmetic_order})


def add_component(request, id):
    pass
