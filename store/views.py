from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, ReviewRating
from .forms import ReviewRatingForm
from category.models import Category
from carts.models import CartItem
from orders.models import OrderProduct
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from carts.views import _cart_id
from django.db.models import Q
from django.http import HttpResponse
from django.contrib import messages

# Create your views here.
def store(request, category_slug=None):

	categories = None
	products = None

	if category_slug:
		categories = get_object_or_404(Category, slug=category_slug)
		products = Product.objects.filter(category=categories, is_available=True).order_by('id')
	else:
		products = Product.objects.all().filter(is_available=True).order_by('id')
	paginator = Paginator(products, 6)
	page = request.GET.get('page')
	paged_products = paginator.get_page(page)
	product_count = products.count()

	context = {
		'products': paged_products,
		'product_count': product_count,
	}

	return render(request, 'store/store.html', context)

def product_detail(request, category_slug, product_slug):

	try:
		single_product = Product.objects.get(category__slug=category_slug,
											 slug=product_slug)
		in_cart = CartItem.objects.filter(cart__cart_id=_cart_id(request),
											product=single_product).exists()
	except Exception as e:
		raise e

	if request.user.is_authenticated:
		try:
			order_product = OrderProduct.objects.filter(user=request.user, product_id=single_product.id).exists()
		except OrderProduct.DoesNotExist:
			order_product = None
	else:
		order_product = None

	reviews = ReviewRating.objects.filter(product_id=single_product.id)

	context = {
		'single_product': single_product,
		'in_cart': in_cart,
		'order_product': order_product,
		'reviews': reviews,
	}

	return render(request, 'store/product_detail.html', context)

def search(request):
	keyword = request.GET.get('keyword')
	if keyword:
		products = Product.objects.order_by('-created_date').filter(Q(description__icontains=keyword) | Q(product_name__icontains=keyword))
		product_count = products.count()
	context = {
		'products': products,
		'product_count': product_count,
	}
	return render(request, 'store/store.html', context)

def submit_review(request, product_id):
	url = request.META.get('HTTP_REFERER')
	if request.method == "POST":
		try:
			review = ReviewRating.objects.get(user=request.user, product_id=product_id)
			form = ReviewRatingForm(request.POST, instance=review)
			form.save()
			messages.success(request, 'Your review has been updated!')
			return redirect(url)
		except ReviewRating.DoesNotExist:
			form = ReviewRatingForm(request.POST)
			if form.is_valid():
				data = ReviewRating()
				data.subject = form.cleaned_data.get('subject')
				data.review = form.cleaned_data.get('review')
				data.rating = form.cleaned_data.get('rating')
				data.ip = request.META.get('REMOTE_ADDR')
				data.user_id = request.user.id
				data.product_id = product_id
				data.save()
				messages.success(request, 'Your review has been submitted!')
				return redirect(url)



