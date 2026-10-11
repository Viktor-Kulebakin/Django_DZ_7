from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import EmployeeViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

app_name = 'employees'

# 1. Настраиваем роутер для API
router = DefaultRouter()
router.register(r'employees', EmployeeViewSet, basename='employee')

# 2. Объединяем все маршруты в один список
urlpatterns = [
    # Старые HTML-маршруты
    path('', views.index_view, name='index'),
    path('employees/', views.employee_list_view, name='list'),
    path('employees/<int:pk>/', views.employee_detail_view, name='detail'),
    path('logout/', views.logout_view, name='custom_logout'),
    
    # Новый API-маршрут (автоматически включает все методы ViewSet)
    path('api/', include(router.urls)),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
     # 4. ДОКУМЕНТАЦИЯ (Добавляем в самый конец)
       # --- ЭНДПОИНТЫ ДОКУМЕНТАЦИИ ---
    # Схема в формате YAML/JSON
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    
    # Интерактивный интерфейс Swagger (ИСПРАВЛЯЕМ ТУТ: добавляем employees:)
    path('api/docs/swagger/', SpectacularSwaggerView.as_view(url_name='employees:schema'), name='swagger-ui'),
    
    # Альтернативный интерфейс ReDoc (ИСПРАВЛЯЕМ ТУТ: добавляем employees:)
    path('api/docs/redoc/', SpectacularRedocView.as_view(url_name='employees:schema'), name='redoc'),

]
