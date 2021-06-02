from django.shortcuts import render, redirect, get_object_or_404
from store.models import Product, Variation
from .models import Cart, CartItem
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist

from django.contrib.auth.decorators import login_required

# Create your views here.
def _cart_id(request):
	cart_id = request.session.session_key
	if not cart_id:
		cart_id = request.session.create()
	return cart_id

def add_cart(request, product_id):
	current_user = request.user
	product = Product.objects.get(id=product_id)
	
	product_variation = []
	if request.method == 'POST':
		for item in request.POST:
			key = item
			value = request.POST.get(key)

			try:
				variation = Variation.objects.get(product=product,
												  variation_category__iexact=key,
												  variation_value__iexact=value)
				product_variation.append(variation) 
			except:
				pass
	if current_user.is_authenticated:
		does_cart_item_exist = CartItem.objects.filter(product=product, user=current_user).exists()
		if does_cart_item_exist:
			cart_items = CartItem.objects.filter(product=product, user=current_user)

			ex_var_list = []
			cart_item_ids = []
			for item in cart_items:
				existing_variation = item.variations.all()
				ex_var_list.append(list(existing_variation))
				cart_item_ids.append(item.id)

			if product_variation in ex_var_list:
				index = ex_var_list.index(product_variation)
				cart_item = CartItem.objects.get(product=product, id=cart_item_ids[index])
				cart_item.quantity += 1
				cart_item.save()
			else:
				cart_item = CartItem.objects.create(product=product, user=current_user, quantity=1)
				if len(product_variation) > 0:
					cart_item.variations.clear()
					cart_item.variations.add(*product_variation)
				cart_item.save()
		else:
			cart_item = CartItem.objects.create(product=product, user=current_user, quantity=1)
			if len(product_variation) > 0:
				cart_item.variations.clear()
				cart_item.variations.add(*product_variation)
			cart_item.save()
	else:
		try:
			cart = Cart.objects.get(cart_id=_cart_id(request))
		except Cart.DoesNotExist:
			cart = Cart.objects.create(cart_id=_cart_id(request))
			cart.save()

		does_cart_item_exist = CartItem.objects.filter(product=product, cart=cart).exists()
		if does_cart_item_exist:
			cart_items = CartItem.objects.filter(product=product, cart=cart)

			ex_var_list = []
			cart_item_ids = []
			for item in cart_items:
				existing_variation = item.variations.all()
				ex_var_list.append(list(existing_variation))
				cart_item_ids.append(item.id)

			if product_variation in ex_var_list:
				index = ex_var_list.index(product_variation)
				cart_item = CartItem.objects.get(product=product, id=cart_item_ids[index])
				cart_item.quantity += 1
				cart_item.save()
			else:
				cart_item = CartItem.objects.create(product=product, cart=cart, quantity=1)
				if len(product_variation) > 0:
					cart_item.variations.clear()
					cart_item.variations.add(*product_variation)
				cart_item.save()
		else:
			cart_item = CartItem.objects.create(product=product, cart=cart, quantity=1)
			if len(product_variation) > 0:
				cart_item.variations.clear()
				cart_item.variations.add(*product_variation)
			cart_item.save()
	return redirect('cart')

def remove_cart(request, product_id, cart_id):
	# cart = Cart.objects.get(cart_id=_cart_id(request))
	# product = get_object_or_404(Product, id=product_id)
	try:
		cart_item = CartItem.objects.get(id=cart_id)
		if cart_item.quantity > 1:
			cart_item.quantity -= 1
			cart_item.save()
		else:
			cart_item.delete()
	except:
		pass
	return redirect('cart')

def remove_cart_item(request, product_id, cart_id):
	# cart = Cart.objects.get(cart_id=_cart_id(request))
	# product = get_object_or_404(Product, id=product_id)
	cart_item = CartItem.objects.get(id=cart_id)
	cart_item.delete()
	return redirect('cart')


def cart(request, total=0, quantity=0, cart_items=None):

	try:
		tax = 0
		grand_total = 0
		if request.user.is_authenticated:
			cart_items = CartItem.objects.filter(user=request.user, is_active=True)
		else:
			cart = Cart.objects.get(cart_id=_cart_id(request))
			cart_items = CartItem.objects.filter(cart=cart, is_active=True)
		for cart_item in cart_items:
			total += (cart_item.product.price * cart_item.quantity)
			quantity += cart_item.quantity
		tax = (total * 2) / 100
		grand_total = total + tax
	except ObjectDoesNotExist:
		pass

	context = {
		'total': total,
		'quantity': quantity,
		'cart_items': cart_items,
		'tax': tax,
		'grand_total': grand_total,
	}

	return render(request, 'store/cart.html', context)

@login_required(login_url='login')
def checkout(request, total=0, quantity=0, cart_items=None):
	try:
		tax = 0
		grand_total = 0
		if request.user.is_authenticated:
			cart_items = CartItem.objects.filter(user=request.user, is_active=True)
		else:
			cart = Cart.objects.get(cart_id=_cart_id(request))
			cart_items = CartItem.objects.filter(cart=cart, is_active=True)
		for cart_item in cart_items:
			total += (cart_item.product.price * cart_item.quantity)
			quantity += cart_item.quantity
		tax = (total * 2) / 100
		grand_total = total + tax
	except ObjectDoesNotExist:
		pass

	context = {
		'total': total,
		'quantity': quantity,
		'cart_items': cart_items,
		'tax': tax,
		'grand_total': grand_total,
	}
	return render(request, 'store/checkout.html', context)

