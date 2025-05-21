# users/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm # UserChangeForm for profile updates
from .models import CustomUser, Profile # Use CustomUser
from courses.models import CourseCategory
class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    last_name = forms.CharField(max_length=150, required=False, help_text='Optional.')

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        
        fields = ('first_name', 'last_name','email', )


class CustomUserChangeForm(UserChangeForm): # For admin or if users can change their email
    class Meta(UserChangeForm.Meta):
        model = CustomUser
        fields = ('email', 'first_name', 'last_name', 'is_active', 'is_staff') # Customize as needed

# Profile Update Form (if separate for bio, picture - no change needed here if it links to Profile)
class CustomUserUpdateForm(forms.ModelForm): # Or use your CustomUserChangeForm if appropriate
    class Meta:
        model = CustomUser # Make sure this is your custom user model
        fields = ['first_name', 'last_name', 'email'] # Email likely readonly

class ProfileUpdateForm(forms.ModelForm):
    preferred_categories = forms.ModelMultipleChoiceField(
        queryset=CourseCategory.objects.all().order_by('name'),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="My Learning Interests (Categories)"
    )
    class Meta:
        model = Profile
        fields = ['bio', 'profile_picture', 'preferred_categories']
from django.contrib.auth.forms import AuthenticationForm

class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(widget=forms.EmailInput(attrs={'autofocus': True, 'placeholder': 'Email'}))
    # The field is still called 'username' internally by AuthenticationForm,
    # but we make it an EmailField and change its label/placeholder.
class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['email', 'first_name', 'last_name']