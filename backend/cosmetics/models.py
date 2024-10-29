from django.db import models
from django.contrib.auth.models import User

# Модель для химических элементов


class ChemicalElement(models.Model):
    title = models.CharField(max_length=30, verbose_name="Название")
    img_path = models.CharField(
        max_length=255, verbose_name="Путь к изображению", default="")
    volume = models.IntegerField(verbose_name="Объем")
    unit = models.CharField(max_length=10, verbose_name="Единица измерения")
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Цена")
    short_description = models.CharField(
        max_length=255, verbose_name="Краткое описание")
    description = models.TextField(verbose_name="Полное описание")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Химический элемент"
        verbose_name_plural = "Химические элементы"
        db_table = 'chemical_element'


# Модель для заявок на косметические средства
class CosmeticOrder(models.Model):
    STATUS_CHOICES = (
        (1, 'Черновик'),
        (2, 'Сформировано'),
        (3, 'Удалено'),
        (4, 'Завершено'),
        (5, 'Отклонено'),
    )

    user = models.ForeignKey(User, on_delete=models.SET_NULL,
                             null=True, blank=True,
                             verbose_name="Пользователь", related_name="created_formulation")
    status = models.IntegerField(
        choices=STATUS_CHOICES, default=1, verbose_name="Статус")
    date_created = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата создания")
    name = models.CharField(
        max_length=50, verbose_name="Название косметики", blank=True, null=True)
    manager = models.ForeignKey(User, on_delete=models.SET_NULL,
                                null=True, blank=True,
                                verbose_name="Менеджер", related_name="managed_formulation")
    date_formation = models.DateTimeField(blank=True, null=True)
    date_completion = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Заказ №{self.pk} от {self.user.username if self.user else 'Удалённый пользователь'}"

    class Meta:
        verbose_name = "Косметическая заявка"
        verbose_name_plural = "Косметические заявки"
        db_table = 'cosmetic_order'


# Модель для компонентов в заявке
class OrderComponent(models.Model):
    order = models.ForeignKey(
        CosmeticOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name="components")
    chemical_element = models.ForeignKey(
        ChemicalElement, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Химический элемент")
    dosage = models.FloatField(verbose_name="Дозировка", default=0)

    def __str__(self):
        return f"{self.chemical_element.title if self.chemical_element else 'Удалённый элемент'} в заявке №{self.order.pk if self.order else 'Удалённая заявка'}"

    class Meta:
        verbose_name = "Компонент заявки"
        verbose_name_plural = "Компоненты заявки"
        db_table = 'order_component'
        unique_together = ('order', 'chemical_element')
