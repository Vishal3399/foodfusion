from django.http import HttpResponse
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
import razorpay

from .models import Customer, Item, Restaurant, Cart


# Create your views here.
def index(request):
    return render(request, "delivery/index.html")


def open_signup(request):
    return render(request, "delivery/signup.html")


def open_login(request):
    return render(request, "delivery/login.html")


def signup(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        email = request.POST.get("email")
        mobile = request.POST.get("mobile")
        address = request.POST.get("address")

        try:
            Customer.objects.get(username=username)
            return HttpResponse("Already Exists")
        except Customer.DoesNotExist:
            Customer.objects.create(
                username=username,
                password=password,
                email=email,
                mobile=mobile,
                address=address,
            )
    return render(request, "delivery/signup.html")


def login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        try:
            Customer.objects.get(username=username, password=password)
            restaurant_list = Restaurant.objects.all()
            if username == "admin":
                context = {
                    "restaurant_count": restaurant_list.count(),
                    "item_count": Item.objects.count(),
                }
                return render(request, "delivery/admin_home.html", context)
            return render(
                request,
                "delivery/customer_home.html",
                {"username": username, "restaurantList": restaurant_list},
            )
        except Customer.DoesNotExist:
            return HttpResponse("Registration failed")

    return render(request, "delivery/login.html")


def open_add_restaurant(request):
    return render(request, "delivery/add_restaurant.html")


def add_restaurant(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        picture = request.POST.get('picture')
        cuisine = request.POST.get('cuisine')
        rating = request.POST.get('rating')

        try:
            Restaurant.objects.get(name=name)
            return HttpResponse("Duplicate restaurant!")
        except Restaurant.DoesNotExist:
            Restaurant.objects.create(
                name=name,
                picture=picture,
                cuisine=cuisine,
                rating=rating,
            )
    return render(request, 'delivery/admin_home.html', {
        'restaurant_count': Restaurant.objects.count(),
        'item_count': Item.objects.count(),
    })


def open_show_restaurant(request):
    restaurants = Restaurant.objects.all()
    return render(request, 'delivery/show_restaurants.html', {'restaurantList': restaurants})


def open_update_restaurant(request, restaurant_id):
    restaurant = Restaurant.objects.get(id=restaurant_id)
    return render(request, 'delivery/update_restaurant.html', {'restaurant': restaurant})


def update_restaurant(request, restaurant_id):
    restaurant = Restaurant.objects.get(id=restaurant_id)
    if request.method == 'POST':
        name = request.POST.get('name')
        picture = request.POST.get('picture')
        cuisine = request.POST.get('cuisine')
        rating = request.POST.get('rating')

        restaurant.name = name
        restaurant.picture = picture
        restaurant.cuisine = cuisine
        restaurant.rating = rating

        restaurant.save()

    restaurant_list = Restaurant.objects.all()
    return render(request, 'delivery/show_restaurants.html', {"restaurantList": restaurant_list})


def delete_restaurant(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    restaurant.delete()

    return redirect('open_show_restaurant')


def view_menu(request, restaurant_id, username=None):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    item_list = restaurant.items.all()
    return render(
        request,
        'delivery/view_menu.html',
        {'restaurant': restaurant, 'itemList': item_list, 'username': username},
    )


def open_update_menu(request, restaurant_id):
    restaurant = Restaurant.objects.get(id=restaurant_id)
    item_list = restaurant.items.all()
    return render(request, 'delivery/update_menu.html', {'itemList': item_list, 'restaurant': restaurant})


def update_menu(request, restaurant_id):
    restaurant = Restaurant.objects.get(id=restaurant_id)

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        vegeterian = request.POST.get('vegeterian') == 'on'
        picture = request.POST.get('picture')

        try:
            Item.objects.get(name=name)
            return HttpResponse("Duplicate item!")
        except Item.DoesNotExist:
            Item.objects.create(
                restaurant=restaurant,
                name=name,
                description=description,
                price=price,
                vegeterian=vegeterian,
                picture=picture,
            )
    return render(request, 'delivery/admin_home.html', {
        'restaurant_count': Restaurant.objects.count(),
        'item_count': Item.objects.count(),
    })
    
def view_menu(request, restaurant_id, username):
    restaurant = Restaurant.objects.get(id = restaurant_id)
    itemList = restaurant.items.all()
    #itemList = Item.objects.all()
    return render(request, 'delivery/customer_menu.html'
                  ,{"itemList" : itemList,
                     "restaurant" : restaurant, 
                     "username":username})
    
    
    
def add_to_cart(request, item_id, username):
    item = Item.objects.get(id=item_id)
    customer = Customer.objects.get(username=username)

    cart, created = Cart.objects.get_or_create(customer=customer)

    cart.items.add(item)

    return redirect(
        'view_menu',
        restaurant_id=item.restaurant.id,
        username=username
    )

def show_cart(request, username):
    customer = Customer.objects.get(username = username)
    cart = Cart.objects.filter(customer=customer).first()
    items = cart.items.all() if cart else []
    total_price = cart.total_price() if cart else 0

    return render(request, 'delivery/cart.html',{"itemList" : items, "total_price" : total_price, "username":username})




def checkout(request, username):
    # Fetch customer and their cart
    customer = get_object_or_404(Customer, username=username)
    cart = Cart.objects.filter(customer=customer).first()
    cart_items = cart.items.all() if cart else []
    total_price = cart.total_price() if cart else 0

    if total_price == 0:
        return render(request, 'delivery/checkout.html', {
            'error': 'Your cart is empty!',
            'username': username,
        })

    # Initialize Razorpay client
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    # Create Razorpay order
    order_data = {
        'amount': int(total_price * 100),  # Amount in paisa
        'currency': 'INR',
        'payment_capture': '1',  # Automatically capture payment
    }
    order = client.order.create(data=order_data)

    # Pass the order details to the frontend
    return render(request, 'delivery/checkout.html', {
        'username': username,
        'cart_items': cart_items,
        'total_price': total_price,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'order_id': order['id'],  # Razorpay order ID
        'amount': total_price,
    })
    
    

def orders(request, username):
    customer = get_object_or_404(Customer, username=username)
    cart = Cart.objects.filter(customer=customer).first()

    # Fetch cart items and total price before clearing the cart
    cart_items = cart.items.all() if cart else []
    total_price = cart.total_price() if cart else 0

    # Clear the cart after fetching its details
    if cart:
        cart.items.clear()

    return render(request, 'delivery/orders.html', {
        'username': username,
        'customer': customer,
        'cart_items': cart_items,
        'total_price': total_price,
    })
    
    