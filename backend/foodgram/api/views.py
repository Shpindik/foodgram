from urllib.parse import urljoin

from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app.models import Subscription
from app.pagination import CustomPagination
from .serializers import AvatarSerializer, SubscriptionSerializer

User = get_user_model()


class SubscribeView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, author_id):
        author = get_object_or_404(User, id=author_id)
        serializer = SubscriptionSerializer(
            data={},
            context={
                'request': request,
                'author': author,
                'recipes_limit': request.query_params.get('recipes_limit')
            }
        )

        if serializer.is_valid():
            Subscription.objects.create(
                follower=request.user,
                author=author
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, author_id):
        author = get_object_or_404(User, id=author_id)
        subscriptions = request.user.subscriptions.filter(author=author)
        if not subscriptions.exists():
            return Response(
                {'error': 'Вы не подписаны на этого автора.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        subscriptions.delete()
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
