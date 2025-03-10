import csv
import hashlib
import io
from urllib.parse import urljoin

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListAPIView
from rest_framework.permissions import (AllowAny, IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .constants import FOODGRAM_URL, RECIPE_HASHCODE_MAX_LEN
from .filters import RecipeFilter
from .models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                     ShoppingCart, Subscription, Tag)
from .pagination import CustomPagination
from .serializers import (AvatarSerializer, FavoriteSerializer,
                          FoodgramUserSerializer, IngredientSerializer,
                          RecipeSerializer, RecipeShortSerializer,
                          SubscriptionSerializer, TagSerializer)

User = get_user_model()


class FoodgramUserViewSet(UserViewSet):
    queryset = User.objects.all()
    serializer_class = FoodgramUserSerializer
    pagination_class = CustomPagination

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'create'):
            return (AllowAny(),)
        return (IsAuthenticated(),)


class SubscribeView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, author_id):
        author = get_object_or_404(User, id=author_id)
        if request.user == author:
            return Response({"error": "Нельзя подписаться на самого себя."},
                            status=status.HTTP_400_BAD_REQUEST)
        if Subscription.objects.filter(follower=request.user,
                                       author=author).exists():
            return Response(
                {"error": "Вы уже подписаны на этого пользователя."},
                status=status.HTTP_400_BAD_REQUEST)

        subscription = Subscription.objects.create(follower=request.user,
                                                   author=author)
        recipes_limit = request.query_params.get('recipes_limit')
        serializer = SubscriptionSerializer(subscription, context={
            'request': request, 'recipes_limit': recipes_limit})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, author_id):
        author = get_object_or_404(User, id=author_id)
        subscription = Subscription.objects.filter(follower=request.user,
                                                   author=author)
        if not subscription.exists():
            return Response(
                {"error": "Вы не подписаны на этого автора."},
                status=status.HTTP_400_BAD_REQUEST)
        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ListMySubscriptionsView(ListAPIView):

    serializer_class = SubscriptionSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = CustomPagination

    def get_queryset(self):
        return Subscription.objects.filter(follower=self.request.user)


class AvatarView(APIView):

    permission_classes = (IsAuthenticated,)

    def put(self, request):
        serializer = AvatarSerializer(instance=request.user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            avatar_url = urljoin(settings.MEDIA_URL, request.user.avatar.name)
            full_avatar_url = request.build_absolute_uri(avatar_url)
            return Response({'avatar': full_avatar_url},
                            status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        request.user.delete_avatar()
        return Response(status=status.HTTP_204_NO_CONTENT)


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
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = CustomPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def perform_update(self, serializer):
        recipe = self.get_object()
        if recipe.author != self.request.user:
            raise PermissionDenied('Вы не можете редактировать чужой рецепт.')
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        recipe = self.get_object()
        if recipe.author != request.user:
            raise PermissionDenied('Вы не може те удалить чужой рецепт.')
        return super().destroy(request, *args, **kwargs)

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
            favorite = Favorite.objects.filter(user=request.user,
                                               recipe=recipe)
            if not favorite.exists():
                return Response({'detail': 'Рецепта нет в избранном.'},
                                status=status.HTTP_400_BAD_REQUEST)
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        favorite, created = Favorite.objects.get_or_create(user=request.user,
                                                           recipe=recipe)
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
            shopping_cart = ShoppingCart.objects.filter(user=request.user,
                                                        recipe=recipe)
            if not shopping_cart.exists():
                return Response({'detail': 'Рецепта нет в списке покупок'},
                                status=status.HTTP_400_BAD_REQUEST)
            shopping_cart.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        shopping_cart, created = ShoppingCart.objects.get_or_create(
            user=request.user, recipe=recipe)
        if not created:
            return Response({'detail': 'Рецепт уже в списке покупок'},
                            status=status.HTTP_400_BAD_REQUEST)

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
