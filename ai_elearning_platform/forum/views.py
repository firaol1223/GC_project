from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator # For paginating threads and posts
from .models import ForumCategory, ForumThread, ForumPost
from .forms import ThreadCreateForm, PostCreateForm
from django.utils import timezone # For the ForumPost save method if needed
from core.notification_utils import create_notification
def forum_home_view(request):
    categories = ForumCategory.objects.all()
    # Optionally, fetch recent threads or stats for display on home
    context = {
        'categories': categories,
        'page_title': "Discussion Forums"
    }
    return render(request, 'forum/forum_home.html', context)

def category_detail_view(request, category_slug):
    category = get_object_or_404(ForumCategory, slug=category_slug)
    threads_list = category.threads.all().order_by('-updated_at') # Already default order

    paginator = Paginator(threads_list, 10) # Show 10 threads per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'category': category,
        'page_obj': page_obj, # Pass paginated threads
        'page_title': category.name
    }
    return render(request, 'forum/category_detail.html', context)


@login_required
def thread_detail_view(request, category_slug, thread_slug):
    thread = get_object_or_404(
        ForumThread.objects.select_related('author', 'category'),
        category__slug=category_slug, slug=thread_slug
    )
    posts_list = thread.posts.all().select_related('author', 'author__profile').order_by('created_at')

    paginator = Paginator(posts_list, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST':
        post_form = PostCreateForm(request.POST)
        if post_form.is_valid():
            new_post = post_form.save(commit=False)
            new_post.thread = thread
            new_post.author = request.user
            new_post.save()  # This updates thread.updated_at

            messages.success(request, "Your reply has been posted.")

            # Award points for posting
            points_for_post = 5
            request.user.profile.award_points(
                points_for_post,
                reason=f"Posted in thread: {thread.title[:30]}..."
            )
            messages.info(request, f"You earned {points_for_post} points for your contribution!")

            # Optional: Award badges
            # check_and_award_badges(request.user)

            # Notify thread author (but not if replying to their own thread)
            if new_post.author != thread.author:
                create_notification(
                    recipient=thread.author,
                    actor=new_post.author,
                    verb='new_reply',
                    message=f"{new_post.author.get_short_name()} replied to your thread: '{thread.title[:50]}...'",
                    link=thread.get_absolute_url() + f"#post-{new_post.id}"
                )

            return redirect(thread.get_absolute_url() + f"?page={paginator.num_pages}")
    else:
        post_form = PostCreateForm()

    context = {
        'thread': thread,
        'category': thread.category,
        'page_obj': page_obj,
        'post_form': post_form,
        'page_title': thread.title,
    }
    return render(request, 'forum/thread_detail.html', context)

@login_required
def create_thread_view(request, category_slug):
    category = get_object_or_404(ForumCategory, slug=category_slug)
    
    # Initialize new_thread outside the if block to ensure it's always defined
    # if a redirect is attempted, though ideally, redirect only happens on success.
    # However, this specific error is about accessing it before assignment in a success path.
    # new_thread = None # Not strictly needed if logic is correct, but helps reasoning.

    if request.method == 'POST':
        form = ThreadCreateForm(request.POST)
        if form.is_valid():
            # Create the ForumThread instance but don't save to DB yet (commit=False)
            # This allows us to set the author and category before saving.
            new_thread_instance = form.save(commit=False) # Use a different variable name temporarily
            new_thread_instance.category = category
            new_thread_instance.author = request.user
            new_thread_instance.save() # Now save the thread. Slug should be generated here.

            # After saving the thread, 'new_thread_instance' is the saved object.
            # Let's assign it to 'new_thread' for clarity or just use 'new_thread_instance'.
            new_thread = new_thread_instance # Now 'new_thread' is defined in this scope

            initial_content = form.cleaned_data.get('initial_post_content')
            if initial_content:
                first_post = ForumPost.objects.create(
                    thread=new_thread, # Use the saved thread instance
                    author=request.user,
                    content=initial_content
                )
                # Award points for the initial post
                points_for_post = 5 # Or your defined value from settings
                if hasattr(request.user, 'profile'): # Check if profile exists
                    request.user.profile.award_points(points_for_post, reason=f"Started thread: {new_thread.title[:30]}...")
                    messages.info(request, f"You earned {points_for_post} points for starting the thread!")
            
            messages.success(request, "New thread created successfully!")
            # Line 98 (approximately) where the error occurs IF new_thread wasn't defined:
            return redirect(new_thread.get_absolute_url()) 
        else:
            # Form is invalid, re-render the page with the form and errors
            # 'new_thread' would not be defined in this 'else' block if we didn't initialize it earlier,
            # but we are not trying to use it here for a redirect.
            messages.error(request, "Please correct the errors below.")
            # The 'form' variable (with errors) will be passed to the context below.
    else: # GET request
        form = ThreadCreateForm()

    context = {
        'category': category,
        'form': form, # Pass the bound form with errors, or the unbound form
        'page_title': f"New Thread in {category.name}"
    }
    return render(request, 'forum/create_thread.html', context)