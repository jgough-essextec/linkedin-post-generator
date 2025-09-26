from django.urls import path
from . import views

app_name = 'generator'

urlpatterns = [
    path('', views.index_view, name='index'),
    path('generate/', views.generate_view, name='generate'),
    path('result/<int:post_id>/', views.result_view, name='result'),
    path('history/', views.history_view, name='history'),
    path('download/markdown/<int:post_id>/', views.download_markdown_view, name='download_markdown'),
    path('api/image-status/<int:post_id>/', views.check_image_status, name='check_image_status'),
]