from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required
from .forms import RegistrationForm, UserForm, UserProfileForm
from .models import Account, UserProfile
from orders.models import Order, OrderProduct
from carts.models import Cart, CartItem
from carts.views import _cart_id
import requests

# Verification email
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage
from django.http import HttpResponse

# Create your views here.
def register(request):
	if request.method == 'POST':
		form = RegistrationForm(request.POST)
		if form.is_valid():
			first_name = form.cleaned_data['first_name']
			last_name = form.cleaned_data['last_name']
			email = form.cleaned_data['email']
			phone_number = form.cleaned_data['phone_number']
			password = form.cleaned_data['password']

			username = email.split('@')[0]
			user = Account.objects.create_user(first_name=first_name, last_name=last_name,
							   				   username=username, email=email, password=password)
			user.phone_number = phone_number
			user.save()

			# USER ACTIVATION
			current_site = get_current_site(request)
			mail_subject = 'TheKart - Activation Link'
			message = render_to_string('accounts/account_verification_email.html', {
				'user': user,
				'domain': current_site,
				'uid': urlsafe_base64_encode(force_bytes(user.pk)),
				'token': default_token_generator.make_token(user),
			})
			to_email = email
			send_email = EmailMessage(mail_subject, message, to=[to_email])
			send_email.send()

			return redirect('/accounts/register/?command=verification&email='+email)
	else:
		form = RegistrationForm()
	context = {
		'form': form,
	}
	return render(request, 'accounts/register.html', context)

def login(request):
	if request.method == 'POST':
		email = request.POST['email']
		password = request.POST['password']

		user = auth.authenticate(email=email, password=password)
		if user:
			try:
				cart = Cart.objects.get(cart_id=_cart_id(request))
				does_cart_item_exist = CartItem.objects.filter(cart=cart).exists()

				if does_cart_item_exist:
					cart_items = CartItem.objects.filter(cart=cart)
					product_variations = []

					# getting the product variation by cart id
					ids = []
					for cart_item in cart_items:
						variation = cart_item.variations.all()
						product_variations.append(list(variation))
						ids.append(cart_item.id)

					# getting the cart items from the user to access his product variations
					cart_items = CartItem.objects.filter(user=user)
					existing_product_variaions = []
					ex_ids = []
					for item in cart_items:
						variation = item.variations.all()
						existing_product_variaions.append(list(variation))
						ex_ids.append(item.id)

					for index_, product_variation in enumerate(product_variations):
						if product_variation in existing_product_variaions:
							index = existing_product_variaions.index(product_variation)
							item_id = ex_ids[index]
							item = CartItem.objects.get(id=item_id)
							pr_item = CartItem.objects.get(id=ids[index_])
							item.quantity += pr_item.quantity
							item.user = user
							item.save()
						else:
							cart_item = CartItem.objects.get(id=ids[index_])
							cart_item.user = user
							cart_item.save()
			except:
				pass
			auth.login(request, user)
			messages.success(request, 'You are logged in.')
			url = request.META.get('HTTP_REFERER')
			try:
				query = requests.utils.urlparse(url).query
				params = dict(x.split('=') for x in query.split('&'))
				if 'next' in params:
					next_page = params.get('next')
					return redirect(next_page)
			except:		
				return redirect('dashboard')
		else:
			messages.error(request, 'Invalid login credentials')
			return redirect('login')

	return render(request, 'accounts/login.html')

@login_required(login_url='login')
def logout(request):
	auth.logout(request)
	messages.success(request, 'You are logged out.')
	return redirect(login)

def activate(request, uidb64, token):
	try:
		uid = urlsafe_base64_decode(uidb64).decode()
		user = Account.objects.get(pk=uid)
	except(TypeError, ValueError, OverflowError, Account.DoesNotExist):
		user = None

	if user and default_token_generator.check_token(user, token):
		user.is_active = True
		user.save()
		messages.success(request, 'Congratulations! Your account successfully activated.')
		return redirect('login')
	else:
		messages.error(request, 'Invalid activation link')
		return redirect('register')

@login_required(login_url='login')
def dashboard(request):
	orders = Order.objects.order_by('-created_at').filter(user=request.user, is_ordered=True)
	orders_count = orders.count()
	user_profile = UserProfile.objects.get(user=request.user)
	context = {
		'orders_count': orders_count,
		'user_profile': user_profile,
	}
	return render(request, 'accounts/dashboard.html', context)

def forgot_password(request):
	if request.method == 'POST':
		email = request.POST['email']
		if Account.objects.filter(email__exact=email).exists():
			user = Account.objects.get(email__exact=email)

			# RESET PASSWORD
			current_site = get_current_site(request)
			mail_subject = 'TheKart - Reset Password Link'
			message = render_to_string('accounts/reset_password_email.html', {
				'user': user,
				'domain': current_site,
				'uid': urlsafe_base64_encode(force_bytes(user.pk)),
				'token': default_token_generator.make_token(user),
			})
			to_email = email
			send_email = EmailMessage(mail_subject, message, to=[to_email])
			send_email.send()

			messages.info(request, 'Password reset link sent to your email address')
			return redirect('login')
		else:
			messages.error(request, 'Account does not exist.')
			return redirect('forgot_password')
	return render(request, 'accounts/forgot_password.html')

def resetpassword_validate(request, uidb64, token):
	try:
		uid = urlsafe_base64_decode(uidb64).decode()
		user = Account.objects.get(pk=uid)
	except(TypeError, ValueError, OverflowError, Account.DoesNotExist):
		user = None

	if user and default_token_generator.check_token(user, token):
		request.session['uid'] = uid
		messages.success(request, 'You can reset your password from here.')
		return redirect('reset_password')
	else:
		messages.error(request, 'Link has been expired')
		return redirect('login')

def reset_password(request):
	if request.method == 'POST':
		try:
			uid = request.session.get('uid')
			user = Account.objects.get(pk=uid)
		except(TypeError, ValueError, OverflowError, Account.DoesNotExist):
			user = None
		if user:
			password = request.POST['password']
			confirm_password = request.POST['confirm_password']
			if password == confirm_password:
				user.set_password(password)
				user.save()
				messages.success(request, 'Password reset successful.')
				return redirect('login')
			else:
				messages.error(request, 'Password do not match.')
				return redirect('reset_password')
		else:
			messages.error(request, 'Please go through [Forgot Password?] link.')
			return redirect('login')
		
	return render(request, 'accounts/reset_password.html')

@login_required(login_url='login')
def my_orders(request):
	orders = Order.objects.filter(user=request.user, is_ordered=True).order_by('-created_at')
	context = {
		'orders': orders,
	}
	return render(request, 'accounts/my_orders.html', context)

@login_required(login_url='login')
def edit_profile(request):
	user_profile = get_object_or_404(UserProfile, user=request.user)
	if request.method == "POST":
		user_form = UserForm(request.POST, instance=request.user)
		user_profile_form = UserProfileForm(request.POST, request.FILES, instance=user_profile)
		if user_form.is_valid() and user_profile_form.is_valid():
			user_form.save()
			user_profile_form.save()
			messages.success(request, 'Your profile has been updated.')
			return redirect('edit_profile')
	else:
		user_form = UserForm(instance=request.user)
		user_profile_form = UserProfileForm(instance=user_profile)
	
	context = {
		'user_form': user_form,
		'user_profile_form': user_profile_form,
		'user_profile': user_profile,
	}

	return render(request, 'accounts/edit_profile.html', context)


@login_required(login_url='login')
def change_password(request):
	if request.method == 'POST':
		current_password = request.POST.get('current_password')
		new_password = request.POST.get('new_password')
		confirm_password = request.POST.get('confirm_password')

		user = request.user
		if new_password == confirm_password:
			success = user.check_password(current_password)
			if success:
				user.set_password(new_password)
				user.save()
				messages.success(request, 'Your password has been updated successfully.')
			else:
				messages.error(request, 'You entered wrong current password')
		else:
			messages.error(request, 'New password and Confirm password are not same.')
		return redirect('change_password')

	return render(request, 'accounts/change_password.html')

@login_required(login_url='login')
def order_detail(request, order_id):
	order_detail = OrderProduct.objects.filter(order__order_number=order_id)
	order = Order.objects.get(order_number=order_id)
	subtotal = 0
	for item in order_detail:
		subtotal += item.order_product_total()
	context = {
		'order_detail': order_detail,
		'order': order,
		'subtotal': subtotal,
	}
	return render(request, 'accounts/order_detail.html', context)

	