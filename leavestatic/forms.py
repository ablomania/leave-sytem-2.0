from django import forms
from .models import Staff
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm



class LoginForm(forms.Form):
    class Meta:
        model = Staff
    username = forms.EmailField(
        label='Email',
        max_length=150,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'autocomplete': 'email', 'placeholder': 'email'})
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'password'})
    )


# # class LeaveDetailsForm(forms.ModelForm):
# #     class Meta:
# #         model = Leave_Details
# #         fields = ('days_entitled', 'days_eligible', 'days_taken')

# #         widgets = {
# #             'days_entitled': forms.NumberInput(attrs={'class': 'form-control', 'min': 0,}),
# #             'days_eligible': forms.NumberInput(attrs={'class': 'form-control', 'min': 0,}),
# #             'days_taken': forms.NumberInput(attrs={'class': 'form-control', 'min': 0,}),
# #         }

# #     def save(self, commit=True):
# #         leave_details = super().save(commit=False)
# #         if commit:
# #             leave_details.save()
# #         return leave_details


# class StaffForm(UserCreationForm):
#     email = forms.EmailField(required=True)

#     class Meta:
#         model = Staff
#         # Include the email along with username and password fields.
#         fields = ( "first_name", "last_name", "other_names", "phone_number", "email", "sex", "password1", "password2", "department", "type", "position")
#         widgets = {
#             'email': forms.EmailInput(attrs={'class': 'form-row'}),
#             'first_name': forms.TextInput(attrs={'class': 'form-row', 'placeholder': 'first name'}),
#             'last_name': forms.TextInput(attrs={'class': 'form-row', 'placeholder': 'last name'}),
#             'other_names': forms.TextInput(attrs={'class': 'form-row', 'placeholder': 'other names'}),
#             'password1': forms.PasswordInput(attrs={'class': 'form-row', 'placeholder': 'password'}),
#             'password2': forms.PasswordInput(attrs={'class': 'form-row', 'placeholder': 'confirm password'}),
#             'department': forms.Select(attrs={'class': 'form-row'}),
#             'sex': forms.Select(attrs={'class': 'form-row'}),
#             'type': forms.Select(attrs={'class': 'form-row'}),
#             'phone_number': forms.TextInput(attrs={'class': 'form-row', 'placeholder': 'phone number'}),
#             'position': forms.TextInput(attrs={'class': 'form-row'})
#         }

#     def save(self, commit=True):
#         # Call the parent's save() method to create a new user
#         user = super().save(commit=False)
#         user.email = self.cleaned_data["email"]
#         if commit:
#             user.save()
#         return user


# class ForgotPasswordForm(forms.Form):
#     class Meta:
#         model = Staff
#     username = forms.CharField(
#     label='Username',
#     max_length=150,
#     widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'username', 'placeholder': 'username'})
#     )
#     password = forms.CharField(
#         label='New Password',
#         widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New Password'})
#     )
#     password2 = forms.CharField(
#         label='Confirm New Password',
#         widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'})
#     )
     