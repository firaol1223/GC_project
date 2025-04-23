# courses/forms.py
from django import forms
from .models import *


# courses/forms.py
from django import forms
from .models import CourseReview
from forum.models import ForumThread

class CourseReviewForm(forms.ModelForm):
    rating = forms.IntegerField(
        min_value=1, 
        max_value=5, 
        widget=forms.Select(
            choices=[(i, f"{i} Star{'s' if i > 1 else ''}") for i in range(1, 6)],
            attrs={'class': 'form-select glass-card-input'} # <--- SET ATTRS HERE
        ),
        label="Your Rating"
    )
    comment = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'rows': 4, 
                'placeholder': 'Share your thoughts about this course...',
                'class': 'form-control glass-card-input' # <--- SET ATTRS HERE
            }
        ),
        required=False,
        label="Your Review (Optional)"
    )

    class Meta:
        model = CourseReview
        fields = ['rating', 'comment']
# Assuming CourseCategory is used

class CourseForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=CourseCategory.objects.all(),
        empty_label="Select a category...",
        widget=forms.Select(attrs={'class': 'form-select glass-card-input'}), # Apply your theme
        required=True # Or False if category is optional
    )
    # You can customize other fields as well if needed
    title = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control glass-card-input', # You can set class here too
            'placeholder': 'e.g., Introduction to Python' # EXPLICIT PLACEHOLDER
        })
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control glass-card-input', 
            'rows': 5, 
            'placeholder': 'Provide a detailed description of the course...' # EXPLICIT PLACEHOLDER
        })
    )
    
    thumbnail = forms.ImageField(
        widget=forms.ClearableFileInput(attrs={'class': 'form-control glass-card-input'}), # Bootstrap styles this by default
        required=False # Make thumbnail optional
    )

    class Meta:
        model = Course
        fields = ['title', 'category', 'description', 'thumbnail'] 
class ThreadCreateForm(forms.ModelForm):
    initial_post_content = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 10}), # Crispy will use this rows attribute
        label="Your first post",
        help_text="Write the main content for your new thread."
    )
    class Meta:
        model = ForumThread
        fields = ['title', 'initial_post_content']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Enter a clear and descriptive title'}),
        }
        labels = { # Optional: override default labels
            'title': 'Thread Title',
        }
        # Exclude 'instructor' (set automatically in view), 'slug' (auto-generated), 'embedding'