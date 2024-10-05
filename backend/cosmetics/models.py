from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

# Модель для химических элементов


class ChemicalElement(models.Model):
    title = models.CharField(max_length=30, verbose_name="Название")
    img_path = models.CharField(
        max_length=255, verbose_name="Путь к изображению")
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

    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             verbose_name="Пользователь", related_name="created_formulation")
    status = models.IntegerField(
        choices=STATUS_CHOICES, default=1, verbose_name="Статус")
    date_created = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата создания")
    category = models.CharField(
        max_length=50, verbose_name="Категория косметики", blank=True, null=True)
    manager = models.ForeignKey(User, on_delete=models.CASCADE,
                                verbose_name="Менеджер", related_name="managed_formulation", blank=True, null=True)
    date_formation = models.DateTimeField(blank=True, null=True)
    date_completion = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Заказ №{self.pk} от {self.user.username}"

    def save(self, *args, **kwargs):
        # Проверка на наличие уже существующей заявки в статусе "черновик"
        if self.status == 1:  # 1 - это статус "Черновик"
            if CosmeticOrder.objects.filter(user=self.user, status=1).exists():
                raise ValidationError(
                    "У вас уже есть заявка в статусе 'Черновик'.")
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Косметическая заявка"
        verbose_name_plural = "Косметические заявки"
        db_table = 'cosmetic_order'


# Модель для компонентов в заявке
class OrderComponent(models.Model):
    order = models.ForeignKey(
        CosmeticOrder, on_delete=models.CASCADE, related_name="components")
    chemical_element = models.ForeignKey(
        ChemicalElement, on_delete=models.CASCADE, verbose_name="Химический элемент")
    dosage = models.FloatField(verbose_name="Дозировка")

    def __str__(self):
        return f"{self.chemical_element.title} в заявке №{self.order.pk}"

    class Meta:
        verbose_name = "Компонент заявки"
        verbose_name_plural = "Компоненты заявки"
        db_table = 'order_component'
        unique_together = ('order', 'chemical_element')
