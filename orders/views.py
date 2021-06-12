from django.shortcuts import render, redirect
from django.http import JsonResponse
from carts.models import CartItem
from .forms import OrderForm
from .models import Order, Payment, OrderProduct
import datetime
import json
from store.models import Product
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

# Create your views here.
def payments(request):
	body = json.loads(request.body)
	order = Order.objects.get(user=request.user, is_ordered=False, order_number=body['orderId'])

	# store transaction details inside Payment model
	payment = Payment(
		user = request.user,
		payment_id = body.get('transId'),
		payment_method = body.get('payment_method'),
		amount_paid = order.order_total,
		status = body.get('status'),
	)
	payment.save()

	order.payment = payment
	order.is_ordered = True
	order.save()

	# Move the cart items to OrderProduct table
	cart_items = CartItem.objects.filter(user=request.user)

	for item in cart_items:
		orderproduct = OrderProduct()
		orderproduct.order_id = order.id
		orderproduct.payment = payment
		orderproduct.user_id = request.user.id
		orderproduct.product_id = item.product_id
		orderproduct.quantity = item.quantity
		orderproduct.product_price = item.product.price
		orderproduct.ordered = True
		orderproduct.save()

		product_variation = item.variations.all()
		orderproduct = OrderProduct.objects.get(id=orderproduct.id)
		orderproduct.variations.set(product_variation) 
		orderproduct.save()

		# Reduce the quantity by number of sold products
		product = Product.objects.get(id=item.product_id)
		product.stock -= item.quantity
		product.save()

	# clear cart
	cart_items.delete()

	# send order received Email to customer
	mail_subject = 'Thank you for your order'
	message = render_to_string('orders/order_received_email.html', {
		'user': request.user,
		'order': order,
	})
	to_email = request.user.email
	send_email = EmailMessage(mail_subject, message, to=[to_email])
	send_email.send()

	# send order number and transaction id back to sendData method via JSON response
	data = {
		'order_number': order.order_number,
		'transId': payment.payment_id,
	}

	return JsonResponse(data)

def place_order(request, total=0, quantity=0):
	current_user = request.user

	cart_items = CartItem.objects.filter(user=current_user)
	cart_count = cart_items.count()
	if cart_count <= 0:
		return redirect('store')

	grand_total = 0
	tax = 0
	for cart_item in cart_items:
		total += (cart_item.product.price * cart_item.quantity)
		quantity += cart_item.quantity
	tax = (2 * total)/100
	grand_total = total + tax

	if request.method == 'POST':
		form = OrderForm(request.POST)
		if form.is_valid():
			# Store all the billing information into Order table
			data = Order()
			data.user = current_user
			data.first_name = form.cleaned_data.get('first_name')
			data.last_name = form.cleaned_data.get('last_name')
			data.phone = form.cleaned_data.get('phone')
			data.email = form.cleaned_data.get('email')
			data.address_line_1 = form.cleaned_data.get('address_line_1')
			data.address_line_2 = form.cleaned_data.get('address_line_2')
			data.country = form.cleaned_data.get('country')
			data.state = form.cleaned_data.get('state')
			data.city = form.cleaned_data.get('city')
			data.order_note = form.cleaned_data.get('order_note')
			data.order_total = grand_total
			data.tax = tax
			data.ip = request.META.get('REMOTE_ADDR')
			data.save()

			# Generate order number
			yr = int(datetime.date.today().strftime('%Y'))
			mt = int(datetime.date.today().strftime('%m'))
			dt = int(datetime.date.today().strftime('%d'))
			d = datetime.date(yr, mt, dt)
			current_date = d.strftime('%Y%m%d') #20211231
			order_number = current_date + str(data.id)
			data.order_number = order_number
			data.save()

			order = Order.objects.get(user=current_user, order_number=order_number, is_ordered=False)

			context = {
				'order': order,
				'cart_items': cart_items,
				'tax': tax,
				'total': total,
				'grand_total': grand_total,
			}
			return render(request, 'orders/payments.html', context)
	else:
		return redirect('checkout')

def order_complete(request):
	order_number = request.GET.get('order_number')
	transId = request.GET.get('payment_id')

	try:
		order = Order.objects.get(order_number=order_number, is_ordered=True)
		order_products = OrderProduct.objects.filter(order_id=order.id)

		payment = Payment.objects.get(payment_id=transId)

		subtotal = 0
		for item in order_products:
			subtotal += item.product_price * item.quantity

		context = {
			'order': order,
			'order_products': order_products,
			'payment': payment,
			'subtotal': subtotal,
		}
		return render(request, 'orders/order_complete.html', context)
	except (Payment.DoesNotExist, Order.DoesNotExist):
		return redirect('home')

