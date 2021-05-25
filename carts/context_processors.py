from .models import Cart, CartItem
from .views import _cart_id

def counter(request):
	if 'admin' in request.path:
		return {}
	cart_count = 0
	try:
		cart = Cart.objects.get(cart_id=_cart_id(request))
		cart_items = CartItem.objects.filter(cart=cart)
		for cart_item in cart_items:
			cart_count += cart_item.quantity
	except Cart.DoesNotExist:
		cart_count = 0
	return dict(cart_count=cart_count)