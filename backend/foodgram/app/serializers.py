import base64
import uuid

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework import serializers

from .constants import DEFAULT_RECIPES_AMOUNT_AT_SUBSCRIPTIONS_PAGE
from .models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                     ShoppingCart, Subscription, Tag)

User = get_user_model()


class Base64ImageField(serializers.ImageField):

    def to_internal_value(self, data):
        if data.startswith('data:image'):
            format_, imgstr = data.split(';base64,')
            ext = format_.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f'temp.{ext}')
        return super().to_internal_value(data)


class FoodgramUserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.ImageField()

    class Meta:
        model = User
        fields = ('email',
                  'id',
                  'username',
                  'first_name',
                  'last_name',
                  'is_subscribed',
                  'avatar')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Subscription.objects.filter(follower=request.user,
                                           author=obj).exists()


class SubscriptionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='author.id', read_only=True)
    email = serializers.EmailField(source='author.email', read_only=True)
    username = serializers.CharField(source='author.username', read_only=True)
    first_name = serializers.CharField(source='author.first_name',
                                       read_only=True)
    last_name = serializers.CharField(source='author.last_name',
                                      read_only=True)
    avatar = serializers.ImageField(source='author.avatar', read_only=True)
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(source='author.recipes.count',
                                             read_only=True)

    class Meta:
        model = Subscription
        fields = ('id', 'email', 'username', 'first_name', 'last_name',
                  'is_subscribed', 'avatar', 'recipes', 'recipes_count')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return Subscription.objects.filter(follower=request.user,
                                           author=obj.author).exists()

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj.author).count()

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit')
        recipes = Recipe.objects.filter(author=obj.author)
        if recipes_limit and recipes_limit.isdigit():
            return RecipeShortSerializer(recipes[:int(recipes_limit)],
                                         many=True).data
        return RecipeShortSerializer(
            recipes[:DEFAULT_RECIPES_AMOUNT_AT_SUBSCRIPTIONS_PAGE],
            many=True).data


class AvatarSerializer(serializers.ModelSerializer):
    avatar = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('avatar',)

    def validate_avatar(self, value):
        try:
            format_, imgstr = value.split(';base64,')
            ext = format_.split('/')[-1]
            return base64.b64decode(imgstr), ext
        except Exception:
            raise serializers.ValidationError('Invalid base64 image format.')

    def update(self, instance, validated_data):
        image_data, ext = validated_data['avatar']
        file_name = f'{uuid.uuid4()}.{ext}'
        instance.avatar.save(file_name, ContentFile(image_data), save=True)
        return instance


class TagSerializer(serializers.ModelSerializer):

    def to_internal_value(self, data):
        if isinstance(data, int):
            return Tag.objects.get(id=data)

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient')
    name = serializers.SerializerMethodField()
    measurement_unit = serializers.SerializerMethodField()

    def get_name(self, obj):
        return obj.ingredient.name

    def get_measurement_unit(self, obj):
        return obj.ingredient.measurement_unit

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    tags = serializers.PrimaryKeyRelatedField(many=True,
                                              queryset=Tag.objects.all())
    ingredients = IngredientInRecipeSerializer(many=True,
                                               source='recipe_ingredients')
    image = Base64ImageField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients',
                  'name', 'image', 'text', 'cooking_time',
                  'is_favorited', 'is_in_shopping_cart')

    def get_author(self, obj):
        request = self.context.get('request')
        if request.user.is_anonymous:
            is_subscribed = False
        else:
            is_subscribed = Subscription.objects.filter(
                follower=request.user, author=obj.author).exists()
        return {
            'email': obj.author.email,
            'id': obj.author.id,
            'username': obj.author.username,
            'first_name': obj.author.first_name,
            'last_name': obj.author.last_name,
            'is_subscribed': is_subscribed,
            'avatar': obj.author.avatar.url if obj.author.avatar and hasattr(
                obj.author.avatar, 'url') else None}

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request.user.is_anonymous:
            return False
        return Favorite.objects.filter(recipe=obj, user=request.user).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request.user.is_anonymous:
            return False
        return ShoppingCart.objects.filter(recipe=obj,
                                           user=request.user).exists()

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['tags'] = TagSerializer(instance.tags.all(),
                                               many=True).data
        return representation

    def validate_tags(self, tags):
        if not tags:
            raise serializers.ValidationError(
                {'tags': 'Необходимо указать хотя бы один тег.'})
        tag_ids = [tag.id for tag in tags]
        if len(tag_ids) != len(set(tag_ids)):
            raise serializers.ValidationError(
                {'tags': 'Теги не должны повторяться.'})
        return tags

    def validate_ingredients(self, ingredients):
        if not ingredients:
            raise serializers.ValidationError(
                {'ingredients': 'Список ингредиентов не может быть пустым.'})
        ingredient_ids = [ingredient['ingredient'].id for ingredient in
                          ingredients]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                {'ingredients': 'Ингредиенты не должны повторяться.'})
        return ingredients

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['author'] = request.user
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('recipe_ingredients')
        self.validate_tags(tags)
        self.validate_ingredients(ingredients)
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(recipe=recipe,
                             ingredient=ingredient.get('ingredient'),
                             amount=ingredient['amount']
                             ) for ingredient in ingredients])
        return recipe

    def update(self, instance, validated_data):
        if 'tags' not in validated_data:
            raise serializers.ValidationError(
                {'tags': 'Поле tags обязательно для обновления.'})
        if 'recipe_ingredients' not in validated_data:
            raise serializers.ValidationError(
                {'ingredients': 'Поле ingredients обязательно для обновления.'}
            )
        tags = validated_data.pop('tags', None)
        if tags is not None:
            self.validate_tags(tags)
            instance.tags.set(tags)
        ingredients = validated_data.pop('recipe_ingredients', None)
        if ingredients is not None:
            self.validate_ingredients(ingredients)
            instance.recipe_ingredients.all().delete()
            RecipeIngredient.objects.bulk_create([
                RecipeIngredient(recipe=instance,
                                 ingredient=ingredient.get('ingredient'),
                                 amount=ingredient['amount']
                                 ) for ingredient in ingredients])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class RecipeShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FavoriteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
