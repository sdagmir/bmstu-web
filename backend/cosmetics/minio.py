from django.conf import settings
from minio import Minio
from django.core.files.uploadedfile import InMemoryUploadedFile
from rest_framework.response import Response
from .models import ChemicalElement

# Функция загрузки файла в MinIO


def process_file_upload(file_object: InMemoryUploadedFile, client, image_name):
    try:
        client.put_object('web-img', image_name, file_object, file_object.size)
        return f"http://localhost:9000/web-img/{image_name}"
    except Exception as e:
        return {"error": str(e)}

# Функция добавления изображения химического элемента


def add_pic(new_element, pic):
    client = Minio(
        endpoint=settings.AWS_S3_ENDPOINT_URL,
        access_key=settings.AWS_ACCESS_KEY_ID,
        secret_key=settings.AWS_SECRET_ACCESS_KEY,
        secure=settings.MINIO_USE_SSL
    )

    # Используем ID химического элемента для наименования изображения
    img_obj_name = f"{new_element.id}.png"

    if not pic:
        return Response({"error": "Нет файла для изображения."})

    # Загружаем изображение
    result = process_file_upload(pic, client, img_obj_name)

    if 'error' in result:
        return Response(result)

    # Сохраняем URL изображения в поле img_path
    new_element.img_path = result
    new_element.save()

    return Response({"message": "Файл успешно добавлен."})

# Функция удаления изображения химического элемента


def delete_pic(image_path):
    client = Minio(
        endpoint=settings.AWS_S3_ENDPOINT_URL,
        access_key=settings.AWS_ACCESS_KEY_ID,
        secret_key=settings.AWS_SECRET_ACCESS_KEY,
        secure=settings.MINIO_USE_SSL
    )

    # Получаем название изображения из пути
    img_obj_name = image_path.split("/")[-1]

    try:
        client.remove_object('web-img', img_obj_name)
        return {"message": "Файл успешно удален."}
    except Exception as e:
        return {"error": str(e)}
