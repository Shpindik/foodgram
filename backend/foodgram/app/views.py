import csv
import hashlib
import io

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import (AllowAny, IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from api.filters import RecipeFilter
from api.permissions import IsAuthorOrReadOnly
from api.serializers import (FavoriteSerializer, FoodgramUserSerializer,
                             IngredientSerializer, RecipeSerializer,
                             RecipeShortSerializer, TagSerializer)
from .constants import FOODGRAM_URL, RECIPE_HASHCODE_MAX_LEN
from .models import Ingredient, Recipe, RecipeIngredient, Tag
from .pagination import CustomPagination

User = get_user_model()


class FoodgramUserViewSet(UserViewSet):
    queryset = User.objects.all()
    serializer_class = FoodgramUserSerializer
    pagination_class = CustomPagination

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'create'):
            return (AllowAny(),)
        return (IsAuthenticated(),)


class TagViewSet(ReadOnlyModelViewSet):
    permission_classes = (AllowAny,)
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientViewSet(ReadOnlyModelViewSet):
    permission_classes = (AllowAny,)
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)

    def get_queryset(self):
        queryset = Ingredient.objects.all()
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__istartswith=name)
        return queryset


class RecipeViewSet(ModelViewSet):
    queryset = Recipe.objects.prefetch_related('tags', 'recipe_ingredients')
    serializer_class = RecipeSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly)
    pagination_class = CustomPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    @action(detail=True, methods=['GET'], url_path='get-link')
    def get_short_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        if not recipe.hashcode:
            hashcode = hashlib.md5(str(recipe.id).encode()).hexdigest()[
                :RECIPE_HASHCODE_MAX_LEN]
            recipe.hashcode = hashcode
            recipe.save()
        short_link = f'{FOODGRAM_URL}s/{recipe.hashcode}'
        return Response({'short-link': short_link}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['GET'], url_path='s/(?P<hashcode>[^/.]+)')
    def redirect_short_link(self, request, hashcode=None):
        recipe = get_object_or_404(Recipe, hashcode=hashcode)
        return redirect(f'{FOODGRAM_URL}recipes/{recipe.id}')

    @action(detail=True, methods=['POST', 'DELETE'],
            permission_classes=[IsAuthenticated], url_path='favorite')
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)

        if request.method == 'DELETE':
            favorite = request.user.favorites.filter(recipe=recipe)
            if not favorite.exists():
                return Response({'detail': 'Рецепта нет в избранном.'},
                                status=status.HTTP_400_BAD_REQUEST)
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        favorite, created = request.user.favorites.get_or_create(recipe=recipe)
        if not created:
            return Response({'detail': 'Рецепт уже в избранном.'},
                            status=status.HTTP_400_BAD_REQUEST)
        serializer = FavoriteSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['POST', 'DELETE'],
            permission_classes=[IsAuthenticated], url_path='shopping_cart')
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)

        if request.method == 'DELETE':
            cart_entry = request.user.shopping_cart.filter(recipe=recipe)
            if not cart_entry.exists():
                return Response(
                    {'detail': 'Рецепта нет в списке покупок'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            cart_entry.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        cart_entry, created = request.user.shopping_cart.get_or_create(
            recipe=recipe
        )
        if not created:
            return Response(
                {'detail': 'Рецепт уже в списке покупок'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = RecipeShortSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['GET'],
            permission_classes=[IsAuthenticated],
            url_path='download_shopping_cart')
    def download_shopping_cart(self, request):
        ingredients = (RecipeIngredient.objects
                       .filter(recipe__in_shopping_cart__user=request.user)
                       .values('ingredient__name',
                               'ingredient__measurement_unit')
                       .annotate(total_amount=Sum('amount')))
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Ингредиент', 'Количество', 'Единица измерения'])
        for item in ingredients:
            writer.writerow([item['ingredient__name'],
                             item['total_amount'],
                             item['ingredient__measurement_unit']])
        response = HttpResponse(output.getvalue(),
                                content_type='text/csv')
        response[
            'Content-Disposition'] = 'attachment; filename="shopping_list.csv"'
        return response
