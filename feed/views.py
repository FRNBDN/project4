from django.shortcuts import render, get_object_or_404, redirect, reverse
from django.db.models import Q
from account.models import Account
from django.forms import ModelForm
from django.views import generic, View
from django.http import HttpResponse, HttpResponseRedirect
from .models import *
from .forms import *


class Feed(generic.ListView):
    model = Post
    queryset = Post.objects.filter(listed=True).order_by('-created_on')
    template_name = 'index.html'
    paginate_by = 10


class PostDetail(View):
    """
    Post Detail View.
    """

    def get(self, request, slug, *args, **kwargs):
        queryset = Post.objects.filter(listed=True)
        post = get_object_or_404(queryset, slug=slug)
        comments = Comment.objects.filter(post=post).order_by('-created_on')
        liked = False
        disliked = False
        if post.likes.filter(id=self.request.user.id).exists():
            liked = True
        if post.dislikes.filter(id=self.request.user.id).exists():
            disliked = True

        return render(
            request,
            'post_detail.html',
            {
                'post': post,
                'comments': comments,
                'liked': liked,
                'disliked': disliked,
                'comment_form': CommentForm()
            }
        )

    def post(self, request, slug, *args, **kwargs):
        queryset = Post.objects.filter(listed=True)
        post = get_object_or_404(queryset, slug=slug)
        if self.request.method == 'POST':
            comment_form = CommentForm(self.request.POST)
            if comment_form.is_valid():
                body = comment_form.cleaned_data['body']
                try:
                    parent = comment_form.cleaned_data['parent']
                except NoParent:
                    parent = None

            new_comment = Comment(
                body=body,
                commenter=self.request.user,
                post=post,
                parent=parent)
            new_comment.save()
            return redirect('post_detail', slug=post.slug)


def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES.get('thumbnail')
            if not file.content_type.startswith('image/'):
                form.add_error('thumbnail', 'File must be an image.')
                return render(request, 'edit_post.html', {'form': form,
                                                          'create': True})
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('post_detail', slug=post.slug)
    else:
        form = PostForm()
    return render(request, 'edit_post.html', {'form': form, 'create': True})


def edit_post(request, slug):
    post = get_object_or_404(Post, slug=slug)
    if post.author != request.user:
        form = PostForm()
        return render(request, 'edit_post.html',
                      {'acccessdenied': True})

    if request.method == "POST":
        old_title = post.title
        old_body = post.body
        old_thumbnail = post.thumbnail
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            file = request.FILES.get('thumbnail')
            if not file.content_type.startswith('image/'):
                form.add_error('thumbnail', 'File must be an image.')
                return render(request, 'edit_post.html', {'form': form,
                                                          'create': True})
            post = form.save(commit=False)
            if (old_title != post.title and
                old_body != post.body and
               old_thumbnail != post.thumbnail):
                post.edited = True
            post.save()
        return redirect('post_detail', slug=post.slug)

    form = PostForm(instance=post, initial={
        'title': post.title,
        'body': post.body,
        'thumbnail': post.thumbnail,
    }
    )

    return render(request, 'edit_post.html',
                  {'form': form, 'create': False})


class PostLike(View):
    """
    PostLike View.
    """

    def post(self, request, slug):
        post = get_object_or_404(Post, slug=slug)

        if post.likes.filter(id=request.user.id).exists():
            post.likes.remove(request.user)

        elif post.dislikes.filter(id=request.user.id).exists():
            post.dislikes.remove(request.user)
            post.likes.add(request.user)

        else:
            post.likes.add(request.user)

        return redirect('post_detail', slug=slug)


class PostDislike(View):
    """
    PostDislike View.
    """

    def post(self, request, slug):
        post = get_object_or_404(Post, slug=slug)

        if post.likes.filter(id=request.user.id).exists():
            post.likes.remove(request.user)
            post.dislikes.add(request.user)

        elif post.dislikes.filter(id=request.user.id).exists():
            post.dislikes.remove(request.user)
        else:
            post.dislikes.add(request.user)

        return redirect('post_detail', slug=slug)


class PostDeleteView(generic.DeleteView):
    """
    Post Delete View.
    """
    model = Post
    success_url = "/"
    template_name = "post_confirm_delete.html"


class CommentDeleteView(View):
    """
    Comment Delete View.
    """

    def get(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        return render(
            request,
            'comment_confirm_delete.html',
            {'comment': comment}
        )

    def post(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        slug = comment.post.slug
        comment.delete()
        return redirect('post_detail', slug=slug)


class EditCommentView(View):
    """
    Comment Edit View.
    """

    def get(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        form = CommentForm(instance=comment)
        return render(
            request,
            'edit_comment.html',
            {
                'form': form,
                'comment': comment
            }
        )

    def post(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        old_comment = comment.body
        parent = comment.parent
        slug = comment.post.slug
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.parent = parent
            if old_comment != comment.body:
                comment.edited = True
            comment.save()
            return redirect('post_detail', slug=slug)
        return redirect('post_detail', slug=slug)
