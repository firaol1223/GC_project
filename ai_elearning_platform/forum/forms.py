from django import forms
from .models import ForumThread, ForumPost

class ThreadCreateForm(forms.ModelForm):
    class Meta:
        model = ForumThread
        fields = ['title'] # Category will be set in the view
        # For initial post content along with thread creation:
        # initial_post_content = forms.CharField(widget=forms.Textarea, label="Your first post")

class PostCreateForm(forms.ModelForm):
    class Meta:
        model = ForumPost
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Write your reply...'}),
        }
        labels = {
            'content': '' # Empty label for a cleaner look
        }