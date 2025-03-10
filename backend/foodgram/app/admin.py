from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                     ShoppingCart, Tag)

User = get_user_model()


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    min_num = 1
    validate_min = True
    extra = 0


class RecipeTagInline(admin.TabularInline):
    model = Recipe.tags.through
    min_num = 1
    extra = 0


class RecipeAdminForm(forms.ModelForm):
    class Meta:
        model = Recipe
        exclude = ('hashcode',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    form = RecipeAdminForm
    list_display = ('id', 'name', 'author', 'get_tags', 'favorite_count')
    search_fields = ('name', 'author__username')
    list_filter = ('tags',)
    filter_horizontal = ('tags',)
    inlines = (RecipeTagInline, RecipeIngredientInline)

    @admin.display(description='Теги')
    def get_tags(self, obj):
        return ', '.join([tag.name for tag in obj.tags.all()])

    def favorite_count(self, obj):
        return Favorite.objects.filter(recipe=obj).count()

    favorite_count.short_description = 'В избранном'


@admin.register(User)
class FoodgramUserAdmin(UserAdmin):
    list_display = ('id', 'email', 'username', 'first_name', 'last_name')
    search_fields = ('email', 'username')
    ordering = ('id',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug')
    search_fields = ('name',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit')
    search_fields = ('name',)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_user_id', 'user', 'recipe', 'get_recipe_id')
    search_fields = ('user__username', 'recipe__name')

    @admin.display(description='User id')
    def get_user_id(self, obj):
        return obj.user.id

    @admin.display(description='Recipe id')
    def get_recipe_id(self, obj):
        return obj.recipe.id


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_user_id', 'user', 'recipe', 'get_recipe_id')
    search_fields = ('user__username', 'recipe__name')

    @admin.display(description='User id')
    def get_user_id(self, obj):
        return obj.user.id

    @admin.display(description='Recipe id')
    def get_recipe_id(self, obj):
        return obj.recipe.id
