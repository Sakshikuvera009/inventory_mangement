from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.password_validation import validate_password

from .models import Customer, Product

User = get_user_model()


class RegisterForm(UserCreationForm):
    """Public sign-up. Always creates a Sales User - never an admin."""

    first_name = forms.CharField(max_length=150, label="First name")
    last_name = forms.CharField(max_length=150, required=False, label="Last name")
    email = forms.EmailField(max_length=254, label="Email address")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("first_name", "last_name", "username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].widget.attrs.update(autocomplete="given-name", placeholder="Aarav")
        self.fields["last_name"].widget.attrs.update(autocomplete="family-name", placeholder="Sharma")
        self.fields["username"].widget.attrs.update(autocomplete="username", placeholder="Choose a username")
        self.fields["username"].help_text = "Letters, digits and @/./+/-/_ only."
        self.fields["email"].widget.attrs.update(autocomplete="email", placeholder="you@company.com")
        self.fields["password1"].widget.attrs.update(autocomplete="new-password", placeholder="Create a password")
        self.fields["password2"].widget.attrs.update(autocomplete="new-password", placeholder="Repeat your password")
        self.fields["password1"].help_text = "At least 8 characters, not too common or similar to your name."
        self.fields["password2"].help_text = ""

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.SALES
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
        return user


class PanelUserForm(forms.ModelForm):
    password = forms.CharField(
        required=False, strip=False, label="Password",
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "role", "is_active"]

    field_order = ["first_name", "last_name", "username", "email", "role", "password", "is_active"]

    def __init__(self, *args, editing_self=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_new = self.instance.pk is None
        self.editing_self = editing_self
        self.fields["email"].required = True
        self.fields["password"].required = self.is_new
        self.fields["password"].help_text = (
            "Set an initial password for this user." if self.is_new
            else "Leave blank to keep the current password."
        )
        if editing_self:
            # An admin must not lock themselves out from the panel.
            for name in ("role", "is_active"):
                self.fields[name].disabled = True
                self.fields[name].help_text = "You cannot change this on your own account."

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        qs = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Another user already uses this email.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            validate_password(password, self.instance)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["name", "email", "mobile", "city", "is_active"]


class ProductForm(forms.ModelForm):
    opening_stock = forms.IntegerField(
        min_value=0, initial=0, required=False, label="Opening stock",
        help_text="Starting quantity. Later changes are made with Adjust stock so every movement is recorded.",
    )

    class Meta:
        model = Product
        fields = ["product_code", "name", "category", "price", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            del self.fields["opening_stock"]
            self.fields["product_code"].disabled = True
            self.fields["product_code"].help_text = "Product code cannot be changed."


class StockAdjustForm(forms.Form):
    quantity_change = forms.IntegerField(
        label="Quantity change",
        help_text="Use a positive number to add stock and a negative number to remove it.",
    )
    reason = forms.CharField(max_length=255, label="Reason")

    def clean_quantity_change(self):
        value = self.cleaned_data["quantity_change"]
        if value == 0:
            raise forms.ValidationError("Adjustment cannot be zero.")
        return value
