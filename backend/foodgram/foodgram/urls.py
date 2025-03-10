from app.views import (AvatarView, FoodgramUserViewSet, IngredientViewSet,
                       ListMySubscriptionsView, RecipeViewSet, SubscribeView,
                       TagViewSet)
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'users', FoodgramUserViewSet)
router.register(r'tags', TagViewSet)
router.register(r'ingredients', IngredientViewSet)
router.register(r'recipes', RecipeViewSet, basename='recipes')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('djoser.urls')),
    path('api/auth/', include('djoser.urls.authtoken')),
    path('api/users/me/avatar/', AvatarView.as_view()),
    path('api/users/<int:author_id>/subscribe/', SubscribeView.as_view()),
    path('api/users/subscriptions/', ListMySubscriptionsView.as_view()),
    path('api/', include(router.urls)),
    path('s/<str:hashcode>/',
         RecipeViewSet.as_view({'get': 'redirect_short_link'})),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
