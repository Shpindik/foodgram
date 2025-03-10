from django.db.models import Exists, OuterRef
from django_filters import rest_framework as filters

from .models import Favorite, Recipe, ShoppingCart


class RecipeFilter(filters.FilterSet):
    author = filters.NumberFilter(field_name='author__id')
    tags = filters.CharFilter(method='filter_by_tags')
    is_favorited = filters.BooleanFilter(method='filter_by_favorited')
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_is_in_shopping_cart')

    def filter_by_tags(self, queryset, name, value):
        tag_slugs = self.data.getlist('tags')
        if tag_slugs:
            return queryset.filter(tags__slug__in=tag_slugs).distinct()
        return queryset

    def filter_by_favorited(self, queryset, name, value):
        user = self.request.user
        if user.is_authenticated and value:
            return queryset.filter(
                Exists(Favorite.objects.filter(user=user,
                                               recipe=OuterRef('pk'))))
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        user = self.request.user
        if user.is_authenticated and value:
            return queryset.filter(
                Exists(ShoppingCart.objects.filter(user=user,
                                                   recipe=OuterRef('pk'))))
        return queryset

    class Meta:
        model = Recipe
        fields = ('author', 'tags', 'is_favorited', 'is_in_shopping_cart')
